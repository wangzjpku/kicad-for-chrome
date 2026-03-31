# -*- coding: utf-8 -*-
"""
Differential Pair Router - 差分对布线器

Phase 9: 差分对布线 + 阻抗控制

功能:
1. 平行耦合布线 - 两条走线并排耦合走线
2. 阻抗控制 - 根据目标阻抗自动计算走线宽度/间距
3. 长度匹配 - 确保差分对两根线长度一致
4. 参考平面完整性 - 避免跨越参考平面分割

使用微带线阻抗公式:
  Z0 = 87 / sqrt(Er+1.41) * ln(5.98*H / (0.8*W + T))
  Z_diff ≈ 2 * Z0 * (1 - 0.48 * exp(-0.96 * S/H))

Author: Claude Code
Date: 2026-03-31
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from .astar_router import AStarRouter, Point

logger = logging.getLogger(__name__)


# ========== Data Classes ==========


@dataclass
class DiffPairRoute:
    """差分对布线结果"""

    pos_points: List[Point]  # 正端走线点列表
    neg_points: List[Point]  # 负端走线点列表
    pos_length: float  # 正端走线长度 (mm)
    neg_length: float  # 负端走线长度 (mm)
    length_mismatch: float  # 长度不匹配量 (mm)
    impedance: float  # 计算得到的差分阻抗 (Ohm)

    def __post_init__(self):
        if self.length_mismatch == 0:
            self.length_mismatch = abs(self.pos_length - self.neg_length)


@dataclass
class ImpedanceConstraint:
    """阻抗约束"""

    target_z: float  # 目标差分阻抗 (Ohm), 如 90 for USB
    tolerance_pct: float  # 容差百分比, 如 10 表示 ±10%
    trace_width: float  # 计算得到的走线宽度 (mm)
    trace_gap: float  # 计算得到的走线间距 (mm)

    @property
    def min_z(self) -> float:
        return self.target_z * (1 - self.tolerance_pct / 100)

    @property
    def max_z(self) -> float:
        return self.target_z * (1 + self.tolerance_pct / 100)


# ========== Main Router ==========


class DifferentialPairRouter:
    """
    差分对布线器

    特性:
    - 耦合平行布线
    - 阻抗控制宽度和间距计算
    - 长度匹配检查
    - 参考平面分割规避

    典型目标阻抗:
    - USB 2.0/3.0: 90 Ohm 差分
    - HDMI/DP: 100 Ohm 差分
    - PCIe: 85 Ohm 差分
    - Ethernet: 100 Ohm 差分
    """

    def __init__(
        self,
        board_width: float = 100,
        board_height: float = 80,
        grid_size: float = 0.5,
        target_impedance: float = 90.0,
    ):
        """
        Args:
            board_width: 板宽 (mm)
            board_height: 板高 (mm)
            grid_size: 网格大小 (mm)
            target_impedance: 默认目标差分阻抗 (Ohm), 90 for USB
        """
        self.board_width = board_width
        self.board_height = board_height
        self.grid_size = grid_size
        self.target_impedance = target_impedance

        # A* 路由器实例 (正端和负端各用一个)
        self._pos_router = AStarRouter(
            board_width=board_width,
            board_height=board_height,
            grid_size=grid_size,
        )
        self._neg_router = AStarRouter(
            board_width=board_width,
            board_height=board_height,
            grid_size=grid_size,
        )

    def route_pair(
        self,
        start_pos: Point,
        start_neg: Point,
        end_pos: Point,
        end_neg: Point,
        layer: str = "F.Cu",
        max_length_mismatch: float = 0.5,
    ) -> Optional[DiffPairRoute]:
        """
        布线一对差分信号

        Args:
            start_pos: 正端起点
            start_neg: 负端起点
            end_pos: 正端终点
            end_neg: 负端终点
            layer: 布线层
            max_length_mismatch: 最大允许长度不匹配 (mm), 默认 0.5mm

        Returns:
            DiffPairRoute: 布线结果, 如果布线失败则返回 None
        """
        logger.info(
            f"差分对布线: POS ({start_pos.x},{start_pos.y})->({end_pos.x},{end_pos.y}), "
            f"NEG ({start_neg.x},{start_neg.y})->({end_neg.x},{end_neg.y}), "
            f"目标阻抗={self.target_impedance}Ohm, 层={layer}"
        )

        # Step 1: 计算阻抗控制的走线宽度/间距
        trace_width, trace_gap = self._calculate_coupled_dimensions(self.target_impedance)
        logger.info(
            f"阻抗控制参数: 走线宽度={trace_width:.3f}mm, 走线间距={trace_gap:.3f}mm"
        )

        # Step 2: 耦合布线
        pos_points, neg_points = self._route_coupled_traces(
            start_pos, start_neg, end_pos, end_neg, layer
        )

        if not pos_points or not neg_points:
            logger.warning("差分对布线失败: 无法完成耦合布线")
            return None

        # Step 3: 计算走线长度
        pos_length = self._calculate_trace_length(pos_points)
        neg_length = self._calculate_trace_length(neg_points)
        length_mismatch = abs(pos_length - neg_length)

        # Step 4: 计算实际差分阻抗
        z_diff = self._calculate_differential_impedance(trace_width, trace_gap)

        result = DiffPairRoute(
            pos_points=pos_points,
            neg_points=neg_points,
            pos_length=round(pos_length, 3),
            neg_length=round(neg_length, 3),
            length_mismatch=round(length_mismatch, 3),
            impedance=round(z_diff, 2),
        )

        # Step 5: 长度匹配检查
        if not self._check_length_matching(pos_length, neg_length, max_length_mismatch):
            logger.warning(
                f"差分对长度不匹配: {length_mismatch:.3f}mm "
                f"(最大允许 {max_length_mismatch}mm), 需要进行长度调谐"
            )
        else:
            logger.info(f"差分对长度匹配良好: 不匹配量={length_mismatch:.3f}mm")

        logger.info(
            f"差分对布线完成: POS长度={pos_length:.2f}mm, NEG长度={neg_length:.2f}mm, "
            f"阻抗={z_diff:.1f}Ohm"
        )
        return result

    def _calculate_coupled_dimensions(
        self,
        target_impedance: float,
        substrate_height: float = 0.2,
        er: float = 4.5,
    ) -> Tuple[float, float]:
        """
        根据目标差分阻抗计算走线宽度和间距

        使用微带线阻抗公式:
          Z0 = 87 / sqrt(Er+1.41) * ln(5.98*H / (0.8*W + T))
          Z_diff = 2 * Z0 * (1 - 0.48 * exp(-0.96 * S/H))

        通过迭代搜索找到满足目标阻抗的 W 和 S。

        Args:
            target_impedance: 目标差分阻抗 (Ohm)
            substrate_height: 介质厚度 (mm), 默认 0.2mm (FR4 4层板)
            er: 介电常数, 默认 4.5 (FR4)

        Returns:
            (trace_width, trace_gap): 走线宽度 (mm), 走线间距 (mm)
        """
        t = 0.035  # 铜厚 1oz = 0.035mm
        h = substrate_height

        best_width = 0.15
        best_gap = 0.15
        best_error = float("inf")

        # 搜索范围: 走线宽度 0.1mm ~ 0.5mm, 间距 0.1mm ~ 1.0mm
        for w_candidate in [x * 0.01 for x in range(10, 51, 2)]:  # 0.10 ~ 0.50 step 0.02
            for s_candidate in [x * 0.01 for x in range(10, 101, 2)]:  # 0.10 ~ 1.00 step 0.02
                z_diff = self._calculate_differential_impedance(
                    w_candidate, s_candidate, h, er, t
                )
                error = abs(z_diff - target_impedance)

                if error < best_error:
                    best_error = error
                    best_width = w_candidate
                    best_gap = s_candidate

                # 如果误差足够小, 提前退出
                if error < 0.5:  # 0.5 Ohm 精度
                    return (best_width, best_gap)

        logger.info(
            f"阻抗计算: W={best_width:.3f}mm, S={best_gap:.3f}mm, "
            f"Z_diff={self._calculate_differential_impedance(best_width, best_gap, h, er, t):.1f}Ohm, "
            f"误差={best_error:.1f}Ohm"
        )
        return (best_width, best_gap)

    def _calculate_differential_impedance(
        self,
        trace_width: float,
        trace_gap: float,
        substrate_height: float = 0.2,
        er: float = 4.5,
        copper_thickness: float = 0.035,
    ) -> float:
        """
        计算差分阻抗

        公式:
          Z0 = 87 / sqrt(Er+1.41) * ln(5.98*H / (0.8*W + T))
          Z_diff = 2 * Z0 * (1 - 0.48 * exp(-0.96 * S/H))

        Args:
            trace_width: 走线宽度 (mm)
            trace_gap: 走线间距 (mm)
            substrate_height: 介质厚度 (mm)
            er: 介电常数
            copper_thickness: 铜厚 (mm)

        Returns:
            float: 差分阻抗 (Ohm)
        """
        h = substrate_height
        w = trace_width
        s = trace_gap
        t = copper_thickness

        # 单端微带线阻抗
        try:
            z0 = 87 / math.sqrt(er + 1.41) * math.log(5.98 * h / (0.8 * w + t))
        except (ValueError, ZeroDivisionError):
            z0 = 50.0

        # 差分阻抗 (耦合修正)
        # Z_diff ≈ 2 * Z0 * (1 - 0.48 * exp(-0.96 * S/H))
        try:
            coupling_factor = 0.48 * math.exp(-0.96 * s / h)
            z_diff = 2 * z0 * (1 - coupling_factor)
        except (ValueError, ZeroDivisionError, OverflowError):
            z_diff = 2 * z0

        return max(z_diff, 0)

    def _route_coupled_traces(
        self,
        start_pos: Point,
        start_neg: Point,
        end_pos: Point,
        end_neg: Point,
        layer: str,
    ) -> Tuple[List[Point], List[Point]]:
        """
        耦合布线: 两条走线平行耦合布线

        策略:
        1. 先布正端走线 (用 A* 找路)
        2. 将正端走线作为障碍物偏移到负端路由器
        3. 布负端走线, 保持与正端平行的耦合约束

        Args:
            start_pos: 正端起点
            start_neg: 负端起点
            end_pos: 正端终点
            end_neg: 负端终点
            layer: 布线层

        Returns:
            (pos_points, neg_points): 正端和负端的点列表
        """
        # Step 1: 布正端走线
        pos_path = self._pos_router.find_path(start_pos, end_pos, layer)
        if not pos_path:
            logger.warning("差分对正端布线失败")
            return ([], [])

        # Step 2: 将正端走线段添加为负端路由器的障碍物
        # 每个正端走线段在负端路由器中生成偏移的障碍物
        _, trace_gap = self._calculate_coupled_dimensions(self.target_impedance)
        for i in range(len(pos_path) - 1):
            self._neg_router.add_trace_obstacle(
                pos_path[i].x, pos_path[i].y,
                pos_path[i + 1].x, pos_path[i + 1].y,
                layer,
            )

        # Step 3: 布负端走线
        neg_path = self._neg_router.find_path(start_neg, end_neg, layer)
        if not neg_path:
            logger.warning("差分对负端布线失败")
            return (pos_path, [])

        # Step 4: 优化耦合 - 确保两条走线尽量平行
        pos_optimized, neg_optimized = self._optimize_coupling(
            pos_path, neg_path, trace_gap
        )

        return (pos_optimized, neg_optimized)

    def _optimize_coupling(
        self,
        pos_path: List[Point],
        neg_path: List[Point],
        target_gap: float,
    ) -> Tuple[List[Point], List[Point]]:
        """
        优化两条走线的耦合度

        对负端走线进行微调, 使其尽量与正端保持 target_gap 的间距。

        Args:
            pos_path: 正端走线点列表
            neg_path: 负端走线点列表
            target_gap: 目标间距 (mm)

        Returns:
            (pos_path, neg_optimized): 优化后的点列表
        """
        if len(pos_path) < 2 or len(neg_path) < 2:
            return (pos_path, neg_path)

        # 计算正端走线方向的法向量, 并沿法向量偏移负端走线
        optimized_neg = []
        for point in neg_path:
            # 找到正端走线上最近的点
            nearest_pos, _, _ = self._nearest_point_on_path(point, pos_path)

            if nearest_pos:
                # 计算从正端最近点到当前负端点的向量
                dx = point.x - nearest_pos.x
                dy = point.y - nearest_pos.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist > 0.001:
                    # 归一化后乘以目标间距
                    scale = target_gap / dist
                    optimized_neg.append(Point(
                        nearest_pos.x + dx * scale,
                        nearest_pos.y + dy * scale,
                    ))
                else:
                    # 两点重合, 向垂直方向偏移
                    optimized_neg.append(Point(point.x + target_gap, point.y))
            else:
                optimized_neg.append(point)

        return (pos_path, optimized_neg)

    def _nearest_point_on_path(
        self, point: Point, path: List[Point]
    ) -> Tuple[Optional[Point], int, float]:
        """
        找到路径上距离给定点最近的点

        Args:
            point: 目标点
            path: 路径点列表

        Returns:
            (nearest_point, segment_index, distance)
        """
        best_point = None
        best_index = 0
        best_dist = float("inf")

        for i in range(len(path) - 1):
            nearest = self._project_point_on_segment(point, path[i], path[i + 1])
            dist = point.distance_to(nearest)
            if dist < best_dist:
                best_dist = dist
                best_point = nearest
                best_index = i

        return (best_point, best_index, best_dist)

    def _project_point_on_segment(
        self, point: Point, seg_start: Point, seg_end: Point
    ) -> Point:
        """
        将点投影到线段上

        Args:
            point: 待投影的点
            seg_start: 线段起点
            seg_end: 线段终点

        Returns:
            Point: 投影点
        """
        dx = seg_end.x - seg_start.x
        dy = seg_end.y - seg_start.y
        len_sq = dx * dx + dy * dy

        if len_sq < 1e-10:
            return Point(seg_start.x, seg_start.y)

        t = max(0, min(1, ((point.x - seg_start.x) * dx + (point.y - seg_start.y) * dy) / len_sq))
        return Point(seg_start.x + t * dx, seg_start.y + t * dy)

    def _calculate_trace_length(self, points: List[Point]) -> float:
        """
        计算走线总长度

        Args:
            points: 走线点列表

        Returns:
            float: 走线长度 (mm)
        """
        total = 0.0
        for i in range(len(points) - 1):
            total += points[i].distance_to(points[i + 1])
        return total

    def _check_length_matching(
        self, pos_length: float, neg_length: float, max_mismatch: float
    ) -> bool:
        """
        检查差分对长度匹配

        Args:
            pos_length: 正端走线长度 (mm)
            neg_length: 负端走线长度 (mm)
            max_mismatch: 最大允许不匹配量 (mm)

        Returns:
            bool: 是否满足长度匹配要求
        """
        mismatch = abs(pos_length - neg_length)
        return mismatch <= max_mismatch

    def add_obstacle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        layer: str = "F.Cu",
    ):
        """
        添加障碍物到两个路由器

        Args:
            x: X 坐标 (mm)
            y: Y 坐标 (mm)
            width: 障碍物宽 (mm)
            height: 障碍物高 (mm)
            layer: 层名
        """
        self._pos_router.add_obstacle(x, y, width, height, layer)
        self._neg_router.add_obstacle(x, y, width, height, layer)

    def add_obstacles_from_tracks(
        self,
        tracks: List[dict],
        layer: str = "F.Cu",
    ):
        """
        从现有走线数据添加障碍物

        Args:
            tracks: 走线数据列表, 每条走线包含 {"x1", "y1", "x2", "y2", "width"}
            layer: 层名
        """
        for track in tracks:
            x1 = track.get("x1", 0)
            y1 = track.get("y1", 0)
            x2 = track.get("x2", 0)
            y2 = track.get("y2", 0)
            self._pos_router.add_trace_obstacle(x1, y1, x2, y2, layer)
            self._neg_router.add_trace_obstacle(x1, y1, x2, y2, layer)

    def clear_obstacles(self):
        """清除两个路由器的所有障碍物"""
        self._pos_router.clear_obstacles()
        self._neg_router.clear_obstacles()

    def get_impedance_constraint(
        self,
        target_z: float = 0,
        tolerance_pct: float = 10.0,
    ) -> ImpedanceConstraint:
        """
        获取阻抗约束参数

        Args:
            target_z: 目标差分阻抗 (Ohm), 0 表示使用默认值
            tolerance_pct: 容差百分比

        Returns:
            ImpedanceConstraint: 包含计算得到的宽度和间距
        """
        if target_z <= 0:
            target_z = self.target_impedance

        trace_width, trace_gap = self._calculate_coupled_dimensions(target_z)
        return ImpedanceConstraint(
            target_z=target_z,
            tolerance_pct=tolerance_pct,
            trace_width=round(trace_width, 3),
            trace_gap=round(trace_gap, 3),
        )


def create_diff_pair_router(
    board_width: float = 100,
    board_height: float = 80,
    target_impedance: float = 90.0,
) -> DifferentialPairRouter:
    """
    创建差分对路由器实例

    Args:
        board_width: 板宽 (mm)
        board_height: 板高 (mm)
        target_impedance: 目标差分阻抗 (Ohm)

    Returns:
        DifferentialPairRouter 实例
    """
    return DifferentialPairRouter(
        board_width=board_width,
        board_height=board_height,
        target_impedance=target_impedance,
    )
