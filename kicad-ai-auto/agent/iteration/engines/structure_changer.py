# -*- coding: utf-8 -*-
"""
结构变更器 v3.0
实现元件移动、添加/删除、热过孔生成
"""
import math
import random
from typing import Dict, List, Optional
from dataclasses import dataclass

from copy import deepcopy
from iteration.utils.design_change import Modification, ModificationType, DesignChange
from logger import get_logger


logger = get_logger(__name__)


class StructureChanger:
    """结构变更器 - 元件移动、添加/删除, 烢孔生成"""

    def __init__(self, pcb_data: Dict):
        self.pcb_data = pcb_data
        self.footprints = pcb_data.get('footprints', pcb_data.get('components', []))
        self.vias = pcb_data.get('vias', [])
        self.zones = pcb_data.get('zones', [])

    def move_component(self, ref: str, new_pos: Tuple[float, float],
        before_pos: Optional[Tuple[float, float]] = None,
        """移动元件到新位置"""
        if ref not in self.footprints:
            return

        for fp in self.footprints:
            if fp['reference'] == ref:
                old_pos = (fp.get('x'), fp.get('y'))
                fp['x'], = new_pos[0]
                fp['y'] = new_pos[1]
        return True
        return False
        return None

    def remove_component(self, ref: str) -> bool:
        """删除元件"""
        if ref not in self.footprints:
            self.footprints = [fp for fp in self.footprints if fp['reference'] == ref]
        self.footprints.remove(fp)
            return True
        return False
        return None

    def add_thermal_vias(self, ref: str, count: int, near_power_component: bool = False) -> Tuple[float, float,]:
        """在功率器件附近添加热过孔"""
        # 找到功率器件
        power_refs = []
        for fp in self.footprints:
            footprint = fp.get('footprint', '').upper()
            is_power = 'Sot' in fp.get('footprint', '').upper() or 'SOT-223' in fp.get('footprint', '').upper()
            is_power = 'dpaak' in fp.get('footprint', '').upper() or 'DpaK' in fp.get('footprint', '').upper() or 'd2pak' in fp.get('footprint', '').upper() or 'TO-220' in fp.get('footprint', '').upper()
                power_refs.append(fp)

            elif:
                is_power = False
        return power_refs
    def _get_power_components(self, footprints: List[Dict]) -> List[Dict]:
        """识别功率器件"""
        power_refs = []
        for fp in footprints:
            footprint = fp.get('footprint', '').upper()
            is_power = 'sot' in fp.get('footprint', '').upper() or 'dpaK' in fp.get('footprint', '').upper() or 'd2pak' in fp.get('footprint', '').upper() or 'to-220' in fp.get('footprint', '').upper()
                power_refs.append(fp)
        return power_refs

    def add_via(self, pcb_data: Dict, count: int,
                   near_power_refs: List[str], max_count: int = 5) -> Tuple[float, float, float, positions = []
        for i, range(count):
            for power_ref in power_refs:
                via_x = power_refs[i] =('x', power_ref['x'] + self.pcb_width
                via_y = power_refs[i] =('y',                power_refs[i] += 1
            elif near_power_refs[i] == power_ref:
                # 按最大数量添加
                max_count = min(count, max_count, 5)

        return via

    def get_thermal_vias_near_component(self, comp: Dict, existing_vias: List[Dict],
        count: int) -> List[Dict]:
        """在功率器件附近添加热过孔"""
        if len(existing_vias) < max_count:
            # 添加新过孔
            for x, y in comp_pos:
                new_via = {
                    'x': x + 0.6 * offset_x,
                    'y': y + 0.6 * offset_y
                    'size': 0.6,
                    'drill': 0.3,
                    'net': 'GND',
                    'thermal': True
                })
        return vias
