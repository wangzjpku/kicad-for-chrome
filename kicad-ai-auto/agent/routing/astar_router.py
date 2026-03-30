"""
A* Pathfinding Router - 避障布线算法

使用A*算法实现避障布线:
- 自动绕开已布线的走线
- 避开组件占用的区域
- 支持多层布线
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum
import heapq
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class Point:
    """2D点"""
    x: float
    y: float

    def __hash__(self):
        return hash((round(self.x, 3), round(self.y, 3)))

    def __eq__(self, other):
        return abs(self.x - other.x) < 0.001 and abs(self.y - other.y) < 0.001

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Obstacle:
    """障碍物"""
    x: float
    y: float
    width: float
    height: float
    layer: str
    clearance: float = 0.2  # 安全间距

    def contains_point(self, px: float, py: float) -> bool:
        """检查点是否在障碍物内（包含安全间距）"""
        return (
            self.x - self.clearance <= px <= self.x + self.width + self.clearance and
            self.y - self.clearance <= py <= self.y + self.height + self.clearance
        )

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """获取边界（包含安全间距）"""
        return (
            self.x - self.clearance,
            self.y - self.clearance,
            self.x + self.width + self.clearance,
            self.y + self.height + self.clearance
        )


@dataclass
class PathNode:
    """路径节点"""
    point: Point
    g_cost: float = 0  # 起点到当前节点的代价
    h_cost: float = 0  # 当前节点到终点的估计代价
    parent: Optional['PathNode'] = None

    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost

    def __lt__(self, other):
        return self.f_cost < other.f_cost


class AStarRouter:
    """
    A* 避障布线器

    特性:
    - A* 寻路算法
    - 45度走线支持
    - 多层布线
    - 避障功能
    """

    def __init__(
        self,
        board_width: float = 100,
        board_height: float = 80,
        grid_size: float = 0.5,
        trace_width: float = 0.25,
        clearance: float = 0.2
    ):
        self.board_width = board_width
        self.board_height = board_height
        self.grid_size = grid_size
        self.trace_width = trace_width
        self.clearance = clearance

        # 障碍物列表
        self.obstacles: List[Obstacle] = []

        # 已占用网格
        self.occupied_cells: Set[Tuple[int, int, str]] = set()

    def add_obstacle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        layer: str = "F.Cu",
        clearance: Optional[float] = None
    ):
        """添加障碍物"""
        if clearance is None:
            clearance = self.clearance + self.trace_width / 2

        obstacle = Obstacle(
            x=x, y=y,
            width=width, height=height,
            layer=layer,
            clearance=clearance
        )
        self.obstacles.append(obstacle)

        # 标记占用的网格
        self._mark_obstacle_cells(obstacle)

    def add_component_obstacle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        layer: str = "F.Cu"
    ):
        """添加组件作为障碍物"""
        self.add_obstacle(x, y, width, height, layer, clearance=self.clearance)

    def add_trace_obstacle(
        self,
        x1: float, y1: float,
        x2: float, y2: float,
        layer: str = "F.Cu"
    ):
        """添加走线作为障碍物"""
        # 将走线转换为矩形障碍物
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length < 0.001:
            return

        # 走线的中点和宽度
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # 走线方向
        angle = math.atan2(y2 - y1, x2 - x1)

        # 走线的包围盒
        cos_a = abs(math.cos(angle))
        sin_a = abs(math.sin(angle))
        box_width = length * cos_a + self.trace_width * sin_a
        box_height = length * sin_a + self.trace_width * cos_a

        self.add_obstacle(
            mid_x - box_width / 2,
            mid_y - box_height / 2,
            box_width,
            box_height,
            layer,
            clearance=self.clearance
        )

    def _mark_obstacle_cells(self, obstacle: Obstacle):
        """标记障碍物占用的网格"""
        x1, y1, x2, y2 = obstacle.get_bounds()

        gx1 = int(x1 / self.grid_size)
        gy1 = int(y1 / self.grid_size)
        gx2 = int(x2 / self.grid_size) + 1
        gy2 = int(y2 / self.grid_size) + 1

        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                self.occupied_cells.add((gx, gy, obstacle.layer))

    def _is_valid_position(self, x: float, y: float, layer: str) -> bool:
        """检查位置是否有效（不在障碍物内，在板子范围内）"""
        # 检查板子边界
        if x < 0 or x > self.board_width or y < 0 or y > self.board_height:
            return False

        # 检查是否在障碍物内
        for obs in self.obstacles:
            if obs.layer == layer and obs.contains_point(x, y):
                return False

        return True

    def _heuristic(self, a: Point, b: Point) -> float:
        """启发式函数 - 使用欧几里得距离"""
        return a.distance_to(b)

    def _get_neighbors(self, node: PathNode, layer: str) -> List[Point]:
        """获取相邻节点（支持8方向移动）"""
        neighbors = []
        x, y = node.point.x, node.point.y

        # 8个方向
        directions = [
            (self.grid_size, 0),      # 右
            (-self.grid_size, 0),     # 左
            (0, self.grid_size),      # 上
            (0, -self.grid_size),     # 下
            (self.grid_size, self.grid_size),    # 右上
            (self.grid_size, -self.grid_size),   # 右下
            (-self.grid_size, self.grid_size),   # 左上
            (-self.grid_size, -self.grid_size),  # 左下
        ]

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self._is_valid_position(nx, ny, layer):
                neighbors.append(Point(nx, ny))

        return neighbors

    def _get_movement_cost(self, from_point: Point, to_point: Point) -> float:
        """计算移动代价"""
        dx = abs(to_point.x - from_point.x)
        dy = abs(to_point.y - from_point.y)

        # 对角线移动代价为 sqrt(2)
        if dx > 0 and dy > 0:
            return self.grid_size * 1.414
        return self.grid_size

    def find_path(
        self,
        start: Point,
        end: Point,
        layer: str = "F.Cu",
        max_iterations: int = 10000
    ) -> Optional[List[Point]]:
        """
        使用A*算法寻找路径

        Args:
            start: 起点
            end: 终点
            layer: 布线层
            max_iterations: 最大迭代次数

        Returns:
            路径点列表，如果找不到则返回None
        """
        # 检查起点和终点是否有效
        if not self._is_valid_position(start.x, start.y, layer):
            logger.warning(f"起点无效: ({start.x}, {start.y})")
            return None
        if not self._is_valid_position(end.x, end.y, layer):
            logger.warning(f"终点无效: ({end.x}, {end.y})")
            return None

        # 初始化
        start_node = PathNode(
            point=start,
            g_cost=0,
            h_cost=self._heuristic(start, end)
        )

        open_set: List[PathNode] = [start_node]
        closed_set: Set[Tuple[float, float]] = set()

        # 用于快速查找已访问的节点
        g_costs: Dict[Tuple[float, float], float] = {(start.x, start.y): 0}

        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1

            # 获取f_cost最小的节点
            current = heapq.heappop(open_set)
            current_key = (round(current.point.x, 3), round(current.point.y, 3))

            # 检查是否到达终点
            if current.point.distance_to(end) < self.grid_size:
                # 重建路径
                path = []
                node = current
                while node:
                    path.append(node.point)
                    node = node.parent
                return path[::-1]  # 反转路径

            # 标记为已访问
            if current_key in closed_set:
                continue
            closed_set.add(current_key)

            # 探索相邻节点
            for neighbor_point in self._get_neighbors(current, layer):
                neighbor_key = (round(neighbor_point.x, 3), round(neighbor_point.y, 3))

                if neighbor_key in closed_set:
                    continue

                tentative_g = current.g_cost + self._get_movement_cost(
                    current.point, neighbor_point
                )

                if neighbor_key not in g_costs or tentative_g < g_costs[neighbor_key]:
                    g_costs[neighbor_key] = tentative_g

                    neighbor_node = PathNode(
                        point=neighbor_point,
                        g_cost=tentative_g,
                        h_cost=self._heuristic(neighbor_point, end),
                        parent=current
                    )
                    heapq.heappush(open_set, neighbor_node)

        if iterations >= max_iterations:
            logger.warning(f"A*寻路超过最大迭代次数: {max_iterations}")

        return None  # 未找到路径

    def route_with_45_degree(
        self,
        start: Point,
        end: Point,
        layer: str = "F.Cu"
    ) -> List[Tuple[Point, Point]]:
        """
        使用45度走线布线

        Returns:
            线段列表 [(起点, 终点), ...]
        """
        # 先尝试A*寻路
        path = self.find_path(start, end, layer)

        if path and len(path) > 1:
            # 转换为线段
            segments = []
            for i in range(len(path) - 1):
                segments.append((path[i], path[i + 1]))
            return segments

        # 如果A*失败，使用简化的45度曼哈顿走线
        return self._fallback_45_degree_route(start, end, layer)

    def _fallback_45_degree_route(
        self,
        start: Point,
        end: Point,
        layer: str
    ) -> List[Tuple[Point, Point]]:
        """备用的45度走线方案"""
        segments = []
        x1, y1 = start.x, start.y
        x2, y2 = end.x, end.y

        dx = x2 - x1
        dy = y2 - y1

        if abs(dx) < 0.01 or abs(dy) < 0.01:
            # 直线
            return [(start, end)]

        # 45度走线
        if abs(dx) > abs(dy):
            # 先斜线再水平
            diag_len = abs(dy)
            diag_x = x1 + (diag_len if dx > 0 else -diag_len)
            mid1 = Point(diag_x, y2)
            segments.append((start, mid1))
            segments.append((mid1, end))
        else:
            # 先斜线再垂直
            diag_len = abs(dx)
            diag_y = y1 + (diag_len if dy > 0 else -diag_len)
            mid1 = Point(x2, diag_y)
            segments.append((start, mid1))
            segments.append((mid1, end))

        return segments

    def clear_obstacles(self):
        """清除所有障碍物"""
        self.obstacles.clear()
        self.occupied_cells.clear()


def create_router(
    board_width: float = 100,
    board_height: float = 80,
    trace_width: float = 0.25
) -> AStarRouter:
    """创建路由器实例"""
    return AStarRouter(
        board_width=board_width,
        board_height=board_height,
        trace_width=trace_width
    )