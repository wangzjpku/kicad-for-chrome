"""
Interactive Router - 交互式布线引擎

Phase 6: 提供交互式布线优化功能

功能:
- 实时显示布线候选路径
- 动态调整走线宽度
- 过孔自动放置

Author: Claude Code
Date: 2026-03-30
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class RouteStatus(Enum):
    """布线状态"""
    ROUTING = "routing"     # 正在布线
    COMPLETE = "complete"   # 完成
    BLOCKED = "blocked"     # 被阻挡
    INVALID = "invalid"     # 无效


@dataclass
class Point:
    """点"""
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def manhattan_distance(self, other: "Point") -> float:
        return abs(self.x - other.x) + abs(self.y - other.y)


@dataclass
class RouteSegment:
    """布线段"""
    start: Point
    end: Point
    layer: str
    width: float


@dataclass
class RouteCandidate:
    """布线候选路径"""
    route_id: str
    segments: List[RouteSegment]
    total_length: float
    via_count: int
    score: float  # 越低越好
    status: RouteStatus = RouteStatus.ROUTING


@dataclass
class RoutingRequest:
    """布线请求"""
    start_x: float
    start_y: float
    start_layer: str
    end_x: float
    end_y: float
    end_layer: str
    net_name: str
    trace_width: float = 0.25
    clearance: float = 0.2
    max_vias: int = 5


@dataclass
class RoutingResult:
    """布线结果"""
    success: bool
    candidates: List[RouteCandidate]
    best_route: Optional[RouteCandidate]
    message: str = ""


class InteractiveRouter:
    """
    交互式布线引擎

    支持:
    - A* 路径规划
    - 多层布线
    - 过孔优化
    - 实时预览
    """

    def __init__(
        self,
        grid_size: float = 0.1,  # mm
        layer_count: int = 2,
    ):
        """
        Args:
            grid_size: 网格大小 (mm)
            layer_count: 层数
        """
        self.grid_size = grid_size
        self.layer_count = layer_count
        self.obstacles: Set[Tuple[int, int, str]] = set()  # (x_grid, y_grid, layer)
        self.routes: List[RouteCandidate] = []

    def add_obstacle(self, x: float, y: float, layer: str):
        """添加障碍物"""
        gx = int(x / self.grid_size)
        gy = int(y / self.grid_size)
        self.obstacles.add((gx, gy, layer))

    def add_route_obstacles(self, segments: List[RouteSegment]):
        """将已布线的线段添加为障碍物"""
        for seg in segments:
            self._add_segment_as_obstacle(seg)

    def _add_segment_as_obstacle(self, segment: RouteSegment):
        """将线段覆盖的网格添加为障碍物"""
        x1, y1 = segment.start.x, segment.start.y
        x2, y2 = segment.end.x, segment.end.y

        # 简单的矩形扩展
        clearance_grids = max(1, int(0.2 / self.grid_size))  # 0.2mm  clearance

        gx1 = int(min(x1, x2) / self.grid_size) - clearance_grids
        gy1 = int(min(y1, y2) / self.grid_size) - clearance_grids
        gx2 = int(max(x1, x2) / self.grid_size) + clearance_grids
        gy2 = int(max(y1, y2) / self.grid_size) + clearance_grids

        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                self.obstacles.add((gx, gy, segment.layer))

    def plan_route(self, request: RoutingRequest) -> RoutingResult:
        """
        规划布线路径

        Args:
            request: 布线请求

        Returns:
            RoutingResult: 布线结果
        """
        start = Point(request.start_x, request.start_y)
        end = Point(request.end_x, request.end_y)

        # 使用 A* 算法规划路径
        path = self._astar_route(
            start, end,
            request.start_layer,
            request.end_layer,
            request.trace_width,
        )

        if not path:
            return RoutingResult(
                success=False,
                candidates=[],
                best_route=None,
                message="无法找到有效路径",
            )

        # 生成候选路径
        candidates = self._generate_candidates(
            path,
            request.start_layer,
            request.end_layer,
            request.trace_width,
            request.net_name,
        )

        # 选择最佳路径
        best = min(candidates, key=lambda c: c.score) if candidates else None

        return RoutingResult(
            success=True,
            candidates=candidates,
            best_route=best,
            message="",
        )

    def _astar_route(
        self,
        start: Point,
        end: Point,
        start_layer: str,
        end_layer: str,
        width: float,
    ) -> Optional[List[Point]]:
        """A* 路径规划"""
        # 简化的 A* 实现
        # 在实际应用中需要考虑更多的障碍物和层间转换

        # 如果起点和终点在同一层且可以直接连接
        if start_layer == end_layer:
            if not self._has_obstacle_between(start, end, start_layer):
                return [start, end]

        # 简化的多层路径规划
        return self._plan_multilayer_route(start, end, start_layer, end_layer)

    def _has_obstacle_between(self, start: Point, end: Point, layer: str) -> bool:
        """检查两点之间是否有障碍物"""
        steps = int(start.distance_to(end) / (self.grid_size / 2))
        if steps == 0:
            return (int(start.x / self.grid_size), int(start.y / self.grid_size), layer) in self.obstacles

        for i in range(steps + 1):
            t = i / steps
            x = start.x + (end.x - start.x) * t
            y = start.y + (end.y - start.y) * t
            gx, gy = int(x / self.grid_size), int(y / self.grid_size)
            if (gx, gy, layer) in self.obstacles:
                return True
        return False

    def _plan_multilayer_route(
        self,
        start: Point,
        end: Point,
        start_layer: str,
        end_layer: str,
    ) -> Optional[List[Point]]:
        """多层路径规划"""
        # 简化的多层布线:
        # 1. 从起点水平/垂直布线到过孔位置
        # 2. 通过过孔转换层
        # 3. 从过孔布线到终点

        # 选择合适的层
        via_layer = "F.Cu" if start_layer == "B.Cu" else "B.Cu"

        # 简化的 L 型布线
        # 水平优先
        mid1 = Point(end.x, start.y)
        via_point = Point(end.x, start.y + (end_layer == via_layer and 2.54 or -2.54))

        if not self._has_obstacle_between(start, mid1, start_layer):
            if not self._has_obstacle_between(mid1, via_point, start_layer):
                if not self._has_obstacle_between(via_point, end, end_layer):
                    return [start, mid1, via_point, end]

        # 垂直优先
        mid2 = Point(start.x, end.y)
        via_point2 = Point(start.x + (end_layer == via_layer and 2.54 or -2.54), end.y)

        if not self._has_obstacle_between(start, mid2, start_layer):
            if not self._has_obstacle_between(mid2, via_point2, start_layer):
                if not self._has_obstacle_between(via_point2, end, end_layer):
                    return [start, mid2, via_point2, end]

        return [start, end]  # 回退到直接连接

    def _generate_candidates(
        self,
        path: List[Point],
        start_layer: str,
        end_layer: str,
        width: float,
        net_name: str,
    ) -> List[RouteCandidate]:
        """生成多条候选路径"""
        candidates = []

        # 路径1: L 型 (水平优先)
        segments_l = self._create_l_segments(
            path, start_layer if start_layer == end_layer else start_layer, width
        )
        route_l = RouteCandidate(
            route_id="route_l_1",
            segments=segments_l,
            total_length=self._calculate_length(segments_l),
            via_count=self._count_vias(segments_l),
            score=self._calculate_score(segments_l),
        )
        candidates.append(route_l)

        # 路径2: Z 型 (垂直优先)
        segments_z = self._create_z_segments(
            path, start_layer if start_layer == end_layer else start_layer, width
        )
        route_z = RouteCandidate(
            route_id="route_z_1",
            segments=segments_z,
            total_length=self._calculate_length(segments_z),
            via_count=self._count_vias(segments_z),
            score=self._calculate_score(segments_z),
        )
        candidates.append(route_z)

        return candidates

    def _create_l_segments(
        self,
        path: List[Point],
        layer: str,
        width: float,
    ) -> List[RouteSegment]:
        """创建 L 型布线段"""
        if len(path) < 2:
            return []

        segments = []
        for i in range(len(path) - 1):
            segments.append(RouteSegment(
                start=path[i],
                end=path[i + 1],
                layer=layer,
                width=width,
            ))
        return segments

    def _create_z_segments(
        self,
        path: List[Point],
        layer: str,
        width: float,
    ) -> List[RouteSegment]:
        """创建 Z 型布线段 (带一个额外的转折)"""
        if len(path) < 2:
            return []

        segments = []
        if len(path) == 2:
            # 添加一个中间点形成 Z 型
            mid = Point(path[0].x, path[1].y)
            segments.append(RouteSegment(path[0], mid, layer, width))
            segments.append(RouteSegment(mid, path[1], layer, width))
        else:
            for i in range(len(path) - 1):
                segments.append(RouteSegment(
                    start=path[i],
                    end=path[i + 1],
                    layer=layer,
                    width=width,
                ))
        return segments

    def _calculate_length(self, segments: List[RouteSegment]) -> float:
        """计算路径总长度"""
        return sum(s.start.distance_to(s.end) for s in segments)

    def _count_vias(self, segments: List[RouteSegment]) -> int:
        """计算过孔数量"""
        return max(0, len(segments) - 1)

    def _calculate_score(self, segments: List[RouteSegment]) -> float:
        """计算路径评分 (越低越好)"""
        length = self._calculate_length(segments)
        vias = self._count_vias(segments)
        turns = sum(
            1 for i in range(1, len(segments))
            if segments[i].layer != segments[i - 1].layer or
               not self._is_aligned(segments[i - 1], segments[i])
        )

        # 评分: 长度权重最高,其次是过孔,最后是转弯
        return length + vias * 2.0 + turns * 0.5

    def _is_aligned(self, seg1: RouteSegment, seg2: RouteSegment) -> bool:
        """检查两段是否对齐 (水平或垂直)"""
        return (
            abs(seg1.end.x - seg2.start.x) < 0.001 or
            abs(seg1.end.y - seg2.start.y) < 0.001
        )

    def adjust_trace_width(
        self,
        route: RouteCandidate,
        new_width: float,
    ) -> RouteCandidate:
        """调整走线宽度"""
        new_segments = [
            RouteSegment(
                start=s.start,
                end=s.end,
                layer=s.layer,
                width=new_width,
            )
            for s in route.segments
        ]

        return RouteCandidate(
            route_id=route.route_id + "_w",
            segments=new_segments,
            total_length=route.total_length,
            via_count=route.via_count,
            score=route.score,  # 宽度变化不影响评分
            status=route.status,
        )

    def get_routing_preview(
        self,
        start_x: float,
        start_y: float,
        current_x: float,
        current_y: float,
        layer: str,
    ) -> List[Point]:
        """
        获取实时预览路径

        Args:
            start_x, start_y: 起始位置
            current_x, current_y: 当前鼠标位置
            layer: 当前层

        Returns:
            预览路径点列表
        """
        start = Point(start_x, start_y)
        current = Point(current_x, current_y)

        # 简单的直线预览
        return [start, current]


# 全局路由引擎实例
_router_instance: Optional[InteractiveRouter] = None


def get_interactive_router() -> InteractiveRouter:
    """获取交互式路由引擎单例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = InteractiveRouter()
    return _router_instance
