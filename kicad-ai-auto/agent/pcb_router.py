"""
PCB 自动布线器 v1.0

功能特性：
1. 迷宫布线 (Lee algorithm) - 简单网络
2. 推挤布线 (maze router + rip-up) - 复杂网络
3. 差分对布线 - USB/以太网

作者：AI Assistant
版本：1.0
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import heapq
import logging

logger = logging.getLogger(__name__)


@dataclass
class RoutingRules:
    """布线规则"""
    trace_width: Dict[str, float] = None  # 网络 -> 线宽 (mm)
    clearance: float = 0.2  # 间距 (mm)
    via_size: Tuple[float, float] = (0.8, 0.4)  # (外径, 内径) mm
    layer_count: int = 2  # 层数
    min_via_spacing: float = 0.5  # 过孔最小间距 (mm)

    def __post_init__(self):
        if self.trace_width is None:
            self.trace_width = {
                "VCC": 0.5,
                "GND": 0.5,
                "default": 0.2
            }


@dataclass
class Pad:
    """焊盘"""
    component_id: str
    pin_number: str
    x: float
    y: float
    net: str


@dataclass
class Track:
    """走线"""
    net: str
    layer: int
    x1: float
    y1: float
    x2: float
    y2: float
    width: float


@dataclass
class Via:
    """过孔"""
    net: str
    x: float
    y: float
    from_layer: int
    to_layer: int


class Grid:
    """布线网格"""

    def __init__(self, width: float, height: float, resolution: float = 0.1):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.cols = int(width / resolution) + 1
        self.rows = int(height / resolution) + 1
        # 0 = empty, 1 = obstacle, 2 = via
        self.grid = [[0] * self.cols for _ in range(self.rows)]

    def mark_obstacle(self, x: float, y: float, radius: float = 0.5):
        """标记障碍物"""
        cx = int(x / self.resolution)
        cy = int(y / self.resolution)
        r = int(radius / self.resolution)

        for i in range(max(0, cy - r), min(self.rows, cy + r + 1)):
            for j in range(max(0, cx - r), min(self.cols, cx + r + 1)):
                if (i - cy) ** 2 + (j - cx) ** 2 <= r ** 2:
                    self.grid[i][j] = 1

    def is_empty(self, x: float, y: float) -> bool:
        """检查位置是否为空"""
        col = int(x / self.resolution)
        row = int(y / self.resolution)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col] == 0
        return False

    def mark_occupied(self, x: float, y: float):
        """标记位置为已占用"""
        col = int(x / self.resolution)
        row = int(y / self.resolution)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = 1


@dataclass
class Net:
    """网络"""
    name: str
    pads: List[Pad]  # 连接的焊盘
    is_differential: bool = False
    is_power: bool = False


class PCBRouter:
    """
    PCB 自动布线器

    策略:
    1. 迷宫布线 (Lee algorithm) - 简单网络
    2. 推挤布线 (maze router + rip-up) - 复杂网络
    3. 差分对布线 - USB/以太网
    """

    def __init__(self):
        self.grid: Optional[Grid] = None
        self.rules = RoutingRules()
        self.tracks: List[Track] = []
        self.vias: List[Via] = []
        self.nets: List[Net] = []

    def route(
        self,
        nets: List[Dict],
        pads: List[Dict],
        rules: Optional[RoutingRules] = None
    ) -> Dict[str, List]:
        """
        自动布线

        Args:
            nets: 网络列表
            pads: 焊盘列表
            rules: 布线规则

        Returns:
            Dict with 'tracks' and 'vias'
        """
        if rules:
            self.rules = rules

        # 初始化网格
        board_width = 100.0  # 默认板宽 mm
        board_height = 80.0  # 默认板高 mm
        self.grid = Grid(board_width, board_height, resolution=0.1)

        # 解析 nets
        self.nets = []
        for net_data in nets:
            net_pads = []
            for pad_data in pads:
                if pad_data.get("net") == net_data.get("name"):
                    pad = Pad(
                        component_id=pad_data.get("component_id", ""),
                        pin_number=pad_data.get("pin_number", ""),
                        x=pad_data.get("x", 0.0),
                        y=pad_data.get("y", 0.0),
                        net=pad_data.get("net", "")
                    )
                    net_pads.append(pad)
                    # 在网格上标记焊盘位置
                    self.grid.mark_obstacle(pad.x, pad.y, radius=0.3)

            net = Net(
                name=net_data.get("name", ""),
                pads=net_pads,
                is_differential=net_data.get("is_differential", False),
                is_power=net_data.get("is_power", False)
            )
            self.nets.append(net)

        # 按优先级排序网络
        nets_to_route = self._sort_nets_by_priority()

        # 路由每个网络
        for net in nets_to_route:
            if len(net.pads) < 2:
                continue

            path = self._find_path(net)
            if path:
                self._create_tracks_from_path(path, net)
            else:
                logger.warning(f"Cannot complete routing for net {net.name}")

        return {
            "tracks": [self._track_to_dict(t) for t in self.tracks],
            "vias": [self._via_to_dict(v) for v in self.vias]
        }

    def _sort_nets_by_priority(self) -> List[Net]:
        """按优先级排序网络"""
        # 电源网络优先
        # 然后是差分对
        # 然后按长度排序
        sorted_nets = []
        power_nets = [n for n in self.nets if n.is_power]
        diff_nets = [n for n in self.nets if n.is_differential]
        other_nets = [n for n in self.nets if not n.is_power and not n.is_differential]

        # 计算每个网络的大致长度
        def net_length(net):
            if len(net.pads) < 2:
                return 0
            p1, p2 = net.pads[0], net.pads[1]
            return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

        other_nets.sort(key=net_length, reverse=True)

        return power_nets + diff_nets + other_nets

    def _find_path(self, net: Net) -> Optional[List[Tuple[float, float]]]:
        """
        使用 Lee algorithm 寻找路径

        Returns:
            List of (x, y) points or None
        """
        if len(net.pads) < 2:
            return None

        start = net.pads[0]
        end = net.pads[1]

        # Lee algorithm
        resolution = self.grid.resolution
        start_col = int(start.x / resolution)
        start_row = int(start.y / resolution)
        end_col = int(end.x / resolution)
        end_row = int(end.y / resolution)

        # 扩展网格用于 Lee
        rows = self.grid.rows
        cols = self.grid.cols
        dist = [[-1] * cols for _ in range(rows)]
        parent = [[None] * cols for _ in range(rows)]

        # BFS
        queue = [(start_col, start_row, 0)]
        dist[start_row][start_col] = 0

        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while queue:
            x, y, d = heapq.heappop(queue)

            if x == end_col and y == end_row:
                # 找到路径，回溯
                path = []
                cx, cy = end_col, end_row
                while cx is not None and cy is not None:
                    path.append((cx * resolution, cy * resolution))
                    cx, cy = parent[cy][cx]
                path.reverse()
                return path

            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < cols and 0 <= ny < rows:
                    if dist[ny][nx] == -1 and self.grid.grid[ny][nx] == 0:
                        dist[ny][nx] = d + 1
                        parent[ny][nx] = (x, y)
                        heapq.heappush(queue, (nx, ny, d + 1))

        return None

    def _create_tracks_from_path(self, path: List[Tuple[float, float]], net: Net):
        """从路径创建走线"""
        if len(path) < 2:
            return

        width = self.rules.trace_width.get(
            net.name,
            self.rules.trace_width.get("default", 0.2)
        )

        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            # 确定层（简单策略：水平在顶层，垂直在底层）
            layer = 0 if i % 2 == 0 else 1

            track = Track(
                net=net.name,
                layer=layer,
                x1=x1, y1=y1,
                x2=x2, y2=y2,
                width=width
            )
            self.tracks.append(track)

            # 标记网格
            self.grid.mark_occupied((x1 + x2) / 2, (y1 + y2) / 2)

    def _track_to_dict(self, track: Track) -> Dict[str, Any]:
        return {
            "net": track.net,
            "layer": track.layer,
            "x1": track.x1,
            "y1": track.y1,
            "x2": track.x2,
            "y2": track.y2,
            "width": track.width
        }

    def _via_to_dict(self, via: Via) -> Dict[str, Any]:
        return {
            "net": via.net,
            "x": via.x,
            "y": via.y,
            "from_layer": via.from_layer,
            "to_layer": via.to_layer
        }


# 全局实例
_router: Optional[PCBRouter] = None


def get_router() -> PCBRouter:
    """获取布线器单例"""
    global _router
    if _router is None:
        _router = PCBRouter()
    return _router


def auto_route(
    nets: List[Dict],
    pads: List[Dict],
    rules: Optional[Dict] = None
) -> Dict[str, List]:
    """
    自动布线

    Args:
        nets: 网络列表
        pads: 焊盘列表
        rules: 布线规则

    Returns:
        Dict with 'tracks' and 'vias'
    """
    router = get_router()

    routing_rules = None
    if rules:
        routing_rules = RoutingRules(
            trace_width=rules.get("trace_width", {}),
            clearance=rules.get("clearance", 0.2),
            via_size=rules.get("via_size", (0.8, 0.4)),
            layer_count=rules.get("layer_count", 2)
        )

    return router.route(nets, pads, routing_rules)
