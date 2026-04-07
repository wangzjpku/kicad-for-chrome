# -*- coding: utf-8 -*-
"""
PCB迭代优化项目池 v3.0
支持渐进式难度和AI生成项目
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional
from enum import Enum
from datetime import datetime
import sys
import os
import copy
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcb_quality_scorer import PCBQualityScorer, QualityReport
from logger import get_logger

logger = get_logger(__name__)


# ============== 常量定义 ==============
PROJECT_TEMPLATES_DIR = "project_templates"
MAX_ITERATIONS = 20
TARGET_SCORE = 89.0


class ProjectDifficulty(Enum):
    """项目难度等级"""
    LEVEL_1 = 1  # 简单模块 - 8-15个元件
    LEVEL_2 = 2  # 标准模块 - 15-30个元件
    LEVEL_3 = 3  # 复杂模块 - 30-50个元件
    LEVEL_4 = 4  # 完整系统 - 50+个元件


@dataclass
class ProjectTemplate:
    """项目模板"""
    name: str
    difficulty: ProjectDifficulty
    category: str  # mcu, power, sensor, mixed
    description: str
    component_templates: List[Dict]
    net_templates: List[Dict]
    layout_hints: Dict[str, Any] = field(default_factory=dict)

    def generate(self) -> Tuple[Dict, Dict]:
        """生成具体项目数据"""
        pass


class ProjectPool:
    """项目池 - 管理所有可生成的项目"""

    def __init__(self, target_score: float = TARGET_SCORE):
        self.target_score = target_score
        self.templates: List[ProjectTemplate] = []
        self.generated_projects: List[Dict] = []
        self.current_difficulty = ProjectDifficulty.LEVEL_1
        self.scorer = PCBQualityScorer(target_score=target_score)
        self.logger = logger
        self._load_benchmark_templates()

    def _load_benchmark_templates(self):
        """加载基准测试项目模板"""
        self._add_builtin_templates()

    def _add_builtin_templates(self):
        """添加内置基准模板"""
        # Level 1: LED驱动模块
        self.templates.append(ProjectTemplate(
            name="LED驱动模块",
            difficulty=ProjectDifficulty.LEVEL_1,
            category="power",
            description="简单的LED驱动电路，带PWM调光",
            component_templates=[
                {'prefix': 'U', 'category': 'driver', 'values': ['WS2812', 'LM3516'], 'footprints': ['SOT-23-5', 'SOIC-8'], 'pin_count': (5, 8)},
                {'prefix': 'R', 'category': 'resistor', 'values': ['10k', '4.7k', '1k'], 'footprints': ['0603', '0402'], 'pin_count': (2, 2)},
                {'prefix': 'C', 'category': 'capacitor', 'values': ['100nF', '1uF', '10uF'], 'footprints': ['0603', '0805'], 'pin_count': (2, 2)},
                {'prefix': 'LED', 'category': 'led', 'values': ['Red', 'Green', 'Blue'], 'footprints': ['0603', '0805'], 'pin_count': (2, 2)},
            ],
            net_templates=[
                {'name': 'VCC', 'type': 'power', 'importance': 'critical'},
                {'name': 'GND', 'type': 'ground', 'importance': 'critical'},
                {'name': 'PWM', 'type': 'signal', 'importance': 'high'},
            ],
            layout_hints={
                'driver_central': True,
                'output_on_edge': True,
            }
        ))

        # Level 1: 传感器模块
        self.templates.append(ProjectTemplate(
            name="温湿度传感器",
            difficulty=ProjectDifficulty.LEVEL_1,
            category="sensor",
            description="DHT22温湿度传感器模块",
            component_templates=[
                {'prefix': 'U', 'category': 'sensor', 'values': ['DHT22', 'DHT11'], 'footprints': ['4-pin-pico', '6-pin-pico'], 'pin_count': (4, 6)},
                {'prefix': 'R', 'category': 'resistor', 'values': ['10k', '4.7k'], 'footprints': ['0603'], 'pin_count': (2, 2)},
                {'prefix': 'C', 'category': 'capacitor', 'values': ['100nF', '1uF'], 'footprints': ['0603', '0805'], 'pin_count': (2, 2)},
            ],
            net_templates=[
                {'name': 'VCC', 'type': 'power', 'importance': 'critical'},
                {'name': 'GND', 'type': 'ground', 'importance': 'critical'},
                {'name': 'SDA', 'type': 'signal', 'importance': 'medium'},
                {'name': 'SCL', 'type': 'signal', 'importance': 'medium'},
            ],
            layout_hints={
                'sensor_central': True,
                'i2c_pins_together': True,
            }
        ))

        # Level 2: LDO稳压模块
        self.templates.append(ProjectTemplate(
            name="LDO稳压模块",
            difficulty=ProjectDifficulty.LEVEL_2,
            category="power",
            description="3.3V LDO稳压器模块",
            component_templates=[
                {'prefix': 'U', 'category': 'regulator', 'values': ['AMS1117-3.3', 'LM1117-3.3'], 'footprints': ['SOT-223', 'TO-220'], 'pin_count': (3, 3)},
                {'prefix': 'C', 'category': 'capacitor', 'values': ['10uF', '100nF', '1uF'], 'footprints': ['0805', '1206'], 'pin_count': (2, 2)},
                {'prefix': 'D', 'category': 'protection', 'values': ['SS34'], 'footprints': ['SMA'], 'pin_count': (2, 2)},
                {'prefix': 'LED', 'category': 'led', 'values': ['Green'], 'footprints': ['0603'], 'pin_count': (2, 2)},
            ],
            net_templates=[
                {'name': 'VIN', 'type': 'power', 'importance': 'critical'},
                {'name': '3V3', 'type': 'power', 'importance': 'critical'},
                {'name': 'GND', 'type': 'ground', 'importance': 'critical'},
            ],
            layout_hints={
                'input_output_separated': True,
                'caps_close_to_regulator': True,
            }
        ))

        # Level 2: STM32最小系统
        self.templates.append(ProjectTemplate(
            name="STM32最小系统",
            difficulty=ProjectDifficulty.LEVEL_2,
            category="mcu",
            description="STM32F103最小系统",
            component_templates=[
                {'prefix': 'U', 'category': 'mcu', 'values': ['STM32F103C8T6', 'STM32F103C8'], 'footprints': ['LQFP-48', 'LQFP-64'], 'pin_count': (48, 64)},
                {'prefix': 'Y', 'category': 'crystal', 'values': ['8MHz'], 'footprints': ['HC49', '5032'], 'pin_count': (2, 2)},
                {'prefix': 'C', 'category': 'capacitor', 'values': ['20pF', '100nF', '1uF'], 'footprints': ['0603', '0805'], 'pin_count': (2, 2)},
                {'prefix': 'R', 'category': 'resistor', 'values': ['10k', '4.7k'], 'footprints': ['0603'], 'pin_count': (2, 2)},
                {'prefix': 'J', 'category': 'connector', 'values': ['PinHeader', 'USB-C'], 'footprints': ['PinHeader_2x20', 'USB-C-16P'], 'pin_count': (20, 16)},
            ],
            net_templates=[
                {'name': 'VCC', 'type': 'power', 'importance': 'critical'},
                {'name': 'GND', 'type': 'ground', 'importance': 'critical'},
                {'name': 'RESET', 'type': 'signal', 'importance': 'high'},
                {'name': 'BOOT0', 'type': 'signal', 'importance': 'high'},
            ],
            layout_hints={
                'mcu_central': True,
                'crystal_close_to_mcu': True,
                'decoupling_caps_around_mcu': True,
            }
        ))

        # Level 3: ESP32 WiFi蓝牙模块
        self.templates.append(ProjectTemplate(
            name="ESP32 WiFi蓝牙模块",
            difficulty=ProjectDifficulty.LEVEL_3,
            category="mcu",
            description="ESP32-WROOM-32E模块带完整外设",
            component_templates=[
                {'prefix': 'U', 'category': 'mcu', 'values': ['ESP32-WROOM-32E'], 'footprints': ['ESP32-WROOM'], 'pin_count': (38, 38)},
                {'prefix': 'U', 'category': 'regulator', 'values': ['AMS1117-3.3'], 'footprints': ['SOT-223'], 'pin_count': (3, 3)},
                {'prefix': 'Y', 'category': 'crystal', 'values': ['40MHz', '26MHz'], 'footprints': ['3225', '2016'], 'pin_count': (2, 2)},
                {'prefix': 'C', 'category': 'capacitor', 'values': ['100nF', '10uF', '22pF', '10pF'], 'footprints': ['0603', '0805', '1206'], 'pin_count': (2, 2)},
                {'prefix': 'R', 'category': 'resistor', 'values': ['10k', '4.7k', '330', '1k'], 'footprints': ['0603'], 'pin_count': (2, 2)},
                {'prefix': 'J', 'category': 'connector', 'values': ['USB-C', 'I2C', 'PinHeader'], 'footprints': ['USB-C-16P', 'PinHeader_1x10', 'PinHeader_1x06'], 'pin_count': (16, 6, 10)},
                {'prefix': 'LED', 'category': 'led', 'values': ['Red', 'Green', 'Blue', 'Yellow'], 'footprints': ['0603'], 'pin_count': (2, 2)},
                {'prefix': 'SW', 'category': 'switch', 'values': ['RESET', 'BOOT'], 'footprints': ['Tactile_Switch'], 'pin_count': (2, 2)},
            ],
            net_templates=[
                {'name': '3V3', 'type': 'power', 'importance': 'critical'},
                {'name': 'GND', 'type': 'ground', 'importance': 'critical'},
                {'name': 'VBUS', 'type': 'power', 'importance': 'critical'},
                {'name': 'USB_D+', 'type': 'signal', 'importance': 'high'},
                {'name': 'USB_D-', 'type': 'signal', 'importance': 'high'},
                {'name': 'EN', 'type': 'signal', 'importance': 'high'},
                {'name': 'IO0', 'type': 'signal', 'importance': 'medium'},
            ],
            layout_hints={
                'mcu_central': True,
                'power_section_separated': True,
                'rf_section_clear': True,
                'crystal_close_to_mcu': True,
            }
        ))

        # Level 4: 锂电池管理系统
        self.templates.append(ProjectTemplate(
            name="锂电池充放电管理",
            difficulty=ProjectDifficulty.LEVEL_4,
            category="power",
            description="锂电池充电+保护+电量计",
            component_templates=[
                {'prefix': 'U', 'category': 'charger', 'values': ['TP4056', 'BQ24072', 'MP2650'], 'footprints': ['SOP-8', 'QFN-24', 'DFN-10'], 'pin_count': (8, 10)},
                {'prefix': 'U', 'category': 'protection', 'values': ['DW01', 'FS3125'], 'footprints': ['SOT-23-5', 'SOT-23-6', 'TSOP-6'], 'pin_count': (5, 6)},
                {'prefix': 'U', 'category': 'gauge', 'values': ['STM32F030', 'ATTINY85'], 'footprints': ['TSSOP-8', 'QFN-20'], 'pin_count': (8, 20)},
                {'prefix': 'C', 'category': 'capacitor', 'values': ['10uF', '1uF', '100nF', '47uF'], 'footprints': ['0805', '1206', '1812'], 'pin_count': (2, 2)},
                {'prefix': 'R', 'category': 'resistor', 'values': ['10k', '100k', '330', '1k', '0.1'], 'footprints': ['0603', '0805', '1206'], 'pin_count': (2, 2)},
                {'prefix': 'L', 'category': 'inductor', 'values': ['2.2uH', '4.7uH'], 'footprints': ['SMD-0805', 'SMD-1206'], 'pin_count': (2, 2)},
                {'prefix': 'J', 'category': 'connector', 'values': ['USB-C', 'JST-PH', 'Battery-2P'], 'footprints': ['USB-C-16P', 'JST-PH-2', 'Battery-Connector'], 'pin_count': (16, 2, 2)},
                {'prefix': 'LED', 'category': 'led', 'values': ['Red', 'Green', 'Blue', 'Yellow'], 'footprints': ['0603'], 'pin_count': (2, 2)},
                {'prefix': 'Q', 'category': 'mosfet', 'values': ['SI4435DY', 'AO3401A'], 'footprints': ['SOT-23', 'SO-8'], 'pin_count': (3, 8)},
                {'prefix': 'NT', 'category': 'ntc', 'values': ['NTC10k'], 'footprints': ['0603'], 'pin_count': (2, 2)},
            ],
            net_templates=[
                {'name': 'VBAT', 'type': 'power', 'importance': 'critical'},
                {'name': 'VCC', 'type': 'power', 'importance': 'critical'},
                {'name': 'GND', 'type': 'ground', 'importance': 'critical'},
                {'name': 'BAT+', 'type': 'power', 'importance': 'critical'},
                {'name': 'BAT-', 'type': 'power', 'importance': 'critical'},
                {'name': 'CHG_EN', 'type': 'signal', 'importance': 'high'},
                {'name': 'DSG_EN', 'type': 'signal', 'importance': 'high'},
                {'name': 'SDA', 'type': 'signal', 'importance': 'medium'},
                {'name': 'SCL', 'type': 'signal', 'importance': 'medium'},
            ],
            layout_hints={
                'power_flow': True,
                'charge_section_left': True,
                'protection_section_right': True,
                'mcu_monitoring': True,
            }
        ))

    def get_template_by_name(self, name: str) -> Optional[ProjectTemplate]:
        """根据名称获取模板"""
        for template in self.templates:
            if template.name == name:
                return template
        return None

    def get_random_project(self) -> Optional[ProjectTemplate]:
        """获取随机项目"""
        if not self.templates:
            return None
        return random.choice(self.templates)

    def get_project_by_difficulty(self, difficulty: ProjectDifficulty) -> Optional[ProjectTemplate]:
        """获取指定难度的项目"""
        available = [t for t in self.templates if t.difficulty == difficulty]
        if not available:
            return None
        return random.choice(available)

    def generate_initial_design(self, template: ProjectTemplate) -> Tuple[Dict, Dict]:
        """生成初始设计"""
        self.logger.info(f"Generating initial design for {template.name}...")

        # 生成原理图
        schematic = self._generate_schematic(template)

        # 生成PCB
        pcb = self._generate_pcb(template)

        return schematic, pcb

    def _generate_schematic(self, template: ProjectTemplate) -> Dict:
        """生成原理图数据"""
        components = []
        comp_id = 1

        for comp_template in template.component_templates:
            ref_prefix = comp_template['prefix']
            value = random.choice(comp_template['values'])
            footprint = random.choice(comp_template['footprints'])

            components.append({
                'reference': f"{ref_prefix}{comp_id}",
                'name': value,
                'value': value,
                'footprint': footprint,
                'category': comp_template['category'],
                'pins': self._generate_pins(comp_template['pin_count']),
                'nets': [],
            })
            comp_id += 1

        # 生成连线
        wires = self._generate_wires(components, template.net_templates)

        # 分配网络
        for comp in components:
            comp['nets'] = self._assign_nets(comp, template.net_templates)

        return {
            'title': template.name,
            'components': components,
            'wires': wires,
            'nets': template.net_templates,
            'power_nets': [n['name'] for n in template.net_templates if n['type'] == 'power'],
        }

    def _generate_pcb(self, template: ProjectTemplate) -> Dict:
        """生成PCB数据"""
        component_count = len(template.component_templates)
        board_width = 50 + component_count * 0.5
        board_height = 35 + component_count * 0.3

        # 生成footprints
        footprints = self._generate_footprints(template)

        # 生成初始布线
        tracks = self._generate_initial_tracks(template)

        # 生成过孔
        vias = self._generate_initial_vias(template)

        # 生成铺铜
        zones = self._generate_initial_zones(template)

        return {
            'project_name': template.name,
            'width': board_width,
            'height': board_height,
            'boardWidth': board_width,
            'boardHeight': board_height,
            'layers': 2,
            'thickness': 1.6,
            'footprints': footprints,
            'tracks': tracks,
            'vias': vias,
            'zones': zones,
            'nets': [{'id': f"net-{n['name'].lower()}", 'name': n['name']} for n in template.net_templates],
            'design_rules': {
                'min_clearance': 0.15,
                'min_track_width': 0.15,
                'min_via_size': 0.4,
                'min_via_drill': 0.2,
            },
            'drc_status': {
                'error_count': random.randint(3, 8),
                'warning_count': random.randint(5, 15),
            },
        }

    def _generate_pins(self, pin_count: Tuple[int, int]) -> List[Dict]:
        """生成引脚"""
        min_pins, max_pins = pin_count
        count = random.randint(min_pins, max_pins)
        pins = []
        for i in range(count):
            pin_type = random.choice(['input', 'output', 'bidirectional', 'power_in', 'power_out'])
            pins.append({
                'number': str(i + 1),
                'name': f"Pin_{i+1}",
                'type': pin_type,
            })
        return pins

    def _generate_wires(self, components: List[Dict], net_templates: List[Dict]) -> List[Dict]:
        """生成连线"""
        wires = []

        for net in net_templates:
            connected_comps = random.sample(components, min(2, 4))
            for comp in connected_comps:
                if comp['pins']:
                    pin = random.choice(comp['pins'])
                    wires.append({
                        'start': f"{comp['reference']}.{pin['number']}",
                        'end': net['name'],
                        'net': net['name'],
                    })

        return wires

    def _assign_nets(self, component: Dict, net_templates: List[Dict]) -> List[str]:
        """为元件分配网络"""
        nets = []

        if component['category'] == 'mcu':
            nets = ['VCC', 'GND', 'RESET']
        elif component['category'] == 'power':
            nets = ['VIN', 'VOUT', 'GND']
        elif component['category'] == 'sensor':
            nets = ['VCC', 'GND', 'SDA', 'SCL']
        else:
            nets = ['VCC', 'GND']

        return nets

    def _generate_footprints(self, template: ProjectTemplate) -> List[Dict]:
        """生成PCB footprints"""
        footprints = []

        board_width = 50 + len(template.component_templates) * 0.5
        board_height = 35 + len(template.component_templates) * 0.3

        grid_cols = int(math.sqrt(len(template.component_templates))) + 1
        grid_rows = (len(template.component_templates) + grid_cols - 1) // grid_cols

        for i in range(len(template.component_templates)):
            col = i % grid_cols
            row = i // grid_cols

            x = 10 + col * (board_width - 20) // grid_cols
            y = 10 + row * (board_height - 20) // grid_rows

            comp_template = template.component_templates[i]
            ref_prefix = comp_template['prefix']

            footprints.append({
                'reference': f"{ref_prefix}{i+1}",
                'x': x,
                'y': y,
                'rotation': 0,
                'layer': 'F.Cu',
                'footprint': random.choice(comp_template['footprints']),
                'pads': self._generate_pads(comp_template),
                'nets': [],
            })

        return footprints

    def _generate_pads(self, comp_template: Dict) -> List[Dict]:
        """生成焊盘"""
        pads = []
        pin_count = comp_template.get('pin_count', (8, 8))

        for i in range(min(pin_count[0], 8)):
            pads.append({
                'number': str(i + 1),
                'net': None,
            })

        return pads

    def _generate_initial_tracks(self, template: ProjectTemplate) -> List[Dict]:
        """生成初始布线"""
        tracks = []
        track_id = 1

        for net in template.net_templates:
            if net['type'] == 'power':
                tracks.append({
                    'id': f'track-{track_id}',
                    'start': {'x': 10, 'y': 10},
                    'end': {'x': 20, 'y': 20},
                    'net': net['name'],
                    'width': 0.25,
                    'layer': 'F.Cu',
                })
                track_id += 1

        return tracks

    def _generate_initial_vias(self, template: ProjectTemplate) -> List[Dict]:
        """生成初始过孔"""
        vias = []

        for i in range(3):
            vias.append({
                'x': 10 + i * 5,
                'y': 10 + i * 5,
                'size': 0.6,
                'drill': 0.3,
                'net': 'GND',
            })

        return vias

    def _generate_initial_zones(self, template: ProjectTemplate) -> List[Dict]:
        """生成初始铺铜"""
        zones = []

        zones.append({
            'net': 'GND',
            'layer': 'B.Cu',
            'outline': [
                {'x': 2, 'y': 2},
                {'x': 48, 'y': 2},
                {'x': 48, 'y': 33},
                {'x': 2, 'y': 33},
            ],
        })

        return zones

    def advance_difficulty(self) -> bool:
        """提升难度等级"""
        if self.current_difficulty == ProjectDifficulty.LEVEL_1:
            self.current_difficulty = ProjectDifficulty.LEVEL_2
            return True
        elif self.current_difficulty == ProjectDifficulty.LEVEL_2:
            self.current_difficulty = ProjectDifficulty.LEVEL_3
            return True
        elif self.current_difficulty == ProjectDifficulty.LEVEL_3:
            self.current_difficulty = ProjectDifficulty.LEVEL_4
            return True
        return False

    def get_progress_stats(self) -> Dict:
        """获取进度统计"""
        return {
            'total_projects': len(self.generated_projects),
            'current_difficulty': self.current_difficulty.name,
            'templates_available': len(self.templates),
        }
