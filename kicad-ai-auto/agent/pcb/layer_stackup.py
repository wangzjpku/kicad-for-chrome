"""
PCB Layer Stackup Manager - 多层板层叠管理

Phase 4: 多层板支持
- 2层/4层/6层板模板
- 电源/地平面定义
- 层叠阻抗计算
- 介电材料管理

参考: circuit-json 标准层叠定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class LayerType(Enum):
    """层类型"""
    SIGNAL = "signal"           # 信号层
    PLANE = "plane"             # 平面层（电源/地）
    MIXED = "mixed"             # 混合层
    DIELECTRIC = "dielectric"   # 介电层


class PlaneType(Enum):
    """平面层类型"""
    GND = "GND"                 # 地平面
    POWER = "PWR"               # 电源平面
    MIXED = "MIXED"             # 混合平面


@dataclass
class DielectricMaterial:
    """介电材料"""
    name: str                           # 材料名称
    dk: float                           # 介电常数 (Er)
    df: float                           # 损耗因子 (TanD)
    thickness: float                    # 厚度 (mm)

    # 常用材料预定义
    FR4_STANDARD = None                 # 将在下面初始化
    FR4_HIGH_TG = None
    RO4003C = None
    RO4350B = None


# 初始化常用材料
DielectricMaterial.FR4_STANDARD = DielectricMaterial(
    name="FR-4 Standard",
    dk=4.5,
    df=0.02,
    thickness=1.6
)

DielectricMaterial.FR4_HIGH_TG = DielectricMaterial(
    name="FR-4 High Tg",
    dk=4.4,
    df=0.018,
    thickness=1.6
)

DielectricMaterial.RO4003C = DielectricMaterial(
    name="Rogers RO4003C",
    dk=3.55,
    df=0.0027,
    thickness=0.813
)

DielectricMaterial.RO4350B = DielectricMaterial(
    name="Rogers RO4350B",
    dk=3.66,
    df=0.0037,
    thickness=0.762
)


@dataclass
class CopperLayer:
    """铜层定义"""
    name: str                           # 层名称 (F.Cu, In1.Cu, etc.)
    layer_number: int                   # 层序号 (0=顶层, 31=底层)
    layer_type: LayerType               # 层类型
    thickness: float                    # 铜厚 (mm)
    copper_weight: float                # 铜重量 (oz)
    plane_type: Optional[PlaneType] = None  # 平面类型（仅平面层）
    net: Optional[str] = None           # 关联网络（电源层）


@dataclass
class DielectricLayer:
    """介电层定义"""
    name: str                           # 层名称
    thickness: float                    # 厚度 (mm)
    material: DielectricMaterial        # 材料
    above_layer: int                    # 上层铜层序号
    below_layer: int                    # 下层铜层序号


@dataclass
class LayerStackup:
    """层叠结构"""
    name: str                           # 层叠名称
    layer_count: int                    # 总层数
    total_thickness: float              # 总厚度 (mm)
    copper_layers: List[CopperLayer] = field(default_factory=list)
    dielectric_layers: List[DielectricLayer] = field(default_factory=list)

    def get_signal_layers(self) -> List[CopperLayer]:
        """获取所有信号层"""
        return [l for l in self.copper_layers if l.layer_type == LayerType.SIGNAL]

    def get_plane_layers(self) -> List[CopperLayer]:
        """获取所有平面层"""
        return [l for l in self.copper_layers if l.layer_type == LayerType.PLANE]

    def get_layer_by_name(self, name: str) -> Optional[CopperLayer]:
        """通过名称获取层"""
        for layer in self.copper_layers:
            if layer.name == name:
                return layer
        return None


@dataclass
class ImpedanceProfile:
    """阻抗配置"""
    name: str                           # 配置名称
    trace_width: float                  # 走线宽度 (mm)
    layer: str                          # 所在层
    target_impedance: float             # 目标阻抗 (Ohms)
    calculated_impedance: float = 0.0   # 计算阻抗
    coupling: str = "single"            # single/diff
    diff_spacing: Optional[float] = None  # 差分对间距


class StackupManager:
    """
    层叠管理器

    提供标准层叠模板和阻抗计算功能
    """

    # 标准层叠模板
    TEMPLATES = {
        "2layer": {
            "name": "2层板标准层叠",
            "layer_count": 2,
            "total_thickness": 1.6,
            "copper_layers": [
                CopperLayer("F.Cu", 0, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("B.Cu", 31, LayerType.SIGNAL, 0.035, 1.0),
            ],
            "dielectric_layers": [
                DielectricLayer(
                    "Core",
                    1.53,
                    DielectricMaterial.FR4_STANDARD,
                    0, 31
                ),
            ]
        },

        "4layer_standard": {
            "name": "4层板标准层叠 (1.6mm)",
            "layer_count": 4,
            "total_thickness": 1.6,
            "copper_layers": [
                CopperLayer("F.Cu", 0, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("GND", 1, LayerType.PLANE, 0.035, 1.0, PlaneType.GND),
                CopperLayer("PWR", 30, LayerType.PLANE, 0.035, 1.0, PlaneType.POWER),
                CopperLayer("B.Cu", 31, LayerType.SIGNAL, 0.035, 1.0),
            ],
            "dielectric_layers": [
                DielectricLayer("Prepreg1", 0.2, DielectricMaterial.FR4_STANDARD, 0, 1),
                DielectricLayer("Core", 1.0, DielectricMaterial.FR4_STANDARD, 1, 30),
                DielectricLayer("Prepreg2", 0.2, DielectricMaterial.FR4_STANDARD, 30, 31),
            ]
        },

        "4layer_thin": {
            "name": "4层板薄型 (1.0mm)",
            "layer_count": 4,
            "total_thickness": 1.0,
            "copper_layers": [
                CopperLayer("F.Cu", 0, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("GND", 1, LayerType.PLANE, 0.035, 1.0, PlaneType.GND),
                CopperLayer("PWR", 30, LayerType.PLANE, 0.035, 1.0, PlaneType.POWER),
                CopperLayer("B.Cu", 31, LayerType.SIGNAL, 0.035, 1.0),
            ],
            "dielectric_layers": [
                DielectricLayer("Prepreg1", 0.12, DielectricMaterial.FR4_STANDARD, 0, 1),
                DielectricLayer("Core", 0.6, DielectricMaterial.FR4_STANDARD, 1, 30),
                DielectricLayer("Prepreg2", 0.12, DielectricMaterial.FR4_STANDARD, 30, 31),
            ]
        },

        "6layer_standard": {
            "name": "6层板标准层叠",
            "layer_count": 6,
            "total_thickness": 1.6,
            "copper_layers": [
                CopperLayer("F.Cu", 0, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("GND1", 1, LayerType.PLANE, 0.035, 1.0, PlaneType.GND),
                CopperLayer("In1.Cu", 2, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("In2.Cu", 29, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("PWR", 30, LayerType.PLANE, 0.035, 1.0, PlaneType.POWER),
                CopperLayer("B.Cu", 31, LayerType.SIGNAL, 0.035, 1.0),
            ],
            "dielectric_layers": [
                DielectricLayer("Prepreg1", 0.2, DielectricMaterial.FR4_STANDARD, 0, 1),
                DielectricLayer("Core1", 0.4, DielectricMaterial.FR4_STANDARD, 1, 2),
                DielectricLayer("Prepreg2", 0.2, DielectricMaterial.FR4_STANDARD, 2, 29),
                DielectricLayer("Core2", 0.4, DielectricMaterial.FR4_STANDARD, 29, 30),
                DielectricLayer("Prepreg3", 0.2, DielectricMaterial.FR4_STANDARD, 30, 31),
            ]
        },

        "6layer_optimized": {
            "name": "6层板优化层叠 (高速)",
            "layer_count": 6,
            "total_thickness": 1.6,
            "copper_layers": [
                CopperLayer("F.Cu", 0, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("In1.Cu", 1, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("GND", 2, LayerType.PLANE, 0.035, 1.0, PlaneType.GND),
                CopperLayer("PWR", 29, LayerType.PLANE, 0.035, 1.0, PlaneType.POWER),
                CopperLayer("In2.Cu", 30, LayerType.SIGNAL, 0.035, 1.0),
                CopperLayer("B.Cu", 31, LayerType.SIGNAL, 0.035, 1.0),
            ],
            "dielectric_layers": [
                DielectricLayer("Prepreg1", 0.2, DielectricMaterial.FR4_STANDARD, 0, 1),
                DielectricLayer("Core1", 0.36, DielectricMaterial.FR4_STANDARD, 1, 2),
                DielectricLayer("Core2", 0.36, DielectricMaterial.FR4_STANDARD, 2, 29),
                DielectricLayer("Prepreg2", 0.2, DielectricMaterial.FR4_STANDARD, 29, 30),
                DielectricLayer("Prepreg3", 0.2, DielectricMaterial.FR4_STANDARD, 30, 31),
            ]
        }
    }

    def __init__(self):
        self.current_stackup: Optional[LayerStackup] = None

    def load_template(self, template_name: str) -> LayerStackup:
        """
        加载标准层叠模板

        Args:
            template_name: 模板名称 (2layer, 4layer_standard, etc.)

        Returns:
            LayerStackup: 层叠结构
        """
        if template_name not in self.TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}. "
                           f"Available: {list(self.TEMPLATES.keys())}")

        template = self.TEMPLATES[template_name]
        stackup = LayerStackup(
            name=template["name"],
            layer_count=template["layer_count"],
            total_thickness=template["total_thickness"],
            copper_layers=template["copper_layers"].copy(),
            dielectric_layers=template["dielectric_layers"].copy()
        )

        self.current_stackup = stackup
        logger.info(f"Loaded stackup template: {template_name}")
        return stackup

    def create_custom_stackup(
        self,
        name: str,
        layer_count: int,
        thickness: float,
        copper_layers: List[CopperLayer],
        dielectric_layers: List[DielectricLayer]
    ) -> LayerStackup:
        """
        创建自定义层叠

        Args:
            name: 层叠名称
            layer_count: 层数
            thickness: 总厚度
            copper_layers: 铜层列表
            dielectric_layers: 介电层列表

        Returns:
            LayerStackup: 层叠结构
        """
        stackup = LayerStackup(
            name=name,
            layer_count=layer_count,
            total_thickness=thickness,
            copper_layers=copper_layers,
            dielectric_layers=dielectric_layers
        )

        self.current_stackup = stackup
        logger.info(f"Created custom stackup: {name}")
        return stackup

    def calculate_impedance(
        self,
        trace_width: float,
        layer_name: str,
        reference_layer: str,
        coupling: str = "single",
        diff_spacing: Optional[float] = None
    ) -> Dict[str, float]:
        """
        计算特征阻抗

        使用微带线/带状线公式:
        - 微带线: Z0 = 87 / sqrt(Er+1.41) * ln(5.98H / (0.8W + T))
        - 带状线: Z0 = 60 / sqrt(Er) * ln(4H / (0.67π(0.8W + T)))

        Args:
            trace_width: 走线宽度 (mm)
            layer_name: 信号层名称
            reference_layer: 参考平面层名称
            coupling: single/diff
            diff_spacing: 差分对间距 (mm)

        Returns:
            Dict with impedance, delay, etc.
        """
        if not self.current_stackup:
            raise ValueError("No stackup loaded. Call load_template() first.")

        layer = self.current_stackup.get_layer_by_name(layer_name)
        ref_layer = self.current_stackup.get_layer_by_name(reference_layer)

        if not layer or not ref_layer:
            raise ValueError(f"Layer not found: {layer_name} or {reference_layer}")

        # 获取层间距离和介电常数
        h, er = self._get_layer_distance_and_dk(layer_name, reference_layer)
        t = layer.thickness
        w = trace_width

        # 计算阻抗
        if coupling == "single":
            # 微带线公式 (简化)
            z0 = 87 / math.sqrt(er + 1.41) * math.log(5.98 * h / (0.8 * w + t))
        elif coupling == "diff":
            if diff_spacing is None:
                diff_spacing = w * 2  # 默认间距为2倍线宽
            # 差分阻抗 (简化公式)
            z_single = 87 / math.sqrt(er + 1.41) * math.log(5.98 * h / (0.8 * w + t))
            z0 = 2 * z_single * (1 - 0.48 * math.exp(-0.96 * diff_spacing / h))
        else:
            raise ValueError(f"Unknown coupling type: {coupling}")

        # 计算传播延迟 (ps/mm)
        delay = 3.34 * math.sqrt(er)  # ps/mm

        return {
            "impedance": round(z0, 2),
            "trace_width": w,
            "dielectric_thickness": h,
            "dk": er,
            "propagation_delay": round(delay, 2),
            "coupling": coupling,
            "diff_spacing": diff_spacing if coupling == "diff" else None,
        }

    def _get_layer_distance_and_dk(
        self,
        layer1_name: str,
        layer2_name: str
    ) -> Tuple[float, float]:
        """
        获取两层之间的距离和介电常数

        Returns:
            Tuple: (distance_mm, dk)
        """
        if not self.current_stackup:
            return (0.2, 4.5)  # 默认值

        layer1 = self.current_stackup.get_layer_by_name(layer1_name)
        layer2 = self.current_stackup.get_layer_by_name(layer2_name)

        if not layer1 or not layer2:
            return (0.2, 4.5)

        # 查找层间的介电层
        total_distance = 0.0
        dk_values = []

        for dielectric in self.current_stackup.dielectric_layers:
            # 检查介电层是否在两个铜层之间
            layers_between = sorted([layer1.layer_number, layer2.layer_number])
            if (dielectric.above_layer >= layers_between[0] and
                dielectric.below_layer <= layers_between[1]):
                total_distance += dielectric.thickness
                dk_values.append(dielectric.material.dk)

        # 使用平均介电常数
        avg_dk = sum(dk_values) / len(dk_values) if dk_values else 4.5

        return (total_distance, avg_dk)

    def get_optimal_trace_width(
        self,
        target_impedance: float,
        layer_name: str,
        reference_layer: str,
        coupling: str = "single"
    ) -> float:
        """
        计算达到目标阻抗的最佳走线宽度

        使用迭代方法反推线宽

        Args:
            target_impedance: 目标阻抗 (Ohms)
            layer_name: 信号层名称
            reference_layer: 参考平面层名称
            coupling: single/diff

        Returns:
            float: 建议走线宽度 (mm)
        """
        # 二分搜索最佳线宽
        low, high = 0.05, 5.0  # 搜索范围 0.05mm - 5mm
        tolerance = 0.5  # 阻抗容差 0.5 Ohm

        best_width = 0.25  # 默认值

        for _ in range(20):  # 最多20次迭代
            mid = (low + high) / 2
            result = self.calculate_impedance(mid, layer_name, reference_layer, coupling)
            z = result["impedance"]

            if abs(z - target_impedance) < tolerance:
                return mid

            if z > target_impedance:
                # 阻抗太高，需要增加线宽
                low = mid
            else:
                # 阻抗太低，需要减小线宽
                high = mid

            best_width = mid

        return round(best_width, 3)

    def get_stackup_summary(self) -> Dict[str, Any]:
        """获取层叠摘要信息"""
        if not self.current_stackup:
            return {"error": "No stackup loaded"}

        stackup = self.current_stackup

        return {
            "name": stackup.name,
            "layer_count": stackup.layer_count,
            "total_thickness": stackup.total_thickness,
            "signal_layers": [l.name for l in stackup.get_signal_layers()],
            "plane_layers": [l.name for l in stackup.get_plane_layers()],
            "copper_layers": [
                {
                    "name": l.name,
                    "type": l.layer_type.value,
                    "plane_type": l.plane_type.value if l.plane_type else None,
                    "thickness": l.thickness,
                }
                for l in stackup.copper_layers
            ],
            "dielectric_layers": [
                {
                    "name": d.name,
                    "thickness": d.thickness,
                    "material": d.material.name,
                    "dk": d.material.dk,
                }
                for d in stackup.dielectric_layers
            ],
        }

    def to_kicad_format(self) -> str:
        """转换为 KiCad 层叠格式"""
        if not self.current_stackup:
            return ""

        lines = [f"(layers\n"]

        for layer in self.current_stackup.copper_layers:
            layer_type = "signal" if layer.layer_type == LayerType.SIGNAL else "power"
            lines.append(f'  ({layer.layer_number} "{layer.name}" {layer_type})\n')

        lines.append(")")
        return "".join(lines)


def get_recommended_stackup(
    layer_count: int,
    application: str = "general"
) -> str:
    """
    获取推荐的层叠模板名称

    Args:
        layer_count: 层数
        application: 应用场景 (general, high_speed, rf, power)

    Returns:
        str: 模板名称
    """
    recommendations = {
        2: "2layer",
        4: "4layer_standard" if application == "general" else "4layer_thin",
        6: "6layer_optimized" if application in ["high_speed", "rf"] else "6layer_standard",
    }

    return recommendations.get(layer_count, "4layer_standard")


def calculate_crosstalk(
    trace_spacing: float,
    dielectric_thickness: float,
    trace_width: float = 0.25
) -> float:
    """
    计算串扰系数

    简化模型: 串扰与间距/高度比相关

    Args:
        trace_spacing: 走线间距 (mm)
        dielectric_thickness: 介质厚度 (mm)
        trace_width: 走线宽度 (mm)

    Returns:
        float: 串扰系数 (0-1, 越小越好)
    """
    # 简化公式
    spacing_ratio = trace_spacing / dielectric_thickness

    if spacing_ratio < 1:
        return 0.3  # 高串扰
    elif spacing_ratio < 3:
        return 0.15  # 中等串扰
    elif spacing_ratio < 5:
        return 0.05  # 低串扰
    else:
        return 0.01  # 可忽略串扰


# 便捷的工厂函数
def create_2layer_stackup() -> LayerStackup:
    """创建2层板层叠"""
    manager = StackupManager()
    return manager.load_template("2layer")


def create_4layer_stackup(thin: bool = False) -> LayerStackup:
    """创建4层板层叠"""
    manager = StackupManager()
    template = "4layer_thin" if thin else "4layer_standard"
    return manager.load_template(template)


def create_6layer_stackup(optimized: bool = True) -> LayerStackup:
    """创建6层板层叠"""
    manager = StackupManager()
    template = "6layer_optimized" if optimized else "6layer_standard"
    return manager.load_template(template)
