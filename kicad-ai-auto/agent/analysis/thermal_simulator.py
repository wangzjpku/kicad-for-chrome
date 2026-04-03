# -*- coding: utf-8 -*-
"""
Thermal Simulator - PCB 热仿真引擎

Phase 14: 高级分析集成

功能:
1. 功率器件热耗计算
2. 热阻网络分析
3. 热点识别 (Hotspot Detection)
4. 散热优化建议
5. 热过孔 (Thermal Via) 生成

基于简化热模型:
- 热阻 = (T_junction - T_ambient) / Power
- PCB 热导率: FR4 ~0.3 W/mK, 铜约 400 W/mK
- 自然对流换热系数: 5-15 W/m²K
- 强制对流换热系数: 20-100 W/m²K

Author: Claude Code
Date: 2026-04-03
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class CoolingMethod(Enum):
    """散热方式"""
    NATURAL_CONVECTION = "natural"      # 自然对流
    FORCED_CONVECTION = "forced"         # 强制对流
    HEAT_SINK = "heatsink"               # 散热器
    FAN = "fan"                          # 风扇


@dataclass
class ComponentPower:
    """元件功耗数据"""
    reference: str           # 元件编号 (如 U1, Q1)
    power_watts: float       # 功耗 (W)
    position: Tuple[float, float]  # 位置 (mm)
    package: str = ""        # 封装类型
    theta_jc: float = 0.0    # 结-壳热阻 (°C/W)
    theta_ja: float = 0.0    # 结-环境热阻 (°C/W)
    max_junction_temp: float = 150.0  # 最大结温 (°C)


@dataclass
class ThermalHotspot:
    """热热点"""
    x: float                  # X 坐标 (mm)
    y: float                  # Y 坐标 (mm)
    radius: float             # 影响半径 (mm)
    temperature: float        # 预估温度 (°C)
    severity: str             # 严重程度: "low", "medium", "high", "critical"
    source_components: List[str] = field(default_factory=list)  # 热源元件
    suggestions: List[str] = field(default_factory=list)  # 优化建议


@dataclass
class ThermalVia:
    """热过孔"""
    x: float
    y: float
    drill_diameter: float = 0.3   # 钻孔直径 (mm)
    outer_diameter: float = 0.6   # 外径 (mm)
    thermal_conductivity: float = 400.0  # 铜热导率 W/mK
    layer_from: str = "F.Cu"
    layer_to: str = "B.Cu"

    def thermal_resistance(self, board_thickness: float = 1.6) -> float:
        """计算热过孔热阻 (°C/W)"""
        # R_th = L / (k * A)
        length = board_thickness / 1000  # 转换为 m
        area = math.pi * (self.drill_diameter / 2000) ** 2  # 转换为 m²
        if area < 1e-12:
            return 1000.0
        return length / (self.thermal_conductivity * area)


@dataclass
class ThermalSimulationResult:
    """热仿真结果"""
    ambient_temp: float          # 环境温度 (°C)
    max_board_temp: float        # 板上最高温度 (°C)
    avg_board_temp: float        # 板上平均温度 (°C)
    hotspots: List[ThermalHotspot]  # 热点列表
    component_temps: Dict[str, float]  # 元件温度 {ref: temp}
    thermal_vias_suggested: List[ThermalVia]  # 建议的热过孔
    passed: bool                 # 是否通过热检查
    total_power: float           # 总功耗 (W)
    cooling_capacity: float      # 散热能力 (W)
    suggestions: List[str] = field(default_factory=list)


class ThermalSimulator:
    """
    PCB 热仿真器

    功能:
    - 计算板上温度分布
    - 识别热热点
    - 生成散热优化建议
    - 自动生成热过孔阵列
    """

    # 材料热导率 (W/mK)
    MATERIAL_CONDUCTIVITY = {
        "copper": 400.0,
        "fr4": 0.3,
        "aluminum": 205.0,
        "air": 0.026,
    }

    # 封装热阻参考值 (°C/W)
    PACKAGE_THETA_JA = {
        "DPAK": 80.0,
        "D2PAK": 60.0,
        "TO-220": 60.0,
        "TO-263": 50.0,
        "QFN-48": 45.0,
        "QFN-64": 35.0,
        "BGA-256": 30.0,
        "BGA-484": 25.0,
        "LQFP-48": 80.0,
        "LQFP-64": 70.0,
        "LQFP-100": 55.0,
        "SOT-23": 150.0,
        "SOT-223": 100.0,
        "SOIC-8": 120.0,
        "SOIC-16": 100.0,
    }

    def __init__(
        self,
        board_width: float = 100.0,
        board_height: float = 80.0,
        board_thickness: float = 1.6,
        copper_layers: int = 2,
        ambient_temp: float = 25.0,
    ):
        """
        初始化热仿真器

        Args:
            board_width: 板宽 (mm)
            board_height: 板高 (mm)
            board_thickness: 板厚 (mm)
            copper_layers: 铜层数
            ambient_temp: 环境温度 (°C)
        """
        self.board_width = board_width
        self.board_height = board_height
        self.board_thickness = board_thickness
        self.copper_layers = copper_layers
        self.ambient_temp = ambient_temp

        # 网格参数 (用于温度场计算)
        self.grid_size = 5.0  # 5mm 网格

        # 元件功耗列表
        self.power_components: List[ComponentPower] = []

    def add_power_component(
        self,
        reference: str,
        power_watts: float,
        position: Tuple[float, float],
        package: str = "",
        max_junction_temp: float = 150.0,
    ):
        """
        添加功耗元件

        Args:
            reference: 元件编号
            power_watts: 功耗 (W)
            position: 位置 (x, y) mm
            package: 封装类型
            max_junction_temp: 最大结温 (°C)
        """
        # 获取封装热阻
        theta_ja = self.PACKAGE_THETA_JA.get(package.upper(), 100.0)

        component = ComponentPower(
            reference=reference,
            power_watts=power_watts,
            position=position,
            package=package,
            theta_ja=theta_ja,
            max_junction_temp=max_junction_temp,
        )
        self.power_components.append(component)
        logger.debug(f"添加功耗元件: {reference} {power_watts}W @ ({position[0]}, {position[1]})")

    def simulate(
        self,
        cooling: CoolingMethod = CoolingMethod.NATURAL_CONVECTION,
        max_allowed_temp: float = 100.0,
    ) -> ThermalSimulationResult:
        """
        执行热仿真

        Args:
            cooling: 散热方式
            max_allowed_temp: 最大允许温度 (°C)

        Returns:
            ThermalSimulationResult: 仿真结果
        """
        logger.info(
            f"开始热仿真: 板子 {self.board_width}x{self.board_height}mm, "
            f"环境温度 {self.ambient_temp}°C, 散热方式 {cooling.value}"
        )

        # 计算总功耗
        total_power = sum(c.power_watts for c in self.power_components)

        # 计算换热系数
        h = self._get_convection_coefficient(cooling)

        # 计算散热能力
        board_area_m2 = (self.board_width / 1000) * (self.board_height / 1000)
        cooling_capacity = h * board_area_m2 * (max_allowed_temp - self.ambient_temp)

        # 计算板上温度分布
        temp_grid = self._calculate_temperature_distribution(h)

        # 找出热点
        hotspots = self._identify_hotspots(temp_grid, max_allowed_temp)

        # 计算元件温度
        component_temps = self._calculate_component_temps(temp_grid)

        # 生成热过孔建议
        thermal_vias = self._generate_thermal_via_suggestions(hotspots)

        # 生成优化建议
        suggestions = self._generate_suggestions(
            total_power, cooling_capacity, hotspots, cooling
        )

        # 计算板上最高和平均温度
        all_temps = [temp_grid[i][j] for i in range(len(temp_grid)) for j in range(len(temp_grid[0]))]
        max_temp = max(all_temps) if all_temps else self.ambient_temp
        avg_temp = sum(all_temps) / len(all_temps) if all_temps else self.ambient_temp

        # 判断是否通过
        passed = max_temp <= max_allowed_temp and all(
            component_temps.get(c.reference, 0) <= c.max_junction_temp
            for c in self.power_components
        )

        result = ThermalSimulationResult(
            ambient_temp=self.ambient_temp,
            max_board_temp=round(max_temp, 1),
            avg_board_temp=round(avg_temp, 1),
            hotspots=hotspots,
            component_temps={k: round(v, 1) for k, v in component_temps.items()},
            thermal_vias_suggested=thermal_vias,
            passed=passed,
            total_power=round(total_power, 2),
            cooling_capacity=round(cooling_capacity, 2),
            suggestions=suggestions,
        )

        logger.info(
            f"热仿真完成: 最高温度 {max_temp:.1f}°C, 平均温度 {avg_temp:.1f}°C, "
            f"发现 {len(hotspots)} 个热点, {'通过' if passed else '未通过'}"
        )

        return result

    def _get_convection_coefficient(self, cooling: CoolingMethod) -> float:
        """获取对流换热系数 (W/m²K)"""
        coefficients = {
            CoolingMethod.NATURAL_CONVECTION: 10.0,
            CoolingMethod.FORCED_CONVECTION: 40.0,
            CoolingMethod.HEAT_SINK: 25.0,  # 被动散热器
            CoolingMethod.FAN: 80.0,  # 风扇强制对流
        }
        return coefficients.get(cooling, 10.0)

    def _calculate_temperature_distribution(self, h: float) -> List[List[float]]:
        """
        计算板上温度分布

        使用简化的稳态热传导模型:
        - 将 PCB 划分为网格
        - 每个功耗元件作为热源
        - 考虑热扩散和散热

        Args:
            h: 对流换热系数 (W/m²K)

        Returns:
            2D 温度网格 (°C)
        """
        # 创建网格
        nx = int(self.board_width / self.grid_size) + 1
        ny = int(self.board_height / self.grid_size) + 1

        # 初始化温度为环境温度
        temp_grid = [[self.ambient_temp for _ in range(ny)] for _ in range(nx)]

        # 计算每个热源对网格点的影响
        for component in self.power_components:
            cx, cy = component.position
            power = component.power_watts

            # 将坐标转换为网格索引
            gi = int(cx / self.grid_size)
            gj = int(cy / self.grid_size)

            if 0 <= gi < nx and 0 <= gj < ny:
                # 计算热源点温度上升
                # 简化模型: ΔT = P / (h * A_eff)
                # A_eff 为有效散热面积 (考虑热扩散)
                effective_area = self._calculate_effective_area(
                    cx, cy, power, h
                )
                delta_t = power / (h * effective_area) if effective_area > 0 else 0

                # 应用温度分布 (高斯分布近似)
                for i in range(nx):
                    for j in range(ny):
                        x = i * self.grid_size
                        y = j * self.grid_size

                        # 距离
                        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)

                        # 热扩散系数 (简化)
                        sigma = 20.0  # 扩散半径 mm

                        # 高斯衰减
                        factor = math.exp(-dist ** 2 / (2 * sigma ** 2))
                        temp_grid[i][j] += delta_t * factor

        return temp_grid

    def _calculate_effective_area(
        self,
        x: float,
        y: float,
        power: float,
        h: float,
    ) -> float:
        """计算有效散热面积 (m²)"""
        # 简化: 假设热扩散半径与功率平方根成正比
        spread_radius = 10.0 + 5.0 * math.sqrt(power)  # mm
        area_mm2 = math.pi * spread_radius ** 2
        return area_mm2 / 1e6  # 转换为 m²

    def _identify_hotspots(
        self,
        temp_grid: List[List[float]],
        threshold: float,
    ) -> List[ThermalHotspot]:
        """
        识别热热点

        Args:
            temp_grid: 温度网格
            threshold: 温度阈值 (°C)

        Returns:
            热点列表
        """
        hotspots = []
        nx = len(temp_grid)
        ny = len(temp_grid[0]) if nx > 0 else 0

        visited = [[False for _ in range(ny)] for _ in range(nx)]

        for i in range(nx):
            for j in range(ny):
                if visited[i][j]:
                    continue

                temp = temp_grid[i][j]
                if temp < threshold:
                    continue

                # 找到连续的高温区域
                region = self._flood_fill_hot_region(temp_grid, visited, i, j, threshold)

                if region:
                    # 计算区域中心
                    cx = sum(r[0] for r in region) / len(region) * self.grid_size
                    cy = sum(r[1] for r in region) / len(region) * self.grid_size
                    max_temp = max(temp_grid[r[0]][r[1]] for r in region)
                    radius = math.sqrt(len(region)) * self.grid_size / 2

                    # 确定严重程度
                    if max_temp >= 120:
                        severity = "critical"
                    elif max_temp >= 100:
                        severity = "high"
                    elif max_temp >= 80:
                        severity = "medium"
                    else:
                        severity = "low"

                    # 找出热源元件
                    source_components = self._find_nearby_components(cx, cy, radius * 2)

                    # 生成建议
                    suggestions = self._generate_hotspot_suggestions(severity, max_temp)

                    hotspot = ThermalHotspot(
                        x=round(cx, 1),
                        y=round(cy, 1),
                        radius=round(radius, 1),
                        temperature=round(max_temp, 1),
                        severity=severity,
                        source_components=source_components,
                        suggestions=suggestions,
                    )
                    hotspots.append(hotspot)

        return hotspots

    def _flood_fill_hot_region(
        self,
        temp_grid: List[List[float]],
        visited: List[List[bool]],
        start_i: int,
        start_j: int,
        threshold: float,
    ) -> List[Tuple[int, int]]:
        """泛洪填充找到连续的高温区域"""
        nx = len(temp_grid)
        ny = len(temp_grid[0]) if nx > 0 else 0

        region = []
        stack = [(start_i, start_j)]

        while stack:
            i, j = stack.pop()

            if i < 0 or i >= nx or j < 0 or j >= ny:
                continue
            if visited[i][j]:
                continue
            if temp_grid[i][j] < threshold:
                continue

            visited[i][j] = True
            region.append((i, j))

            # 4 连通扩展
            stack.extend([
                (i + 1, j),
                (i - 1, j),
                (i, j + 1),
                (i, j - 1),
            ])

        return region

    def _find_nearby_components(
        self,
        x: float,
        y: float,
        radius: float,
    ) -> List[str]:
        """找出附近的功耗元件"""
        nearby = []
        for c in self.power_components:
            dist = math.sqrt((c.position[0] - x) ** 2 + (c.position[1] - y) ** 2)
            if dist <= radius:
                nearby.append(c.reference)
        return nearby

    def _calculate_component_temps(
        self,
        temp_grid: List[List[float]],
    ) -> Dict[str, float]:
        """计算各元件的温度"""
        component_temps = {}

        for c in self.power_components:
            cx, cy = c.position
            gi = int(cx / self.grid_size)
            gj = int(c / self.grid_size)

            nx = len(temp_grid)
            ny = len(temp_grid[0]) if nx > 0 else 0

            if 0 <= gi < nx and 0 <= gj < ny:
                board_temp = temp_grid[gi][gj]
                # 元件结温 = 板温 + 功耗 * 热阻
                junction_temp = board_temp + c.power_watts * c.theta_ja
                component_temps[c.reference] = junction_temp
            else:
                component_temps[c.reference] = self.ambient_temp

        return component_temps

    def _generate_thermal_via_suggestions(
        self,
        hotspots: List[ThermalHotspot],
    ) -> List[ThermalVia]:
        """生成热过孔建议"""
        vias = []

        for hotspot in hotspots:
            if hotspot.severity in ["high", "critical"]:
                # 在热点周围生成热过孔阵列
                via_spacing = 2.0  # mm
                via_radius = hotspot.radius

                # 圆形阵列
                num_rings = max(1, int(via_radius / via_spacing))

                for ring in range(1, num_rings + 1):
                    ring_radius = ring * via_spacing
                    circumference = 2 * math.pi * ring_radius
                    num_vias = max(4, int(circumference / via_spacing))

                    for v in range(num_vias):
                        angle = 2 * math.pi * v / num_vias
                        via_x = hotspot.x + ring_radius * math.cos(angle)
                        via_y = hotspot.y + ring_radius * math.sin(angle)

                        # 确保在板子范围内
                        if 0 < via_x < self.board_width and 0 < via_y < self.board_height:
                            vias.append(ThermalVia(
                                x=round(via_x, 2),
                                y=round(via_y, 2),
                            ))

        logger.info(f"生成 {len(vias)} 个热过孔建议")
        return vias

    def _generate_hotspot_suggestions(
        self,
        severity: str,
        temp: float,
    ) -> List[str]:
        """生成热点优化建议"""
        suggestions = []

        if severity == "critical":
            suggestions.append(f"严重热点! 温度 {temp:.0f}°C 超过安全阈值")
            suggestions.append("建议: 1) 增加散热铺铜面积 2) 添加热过孔 3) 考虑使用散热器或风扇")
        elif severity == "high":
            suggestions.append(f"高温热点: 温度 {temp:.0f}°C")
            suggestions.append("建议: 增加铺铜面积或添加热过孔")
        elif severity == "medium":
            suggestions.append(f"中等热点: 温度 {temp:.0f}°C")
            suggestions.append("建议: 检查元件布局， 避免热聚集")
        else:
            suggestions.append(f"轻微热点: 温度 {temp:.0f}°C")
            suggestions.append("建议: 监控运行温度")

        return suggestions

    def _generate_suggestions(
        self,
        total_power: float,
        cooling_capacity: float,
        hotspots: List[ThermalHotspot],
        cooling: CoolingMethod,
    ) -> List[str]:
        """生成整体优化建议"""
        suggestions = []

        # 功耗与散热能力对比
        if total_power > cooling_capacity * 0.8:
            suggestions.append(
                f"警告: 总功耗 {total_power:.1f}W 接近散热能力 {cooling_capacity:.1f}W"
            )
            if cooling == CoolingMethod.NATURAL_CONVECTION:
                suggestions.append("建议: 考虑添加风扇或散热器以增强散热")

        # 热点建议
        critical_count = len([h for h in hotspots if h.severity == "critical"])
        high_count = len([h for h in hotspots if h.severity == "high"])

        if critical_count > 0:
            suggestions.append(f"发现 {critical_count} 个严重热点, 必须优化散热设计")
        if high_count > 0:
            suggestions.append(f"发现 {high_count} 个高温热点, 建议优化散热")

        # 布局建议
        if len(hotspots) > 2:
            suggestions.append("热点较多, 建议重新规划元件布局, 分散热源")

        # 铺铜建议
        if total_power > 5.0:
            suggestions.append("功耗较高, 建议增加GND铺铜面积以提高散热能力")

        if not suggestions:
            suggestions.append("热设计良好, 无需特殊优化")

        return suggestions


def create_thermal_simulator(
    board_width: float = 100.0,
    board_height: float = 80.0,
    ambient_temp: float = 25.0,
) -> ThermalSimulator:
    """创建热仿真器实例"""
    return ThermalSimulator(
        board_width=board_width,
        board_height=board_height,
        ambient_temp=ambient_temp,
    )
