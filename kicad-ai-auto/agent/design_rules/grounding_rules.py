"""
接地设计规则
Grounding Design Rules

确保电路板有正确的接地设计：
- 地平面完整性
- 模拟/数字地分离
- 星形接地
- 高频信号地回流路径
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class GroundingSpec:
    """接地规格"""

    ground_type: str  # analog, digital, power, chassis
    min_plane_area_pct: float  # 最小地平面面积百分比
    max_via_spacing_mm: float  # 最大过孔间距
    required: bool


# ========== 接地设计规则 ==========

GROUNDING_CONFIGS = {
    "mixed_signal": {
        "description": "混合信号电路（ADC/DAC）",
        "grounding_scheme": "split_ground",
        "agnd_spec": GroundingSpec(
            ground_type="analog",
            min_plane_area_pct=30,
            max_via_spacing_mm=3,
            required=True,
        ),
        "dgnd_spec": GroundingSpec(
            ground_type="digital",
            min_plane_area_pct=30,
            max_via_spacing_mm=2,
            required=True,
        ),
        "connection_point": "电源入口单点连接",
    },
    "power_supply": {
        "description": "电源电路",
        "grounding_scheme": "star_ground",
        "pgnd_spec": GroundingSpec(
            ground_type="power",
            min_plane_area_pct=50,
            max_via_spacing_mm=2,
            required=True,
        ),
        "sgnd_spec": GroundingSpec(
            ground_type="signal",
            min_plane_area_pct=20,
            max_via_spacing_mm=5,
            required=True,
        ),
        "connection_point": "大电流地与小信号地在电源入口星形连接",
    },
    "rf_circuit": {
        "description": "射频电路",
        "grounding_scheme": "solid_ground",
        "gnd_spec": GroundingSpec(
            ground_type="rf",
            min_plane_area_pct=70,
            max_via_spacing_mm=1.5,
            required=True,
        ),
        "via_fence": True,  # 需要过孔栅栏
        "via_fence_spacing_mm": 1.0,
    },
    "digital_only": {
        "description": "纯数字电路",
        "grounding_scheme": "solid_ground",
        "gnd_spec": GroundingSpec(
            ground_type="digital",
            min_plane_area_pct=40,
            max_via_spacing_mm=3,
            required=True,
        ),
    },
    "motor_driver": {
        "description": "电机驱动电路",
        "grounding_scheme": "separated_ground",
        "hgnd_spec": GroundingSpec(
            ground_type="high_current",
            min_plane_area_pct=40,
            max_via_spacing_mm=2,
            required=True,
        ),
        "lgnd_spec": GroundingSpec(
            ground_type="logic",
            min_plane_area_pct=20,
            max_via_spacing_mm=5,
            required=True,
        ),
        "connection_note": "大电流地与逻辑地在电源入口单点连接，使用0Ω电阻或磁珠",
    },
}


def get_grounding_rules() -> List[DesignRule]:
    """获取接地设计规则"""
    return [
        DesignRule(
            id="GROUNDING_001",
            category=DesignCategory.GROUNDING,
            name="地平面完整性",
            description="PCB必须有足够的地平面面积",
            check_function="check_ground_plane",
            fix_function="add_ground_plane",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="GROUNDING_002",
            category=DesignCategory.GROUNDING,
            name="模拟数字地分离",
            description="混合信号电路需要AGND/DGND分离",
            check_function="check_ground_separation",
            fix_function="separate_grounds",
            priority=1,
            auto_fix=False,
        ),
        DesignRule(
            id="GROUNDING_003",
            category=DesignCategory.GROUNDING,
            name="地回流路径",
            description="高频信号地回流路径不能过长",
            check_function="check_return_path",
            fix_function="optimize_return_path",
            priority=2,
            auto_fix=False,
        ),
        DesignRule(
            id="GROUNDING_004",
            category=DesignCategory.GROUNDING,
            name="接地过孔",
            description="地平面需要足够的接地过孔",
            check_function="check_ground_vias",
            fix_function="add_ground_vias",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="GROUNDING_005",
            category=DesignCategory.GROUNDING,
            name="星形接地",
            description="电源电路需要星形接地设计",
            check_function="check_star_ground",
            fix_function="implement_star_ground",
            priority=2,
            auto_fix=False,
        ),
    ]


def check_grounding(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查接地设计"""
    issues = []
    components = circuit_data.get("components", [])
    pcb_info = circuit_data.get("pcb_info", {})

    if rule.id == "GROUNDING_001":
        issues.extend(_check_ground_plane(components, pcb_info))
    elif rule.id == "GROUNDING_002":
        issues.extend(_check_ground_separation(components, pcb_info))
    elif rule.id == "GROUNDING_003":
        issues.extend(_check_return_path(components, pcb_info))
    elif rule.id == "GROUNDING_004":
        issues.extend(_check_ground_vias(pcb_info))
    elif rule.id == "GROUNDING_005":
        issues.extend(_check_star_ground(components, pcb_info))

    return issues


