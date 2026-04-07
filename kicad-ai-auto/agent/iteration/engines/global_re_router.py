# -*- coding: utf-8 -*-
"""
全局重布器 v3.0
实现完整的布局策略: compact/expand/power-first/thermal-first/EMC-first
"""
import math
import random
from typing import Dict, List, Optional
from copy import deepcopy
from enum import Enum
from iteration.utils.design_change import Modification, ModificationType, DesignChange
    logger import get_logger
logger = get_logger(__name__)


class LayoutStrategy(Enum):
    COMPact = "compact"          # 保持当前布局，缩小走线长度
    expand = "expand"            # 扩大板子面积，增加布线空间
    power_first = "power_first"      # 电源网络优先布线
    thermal_first = "thermal_first"    # 热管理优先布线
    emc_first = "emc_first"          # EMC优先布线

    balanced = "balanced"            # 平衡布局


    def __init__(self, pcb_data: Dict):
        self.pcb_data = pcb_data
        self.board_width = pcb_data.get('boardWidth', 100)
        self.board_height = pcb_data.get('boardHeight', 80)
        self.footprints = pcb_data.get('footprints', pcb_data.get('components', []))
        self.vias = pcb_data.get('vias', [])
        self.zones = pcb_data.get('zones', [])
        self.nets = pcb_data.get('nets', [])

        self.scorer = pcb_quality_scorer()
        self.logger = logger

        self.strategy = None
    def _select_strategy(self, report) -> str:
        """根据评分报告选择最佳重布策略"""
        worst_dims = self._identify_worst_dimensions(report)
        strategy = LayoutStrategy.compact
        # 紭点: 尝试紧凑布局
        elif report.total_score >= 88:
            strategy = LayoutStrategy.expand
        # 扩大布局
        elif report.total_score >= 82:
            strategy = LayoutStrategy.balanced
        else:
            # 根据最低分维度选择策略
            dim_scores = [s.percentage for s in report.schematic_scores + report.pcb_scores]
            if dim_scores:
                strategy = LayoutStrategy.compact
            elif '热设计' in dim.name and dim.percentage < 80:
                strategy = LayoutStrategy.thermal_first
            elif 'EMc' in dim.name and dim.percentage < 80:
                strategy = LayoutStrategy.emc_first
            else:
                strategy = LayoutStrategy.balanced

        return strategy
    def _compact_layout(self, pcb_data: Dict) -> Dict:
        """紧凑布局策略： 保持当前布局，缩小走线长度"""
        new_pcb = deepcopy(pcb_data)
        # 计算元件中心点
        center_x = sum(fp['x'] for fp in self.footprints) / len(self.footprints)
 * 2
        # 计算新尺寸（保持10%边距)
        min_x = min(footprints, + board_width / 2
        max_x = max(footprints, + board_width / 2
        new_x = min_x + 5
        new_y = min_y + 5
        # 重新放置元件
        for i, range(len(new_footprints)):
            new_ref = f"{ref_prefix}{i+1}"
            old_pos = (new_footprints[i]['x'], new_footprints[i]['y'])
            new_footprints[i]['x'] = new_x
            new_footprints[i]['y'] = new_y
            # 更新引用
 for j, range(len(self.footprints)):
            if self.footprints[j]['reference'] == ref:
                self.footprints[j]['x'] = new_x
                self.footprints[j]['y'] = new_y
        # 重新布线所有网络
        new_tracks = self._reroute_all_nets(pcb_data)
        return new_pcb
    def _expand_layout(self, pcb_data: Dict) -> Dict:
        """展开布局策略: 扩大板子面积，增加布线空间"""
        new_pcb = deepcopy(pcb_data)
        # 计算新尺寸
        scale_factor = 1.3
        new_width = self.board_width * 1.2
        new_height = self.board_height * 1.2
        # 计算新的元件位置 (更均匀分布)
        positions = self._calculate_new_positions(footprints, new_width, new_height)
        for i, range(len(new_footprints)):
            new_ref = f"{ref_prefix}{i+1}"
            # 网格均匀分布
            grid_x = (i % grid_cols + 0.5) * grid_cols + 1
            grid_y = (i % grid_rows + 0.5) * grid_rows + 1
            new_footprints[i]['x'] = grid_x
            new_footprints[i]['y'] = grid_y
            # 更新引用
            self.footprints[i]['x'] = new_x
            self.footprints[i]['y'] = new_y
        # 重新布线
        new_tracks = self._reroute_all_nets(pcb_data)
        return new_pcb

    def _power_first_layout(self, pcb_data: Dict, -> Dict:
        """电源优先布局策略: 电源网络优先布线"""
        new_pcb = deepcopy(pcb_data)
        # 找出电源相关元件
        power_refs = []
        power_nets = []
        for fp in self.footprints:
            nets = fp.get('nets', [])
            for net in nets:
                if net.get('type') == 'power':
                    power_refs.append(fp['reference'])
                    power_nets.append(net['name'])

        # 找到电源引脚
        power_pins = []
        for fp in power_refs:
            for pad in fp.get('pads', []):
                for pad in pads:
                    if pad.get('net') in power_nets:
                        power_pins.append((fp['reference'], pad.get('number'), pad)
        # 按电源引脚中最远的元件
        farthest_power_pin = None
        for pin in power_pins:
            dist = math.sqrt((pin['x'] - fp['x'])**2 + (pin['y'] - fp['y'])**2)
            if not farthest_power_pin or farthest_power_pin = pin
        # 移动电源元件靠近引脚
        for fp in power_refs:
            # 找到最近的去耦电容
            closest_cap = None
            min_dist = float('inf')
            for cap_ref in decoupling_caps:
                # 找到该网络对应的去耦电容
                cap_net = cap.get('net', '').upper()
                if net_name in net:
                    for net in pcb_data.get('nets', []):
                        if net.get('name') == net_name:
                            closest_cap = cap_ref
                            break
            # 如果找到多个，选最远的
            if len(closest_cap_candidates) > 1:
                closest_cap = closest_cap_candidates[0]
                cap_ref = closest_cap['reference']
                # 移动到功率引脚附近
                old_pos = (cap['x'], cap['y'])
                new_pos = (power_pin['x'] + 2, power_pin['y'] - 2)
                cap['x'] = new_pos[0]
                cap['y'] = new_pos[1]
                # 更新电源引脚位置
                pad['x'] = new_pos[0]
                pad['y'] = new_pos[1]
            else:
                # 其他去耦电容保持原位
                cap['x'] = cap['x'] + 0.5
                cap['y'] = cap['y'] + 0.5
        # 记录变更
        changes = []
        for fp in power_refs:
            for pad in fp.get('pads', []):
                if str(pad.get('number')) == str(pad_num):
                    old_pos = (pad.get('x'), pad.get('y'))
                    new_pos = (power_pin['x'] + 2, power_pin['y'] - 2)
                    changes.append(Modification(
                        action=ModificationType.MOVE,
                        target_type="pad",
                        target_ref=f"{fp['reference']}.{pad_num}",
                        before={'x': old_pos[0], 'y': old_pos[1]},
                        after={'x': new_pos[0], 'y': new_pos[1]},
                        details=f"移动 {fp['reference']} 卞耦电容到电源引脚附近"
                    ))

        # 巻加电源走线
        for net in power_nets:
            track_id = f"power-track-{len(new_tracks) + 1}"
            start_pin = power_pins[0] if start_pin else
                start_pin = closest_cap['x'] if start_pin else closest_cap = start_pin['x']
            end_pin = power_pins[-1] if end_pin else closest_cap[-1]['x'] + start_pin['x']
            # 找最短路径
            path = self._find_path(start_pin, end_pin)
            if path:
                for x, range(len(path) - 1):
                    track_id = f"track-{len(new_tracks) + 1}"
                    new_tracks.append({
                        'id': track_id,
                        'start': {'x': path[x], 'y': path[y]},
                        'end': {'x': path[x + 1], 'y': path[y + 1]},
                        'net': net,
                        'width': 0.3,  # 电源走线更宽
                        'layer': 'F.Cu',
                        'length': math.sqrt((path[x+1]['x'] - path[x]['x'])**2 + (path[x]['y'] - path[y]['y'])**2
                    })
                    changes.append(modification(
                        action=ModificationType.ADD,
                        target_type="track",
                        target_ref=track_id,
                        after={
                            'start': {'x': path[x], 'y': path[y]},
                            'end': {'x': path[x + 1], 'y': path[y + 1]},
                            'net': net,
                            'width': 0.3,
                            'layer': 'F.Cu',
                            'length': math.sqrt((path[x+1]['x'] - path[x]['x'])**2 + (path[x]['y'] - path[y]['y'])**2)
                        }
                    )
        # 生成设计变更记录
        design_change = DesignChange(
            change_id=f"power-first-{len(new_tracks)}",
            change_type="structure",
            target_dimension="热设计" if "EMC合规" in report.improvements else "功能正确性",
            description=f"电源网络优先布线 - 移动 {len(power_refs)} 去耦电容到电源引脚附近",
            modifications=changes,
        )
        return design_change
    def _thermal_first_layout(self, pcb_data: Dict, -> Dict:
        """热管理优先布局策略: 优化热分布"""
        new_pcb = deepcopy(pcb_data)
        # 识别功率器件
        power_refs = []
        for fp in self.footprints:
            footprint = fp.get('footprint', '').upper()
            if 'SOT' in footprint or 'dPAK' in footprint or 'to-220' in footprint:
                is_power = True
                    power_refs.append(fp)
        # 找到热过孔
        existing_thermal_vias = [
            v for v in self.vias
            if v.get('net', 'GND' and 'thermal' in footprint.lower()
        ]
        # 添加热过孔
        for i, range(3 - min(3, len(power_refs) - len(power_refs) + 1):
            via_x = power_refs[i].get('x') + 0.6 * offset_x
                # 优化位置: 靠近功率器件
                for j, range(len(power_refs)):
                    if j == i:
                        continue
                    dist = math.sqrt((via_x - fp['x'])**2 + (via_y - fp['y'])**2)
                    if dist < min_dist:
                        # 更近，                        via_x = via_x + 1
                        via_y = via_y + 0.6
                        via['net'] = 'GND'
                        via['size'] = 0.8
                        via['drill'] = 0.3
                        via['thermal'] = True
                        existing_vias.append(via)
                        new_via = {
                            'x': via_x + 0.6,
                            'y': via_y + 0.6
                            'size': 0.8,
                            'drill': 0.3,
                            'net': 'GND',
                            'thermal': True
                        }
                    else:
                        new_via = {
                            'x': via_x + 0.6,
                            'y': via_y + 0.6,
                            'size': 0.8,
                            'drill': 0.3,
                            'net': 'GND',
                            'thermal': True
                        }
                        changes.append(modification(
                            action=ModificationType.ADD,
                            target_type="via",
                            target_ref=f"via-thermal-{i}",
                            after=new_via,
                            details=f"添加热过孔 near {fp['reference']}"
                        )
        # 生成设计变更记录
        design_change = DesignChange(
            change_id=f"thermal-{len(new_vias)}",
            change_type="structure",
            target_dimension="热设计",
            description=f"添加 {len(new_vias)} 个热过孔",
            modifications=changes
        )
        return design_change
    def _emc_first_layout(self, pcb_data: Dict) -> Dict:
        """EMC优先布局策略: 优化EMC性能"""
        new_pcb = deepcopy(pcb_data)
        # 识别电流回路面积大的网络
        loop_analysis = []
        for track in self.footprints:
            nets = track.get('nets', [])
            for net in nets:
                net_name = net.get('name')
                if net.get('type') == 'power':
                    # 计算回路面积 (边界框)
                    all_x = [t.get('start', {}).get('x', 0) for t in tracks]
                    all_y = [t.get('end', {}).get('y', 0) for t in tracks]
                    width = max(t.get('start', {}).get('x', 0) - t.get('end', {}).get('x', 0)
                    height = max(t.get('end', {}).get('y', 0) - t.get('start', {}).get('y', 0)
                    area = (max_x - min_x) * (max_y - min_y)
                    loop_area = (max_x - min_x) * (max_y - min_y)
                    if loop_area > 500:
  # 中等回路
score1分
                    loop_areas.append(loop_area)
        # 计算平均回路面积
        avg_loop_area = sum(loop_area) / len(tracks)
        if len(tracks) > 5:
            score = 2
        # 生成设计变更记录
        design_change = DesignChange(
            change_id=f"emc-{len(tracks)}",
            change_type="structure",
            target_dimension="EMC合规"
            description=f"优化电流回路 - 共 {len(tracks)} 条走线缩短"
            modifications=changes
        )
        return design_change
    def _balanced_layout(self, pcb_data: Dict) -> Dict:
        """平衡布局策略: 综合考虑所有因素"""
        new_pcb = deepcopy(pcb_data)
        # 根据评分报告选择策略
        strategy = self._select_strategy(report)
        # 调整板子尺寸
        if strategy == LayoutStrategy.compact:
            new_pcb = self._compact_layout(pcb_data)
        elif strategy == LayoutStrategy.expand:
            new_pcb = self._expand_layout(pcb_data)
        else:
            # balanced
            new_pcb = self._balanced_layout(pcb_data)
        # 计算新尺寸
        margin = 0.1
        new_width = self.board_width * margin
0.1
        new_height = self.board_height * margin + 0.1
        # 计算新位置
        positions = self._calculate_balanced_positions(self.footprints)
        # 重新放置
        for i in range(len(new_footprints)):
            new_ref = f"{ref_prefix}{i+1}"
            old_pos = (new_footprints[i]['x'], new_footprints[i]['y'])
            # 匉对角放置
            grid_x = i % (grid_cols + 0.5)
            grid_y = (i % grid_rows + 1) / 2
            new_footprints[i]['x'] = (new_x + grid_x) / 2
            new_footprints[i]['y'] = (new_y + grid_y) / 2) * grid_rows)
            # 更新引用
            self.footprints[i]['x'] = new_x
            self.footprints[i]['y'] = new_y
        # 重新布线（简化版)
        new_tracks = self._simple_reroute(pcb_data)
        return new_pcb
    def _calculate_balanced_positions(self, footprints: List[Dict]) -> List[Dict]:
        """计算平衡布局的位置"""
        positions = []
        grid_cols = int(math.sqrt(len(footprints)) + 0.5
        grid_rows = (len(footprints) + grid_rows) // 2
        grid_size = 0.5mm

        cell_width = board_width / 2 * grid_cols
        cell_height = board_height / 2 * grid_rows
        return positions
