# -*- coding: utf-8 -*-
"""
Push Router - 推挤式布线器

Phase 5: 实现推挤式自动布线算法

推挤式布线算法能够：
1. 在布线时推挤现有走线以避开障碍
2. 提供更高的布线完成率
3. 支持多层板复杂布线

注意：这是一个基础实现，完整的推挤算法需要考虑：
- 线的可压缩性（不同角度的线压缩能力不同）
- 平行线之间的耦合效应
- 阻抗连续性
- 生产制造约束
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum

from routing.shove_types import (
    ShoveConflict, ShoveDirection, ConflictType,
    ShoveAction, ShoveOptions, CostBreakdown,
)

logger = logging.getLogger(__name__)


class RouteStatus(Enum):
    """布线状态"""
    SUCCESS = "success"
    BLOCKED = "blocked"
    FAILED = "failed"
    OPTIMAL = "optimal"


@dataclass
class Point:
    """二维点"""
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def manhattan_distance(self, other: "Point") -> float:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return abs(self.x - other.x) < 0.001 and abs(self.y - other.y) < 0.001


@dataclass
class Segment:
    """线段"""
    start: Point
    end: Point
    layer: str = "F.Cu"
    width: float = 0.25

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def is_horizontal(self) -> bool:
        return abs(self.start.y - self.end.y) < 0.001

    @property
    def is_vertical(self) -> bool:
        return abs(self.start.x - self.end.x) < 0.001

    def direction(self) -> Tuple[float, float]:
        """返回单位方向向量"""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length = self.length
        if length < 0.001:
            return (0, 0)
        return (dx / length, dy / length)


@dataclass
class Obstacle:
    """障碍物（现有走线、铜箔、焊盘等）"""
    segment: Segment
    priority: int = 0  # 优先级，较低的可以被推挤


@dataclass
class PushResult:
    """推挤结果"""
    success: bool
    status: RouteStatus
    routed_segments: List[Segment]
    pushed_obstacles: List[Tuple[Obstacle, Segment]]  # (被推挤的障碍, 推送后的位置)
    total_length: float
    via_count: int
    message: str = ""


class PushRouter:
    """
    推挤式布线器

    基础策略：
    1. 使用 A* 算法找到最短路径
    2. 遇到障碍时，尝试推挤附近走线
    3. 如果无法推挤，尝试改变层（添加过孔）
    4. 如果所有策略都失败，则标记为 BLOCKED
    """

    def __init__(
        self,
        grid_size: float = 0.25,
        trace_width: float = 0.25,
        clearance: float = 0.2,
        max_vias: int = 10,
    ):
        """
        Args:
            grid_size: 网格大小（mm）
            trace_width: 默认走线宽度（mm）
            clearance: 默认安全间距（mm）
            max_vias: 最大过孔数量
        """
        self.grid_size = grid_size
        self.trace_width = trace_width
        self.clearance = clearance
        self.max_vias = max_vias
        self.obstacles: List[Obstacle] = []
        self.layers = ["F.Cu", "B.Cu"]  # 默认双面板

    def add_obstacle(self, obstacle: Obstacle):
        """添加障碍物"""
        self.obstacles.append(obstacle)

    def add_obstacles_from_segments(
        self,
        segments: List[Segment],
        priority: int = 0,
    ):
        """从线段列表添加障碍物"""
        for seg in segments:
            self.add_obstacle(Obstacle(segment=seg, priority=priority))

    def clear_obstacles(self):
        """清除所有障碍物"""
        self.obstacles = []

    def route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        start_layer: str = "F.Cu",
        end_layer: str = "F.Cu",
        net_name: str = "",
        shove_options: Optional[ShoveOptions] = None,
    ) -> PushResult:
        """
        路由一条net（带推挤支持）

        Args:
            start: 起点坐标 (x, y)
            end: 终点坐标 (x, y)
            start_layer: 起始层
            end_layer: 结束层
            net_name: 网络名称
            shove_options: 推挤参数

        Returns:
            PushResult: 包含布线结果
        """
        if shove_options is None:
            shove_options = ShoveOptions()

        start_point = Point(start[0], start[1])
        end_point = Point(end[0], end[1])

        logger.info(f"推挤布线: {start} -> {end} on {start_layer} to {end_layer}")

        # 第1步：尝试A*直接布线（不考虑障碍为阻挡点）
        path = self._astar_path(start_point, end_point, start_layer)

        if not path:
            # A* 完全无法找到路径
            return PushResult(
                success=False,
                status=RouteStatus.FAILED,
                routed_segments=[],
                pushed_obstacles=[],
                total_length=0,
                via_count=0,
                message="无法找到路径",
            )

        # 将路径转换为线段
        segments = self._path_to_segments(path, start_layer)

        # 第2步：检查碰撞并尝试推挤
        all_pushed: List[Tuple[Obstacle, Segment]] = []
        all_shove_results: List = []
        blocked_segments: List[Segment] = []

        for seg in segments:
            colliding = self._find_colliding_obstacles(seg)

            if not colliding:
                # 无碰撞，直接通过
                self.add_obstacle(Obstacle(segment=seg, priority=0))
                continue

            # 有碰撞，决策策略
            # 估算绕行额外长度（简化：碰撞数 * 2mm）
            extra_len = len(colliding) * 2.0
            strategy = self._should_shove_or_walkaround(
                seg, colliding, extra_len, shove_options
            )

            if strategy == "shove":
                # 执行推挤
                shove_ok = True
                for obs in colliding:
                    action = self._resolve_collision(seg, obs, shove_options)
                    if action is None:
                        shove_ok = False
                        blocked_segments.append(seg)
                        break

                    # 执行推移
                    new_segs, has_drc = self._shove_track(obs, action, shove_options)

                    # 级联处理
                    cascade_result = self._cascade_shove(action, options=shove_options)
                    all_shove_results.append(cascade_result)

                    # 记录推移结果
                    if new_segs:
                        for ns in new_segs:
                            all_pushed.append((obs, ns))

                    if has_drc and cascade_result.drc_violations > 0:
                        logger.warning(f"推挤导致 DRC 违规，但仍继续")

                if shove_ok:
                    self.add_obstacle(Obstacle(segment=seg, priority=0))

            elif strategy == "walkaround":
                # 尝试重新路由（绕行）
                alt_path = self._find_walkaround_path(
                    seg.start, seg.end, start_layer, colliding, shove_options
                )
                if alt_path:
                    alt_segs = self._path_to_segments(alt_path, start_layer)
                    segments = self._replace_segment(segments, seg, alt_segs)
                    for as_ in alt_segs:
                        self.add_obstacle(Obstacle(segment=as_, priority=0))
                else:
                    blocked_segments.append(seg)

            else:
                # ripup 或其他策略：标记为阻挡
                blocked_segments.append(seg)

        # 第3步：汇总结果
        if blocked_segments:
            return PushResult(
                success=False,
                status=RouteStatus.BLOCKED,
                routed_segments=[],
                pushed_obstacles=all_pushed,
                total_length=0,
                via_count=0,
                message=f"路径被阻挡，{len(blocked_segments)} 段无法布线",
            )

        total_length = sum(seg.length for seg in segments)
        via_count = self._count_vias(segments)

        return PushResult(
            success=True,
            status=RouteStatus.SUCCESS,
            routed_segments=segments,
            pushed_obstacles=all_pushed,
            total_length=total_length,
            via_count=via_count,
            message=f"布线成功，推挤 {len(all_pushed)} 条走线",
        )

    def _astar_path(
        self,
        start: Point,
        end: Point,
        layer: str,
    ) -> List[Point]:
        """
        A* 路径搜索

        返回路径点列表
        """
        # 简化的 A* 实现
        # 实际应该使用优先级队列和更完善的启发函数

        open_set = {start}
        came_from = {}
        g_score = {start: 0}
        f_score = {start: start.distance_to(end)}

        while open_set:
            # 找到 f_score 最低的点
            current = min(open_set, key=lambda p: f_score.get(p, float("inf")))

            if current.distance_to(end) < self.grid_size * 2:
                # 找到终点
                return self._reconstruct_path(came_from, current, end)

            open_set.remove(current)

            # 探索邻居（简化的4方向）
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = Point(
                    current.x + dx * self.grid_size,
                    current.y + dy * self.grid_size,
                )

                # 检查是否是有效点（未被阻挡）
                if self._is_blocked(neighbor, layer):
                    continue

                tentative_g = g_score[current] + self.grid_size

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + neighbor.distance_to(end)
                    open_set.add(neighbor)

        return []  # 没有找到路径

    def _is_blocked(self, point: Point, layer: str) -> bool:
        """检查点是否被阻挡"""
        for obs in self.obstacles:
            seg = obs.segment
            if seg.layer != layer:
                continue

            # 简单的距离检查
            dist = self._point_to_segment_distance(point, seg)
            if dist < self.clearance + self.trace_width / 2:
                return True

        return False

    def _point_to_segment_distance(self, point: Point, segment: Segment) -> float:
        """计算点到线段的距离"""
        px, py = point.x, point.y
        x1, y1 = segment.start.x, segment.start.y
        x2, y2 = segment.end.x, segment.end.y

        # 投影到线段上
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return point.distance_to(segment.start)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return point.distance_to(Point(proj_x, proj_y))

    def _reconstruct_path(
        self,
        came_from: Dict[Point, Point],
        current: Point,
        end: Point,
    ) -> List[Point]:
        """重建路径"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()

        # 添加终点
        if path[-1].distance_to(end) > 0.001:
            path.append(end)

        return path

    def _path_to_segments(self, path: List[Point], layer: str) -> List[Segment]:
        """将路径点列表转换为线段列表"""
        if len(path) < 2:
            return []

        segments = []
        for i in range(len(path) - 1):
            segments.append(
                Segment(
                    start=path[i],
                    end=path[i + 1],
                    layer=layer,
                    width=self.trace_width,
                )
            )

        return segments

    def _find_colliding_obstacles(
        self,
        seg: Segment,
    ) -> List[Obstacle]:
        """找出与给定线段碰撞的所有障碍物"""
        colliding = []
        for obs in self.obstacles:
            if obs.segment.layer != seg.layer:
                continue
            if self._segments_intersect(seg, obs.segment):
                colliding.append(obs)
        return colliding

    def _should_shove_or_walkaround(
        self,
        seg: Segment,
        obstacles: List[Obstacle],
        extra_length: float,
        options: ShoveOptions,
    ) -> str:
        """决策：推挤还是绕行（委托给成本函数）"""
        return self._should_shove_or_walkaround_internal(
            seg, obstacles, extra_length, options
        )

    def _should_shove_or_walkaround_internal(
        self,
        seg: Segment,
        obstacles: List[Obstacle],
        extra_length: float,
        options: ShoveOptions,
    ) -> str:
        """内部决策方法"""
        if not obstacles:
            return "shove"

        all_fixed = all(obs.priority >= 100 for obs in obstacles)
        if all_fixed:
            return "walkaround"

        shove_cost = self._calculate_shove_cost(seg, obstacles, options)
        walkaround_cost = extra_length * options.cost_per_mm

        if shove_cost.drc_penalty > 0 and walkaround_cost < shove_cost.total:
            return "walkaround"

        if shove_cost.total <= walkaround_cost:
            return "shove"
        else:
            return "walkaround"

    def _shove_track(
        self,
        obstacle: Obstacle,
        action: ShoveAction,
        options: ShoveOptions,
    ) -> Tuple[List[Segment], bool]:
        """执行推移（委托给已有的 _shove_track 方法）"""
        return self._shove_track_impl(obstacle, action, options)

    def _cascade_shove(
        self,
        trigger_action: ShoveAction,
        depth: int = 0,
        visited: Optional[Set[Tuple]] = None,
        options: Optional[ShoveOptions] = None,
    ) -> "ShoveResult":
        """级联推移（委托给已有的方法）"""
        return self._cascade_shove_impl(trigger_action, depth, visited, options)

    def _find_walkaround_path(
        self,
        start: Point,
        end: Point,
        layer: str,
        blocking_obstacles: List[Obstacle],
        options: ShoveOptions,
    ) -> List[Point]:
        """
        尝试找到绕行路径。

        策略：临时标记障碍为不可通过，重新运行A*。
        如果仍然失败，尝试扩大搜索范围（偏移路径）。
        """
        # 临时提高碰撞障碍的阻挡范围
        old_clearance = self.clearance
        self.clearance = old_clearance * 2.5

        path = self._astar_path(start, end, layer)

        self.clearance = old_clearance

        if path:
            return path

        # 尝试通过偏移中间点绕行
        mid_x = (start.x + end.x) / 2
        mid_y = (start.y + end.y) / 2

        # 4个偏移方向
        offsets = [
            (0, options.max_shove_distance),
            (0, -options.max_shove_distance),
            (options.max_shove_distance, 0),
            (-options.max_shove_distance, 0),
        ]

        for dx, dy in offsets:
            waypoint = Point(mid_x + dx, mid_y + dy)
            path1 = self._astar_path(start, waypoint, layer)
            if path1:
                path2 = self._astar_path(waypoint, end, layer)
                if path2:
                    return path1 + path2[1:]

        return []

    def _replace_segment(
        self,
        segments: List[Segment],
        old_seg: Segment,
        new_segs: List[Segment],
    ) -> List[Segment]:
        """替换线段列表中的一个段为多个新段"""
        result = []
        for seg in segments:
            if seg is old_seg:
                result.extend(new_segs)
            else:
                result.append(seg)
        return result

    def _segments_intersect(self, seg1: Segment, seg2: Segment) -> bool:
        """检查两条线段是否相交"""
        # 简化的碰撞检测
        dist = self._segments_min_distance(seg1, seg2)
        return dist < self.clearance + self.trace_width

    def _segments_min_distance(self, seg1: Segment, seg2: Segment) -> float:
        """计算两条线段的最小距离"""
        # 使用四次距离检查（端点到端点、端点到线段）
        d1 = self._point_to_segment_distance(seg1.start, seg2)
        d2 = self._point_to_segment_distance(seg1.end, seg2)
        d3 = self._point_to_segment_distance(seg2.start, seg1)
        d4 = self._point_to_segment_distance(seg2.end, seg1)
        return min(d1, d2, d3, d4)

    def _count_vias(self, segments: List[Segment]) -> int:
        """计算线段中的过孔数量"""
        if len(segments) < 2:
            return 0

        count = 0
        for i in range(len(segments) - 1):
            if segments[i].layer != segments[i + 1].layer:
                count += 1

        return count

    # ── 碰撞解析方法 ──────────────────────────────────────────

    def _resolve_collision(
        self,
        active_seg: Segment,
        obstacle: Obstacle,
        options: Optional[ShoveOptions] = None,
    ) -> Optional[ShoveAction]:
        """
        解析一次碰撞，计算推挤方向和距离。

        Args:
            active_seg: 正在布的线段
            obstacle: 被碰撞的障碍物
            options: 推挤参数

        Returns:
            ShoveAction 如果可以推挤，否则 None
        """
        if options is None:
            options = ShoveOptions()

        obs_seg = obstacle.segment

        # 固定障碍不可推挤
        if obstacle.priority >= 100:
            logger.debug(f"障碍物优先级 {obstacle.priority}，不可推挤")
            return None

        # 分类碰撞类型
        conflict_type = self._classify_conflict(active_seg, obs_seg)

        # 计算推挤向量
        shove_dir, shove_dist = self._compute_shove_vector(
            active_seg, obs_seg, conflict_type, options
        )

        if shove_dir is None or shove_dist <= 0:
            return None

        # 超出最大推挤距离则放弃
        if shove_dist > options.max_shove_distance:
            logger.debug(f"推挤距离 {shove_dist:.2f}mm 超出上限 {options.max_shove_distance}mm")
            return None

        # 计算推挤后新位置
        dx_map = {
            ShoveDirection.UP: 0,
            ShoveDirection.DOWN: 0,
            ShoveDirection.LEFT: -1,
            ShoveDirection.RIGHT: 1,
            ShoveDirection.CUSTOM: 0,
        }
        dy_map = {
            ShoveDirection.UP: 1,
            ShoveDirection.DOWN: -1,
            ShoveDirection.LEFT: 0,
            ShoveDirection.RIGHT: 0,
            ShoveDirection.CUSTOM: 0,
        }

        dx = dx_map[shove_dir] * shove_dist
        dy = dy_map[shove_dir] * shove_dist

        new_start = (obs_seg.start.x + dx, obs_seg.start.y + dy)
        new_end = (obs_seg.end.x + dx, obs_seg.end.y + dy)

        # 计算成本
        cost = self._calculate_action_cost(
            obs_seg, shove_dir, shove_dist, obstacle.priority, options
        )

        return ShoveAction(
            original_start=(obs_seg.start.x, obs_seg.start.y),
            original_end=(obs_seg.end.x, obs_seg.end.y),
            original_layer=obs_seg.layer,
            direction=shove_dir,
            distance=shove_dist,
            cost=cost,
            new_start=new_start,
            new_end=new_end,
        )

    def _classify_conflict(
        self,
        seg1: Segment,
        seg2: Segment,
    ) -> ConflictType:
        """
        分类两条线段的碰撞类型。

        根据「线段角度关系」判断是平行碰撞还是交叉碰撞。
        """
        h1 = seg1.is_horizontal
        v1 = seg1.is_vertical
        h2 = seg2.is_horizontal
        v2 = seg2.is_vertical

        if (h1 and h2) or (v1 and v2):
            # 两条平行线
            return ConflictType.PARALLEL

        if (h1 and v2) or (v1 and h2):
            # 正交交叉
            return ConflictType.CROSSING

        # 检查端点碰撞
        for pt in [seg1.start, seg1.end]:
            if self._point_to_segment_distance(pt, seg2) < self.clearance:
                return ConflictType.ENDPOINT

        return ConflictType.CORNER

    def _compute_shove_vector(
        self,
        active_seg: Segment,
        obs_seg: Segment,
        conflict_type: ConflictType,
        options: ShoveOptions,
    ) -> Tuple[Optional[ShoveDirection], float]:
        """
        计算推挤方向和距离。

        Returns:
            (推挤方向, 推挤距离) 或 (None, 0) 如果无法推挤
        """
        # 所需间距 = clearance + trace_width
        required_gap = options.post_shove_clearance + self.trace_width / 2 + obs_seg.width / 2

        if conflict_type == ConflictType.PARALLEL:
            # 平行走线：计算当前间距，确定推移方向
            if obs_seg.is_horizontal:
                # 两条水平线，需要垂直推移
                dy = obs_seg.start.y - active_seg.start.y
                current_gap = abs(dy)
                shove_dist = max(0, required_gap - current_gap + options.min_shove_step)
                direction = ShoveDirection.UP if dy > 0 else ShoveDirection.DOWN
                return direction, shove_dist

            elif obs_seg.is_vertical:
                # 两条垂直线，需要水平推移
                dx = obs_seg.start.x - active_seg.start.x
                current_gap = abs(dx)
                shove_dist = max(0, required_gap - current_gap + options.min_shove_step)
                direction = ShoveDirection.RIGHT if dx > 0 else ShoveDirection.LEFT
                return direction, shove_dist

            else:
                return None, 0

        elif conflict_type == ConflictType.CROSSING:
            # 正交交叉：推移被碰线段（沿其法线方向）
            if obs_seg.is_horizontal:
                # 障碍是水平的，垂直推移
                mid_y = (obs_seg.start.y + obs_seg.end.y) / 2
                active_y = (active_seg.start.y + active_seg.end.y) / 2
                dy = mid_y - active_y
                shove_dist = required_gap + options.min_shove_step
                direction = ShoveDirection.UP if dy >= 0 else ShoveDirection.DOWN
                return direction, shove_dist

            elif obs_seg.is_vertical:
                # 障碍是垂直的，水平推移
                mid_x = (obs_seg.start.x + obs_seg.end.x) / 2
                active_x = (active_seg.start.x + active_seg.end.x) / 2
                dx = mid_x - active_x
                shove_dist = required_gap + options.min_shove_step
                direction = ShoveDirection.RIGHT if dx >= 0 else ShoveDirection.LEFT
                return direction, shove_dist

            else:
                return None, 0

        elif conflict_type == ConflictType.ENDPOINT:
            # 端点碰撞：沿障碍线段法线方向推移
            dx = obs_seg.end.x - obs_seg.start.x
            dy = obs_seg.end.y - obs_seg.start.y
            length = math.sqrt(dx * dx + dy * dy)
            if length < 0.001:
                return None, 0

            # 法线方向（垂直于线段方向）
            nx, ny = -dy / length, dx / length
            shove_dist = required_gap + options.min_shove_step

            # 映射到最近的正交方向
            if abs(nx) > abs(ny):
                direction = ShoveDirection.RIGHT if nx > 0 else ShoveDirection.LEFT
            else:
                direction = ShoveDirection.UP if ny > 0 else ShoveDirection.DOWN

            return direction, shove_dist

        else:
            # CORNER 或其他类型：使用简单距离计算
            dist = self._segments_min_distance(active_seg, obs_seg)
            if dist >= required_gap:
                return None, 0

            shove_dist = required_gap - dist + options.min_shove_step
            # 简单策略：往障碍中心远离active的方向推
            obs_cx = (obs_seg.start.x + obs_seg.end.x) / 2
            obs_cy = (obs_seg.start.y + obs_seg.end.y) / 2
            act_cx = (active_seg.start.x + active_seg.end.x) / 2
            act_cy = (active_seg.start.y + active_seg.end.y) / 2

            ddx = obs_cx - act_cx
            ddy = obs_cy - act_cy

            if abs(ddx) > abs(ddy):
                direction = ShoveDirection.RIGHT if ddx > 0 else ShoveDirection.LEFT
            else:
                direction = ShoveDirection.UP if ddy > 0 else ShoveDirection.DOWN

            return direction, shove_dist

    def _calculate_action_cost(
        self,
        obs_seg: Segment,
        direction: ShoveDirection,
        distance: float,
        priority: int,
        options: ShoveOptions,
    ) -> float:
        """计算单个推挤动作的成本"""
        cost = distance * options.cost_per_mm

        # 高优先级障碍推挤成本更高
        if priority >= 50:
            cost *= 2.0

        # 非正交方向的额外成本
        if direction == ShoveDirection.CUSTOM:
            cost += options.cost_per_mm

        return cost

    # ── 单线推移 ──────────────────────────────────────────────

    def _shove_track(
        self,
        obstacle: Obstacle,
        action: ShoveAction,
        options: Optional[ShoveOptions] = None,
    ) -> Tuple[List[Segment], bool]:
        """
        推移一条线段。

        根据 action 中指定的方向和距离，将 obstacle 的线段推到新位置。
        支持两种推移模式：
        - 整体推移：整条线段平移（用于短线段或完全被覆盖的情况）
        - 局部推移：只推移碰撞段（用于长线段被短碰撞的情况）

        Args:
            obstacle: 被推挤的障碍物
            action: 推挤动作（包含方向和距离）
            options: 推挤参数

        Returns:
            (推移后的新线段列表, 是否产生DRC冲突)
        """
        if options is None:
            options = ShoveOptions()

        seg = obstacle.segment

        # 计算位移向量
        dx, dy = self._direction_to_delta(action.direction, action.distance)

        # 决定推移策略：整体还是局部
        if self._should_shove_entire(seg, action):
            return self._shove_entire_track(seg, dx, dy, options)
        else:
            return self._shove_partial_track(seg, action, dx, dy, options)

    def _should_shove_entire(self, seg: Segment, action: ShoveAction) -> bool:
        """判断是否应该整体推移（而非局部推移）"""
        # 短线段（<2mm）整体推移
        if seg.length < 2.0:
            return True

        # 如果碰撞类型是平行且整条线都在碰撞范围内
        # 简化判断：默认对较短的线段整体推移
        return seg.length < 5.0

    def _shove_entire_track(
        self,
        seg: Segment,
        dx: float,
        dy: float,
        options: ShoveOptions,
    ) -> Tuple[List[Segment], bool]:
        """
        整体推移：将整条线段平移。
        """
        new_start = Point(seg.start.x + dx, seg.start.y + dy)
        new_end = Point(seg.end.x + dx, seg.end.y + dy)

        new_seg = Segment(
            start=new_start,
            end=new_end,
            layer=seg.layer,
            width=seg.width,
        )

        # 检查推移后是否与其他障碍冲突
        has_drc = self._check_shove_drc(new_seg)

        if options.force_orthogonal:
            new_seg = self._ensure_orthogonal(new_seg)

        return [new_seg], has_drc

    def _shove_partial_track(
        self,
        seg: Segment,
        action: ShoveAction,
        dx: float,
        dy: float,
        options: ShoveOptions,
    ) -> Tuple[List[Segment], bool]:
        """
        局部推移：只推移碰撞区域，保留两端。

        将原始线段拆分为最多3段：
        - 前段（不动）
        - 中段（推移）
        - 后段（不动）

        加上两个过渡斜线连接。
        """
        # 确定碰撞区间（简化：用action的原始位置来确定）
        # 碰撞的X/Y范围
        act_sx, act_sy = action.original_start
        act_ex, act_ey = action.original_end

        # 计算碰撞区域在线段上的投影
        collision_min_x = min(act_sx, act_ex) - self.clearance
        collision_max_x = max(act_sx, act_ex) + self.clearance
        collision_min_y = min(act_sy, act_ey) - self.clearance
        collision_max_y = max(act_sy, act_ey) + self.clearance

        result_segments = []
        has_drc = False

        if seg.is_horizontal:
            # 水平线段：沿X轴拆分
            result_segments, has_drc = self._split_and_shove_horizontal(
                seg, dx, dy,
                collision_min_x, collision_max_x, options
            )
        elif seg.is_vertical:
            # 垂直线段：沿Y轴拆分
            result_segments, has_drc = self._split_and_shove_vertical(
                seg, dx, dy,
                collision_min_y, collision_max_y, options
            )
        else:
            # 非正交线段：退化为整体推移
            return self._shove_entire_track(seg, dx, dy, options)

        return result_segments, has_drc

    def _split_and_shove_horizontal(
        self,
        seg: Segment,
        dx: float,
        dy: float,
        col_min_x: float,
        col_max_x: float,
        options: ShoveOptions,
    ) -> Tuple[List[Segment], bool]:
        """拆分并推移水平线段"""
        x1, y1 = seg.start.x, seg.start.y
        x2, y2 = seg.end.x, seg.end.y

        # 确保 x1 < x2
        if x1 > x2:
            x1, x2 = x2, x1

        segments = []
        has_drc = False

        # 前段（碰撞区之前，不动）
        if x1 < col_min_x:
            front_end_x = min(col_min_x, x2)
            front = Segment(
                start=Point(x1, y1), end=Point(front_end_x, y1),
                layer=seg.layer, width=seg.width
            )
            segments.append(front)

            # 过渡斜线（从前段端点到推移后的起点）
            if options.force_orthogonal:
                # L形过渡
                mid_y = y1 + dy
                transition = Segment(
                    start=Point(front_end_x, y1), end=Point(front_end_x, mid_y),
                    layer=seg.layer, width=seg.width
                )
                segments.append(transition)
            else:
                transition = Segment(
                    start=Point(front_end_x, y1),
                    end=Point(front_end_x, y1 + dy),
                    layer=seg.layer, width=seg.width
                )
                segments.append(transition)

        # 中段（推移区）
        mid_start_x = max(x1, col_min_x)
        mid_end_x = min(x2, col_max_x)
        if mid_start_x < mid_end_x:
            mid = Segment(
                start=Point(mid_start_x, y1 + dy),
                end=Point(mid_end_x, y1 + dy),
                layer=seg.layer, width=seg.width
            )
            segments.append(mid)
            has_drc = self._check_shove_drc(mid)

        # 后段（碰撞区之后，不动）
        if x2 > col_max_x:
            back_start_x = max(col_max_x, x1)

            # 过渡斜线
            if mid_start_x < mid_end_x:
                if options.force_orthogonal:
                    transition2 = Segment(
                        start=Point(mid_end_x, y1 + dy),
                        end=Point(mid_end_x, y1),
                        layer=seg.layer, width=seg.width
                    )
                    segments.append(transition2)

            back = Segment(
                start=Point(back_start_x, y1), end=Point(x2, y1),
                layer=seg.layer, width=seg.width
            )
            segments.append(back)

        # 如果没有碰撞区域在线段内，退化为整体推移
        if not segments:
            return self._shove_entire_track(seg, dx, dy, options)

        return segments, has_drc

    def _split_and_shove_vertical(
        self,
        seg: Segment,
        dx: float,
        dy: float,
        col_min_y: float,
        col_max_y: float,
        options: ShoveOptions,
    ) -> Tuple[List[Segment], bool]:
        """拆分并推移垂直线段"""
        x1, y1 = seg.start.x, seg.start.y
        x2, y2 = seg.end.x, seg.end.y

        # 确保 y1 < y2
        if y1 > y2:
            y1, y2 = y2, y1

        segments = []
        has_drc = False

        # 前段
        if y1 < col_min_y:
            front_end_y = min(col_min_y, y2)
            front = Segment(
                start=Point(x1, y1), end=Point(x1, front_end_y),
                layer=seg.layer, width=seg.width
            )
            segments.append(front)

            if options.force_orthogonal:
                transition = Segment(
                    start=Point(x1, front_end_y), end=Point(x1 + dx, front_end_y),
                    layer=seg.layer, width=seg.width
                )
                segments.append(transition)

        # 中段（推移区）
        mid_start_y = max(y1, col_min_y)
        mid_end_y = min(y2, col_max_y)
        if mid_start_y < mid_end_y:
            mid = Segment(
                start=Point(x1 + dx, mid_start_y),
                end=Point(x1 + dx, mid_end_y),
                layer=seg.layer, width=seg.width
            )
            segments.append(mid)
            has_drc = self._check_shove_drc(mid)

        # 后段
        if y2 > col_max_y:
            back_start_y = max(col_max_y, y1)

            if mid_start_y < mid_end_y:
                if options.force_orthogonal:
                    transition2 = Segment(
                        start=Point(x1 + dx, mid_end_y),
                        end=Point(x1, mid_end_y),
                        layer=seg.layer, width=seg.width
                    )
                    segments.append(transition2)

            back = Segment(
                start=Point(x1, back_start_y), end=Point(x1, y2),
                layer=seg.layer, width=seg.width
            )
            segments.append(back)

        if not segments:
            return self._shove_entire_track(seg, dx, dy, options)

        return segments, has_drc

    def _direction_to_delta(
        self,
        direction: ShoveDirection,
        distance: float,
    ) -> Tuple[float, float]:
        """将推挤方向和距离转换为 dx, dy 位移"""
        deltas = {
            ShoveDirection.UP: (0, distance),
            ShoveDirection.DOWN: (0, -distance),
            ShoveDirection.LEFT: (-distance, 0),
            ShoveDirection.RIGHT: (distance, 0),
            ShoveDirection.CUSTOM: (0, 0),
        }
        return deltas[direction]

    def _check_shove_drc(self, new_seg: Segment) -> bool:
        """检查推移后的新线段是否与其他障碍冲突"""
        for obs in self.obstacles:
            if obs.segment.layer != new_seg.layer:
                continue
            if self._segments_intersect(new_seg, obs.segment):
                return True
        return False

    def _ensure_orthogonal(self, seg: Segment) -> Segment:
        """确保线段是正交的（水平或垂直），如果不是则取主方向"""
        if seg.is_horizontal or seg.is_vertical:
            return seg

        dx = abs(seg.end.x - seg.start.x)
        dy = abs(seg.end.y - seg.start.y)

        if dx > dy:
            # 取水平
            return Segment(
                start=seg.start,
                end=Point(seg.end.x, seg.start.y),
                layer=seg.layer,
                width=seg.width,
            )
        else:
            # 取垂直
            return Segment(
                start=seg.start,
                end=Point(seg.start.x, seg.end.y),
                layer=seg.layer,
                width=seg.width,
            )

    # ── 级联推移 ──────────────────────────────────────────────

    def _cascade_shove(
        self,
        trigger_action: ShoveAction,
        depth: int = 0,
        visited: Optional[Set[Tuple]] = None,
        options: Optional[ShoveOptions] = None,
    ) -> "ShoveResult":
        """
        递归级联推移。

        当推挤一条线段后，新位置的线段可能碰撞其他线段。
        此方法递归处理这些碰撞。

        Args:
            trigger_action: 触发级联的推挤动作
            depth: 当前递归深度
            visited: 已访问的线段集合（防环路）
            options: 推挤参数

        Returns:
            ShoveResult: 级联推移的总结果
        """
        from routing.shove_types import ShoveResult as SR, CascadeEntry

        if options is None:
            options = ShoveOptions()

        # 深度限制
        if depth >= options.max_shove_depth:
            logger.debug(f"级联深度 {depth} 达到上限 {options.max_shove_depth}")
            return SR(
                success=False,
                message=f"级联深度达到上限 {options.max_shove_depth}",
            )

        # 初始化已访问集合
        if visited is None:
            visited = set()

        # 环路检测：用线段的起点+终点作为标识
        seg_key = (
            round(trigger_action.original_start[0], 2),
            round(trigger_action.original_start[1], 2),
            round(trigger_action.original_end[0], 2),
            round(trigger_action.original_end[1], 2),
        )
        if seg_key in visited:
            logger.debug(f"检测到环路，跳过已访问线段 {seg_key}")
            return SR(success=True, message="环路检测，跳过")
        visited.add(seg_key)

        # 找到被推移线段的新位置碰撞到的其他障碍
        new_start = trigger_action.new_start
        new_end = trigger_action.new_end

        new_seg = Segment(
            start=Point(new_start[0], new_start[1]),
            end=Point(new_end[0], new_end[1]),
            layer=trigger_action.original_layer,
            width=self.trace_width,
        )

        cascade_actions: List[ShoveAction] = []
        cascade_cost = 0.0
        all_sub_cascades: List[CascadeEntry] = []
        total_drc = 0

        for obs in self.obstacles:
            # 跳过自己（用原始位置比较）
            obs_key = (
                round(obs.segment.start.x, 2),
                round(obs.segment.start.y, 2),
                round(obs.segment.end.x, 2),
                round(obs.segment.end.y, 2),
            )
            if obs_key == seg_key:
                continue

            # 跳过固定障碍
            if obs.priority >= 100:
                continue

            # 跳过不同层
            if obs.segment.layer != new_seg.layer:
                continue

            # 检查碰撞
            if not self._segments_intersect(new_seg, obs.segment):
                continue

            # 发现级联碰撞！解析并推挤
            sub_action = self._resolve_collision(new_seg, obs, options)
            if sub_action is None:
                # 无法推挤此障碍
                total_drc += 1
                continue

            # 执行推挤
            new_segs, drc = self._shove_track(obs, sub_action, options)
            if drc:
                total_drc += 1

            cascade_actions.append(sub_action)
            cascade_cost += sub_action.cost + options.cost_per_cascade * (depth + 1)

            # 如果允许级联，递归处理
            if options.allow_cascade and new_segs:
                for ns in new_segs:
                    # 用新位置创建一个临时 action 用于递归
                    temp_action = ShoveAction(
                        original_start=(ns.start.x, ns.start.y),
                        original_end=(ns.end.x, ns.end.y),
                        original_layer=ns.layer,
                        new_start=(ns.start.x, ns.start.y),
                        new_end=(ns.end.x, ns.end.y),
                        direction=sub_action.direction,
                        distance=sub_action.distance,
                        cost=0,
                    )
                    sub_result = self._cascade_shove(
                        temp_action, depth + 1, visited.copy(), options
                    )
                    all_sub_cascades.extend(sub_result.cascades)
                    cascade_cost += sub_result.total_cost
                    total_drc += sub_result.drc_violations

                    if not sub_result.success and depth < options.max_shove_depth - 2:
                        # 级联失败，但不立即放弃（可能其他方向成功）
                        logger.debug(f"级联深度 {depth+1} 失败: {sub_result.message}")

        # 汇总结果
        entry = CascadeEntry(
            depth=depth + 1,
            trigger_action=trigger_action,
            resulting_actions=cascade_actions,
            total_cost=cascade_cost,
        )

        all_cascades = [entry] + all_sub_cascades
        max_depth = max((c.depth for c in all_cascades), default=0)

        result = SR(
            success=total_drc == 0 or len(cascade_actions) > 0,
            actions=cascade_actions,
            cascades=all_cascades,
            total_shoved_tracks=len(cascade_actions),
            total_shove_distance=sum(a.distance for a in cascade_actions),
            max_cascade_depth=max_depth,
            total_cost=cascade_cost,
            drc_violations=total_drc,
            message=f"级联推移完成，深度 {max_depth}，推挤 {len(cascade_actions)} 条线",
        )

        return result

    # ── 成本评估 ──────────────────────────────────────────────

    def _calculate_shove_cost(
        self,
        active_seg: Segment,
        obstacles_to_shove: List[Obstacle],
        options: Optional[ShoveOptions] = None,
    ) -> CostBreakdown:
        """
        计算推挤一组障碍物的完整成本。

        用于比较推挤 vs 绕行的成本，决定策略。

        Args:
            active_seg: 正在布的线段
            obstacles_to_shove: 需要推挤的障碍物列表
            options: 推挤参数

        Returns:
            CostBreakdown: 成本分解
        """
        if options is None:
            options = ShoveOptions()

        breakdown = CostBreakdown()

        for obs in obstacles_to_shove:
            action = self._resolve_collision(active_seg, obs, options)
            if action is None:
                breakdown.drc_penalty += options.cost_drc_violation
                continue

            breakdown.distance_cost += action.distance * options.cost_per_mm

            if options.allow_cross_net_shove:
                breakdown.cross_net_cost += options.cost_per_cross_net

            cascade_result = self._cascade_shove(action, options=options)
            if cascade_result.has_cascades:
                cascade_count = len(cascade_result.cascades)
                breakdown.cascade_cost += cascade_count * options.cost_per_cascade
                if cascade_result.drc_violations > 0:
                    breakdown.drc_penalty += (
                        cascade_result.drc_violations * options.cost_drc_violation * 0.5
                    )

            if action.causes_drc:
                breakdown.drc_penalty += options.cost_drc_violation

            if action.direction == ShoveDirection.CUSTOM:
                breakdown.ortho_penalty += options.cost_per_mm

        return breakdown

    def _should_shove_or_walkaround(
        self,
        active_seg: Segment,
        obstacles: List[Obstacle],
        walkaround_extra_length: float,
        options: Optional[ShoveOptions] = None,
    ) -> str:
        """
        决策：推挤还是绕行？

        Args:
            active_seg: 正在布的线段
            obstacles: 碰撞的障碍物列表
            walkaround_extra_length: 绕行所需额外长度（mm）
            options: 推挤参数

        Returns:
            "shove" 或 "walkaround" 或 "ripup"
        """
        if options is None:
            options = ShoveOptions()

        if not obstacles:
            return "shove"

        all_fixed = all(obs.priority >= 100 for obs in obstacles)
        if all_fixed:
            return "walkaround"

        shove_cost = self._calculate_shove_cost(active_seg, obstacles, options)

        walkaround_cost = (
            walkaround_extra_length * options.cost_per_mm
            + (options.cost_per_via if walkaround_extra_length > 3.0 else 0)
        )

        if shove_cost.drc_penalty > 0 and walkaround_cost < shove_cost.total:
            return "walkaround"

        if shove_cost.total <= walkaround_cost:
            return "shove"
        elif options.fallback_to_ripup and shove_cost.total > options.cost_drc_violation:
            return "ripup"
        else:
            return "walkaround"


def get_push_router() -> PushRouter:
    """获取推挤路由器实例"""
    return PushRouter()
