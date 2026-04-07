# -*- coding: utf-8 -*-
"""
拓扑变更器 v3.0
实现真实的走线重新布线
"""
import math
import random
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

from iteration.utils.design_change import Modification, ModificationType, DesignChange


class GridNode:
    """网格节点 - 用于A*寻路"""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.g = 0      # g值: 从起点到当前点的实际代价
        self.h = 0      # h值: g + 启发式估计
        self.f = float('inf')  # f值: g + h
        self.parent: Optional['GridNode'] = None
        self.walkable = True

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


@dataclass
class Obstacle:
    """障碍物"""
    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float) -> bool:
        """检查点是否在障碍物内"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)


class TopologyChanger:
    """拓扑变更器 - 重新布线网络"""

    GRID_SIZE = 0.5  # 0.5mm网格
    SAFETY_MARGIN = 0.3  # 安全间距

    MIN_TRACK_WIDTH = 0.15
    MAX_ITERATIONS = 1000

    def __init__(self, board_width: float, 100, board_height: float = 80):
        self.board_width = board_width
        self.board_height = board_height
        self.grid_cols = int(board_width / self.GRID_SIZE)
        self.grid_rows = int(board_height / self.GRID_SIZE)

        self.grid: Dict[Tuple[int, int], GridNode] = {}
        self.obstacles: List[Obstacle] = []

    def reroute_net(self, pcb_data: Dict, net_name: str,
                   connected_pins: List[Dict]) -> DesignChange:
        """
        重新布线指定网络

        Args:
            pcb_data: 当前PCB数据
            net_name: 网络名称
            connected_pins: 连接到该网络的引脚列表

        Returns:
            DesignChange: 设计变更记录
        """
        # 1. 识别障碍物
        self._identify_obstacles(pcb_data, net_name)

        # 2. 初始化网格
        self._init_grid()

        # 3. 标记障碍物区域
        self._mark_obstacles()

        # 4. 获取连接点坐标
        pins = self._extract_pin_positions(connected_pins)

        if len(pins) < 2:
            return DesignChange(
                change_id=f"reroute-{net_name}",
                change_type="topology",
                target_dimension="功能正确性",
                description=f"网络 {net_name} 连接点不足",
            )

        # 5. 使用MST找到连接所有引脚的最小生成树
        mst_edges = self._minimum_spanning_tree(pins)

        # 6. 为每条边找到路径
        modifications = []
        old_tracks = [t for t in pcb_data.get('tracks', []) if t.get('net') == net_name]

        for start_pin, end_pin in mst_edges:
                path = self._find_path(start_pin, end_pin)

                if path:
                    # 生成走线修改
                    for i in range(len(path) - 1):
                        mod = Modification(
                            action=ModificationType.ADD if i >= len(old_tracks) else ModificationType.REROUTE,
                            target_type="track",
                            target_ref=f"track-{net_name}-{i}",
                            after={
                                'id': f"track-{net_name}-{i}",
                                'start': {'x': path[i]['x'], 'y': path[i]['y']},
                                'end': {'x': path[i+1]['x'], 'y': path[i+1]['y']},
                                'net': net_name,
                                'width': self._get_track_width(net_name),
                                'layer': 'F.Cu',
                            },
                            details=f"Reroute {net_name} segment {i+1}"
                        )
                        modifications.append(mod)
                    if i < len(old_tracks):
                        mod.before = old_tracks[i]

                        modifications.append(mod)
                else:
                    # 没找到路径，保留直线连接
                    mod = Modification(
                        action=ModificationType.ADD,
                        target_type="track",
                        target_ref=f"track-{net_name}-direct",
                        after={
                            'id': f"track-{net_name}-direct",
                            'start': {'x': start_pin['x'], 'y': start_pin['y']},
                            'end': {'x': end_pin['x'], 'y': end_pin['y']},
                            'net': net_name,
                            'width': self._get_track_width(net_name),
                            'layer': 'F.Cu',
                        },
                        details=f"Direct route for {net_name}"
                    )
                    modifications.append(mod)

        # 删除多余的旧走线
        if len(modifications) < len(old_tracks):
            for i in range(len(modifications), len(old_tracks)):
                mod = Modification(
                    action=ModificationType.REMOVE,
                    target_type="track",
                    target_ref=old_tracks[i].get('id', f"old-{i}"),
                    before=old_tracks[i],
                    details=f"Remove unused track for {net_name}"
                )
                modifications.append(mod)
        return DesignChange(
            change_id=f"reroute-{net_name}-{random.randint(1000, 9999)}",
            change_type="topology",
            target_dimension="功能正确性",
            modifications=modifications,
            description=f"Rerouted {net_name} with {len(pins)} pins, {len(mst_edges)} edges",
            expected_improvement=2.0,
        )
    def _identify_obstacles(self, pcb_data: Dict, exclude_net: str):
        """识别障碍物 - 其他网络的走线、元件焊盘等"""
        self.obstacles = []
        # 元件作为障碍物
        for fp in pcb_data.get('footprints', []):
            # 简化为元件的外接框
            x, y = fp.get('x', 0), fp.get('y', 0)
            # 假设元件大小
            width = 5
            height = 5
            self.obstacles.append(Obstacle(x - width/2, y - height/2, width, height))
        # 其他网络的走线作为障碍物
        for track in pcb_data.get('tracks', []):
            if track.get('net') != exclude_net:
                start = track.get('start', {})
                end = track.get('end', {})
                # 走线宽度
                width = track.get('width', 0.2) + self.SAFETY_MARGIN
                # 简化为线段
                x1, y1 = start.get('x', 0), start.get('y', 0)
                x2, y2 = end.get('x', 0), end.get('y', 0)
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)
                self.obstacles.append(Obstacle(
                    min_x - width/2, min_y - width/2,
                    max_x - min_x + width, max_y - min_y + width
                ))
        # 过孔作为障碍物
        for via in pcb_data.get('vias', []):
                x, y = via.get('x', 0), via.get('y', 0)
                size = via.get('size', 0.6)
                self.obstacles.append(Obstacle(
                    x - size/2, y - size/2, size, size
                ))
    def _init_grid(self):
        """初始化搜索网格"""
        self.grid = {}
        for col in range(self.grid_cols):
            for row in range(self.grid_rows):
                node = GridNode(col * self.GRID_SIZE, row * self.GRID_SIZE)
                self.grid[(col, row)] = node
    def _mark_obstacles(self):
        """标记障碍物区域为不可通行"""
        for obs in self.obstacles:
                # 计算障碍物覆盖的网格范围
                min_col = max(0, int((obs.x - self.SAFETY_MARGIN) / self.GRID_SIZE))
                max_col = min(self.grid_cols - 1, int((obs.x + obs.width + self.SAFETY_MARGIN) / self.GRID_SIZE))
                min_row = max(0, int((obs.y - self.SAFETY_MARGIN) / self.GRID_SIZE))
                max_row = min(self.grid_rows - 1, int((obs.y + obs.height + self.SAFETY_MARGIN) / self.GRID_SIZE))
                for col in range(min_col, max_col + 1):
                    for row in range(min_row, max_row + 1):
                        if (col, row) in self.grid:
                            self.grid[(col, row)].walkable = False
    def _extract_pin_positions(self, connected_pins: List[Dict]) -> List[Dict]:
        """提取引脚位置"""
        positions = []
        for pin in connected_pins:
            if 'x' in pin and 'y' in pin:
                positions.append({'x': pin['x'], 'y': pin['y']})
            elif 'position' in pin:
                positions.append(pin['position'])
        return positions
    def _minimum_spanning_tree(self, pins: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """使用Prim算法找到MST"""
        if len(pins) < 2:
            return []
        edges = []
        # 计算所有边
        for i, p1 in enumerate(pins):
            for j, p2 in enumerate(pins):
                if i < j:
                    dist = math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
                    edges.append((dist, p1, p2))
        # 排序
        edges.sort(key=lambda e: e[0])
        # Kruskal算法
        parent = {i: i for i in range(len(pins))}
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        mst_edges = []
        for dist, p1, p2 in edges:
            i, j = pins.index(p1), pins.index(p2)
            if find(i) != find(j):
                parent[find(i)] = find(j)
                mst_edges.append((p1, p2))
                if len(mst_edges) == len(pins) - 1:
                    break
        return mst_edges
    def _find_path(self, start: Dict, end: Dict) -> Optional[List[Dict]]:
        """A*寻路算法"""
        # 转换为网格坐标
        start_col = int(start['x'] / self.GRID_SIZE)
        start_row = int(start['y'] / self.GRID_SIZE)
        end_col = int(end['x'] / self.GRID_SIZE)
        end_row = int(end['y'] / self.GRID_SIZE)
        # 边界检查
        if (start_col, start_row) not in self.grid or (end_col, end_row) not in self.grid:
            return None
        # 重置网格
        for node in self.grid.values():
            node.g = float('inf')
            node.h = 0
            node.f = float('inf')
            node.parent = None
        # 初始化起点
        start_node = self.grid.get((start_col, start_row))
        end_node = self.grid.get((end_col, end_row))
        if not start_node or not end_node:
            return None
        start_node.g = 0
        start_node.h = self._heuristic(start_node, end_node)
        start_node.f = start_node.h
        open_set = {start_node}
        closed_set: Set = set()
        # A*搜索
        iterations = 0
        while open_set and iterations < self.MAX_ITERATIONS:
            iterations += 1
            # 找f值最小的节点
            current = min(open_set, key=lambda n: n.f)
            open_set.remove(current)
            if current == end_node:
                # 找到路径， return self._reconstruct_path(current)
            closed_set.add(current)
            # 扩展邻居
            for neighbor in self._get_neighbors(current):
                if neighbor in closed_set:
                    continue
                tentative_g = current.g + self._distance(current, neighbor)
                if tentative_g < neighbor.g:
                    neighbor.g = tentative_g
                    neighbor.h = self._heuristic(neighbor, end_node)
                    neighbor.f = neighbor.g + neighbor.h
                    neighbor.parent = current
                    open_set.add(neighbor)
        return None  # 没找到路径
    def _heuristic(self, node: GridNode, end: GridNode) -> float:
        """启发式估计 - 曼哈顿距离"""
        return abs(node.x - end.x) + abs(node.y - end.y)
    def _distance(self, a: GridNode, b: GridNode) -> float:
        """两点间的距离"""
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)
    def _get_neighbors(self, node: GridNode) -> List[GridNode]:
        """获取相邻节点"""
        neighbors = []
        col = int(node.x / self.GRID_SIZE)
        row = int(node.y / self.GRID_SIZE)
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = col + dc, row + dr
            if (nc, nr) in self.grid and self.grid[(nc, nr)].walkable:
                neighbors.append(self.grid[(nc, nr)])
        return neighbors
    def _reconstruct_path(self, end_node: GridNode) -> List[Dict]:
        """从终点回溯重建路径"""
        path = []
        current = end_node
        while current:
            path.append({'x': current.x, 'y': current.y})
            current = current.parent
        path.reverse()
        return path
    def _get_track_width(self, net_name: str) -> float:
        """根据网络类型获取走线宽度"""
        power_nets = ['VCC', '3V3', 'VIN', 'VBUS', 'GND', '+5V', '+3V3', '+12V']
        if any(pn in net_name.upper() for pn in power_nets):
            return 0.25  # 电源走线更宽
        return 0.15  # 信号走线

 def optimize_routing_topology(self, pcb_data: Dict, score_report) -> List[DesignChange]:
        """
        根据评分报告优化布线拓扑

        Args:
            pcb_data: 当前PCB数据
            score_report: 质量评分报告
        Returns:
            List[DesignChange]: 优化变更列表
        """
        changes = []
        # 分析低分维度
        for dim in score_report.pcb_scores:
            if dim.name == "功能正确性" and dim.percentage < 90:
                # 找出未完成的网络
                unrouted_nets = self._find_unrouted_nets(pcb_data)
                for net_name in unrouted_nets:
                    # 获取该网络的连接引脚
                    pins = self._get_net_pins(pcb_data, net_name)
                    if pins:
                        change = self.reroute_net(pcb_data, net_name, pins)
                        changes.append(change)
            elif dim.name == "信号完整性" and dim.percentage < 80:
                # 优化高速信号网络
                high_speed_nets = self._find_high_speed_nets(pcb_data)
                for net_name in high_speed_nets:
                    pins = self._get_net_pins(pcb_data, net_name)
                    if pins:
                        change = self.reroute_net(pcb_data, net_name, pins)
                        changes.append(change)
        return changes
    def _find_unrouted_nets(self, pcb_data: Dict) -> List[str]:
        """找出未布线的网络"""
        all_nets = {n.get('name') for n in pcb_data.get('nets', [])}
        routed_nets = {t.get('net') for t in pcb_data.get('tracks', [])}
        return list(all_nets - routed_nets)
    def _find_high_speed_nets(self, pcb_data: Dict) -> List[str]:
        """找出高速信号网络"""
        high_speed_keywords = ['USB', 'CLK', 'XTAL', 'D+', 'D-', 'SD', 'DATA']
        high_speed_nets = []
        for net in pcb_data.get('nets', []):
            name = net.get('name', '').upper()
            if any(kw in name for kw in high_speed_keywords):
                high_speed_nets.append(net.get('name'))
        return high_speed_nets
    def _get_net_pins(self, pcb_data: Dict, net_name: str) -> List[Dict]:
        """获取网络的所有连接引脚"""
        pins = []
        for fp in pcb_data.get('footprints', []):
            for pad in fp.get('pads', []):
                if pad.get('net') == net_name:
                    pins.append({
                        'x': fp.get('x') + pad.get('x', 0),  # 简化
 pad offset
                        'y': fp.get('y') + pad.get('y', 0),
                        'reference': fp.get('reference'),
                        'pad': pad.get('number'),
                    })
        return pins