def _detect_circuit_type(components: List[Dict]) -> str:
    """检测电路类型"""
    has_adc = False
    has_dac = False
    has_mcu = False
    has_motor_driver = False
    has_rf = False
    has_power_ic = False

    for comp in components:
        model = comp.get("model", "").lower()
        name = comp.get("name", "").lower()

        if any(x in model for x in ["adc", "ads1115", "mcp3008"]):
            has_adc = True
        if any(x in model for x in ["dac", "mcp4725", "pcm5"]):
            has_dac = True
        if any(x in model for x in ["stm32", "atmega", "esp32", "attiny"]):
            has_mcu = True
        if any(x in model for x in ["l298", "tb6612", "drv88", "a4988"]):
            has_motor_driver = True
        if any(x in model for x in ["nrf24", "cc1101", "sx127", "rfm"]):
            has_rf = True
        if any(x in model for x in ["7805", "1117", "2596", "lm317", "uc384"]):
            has_power_ic = True

    if has_adc or has_dac:
        return "mixed_signal"
    if has_motor_driver:
        return "motor_driver"
    if has_rf:
        return "rf_circuit"
    if has_power_ic:
        return "power_supply"
    if has_mcu:
        return "digital_only"

    return "digital_only"


def _check_ground_plane(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查地平面完整性"""
    issues = []

    circuit_type = _detect_circuit_type(components)
    config = GROUNDING_CONFIGS.get(circuit_type, GROUNDING_CONFIGS["digital_only"])

    # 检查是否有地平面信息
    ground_plane_area = pcb_info.get("ground_plane_area_pct", 0)

    # 获取所需的最小地平面面积
    min_area = 0
    for key, spec in config.items():
        if isinstance(spec, GroundingSpec) and spec.required:
            min_area = max(min_area, spec.min_plane_area_pct)

    if ground_plane_area < min_area:
        issues.append(
            DesignIssue(
                rule_id="GROUNDING_001",
                category=DesignCategory.GROUNDING,
                severity="critical",
                message=f"地平面面积不足: {ground_plane_area}% < {min_area}%",
                suggestion=f"增加地平面铺铜至至少{min_area}%的PCB面积",
                auto_fixable=True,
            )
        )

    # 如果没有PCB信息，给出提示
    if ground_plane_area == 0:
        issues.append(
            DesignIssue(
                rule_id="GROUNDING_001",
                category=DesignCategory.GROUNDING,
                severity="warning",
                message="未检测到地平面设计",
                suggestion="在PCB底层或顶层添加地平面铺铜",
                auto_fixable=True,
            )
        )

    return issues


def _check_ground_separation(
    components: List[Dict], pcb_info: Dict
) -> List[DesignIssue]:
    """检查模拟数字地分离"""
    issues = []

    circuit_type = _detect_circuit_type(components)

    if circuit_type == "mixed_signal":
        # 检查是否有AGND和DGND网络
        nets = pcb_info.get("nets", [])
        has_agnd = any("agnd" in n.lower() or "analog" in n.lower() for n in nets)
        has_dgnd = any("dgnd" in n.lower() or "digital" in n.lower() for n in nets)

        if not (has_agnd and has_dgnd):
            issues.append(
                DesignIssue(
                    rule_id="GROUNDING_002",
                    category=DesignCategory.GROUNDING,
                    severity="warning",
                    message="混合信号电路缺少AGND/DGND分离",
                    suggestion="创建独立的AGND和DGND网络，在电源入口单点连接",
                    auto_fixable=False,
                )
            )

    return issues


def _check_return_path(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查地回流路径"""
    issues = []

    # 检查高频信号
    high_freq_signals = pcb_info.get("high_freq_signals", [])

    for signal in high_freq_signals:
        return_path_length = signal.get("return_path_length_mm", 0)
        signal_length = signal.get("signal_length_mm", 0)

        # 回流路径不应超过信号路径的1.5倍
        if return_path_length > signal_length * 1.5:
            issues.append(
                DesignIssue(
                    rule_id="GROUNDING_003",
                    category=DesignCategory.GROUNDING,
                    severity="warning",
                    message=f"信号 {signal.get('name', 'unknown')} 回流路径过长",
                    suggestion="调整地平面或在信号路径下方添加地线",
                    auto_fixable=False,
                )
            )

    return issues


def _check_ground_vias(pcb_info: Dict) -> List[DesignIssue]:
    """检查接地过孔"""
    issues = []

    ground_vias = pcb_info.get("ground_via_count", 0)
    board_area_mm2 = pcb_info.get("board_area_mm2", 1000)

    # 计算推荐的过孔数量
    # 经验规则: 每100mm²至少1个地过孔
    min_vias = max(4, int(board_area_mm2 / 100))

    if ground_vias < min_vias:
        issues.append(
            DesignIssue(
                rule_id="GROUNDING_004",
                category=DesignCategory.GROUNDING,
                severity="info",
                message=f"接地过孔数量不足: {ground_vias} < {min_vias}",
                suggestion=f"添加更多接地过孔，特别是在高频区域和IC接地引脚附近",
                auto_fixable=True,
            )
        )

    return issues


def _check_star_ground(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查星形接地"""
    issues = []

    circuit_type = _detect_circuit_type(components)

    if circuit_type in ["power_supply", "motor_driver"]:
        # 检查是否有星形接地设计
        has_star_ground = pcb_info.get("has_star_ground", False)

        if not has_star_ground:
            issues.append(
                DesignIssue(
                    rule_id="GROUNDING_005",
                    category=DesignCategory.GROUNDING,
                    severity="warning",
                    message="电源电路缺少星形接地设计",
                    suggestion="将大电流地和小信号地在电源入口单点连接",
                    auto_fixable=False,
                )
            )

    return issues


def fix_grounding(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复接地问题"""
    pcb_info = circuit_data.get("pcb_info", {})

    if rule.id == "GROUNDING_001":
        # 添加地平面设计建议
        if "pcb_design_notes" not in circuit_data:
            circuit_data["pcb_design_notes"] = []
        circuit_data["pcb_design_notes"].append(
            {
                "category": "grounding",
                "note": "在底层添加完整地平面铺铜，顶层在元件间隙添加地填充",
                "priority": "high",
            }
        )

    elif rule.id == "GROUNDING_004":
        # 添加接地过孔建议
        if "pcb_design_notes" not in circuit_data:
            circuit_data["pcb_design_notes"] = []
        circuit_data["pcb_design_notes"].append(
            {
                "category": "grounding",
                "note": "每隔2-3mm添加接地过孔，特别是IC接地引脚附近",
                "priority": "medium",
            }
        )

    return circuit_data


def get_grounding_recommendation(components: List[Dict]) -> Dict:
    """获取接地设计建议"""
    circuit_type = _detect_circuit_type(components)
    config = GROUNDING_CONFIGS.get(circuit_type, GROUNDING_CONFIGS["digital_only"])

    recommendation = {
        "circuit_type": circuit_type,
        "description": config.get("description", ""),
        "grounding_scheme": config.get("grounding_scheme", "solid_ground"),
        "requirements": [],
        "implementation_notes": [],
    }

    for key, spec in config.items():
        if isinstance(spec, GroundingSpec):
            recommendation["requirements"].append(
                {
                    "ground_type": spec.ground_type,
                    "min_plane_area_pct": spec.min_plane_area_pct,
                    "max_via_spacing_mm": spec.max_via_spacing_mm,
                    "required": spec.required,
                }
            )

    if "connection_point" in config:
        recommendation["implementation_notes"].append(config["connection_point"])

    if "connection_note" in config:
        recommendation["implementation_notes"].append(config["connection_note"])

    return recommendation
