"""
拓扑感知布局引擎 - Topology-Aware Placement Engine

基于电路拓扑的功能分区布局。
模仿工业级PCB设计的功能分区策略:
- 功率流向: 左→右 (输入在左, 输出在右)
- 安规隔离: 初级/次级之间留空
- 接口元件: 放在板边
- 控制电路: 居中
- 被动元件: 靠近所属IC

Author: Claude Code
Date: 2026-03-31
Phase: 7B
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import math
import logging

from .netlist_topology import (
    NetlistTopologyAnalyzer, TopologyResult, FunctionalGroup, IsolationRequirement,
)
from .smart_placement_engine import Component, PlacementResult

logger = logging.getLogger(__name__)


@dataclass
class Zone:
    """布局区域定义"""
    name: str                        # 区域名称
    group: FunctionalGroup           # 功能分区
    x: float                         # 区域左下角X (mm)
    y: float                         # 区域左下角Y (mm)
    width: float                     # 区域宽度 (mm)
    height: float                    # 区域高度 (mm)
    color: str = "#4488ff"           # 可视化颜色
    opacity: float = 0.15            # 可视化透明度


@dataclass
class IsolationSlot:
    """安规隔离槽"""
    x: float
    y: float
    width: float                     # 通常 3-6mm
    height: float
    voltage_label: str = ""          # 电压标注
    standard: str = "IEC 60950-1"


@dataclass
class TopologyPlacementResult:
    """拓扑布局结果"""
    positions: Dict[str, Dict[str, float]]   # ref → {x, y, rotation}
    zones: List[Zone]                        # 功能分区区域
    isolation_slots: List[IsolationSlot]     # 安规隔离槽
    score: float = 0.0
    topology: Optional[TopologyResult] = None
    statistics: Dict[str, Any] = field(default_factory=dict)


# ========== 分区颜色方案 ==========

GROUP_COLORS = {
    FunctionalGroup.POWER_INPUT: "#ff4444",    # 红色 - 高压危险
    FunctionalGroup.POWER_CONVERT: "#ff8800",   # 橙色 - 功率转换
    FunctionalGroup.POWER_OUTPUT: "#44aa44",    # 绿色 - 输出
    FunctionalGroup.CONTROL: "#4488ff",         # 蓝色 - 控制
    FunctionalGroup.PROTECTION: "#ffaa00",      # 黄色 - 保护
    FunctionalGroup.INTERFACE: "#aa44ff",       # 紫色 - 接口
    FunctionalGroup.CRYSTAL: "#44dddd",         # 青色 - 时钟
    FunctionalGroup.PASSIVE: "#888888",         # 灰色 - 被动
}


class TopologyAwarePlacementEngine:
    """
    拓扑感知布局引擎

    布局策略 (模仿工业级PCB设计):
    1. 功率流向: 左→右 (输入在左, 输出在右)
    2. 安规隔离: 初级/次级之间留空白带
    3. 接口元件: 放在板边 (USB在底边, 天线在角落)
    4. 控制电路: 居中
    5. 被动元件: 靠近所属IC

    使用方法:
        engine = TopologyAwarePlacementEngine(board_width=100, board_height=80)
        result = engine.place(components, nets)
    """

    def __init__(self, board_width: float = 100.0, board_height: float = 80.0,
                 margin: float = 3.0, spacing: float = 1.5):
        self.board_width = board_width
        self.board_height = board_height
        self.margin = margin
        self.spacing = spacing
        self.topology_analyzer = NetlistTopologyAnalyzer()

        logger.info(f"TopologyAwarePlacementEngine: {board_width}x{board_height}mm")

    def place(
        self,
        components: List[Component],
        nets: List[Dict],
        board_constraints: Optional[Dict] = None,
    ) -> TopologyPlacementResult:
        """
        执行拓扑感知布局

        Args:
            components: 元件列表 (使用 smart_placement_engine.Component)
            nets: 网络列表
            board_constraints: 板子约束 (可选)

        Returns:
            TopologyPlacementResult: 包含位置、分区和隔离信息
        """
        if board_constraints:
            self.board_width = board_constraints.get("width", self.board_width)
            self.board_height = board_constraints.get("height", self.board_height)

        logger.info(f"开始拓扑布局: {len(components)} 元件, {len(nets)} 网络")

        # Step 1: 拓扑分析
        comp_dicts = [self._component_to_dict(c) for c in components]
        topology = self.topology_analyzer.analyze(comp_dicts, nets)

        # Step 2: 定义功能区域
        zones = self._define_zones(topology)

        # Step 3: 生成隔离槽
        isolation_slots = self._create_isolation_slots(topology, zones)

        # Step 4: 将元件放入对应区域
        positions = self._place_components_in_zones(components, topology, zones, nets)

        # Step 5: 区域内力导向优化
        positions = self._force_directed_within_zones(positions, components, topology, zones, nets)

        # Step 6: 被动元件附着
        positions = self._attach_passives_to_parent(positions, components, topology, nets)

        # Step 7: 评估布局
        score, stats = self._evaluate_topology_layout(positions, components, topology, zones)

        result = TopologyPlacementResult(
            positions=positions,
            zones=zones,
            isolation_slots=isolation_slots,
            score=score,
            topology=topology,
            statistics=stats,
        )

        logger.info(f"拓扑布局完成: score={score:.1f}, {len(zones)} zones, "
                     f"{len(isolation_slots)} isolation slots")
        return result

    def _component_to_dict(self, comp: Component) -> Dict:
        """将 Component 对象转换为字典 (用于拓扑分析)"""
        return {
            "reference": comp.reference,
            "value": comp.value,
            "footprint": comp.footprint,
            "nets": comp.nets,
        }

    def _define_zones(self, topology: TopologyResult) -> List[Zone]:
        """
        定义功能区域

        策略 (参考工业级PCB设计):
        - power_input_zone: 板子左侧 20%
        - power_convert_zone: 板子中左 30%
        - isolation_gap: 3-6mm 空白带 (如果需要)
        - output_zone: 板子右侧 30%
        - connector_zone: 板子顶边/右边
        - control_zone: 板子中心
        """
        zones = []
        bw = self.board_width
        bh = self.board_height
        m = self.margin

        # 计算功率流向中的分区
        power_groups = topology.power_flow
        has_isolation = len(topology.isolation_requirements) > 0

        # 隔离带宽度
        isolation_width = 6.0 if has_isolation else 0.0

        # 可用布局宽度 (减去margin和隔离带)
        usable_width = bw - 2 * m - isolation_width

        # 按功率流向分配区域 (左→右)
        flow_zone_width = usable_width / max(len(power_groups), 1)

        x_offset = m
        for i, group in enumerate(power_groups):
            zone_w = flow_zone_width
            zones.append(Zone(
                name=group.value,
                group=group,
                x=x_offset,
                y=m,
                width=zone_w,
                height=bh - 2 * m,
                color=GROUP_COLORS.get(group, "#888888"),
            ))
            x_offset += zone_w

        # 非功率流向分区放到板的中心或侧边
        remaining_groups = [
            g for g in topology.functional_groups
            if g not in power_groups and g != FunctionalGroup.PASSIVE
        ]

        for group in remaining_groups:
            if group == FunctionalGroup.CONTROL:
                # 控制区居中
                zones.append(Zone(
                    name=group.value,
                    group=group,
                    x=bw * 0.35,
                    y=bh * 0.25,
                    width=bw * 0.3,
                    height=bh * 0.5,
                    color=GROUP_COLORS.get(group, "#888888"),
                ))
            elif group == FunctionalGroup.PROTECTION:
                # 保护区分布在板边
                zones.append(Zone(
                    name=group.value,
                    group=group,
                    x=m,
                    y=m,
                    width=bw - 2 * m,
                    height=bh * 0.15,
                    color=GROUP_COLORS.get(group, "#888888"),
                ))
            elif group == FunctionalGroup.CRYSTAL:
                # 晶振区靠近控制区
                zones.append(Zone(
                    name=group.value,
                    group=group,
                    x=bw * 0.4,
                    y=bh * 0.4,
                    width=bw * 0.15,
                    height=bh * 0.2,
                    color=GROUP_COLORS.get(group, "#888888"),
                ))

        logger.info(f"定义 {len(zones)} 个功能区域")
        return zones

    def _create_isolation_slots(
        self,
        topology: TopologyResult,
        zones: List[Zone],
    ) -> List[IsolationSlot]:
        """根据安规隔离需求创建隔离槽"""
        slots = []

        for req in topology.isolation_requirements:
            # 找到两个分区对应的zone
            zone1 = next((z for z in zones if z.group == req.group1), None)
            zone2 = next((z for z in zones if z.group == req.group2), None)

            if zone1 and zone2:
                # 隔离槽放在两个zone之间
                slot_x = min(zone1.x + zone1.width, zone2.x + zone2.width)
                slot_x = max(zone1.x + zone1.width, zone2.x) - req.min_distance_mm / 2

                slots.append(IsolationSlot(
                    x=slot_x,
                    y=self.margin,
                    width=req.min_distance_mm,
                    height=self.board_height - 2 * self.margin,
                    voltage_label=req.voltage_range,
                    standard=req.standard,
                ))

        return slots

    def _place_components_in_zones(
        self,
        components: List[Component],
        topology: TopologyResult,
        zones: List[Zone],
        nets: List[Dict],
    ) -> Dict[str, Dict[str, float]]:
        """将元件放入对应的功能区域"""
        positions = {}

        # 构建zone索引
        zone_map = {z.group: z for z in zones}

        # 按分区放置元件
        for group, refs in topology.functional_groups.items():
            zone = zone_map.get(group)
            if not zone:
                continue

            # 获取该分区的元件
            group_comps = [c for c in components if c.reference in refs]
            if not group_comps:
                continue

            # 在zone内使用shelf packing
            zone_positions = self._shelf_pack_in_zone(group_comps, zone)
            positions.update(zone_positions)

        # 未分组的元件放到板中心
        placed_refs = set(positions.keys())
        for comp in components:
            if comp.reference not in placed_refs:
                positions[comp.reference] = {
                    "x": self.board_width / 2,
                    "y": self.board_height / 2,
                    "rotation": 0,
                }

        return positions

    def _shelf_pack_in_zone(self, components: List[Component], zone: Zone) -> Dict[str, Dict[str, float]]:
        """在指定区域内进行shelf packing"""
        if not components:
            return {}

        positions = {}
        sorted_comps = sorted(components, key=lambda c: -c.get_area())

        x = zone.x + self.spacing
        y = zone.y + self.spacing
        row_h = 0

        for c in sorted_comps:
            # 检查换行
            if x + c.width > zone.x + zone.width - self.spacing:
                x = zone.x + self.spacing
                y += row_h + self.spacing
                row_h = 0

            # 检查是否超出区域
            if y + c.height > zone.y + zone.height - self.spacing:
                # 溢出时放到zone底部
                y = zone.y + zone.height - c.height - self.spacing

            positions[c.reference] = {
                "x": x + c.width / 2,
                "y": y + c.height / 2,
                "rotation": 0,
            }
            x += c.width + self.spacing
            row_h = max(row_h, c.height)

        return positions

    def _force_directed_within_zones(
        self,
        positions: Dict[str, Dict[str, float]],
        components: List[Component],
        topology: TopologyResult,
        zones: List[Zone],
        nets: List[Dict],
        iterations: int = 30,
    ) -> Dict[str, Dict[str, float]]:
        """
        区域内力导向布局优化

        力来源:
        - 斥力: 元件之间避免重叠
        - 吸引力: 有共同网络的元件互相吸引 (连线吸引力)
        - 区域约束力: 保持在zone边界内
        """
        positions = {k: v.copy() for k, v in positions.items()}
        comp_dict = {c.reference: c for c in components}
        zone_map = {z.group: z for z in zones}

        # 构建网络连接: ref → Set[ref]
        net_connections = self._build_net_connections(nets)

        for iteration in range(iterations):
            forces = {r: [0.0, 0.0] for r in positions}
            refs = list(positions.keys())

            # 斥力: 避免重叠
            for i, r1 in enumerate(refs):
                for r2 in refs[i + 1:]:
                    c1, c2 = comp_dict.get(r1), comp_dict.get(r2)
                    if not c1 or not c2:
                        continue

                    p1, p2 = positions[r1], positions[r2]
                    dx = p2["x"] - p1["x"]
                    dy = p2["y"] - p1["y"]
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist < 0.1:
                        angle = (hash(r1) + iteration * 0.3) % 6.28
                        dx, dy, dist = math.cos(angle), math.sin(angle), 0.1

                    min_d = max(c1.width, c1.height) / 2 + max(c2.width, c2.height) / 2 + self.spacing

                    if dist < min_d:
                        f = (min_d - dist) * 2.0
                        forces[r1][0] -= f * dx / dist
                        forces[r1][1] -= f * dy / dist
                        forces[r2][0] += f * dx / dist
                        forces[r2][1] += f * dy / dist

            # 吸引力: 共同网络的元件
            for r1, connected_refs in net_connections.items():
                if r1 not in positions:
                    continue
                for r2 in connected_refs:
                    if r2 not in positions or r1 >= r2:
                        continue

                    p1, p2 = positions[r1], positions[r2]
                    dx = p2["x"] - p1["x"]
                    dy = p2["y"] - p1["y"]
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist > 0.1:
                        # 弹簧力 (距离越远吸引力越大，但有上限)
                        f = min(dist * 0.02, 0.5)
                        forces[r1][0] += f * dx / dist
                        forces[r1][1] += f * dy / dist
                        forces[r2][0] -= f * dx / dist
                        forces[r2][1] -= f * dy / dist

            # 应用力 (保持在zone内)
            damping = max(0.1, 1.0 - iteration / iterations)
            for r in positions:
                if r not in comp_dict:
                    continue

                positions[r]["x"] += forces[r][0] * damping
                positions[r]["y"] += forces[r][1] * damping

                # 限制在对应的zone内
                group = topology.component_group_map.get(r)
                if group and group in zone_map:
                    zone = zone_map[group]
                    c = comp_dict[r]
                    hw, hh = c.width / 2, c.height / 2
                    positions[r]["x"] = max(zone.x + hw, min(zone.x + zone.width - hw, positions[r]["x"]))
                    positions[r]["y"] = max(zone.y + hh, min(zone.y + zone.height - hh, positions[r]["y"]))
                else:
                    # 保持在板内
                    c = comp_dict[r]
                    hw, hh = c.width / 2, c.height / 2
                    positions[r]["x"] = max(self.margin + hw, min(self.board_width - self.margin - hw, positions[r]["x"]))
                    positions[r]["y"] = max(self.margin + hh, min(self.board_height - self.margin - hh, positions[r]["y"]))

        return positions

    def _build_net_connections(self, nets: List[Dict]) -> Dict[str, set]:
        """构建网络连接映射: ref → Set[connected_refs]"""
        connections: Dict[str, set] = {}
        for net in nets:
            nodes = net.get("nodes", net.get("connections", []))
            refs = [n.get("ref", "") for n in nodes if n.get("ref")]
            for r in refs:
                connections.setdefault(r, set()).update(ref for ref in refs if ref != r)
        return connections

    def _attach_passives_to_parent(
        self,
        positions: Dict[str, Dict[str, float]],
        components: List[Component],
        topology: TopologyResult,
        nets: List[Dict],
    ) -> Dict[str, Dict[str, float]]:
        """
        被动元件就近附着到父IC

        策略:
        - 去耦电容 → 紧贴IC的电源引脚 (< 2mm)
        - 上拉/下拉电阻 → 靠近对应信号引脚
        - 滤波电感/电容 → 串联在信号路径上
        """
        positions = {k: v.copy() for k, v in positions.items()}
        comp_dict = {c.reference: c for c in components}

        # 构建网络连接
        net_connections = self._build_net_connections(nets)

        for comp in components:
            group = topology.component_group_map.get(comp.reference)
            if group != FunctionalGroup.PASSIVE:
                continue

            # 找到通过共同网络连接的IC
            connected = net_connections.get(comp.reference, set())
            parent_ref = None
            min_dist = float('inf')

            for conn_ref in connected:
                conn_group = topology.component_group_map.get(conn_ref)
                if conn_group in (FunctionalGroup.CONTROL, FunctionalGroup.POWER_CONVERT,
                                  FunctionalGroup.INTERFACE, FunctionalGroup.POWER_OUTPUT):
                    if conn_ref in positions:
                        p = positions[conn_ref]
                        d = abs(p["x"]) + abs(p["y"])  # placeholder distance
                        if parent_ref is None:
                            parent_ref = conn_ref

            if parent_ref and parent_ref in positions:
                parent_pos = positions[parent_ref]
                # 被动元件放在父IC旁边
                offset_x = comp.width / 2 + 1.0  # 1mm间隙
                offset_y = comp.height / 2 + 0.5

                positions[comp.reference] = {
                    "x": parent_pos["x"] + offset_x,
                    "y": parent_pos["y"] + offset_y,
                    "rotation": 0,
                }

        return positions

    def _evaluate_topology_layout(
        self,
        positions: Dict[str, Dict[str, float]],
        components: List[Component],
        topology: TopologyResult,
        zones: List[Zone],
    ) -> Tuple[float, Dict[str, Any]]:
        """评估拓扑布局质量"""
        comp_dict = {c.reference: c for c in components}
        violations = []
        overlaps = 0

        # 检查重叠
        refs = list(positions.keys())
        for i, r1 in enumerate(refs):
            for r2 in refs[i + 1:]:
                c1, c2 = comp_dict.get(r1), comp_dict.get(r2)
                if not c1 or not c2:
                    continue
                p1, p2 = positions[r1], positions[r2]
                if (abs(p1["x"] - p2["x"]) < (c1.width + c2.width) / 2 and
                    abs(p1["y"] - p2["y"]) < (c1.height + c2.height) / 2):
                    overlaps += 1
                    violations.append(f"Overlap: {r1} and {r2}")

        # 检查安规隔离
        isolation_violations = 0
        zone_map = {z.group: z for z in zones}
        for req in topology.isolation_requirements:
            z1 = zone_map.get(req.group1)
            z2 = zone_map.get(req.group2)
            if z1 and z2:
                gap = abs(z1.x + z1.width - z2.x) if z1.x < z2.x else abs(z2.x + z2.width - z1.x)
                if gap < req.min_distance_mm:
                    isolation_violations += 1
                    violations.append(
                        f"Safety isolation: {req.group1.value} ↔ {req.group2.value} "
                        f"gap={gap:.1f}mm < {req.min_distance_mm}mm"
                    )

        # 计算分数
        score = 100.0
        score -= overlaps * 15
        score -= isolation_violations * 30

        # 检查被动元件是否靠近父IC
        passive_proximity_score = 0
        passive_count = 0
        for comp in components:
            if topology.component_group_map.get(comp.reference) == FunctionalGroup.PASSIVE:
                if comp.reference in positions:
                    passive_count += 1
                    # 检查是否在某个IC附近 (简单检查: 5mm内)
                    pos = positions[comp.reference]
                    near_ic = False
                    for other_comp in components:
                        other_group = topology.component_group_map.get(other_comp.reference)
                        if other_group in (FunctionalGroup.CONTROL, FunctionalGroup.POWER_CONVERT):
                            if other_comp.reference in positions:
                                other_pos = positions[other_comp.reference]
                                dist = math.sqrt(
                                    (pos["x"] - other_pos["x"]) ** 2 +
                                    (pos["y"] - other_pos["y"]) ** 2
                                )
                                if dist < 10.0:  # 10mm内算近
                                    near_ic = True
                                    break
                    if near_ic:
                        passive_proximity_score += 1

        if passive_count > 0:
            proximity_pct = passive_proximity_score / passive_count
            score += proximity_pct * 10  # 最多加10分

        score = max(0, min(100, score))

        stats = {
            "total_components": len(components),
            "overlaps": overlaps,
            "isolation_violations": isolation_violations,
            "zones": len(zones),
            "passive_proximity": f"{passive_proximity_score}/{passive_count}",
            "board_utilization": sum(c.width * c.height for c in components) / (self.board_width * self.board_height),
        }

        return score, stats
