# -*- coding: utf-8 -*-
"""
Length Tuner - 长度调谐器

Phase 9: 差分对布线 + 阻抗控制

功能:
1. 蛇形走线 (Serpentine) - 在短线段上添加蛇形弯曲以增加长度
2. 锯齿走线 (Sawtooth) - 添加锯齿形弯曲
3. 最小弯曲半径验证
4. 差分对长度匹配

蛇形弯曲模式:
  在直线段上插入 U 形弯曲, 每个弯曲增加的长度为 2 * amplitude。
  弯曲间距为 pitch, 弯曲仅插入在直线段上, 不在拐角上。

Author: Claude Code
Date: 2026-03-31
"""

import math
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional

from .astar_router import Point

logger = logging.getLogger(__name__)


# ========== Data Classes ==========


@dataclass
class TuningResult:
    """长度调谐结果"""

    tuned_points: List[Point]  # 调谐后的走线点列表
    original_length: float  # 原始长度 (mm)
    tuned_length: float  # 调谐后长度 (mm)
    added_length: float  # 增加的长度 (mm)
    bend_count: int  # 添加的弯曲数量


# ========== Length Tuner ==========


class LengthTuner:
    """
    长度调谐器

    通过在走线中添加蛇形/锯齿弯曲来匹配目标长度。
    主要用于差分对的长度匹配, 使正端和负端走线长度一致。

    使用方式:
        tuner = LengthTuner()
        result = tuner.tune(shorter_points, target_length=target)

    弯曲参数:
    - amplitude: 弯曲幅度 (mm), 即蛇形的高度
    - pitch: 弯曲间距 (mm), 即相邻弯曲之间的距离
    - min_bend_radius: 最小弯曲半径 (mm)
    """

    def tune(
        self,
        trace_points: List[Point],
        target_length: float,
        style: str = "serpentine",
        amplitude: float = 2.0,
        pitch: float = 1.0,
        min_bend_radius: float = 0.5,
    ) -> TuningResult:
        """
        对走线进行长度调谐

        在较短的走线上添加弯曲, 使其长度匹配目标长度。

        Args:
            trace_points: 待调谐的走线点列表
            target_length: 目标长度 (mm)
            style: 弯曲样式 ("serpentine" 或 "sawtooth")
            amplitude: 弯曲幅度 (mm)
            pitch: 弯曲间距 (mm)
            min_bend_radius: 最小弯曲半径 (mm)

        Returns:
            TuningResult: 调谐结果
        """
        if len(trace_points) < 2:
            logger.warning("长度调谐: 走线点数不足")
            return TuningResult(
                tuned_points=list(trace_points),
                original_length=0,
                tuned_length=0,
                added_length=0,
                bend_count=0,
            )

        current_length = self._calculate_current_length(trace_points)
        needed = self._calculate_needed_lengthening(current_length, target_length)

        if needed <= 0:
            logger.info(
                f"长度调谐: 无需调谐, 当前长度={current_length:.3f}mm, "
                f"目标={target_length:.3f}mm"
            )
            return TuningResult(
                tuned_points=list(trace_points),
                original_length=round(current_length, 3),
                tuned_length=round(current_length, 3),
                added_length=0,
                bend_count=0,
            )

        logger.info(
            f"长度调谐: 当前={current_length:.3f}mm, "
            f"目标={target_length:.3f}mm, 需增加={needed:.3f}mm, "
            f"样式={style}, 幅度={amplitude}mm, 间距={pitch}mm"
        )

        # 确保幅度和间距合理
        amplitude = max(amplitude, min_bend_radius * 2)
        pitch = max(pitch, amplitude * 0.5)

        # 计算需要多少个弯曲
        # 每个弯曲增加的长度 ≈ 2 * amplitude (U 形来回)
        length_per_bend = 2 * amplitude
        required_bends = math.ceil(needed / length_per_bend)

        # 找到适合插入弯曲的直线段
        straight_segments = self._find_straight_segments(trace_points)

        if not straight_segments:
            logger.warning("长度调谐: 未找到适合插入弯曲的直线段")
            return TuningResult(
                tuned_points=list(trace_points),
                original_length=round(current_length, 3),
                tuned_length=round(current_length, 3),
                added_length=0,
                bend_count=0,
            )

        # 在直线段上插入弯曲
        tuned_points = list(trace_points)
        bends_added = 0
        added_length_total = 0.0

        # 选择最长的直线段来插入弯曲
        straight_segments.sort(key=lambda s: s[1], reverse=True)

        for seg_idx, seg_length, insert_index in straight_segments:
            if bends_added >= required_bends:
                break

            # 检查段长度是否足够容纳弯曲
            min_segment_for_bend = amplitude * 2 + pitch
            if seg_length < min_segment_for_bend:
                continue

            if style == "serpentine":
                new_points = self._add_serpentine_bend(
                    tuned_points, insert_index, amplitude, pitch
                )
            else:
                new_points = self._add_sawtooth_bend(
                    tuned_points, insert_index, amplitude, pitch
                )

            if new_points:
                tuned_points = new_points
                bends_added += 1
                added_length_total += length_per_bend

        # 验证弯曲半径
        valid = self._validate_bend_radius(tuned_points, min_bend_radius)
        if not valid:
            logger.warning("长度调谐: 部分弯曲半径小于最小值, 可能需要增大 amplitude")

        new_length = self._calculate_current_length(tuned_points)

        result = TuningResult(
            tuned_points=tuned_points,
            original_length=round(current_length, 3),
            tuned_length=round(new_length, 3),
            added_length=round(new_length - current_length, 3),
            bend_count=bends_added,
        )

        logger.info(
            f"长度调谐完成: 原始={current_length:.3f}mm, "
            f"调谐后={new_length:.3f}mm, "
            f"增加={new_length - current_length:.3f}mm, "
            f"弯曲数={bends_added}"
        )
        return result

    def _calculate_current_length(self, points: List[Point]) -> float:
        """
        计算走线的当前总长度

        Args:
            points: 走线点列表

        Returns:
            float: 总长度 (mm)
        """
        total = 0.0
        for i in range(len(points) - 1):
            total += points[i].distance_to(points[i + 1])
        return total

    def _calculate_needed_lengthening(
        self, current: float, target: float
    ) -> float:
        """
        计算需要增加的长度

        Args:
            current: 当前长度 (mm)
            target: 目标长度 (mm)

        Returns:
            float: 需要增加的长度 (mm), 如果当前已足够则返回 0
        """
        if current >= target:
            return 0.0
        return target - current

    def _find_straight_segments(
        self, points: List[Point]
    ) -> List[Tuple[int, float, int]]:
        """
        找到走线中的直线段

        在走线上寻找方向不变的连续线段, 这些线段适合插入蛇形弯曲。

        Args:
            points: 走线点列表

        Returns:
            List of (segment_index, segment_length, insert_point_index):
              - segment_index: 走线线段的索引
              - segment_length: 线段长度
              - insert_point_index: 插入弯曲的起始点索引
        """
        segments = []

        for i in range(len(points) - 1):
            seg_len = points[i].distance_to(points[i + 1])
            if seg_len > 0.5:  # 忽略过短的段
                segments.append((i, seg_len, i + 1))

        return segments

    def _add_serpentine_bend(
        self,
        points: List[Point],
        insert_index: int,
        amplitude: float,
        pitch: float,
    ) -> Optional[List[Point]]:
        """
        在指定位置添加蛇形弯曲

        蛇形弯曲形状:
              ___
             |   |
        _____|   |_____
             ^ pitch

        在 insert_index 之前的线段中间插入一个 U 形弯曲。

        Args:
            points: 当前走线点列表
            insert_index: 插入位置的索引 (在此点之前的线段)
            amplitude: 弯曲幅度 (mm)
            pitch: 弯曲间距 (mm)

        Returns:
            List[Point]: 新的点列表, 如果无法插入则返回 None
        """
        if insert_index < 1 or insert_index >= len(points):
            return None

        p_before = points[insert_index - 1]
        p_after = points[insert_index]

        # 计算线段方向
        dx = p_after.x - p_before.x
        dy = p_after.y - p_before.y
        seg_len = math.sqrt(dx * dx + dy * dy)

        if seg_len < amplitude * 2 + pitch:
            return None

        # 单位方向向量
        ux = dx / seg_len
        uy = dy / seg_len

        # 法向量 (垂直于线段方向)
        nx = -uy
        ny = ux

        # 插入点在线段中间
        mid_x = (p_before.x + p_after.x) / 2
        mid_y = (p_before.y + p_after.y) / 2

        # 蛇形弯曲的 5 个点
        half_pitch = pitch / 2

        # 弯曲起点 (线段中点后退 half_pitch)
        bend_start = Point(
            mid_x - ux * half_pitch,
            mid_y - uy * half_pitch,
        )

        # 弯曲顶点1 (沿法线方向偏移 amplitude)
        bend_top = Point(
            bend_start.x + nx * amplitude,
            bend_start.y + ny * amplitude,
        )

        # 弯曲远端 (沿方向前进 pitch)
        bend_far = Point(
            bend_start.x + ux * pitch,
            bend_start.y + uy * pitch,
        )

        # 弯曲底点 (回到线段)
        bend_bottom = Point(
            bend_far.x + nx * amplitude,
            bend_far.y + ny * amplitude,
        )

        # 弯曲终点 (回到线段方向)
        bend_end = Point(
            mid_x + ux * half_pitch,
            mid_y + uy * half_pitch,
        )

        # 构建新的点列表
        new_points = (
            list(points[:insert_index])
            + [bend_start, bend_top, bend_far, bend_bottom, bend_end]
            + list(points[insert_index:])
        )

        return new_points

    def _add_sawtooth_bend(
        self,
        points: List[Point],
        insert_index: int,
        amplitude: float,
        pitch: float,
    ) -> Optional[List[Point]]:
        """
        在指定位置添加锯齿形弯曲

        锯齿弯曲形状:
              /|
             / |
        ____/  |_____
                ^ pitch

        Args:
            points: 当前走线点列表
            insert_index: 插入位置的索引
            amplitude: 弯曲幅度 (mm)
            pitch: 弯曲间距 (mm)

        Returns:
            List[Point]: 新的点列表, 如果无法插入则返回 None
        """
        if insert_index < 1 or insert_index >= len(points):
            return None

        p_before = points[insert_index - 1]
        p_after = points[insert_index]

        # 计算线段方向
        dx = p_after.x - p_before.x
        dy = p_after.y - p_before.y
        seg_len = math.sqrt(dx * dx + dy * dy)

        if seg_len < amplitude * 2 + pitch:
            return None

        # 单位方向向量
        ux = dx / seg_len
        uy = dy / seg_len

        # 法向量
        nx = -uy
        ny = ux

        # 线段中点
        mid_x = (p_before.x + p_after.x) / 2
        mid_y = (p_before.y + p_after.y) / 2

        # 锯齿弯曲的 3 个点
        half_pitch = pitch / 2

        # 锯齿上升点
        tooth_start = Point(
            mid_x - ux * half_pitch,
            mid_y - uy * half_pitch,
        )

        # 锯齿顶点
        tooth_peak = Point(
            mid_x + nx * amplitude,
            mid_y + ny * amplitude,
        )

        # 锯齿下降回到线段
        tooth_end = Point(
            mid_x + ux * half_pitch,
            mid_y + uy * half_pitch,
        )

        # 构建新的点列表
        new_points = (
            list(points[:insert_index])
            + [tooth_start, tooth_peak, tooth_end]
            + list(points[insert_index:])
        )

        return new_points

    def _validate_bend_radius(
        self, points: List[Point], min_radius: float
    ) -> bool:
        """
        验证所有弯曲是否满足最小弯曲半径要求

        检查每三个连续点形成的弯曲, 计算等效弯曲半径:
          R = d / (2 * sin(theta/2))
        其中 d 是点间距, theta 是转角。

        Args:
            points: 走线点列表
            min_radius: 最小弯曲半径 (mm)

        Returns:
            bool: 是否所有弯曲都满足要求
        """
        if len(points) < 3:
            return True

        all_valid = True

        for i in range(1, len(points) - 1):
            p_prev = points[i - 1]
            p_curr = points[i]
            p_next = points[i + 1]

            # 两个向量
            v1x = p_curr.x - p_prev.x
            v1y = p_curr.y - p_prev.y
            v2x = p_next.x - p_curr.x
            v2y = p_next.y - p_curr.y

            len1 = math.sqrt(v1x * v1x + v1y * v1y)
            len2 = math.sqrt(v2x * v2x + v2y * v2y)

            if len1 < 1e-10 or len2 < 1e-10:
                continue

            # 计算转角
            cos_theta = (v1x * v2x + v1y * v2y) / (len1 * len2)
            cos_theta = max(-1, min(1, cos_theta))

            # 如果接近直线 (cos_theta 接近 1), 跳过
            if cos_theta > 0.999:
                continue

            sin_half_theta = math.sqrt((1 - cos_theta) / 2)

            if sin_half_theta < 1e-10:
                continue

            # 等效弯曲半径
            d = min(len1, len2)
            radius = d / (2 * sin_half_theta)

            if radius < min_radius:
                logger.debug(
                    f"弯曲半径不足: 索引={i}, 半径={radius:.3f}mm < {min_radius}mm"
                )
                all_valid = False

        return all_valid


def create_length_tuner() -> LengthTuner:
    """
    创建长度调谐器实例

    Returns:
        LengthTuner 实例
    """
    return LengthTuner()
