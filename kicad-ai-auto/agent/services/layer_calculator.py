"""
PCB Layer Calculator - 自动层数判定引擎

根据电路复杂度自动判定 PCB 层数，支持:
- 高频信号分析
- 电源完整性分析
- 高速 IO 数量统计
- 差分对数量统计
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class CircuitComplexity(Enum):
    """电路复杂度等级"""
    SIMPLE = "simple"           # 简单电路
    STANDARD = "standard"       # 普通数字电路
    COMPLEX = "complex"         # 复杂电路
    HIGH_SPEED = "high_speed"   # 高速电路
    ADVANCED = "advanced"       # 高级电路


@dataclass
class CircuitAnalysis:
    """电路分析结果"""
    circuit_type: str = "digital"  # "digital", "power", "mixed", "rf", "analog"
    complexity: CircuitComplexity = CircuitComplexity.STANDARD

    # 信号分析
    high_speed_signal_ghz: float = 0.0  # 最高信号频率 (GHz)
    high_speed_io_count: int = 0          # 高速 IO 数量
    differential_pair_count: int = 0      # 差分对数量

    # 电源分析
    power_rails_count: int = 0           # 电源路数
    max_current_ma: float = 0.0          # 最大电流 (mA)
    is_power_critical: bool = False       # 是否是电源关键电路

    # 布局分析
    component_count: int = 0             # 元器件数量
    estimated_pins: int = 0             # 预估引脚数
    has_rf: bool = False                # 是否有 RF 元件

    # 特殊需求
    has_impedance_control: bool = False   # 是否需要阻抗控制
    has_analog_mixed: bool = False       # 是否有模拟混合信号
    is_high_density: bool = False        # 是否是高密度设计

    def to_dict(self) -> Dict[str, Any]:
        return {
            "circuit_type": self.circuit_type,
            "complexity": self.complexity.value,
            "high_speed_signal_ghz": self.high_speed_signal_ghz,
            "high_speed_io_count": self.high_speed_io_count,
            "differential_pair_count": self.differential_pair_count,
            "power_rails_count": self.power_rails_count,
            "max_current_ma": self.max_current_ma,
            "is_power_critical": self.is_power_critical,
            "component_count": self.component_count,
            "estimated_pins": self.estimated_pins,
            "has_rf": self.has_rf,
            "has_impedance_control": self.has_impedance_control,
            "has_analog_mixed": self.has_analog_mixed,
            "is_high_density": self.is_high_density,
        }


@dataclass
class LayerRecommendation:
    """层数推荐结果"""
    layer_count: int                      # 推荐层数
    primary_reason: str                   # 主要原因
    reasons: List[str] = field(default_factory=list)  # 所有原因列表
    confidence: float = 0.9              # 推荐置信度
    alternatives: Dict[int, str] = field(default_factory=dict)  # 替代方案
    warnings: List[str] = field(default_factory=list)  # 警告信息
    analysis: Optional[CircuitAnalysis] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "layer_count": self.layer_count,
            "primary_reason": self.primary_reason,
            "reasons": self.reasons,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "warnings": self.warnings,
        }
        if self.analysis:
            result["analysis"] = self.analysis.to_dict()
        return result


class LayerCalculator:
    """
    PCB 层数自动判定引擎

    根据电路特性自动计算最佳 PCB 层数。

    判定规则:
    - 高频信号 > 5GHz 或 差分对 > 4对 → 6层
    - 高频信号 > 1GHz 或 > 20个高速IO → 4层
    - 电源 > 3路 或 > 10A电流 → 4层
    - 普通数字电路 → 2层
    - 单面THT或简单电路 → 1层
    """

    # 层数判定阈值
    THRESHOLDS = {
        # 高速信号阈值 (GHz)
        "high_speed_5g": 5.0,    # > 5GHz 需要 6层
        "high_speed_1g": 1.0,    # > 1GHz 需要 4层

        # 高速 IO 阈值
        "high_io_count": 20,     # > 20 高速 IO 需要 4层

        # 差分对阈值
        "diff_pair_4": 4,        # > 4 对差分对需要 6层

        # 电源阈值
        "power_rails_3": 3,      # > 3 路电源需要 4层
        "current_10a": 10000,    # > 10A 需要 4层 (单位: mA)

        # 复杂度阈值
        "components_50": 50,      # > 50 元件可能是复杂设计
        "pins_300": 300,         # > 300 引脚需要多层
    }

    # 层数配置
    LAYER_CONFIGS = {
        1: {"name": "单层板", "cost": 1.0, "best_for": ["简单电路", "THT", "原型"]},
        2: {"name": "双层板", "cost": 1.5, "best_for": ["普通数字电路", "简单电源"]},
        4: {"name": "四层板", "cost": 3.0, "best_for": ["高速电路", "电源完整性", "多电源"]},
        6: {"name": "六层板", "cost": 5.0, "best_for": ["高频电路", "差分对", "阻抗控制"]},
        8: {"name": "八层板", "cost": 8.0, "best_for": ["高端产品", "复杂系统"]},
    }

    def analyze_circuit(self, circuit_data: Dict[str, Any]) -> CircuitAnalysis:
        """
        分析电路数据，提取特征

        Args:
            circuit_data: 电路数据字典，包含以下可选字段:
                - components: 元件列表
                - nets: 网络列表
                - requirements: 需求描述
                - component_count: 元件数量
                - high_speed_signals: 高速信号列表
                - power_rails: 电源轨道列表

        Returns:
            CircuitAnalysis: 电路分析结果
        """
        analysis = CircuitAnalysis()

        # 从 components 提取基本信息
        components = circuit_data.get("components", [])
        if isinstance(components, list):
            analysis.component_count = len(components)
            # 估算引脚数 (假设每个元件平均 4 个引脚)
            analysis.estimated_pins = analysis.component_count * 4

        # 从 requirements 提取需求信息
        requirements = circuit_data.get("requirements", "")
        if requirements:
            requirements_lower = requirements.lower()
            self._analyze_requirements(analysis, requirements_lower)

        # 从 high_speed_signals 提取高速信号信息
        high_speed_signals = circuit_data.get("high_speed_signals", [])
        if isinstance(high_speed_signals, list):
            analysis.high_speed_io_count = len(high_speed_signals)
            for signal in high_speed_signals:
                if isinstance(signal, dict):
                    freq = signal.get("frequency_ghz", 0)
                    if freq > analysis.high_speed_signal_ghz:
                        analysis.high_speed_signal_ghz = freq

        # 从 power_rails 提取电源信息
        power_rails = circuit_data.get("power_rails", [])
        if isinstance(power_rails, list):
            analysis.power_rails_count = len(power_rails)
            for rail in power_rails:
                if isinstance(rail, dict):
                    current = rail.get("current_ma", 0)
                    if current > analysis.max_current_ma:
                        analysis.max_current_ma = current

        # 从 nets 推断电源信息
        nets = circuit_data.get("nets", [])
        if isinstance(nets, list):
            self._analyze_nets(analysis, nets)

        # 从 components 推断类型
        if components:
            self._analyze_components(analysis, components)

        # 计算复杂度
        analysis.complexity = self._determine_complexity(analysis)

        return analysis

    def _analyze_requirements(self, analysis: CircuitAnalysis, requirements: str) -> None:
        """从需求描述中提取信息"""
        import re

        # 使用灵活的分隔符匹配关键词
        # 关键词可以是: USB, USB-C, USB_C, usb-c 等
        def contains_keyword(keywords: list, text: str) -> bool:
            """检查文本中是否包含关键词（支持连字符和下划线分隔）"""
            for kw in keywords:
                # 匹配: 独立单词, 或带连字符/下划线/点号的组合
                # 例如 "usb" 匹配 "USB", "USB-C", "usb_c", "usb.type"
                pattern = r'(?:^|[\s\-_.,])' + re.escape(kw) + r'(?:[\s\-_.,]|$)'
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            return False

        # 检测电路类型
        if contains_keyword(["usb", "ethernet", "pcie", "ddr", "hdmi"], requirements):
            # USB/Ethernet 即使 IO 数量少也是高速接口，直接标记
            analysis.high_speed_io_count = max(analysis.high_speed_io_count, 8)
        if contains_keyword(["rf", "radio", "wifi", "bluetooth"], requirements):
            analysis.has_rf = True
        if contains_keyword(["motor", "driver", "mosfet"], requirements):
            analysis.circuit_type = "power"
            analysis.is_power_critical = True
        if contains_keyword(["audio", "adc", "dac", "analog", "sensor"], requirements):
            analysis.has_analog_mixed = True

        # 检测阻抗控制需求
        if "impedance" in requirements or "differential" in requirements:
            analysis.has_impedance_control = True

        # 检测高频信号 - 解析所有频率并取最大值
        freq_matches = re.findall(r'(\d+(?:\.\d+)?)\s*GHz', requirements, re.IGNORECASE)
        for match in freq_matches:
            freq = float(match)
            if freq > analysis.high_speed_signal_ghz:
                analysis.high_speed_signal_ghz = freq

        # 如果没有显式频率但检测到RF关键词，设置默认RF频率
        if analysis.has_rf and not freq_matches:
            analysis.high_speed_signal_ghz = max(analysis.high_speed_signal_ghz, 2.4)

    def _analyze_nets(self, analysis: CircuitAnalysis, nets: List) -> None:
        """从网络列表中提取电源信息"""
        power_keywords = ["vcc", "vdda", "vdd", "gnd", "agnd", "power", "3v3", "5v", "12v", "24v"]
        diff_pair_patterns = ["_p_", "_n_", "_p$", "_n$", "_p-", "_n-", "diff", "pair", "_tx", "_rx"]
        high_speed_prefixes = ["usb", "eth", "pcie", "ddr", "hdmi", "dp_", "sata", "sfp"]

        diff_pair_count = 0  # Track potential diff pairs

        for net in nets:
            if isinstance(net, dict):
                net_name = net.get("name", "").lower()
                net_type = net.get("type", "").lower()

                # 检测电源网络
                if any(kw in net_name for kw in power_keywords):
                    analysis.power_rails_count = max(analysis.power_rails_count, 1)

                # 检测显式标记的差分对
                if "diff" in net_name or "pair" in net_type:
                    analysis.differential_pair_count += 1

                # 检测高速网络
                if any(net_name.startswith(prefix) for prefix in high_speed_prefixes):
                    analysis.high_speed_io_count += 1

                # 检测可能的差分对 (通过 _P/_N 后缀模式)
                if any(pattern in net_name for pattern in diff_pair_patterns):
                    diff_pair_count += 1

        # 每2个差分对构成一对
        analysis.differential_pair_count += diff_pair_count // 2

    def _analyze_components(self, analysis: CircuitAnalysis, components: List) -> None:
        """从元件列表中推断电路类型"""
        high_speed_keywords = ["USB", "Ethernet", "PCIe", "DDR", "HDMI", "DP", "SFP"]
        power_keywords = ["MOSFET", "IGBT", "Motor", "Driver", " regulator", "power"]
        rf_keywords = ["RF", "Wifi", "Bluetooth", " transceiver", "antenna"]

        component_refs = [str(c) for c in components]

        # 简单计数
        analysis.component_count = len(components)

        # 检查高速元件
        for comp in components:
            if isinstance(comp, dict):
                comp_str = str(comp)
            else:
                comp_str = str(comp)

            if any(kw in comp_str.lower() for kw in [k.lower() for k in high_speed_keywords]):
                analysis.high_speed_io_count += 4
            if any(kw in comp_str.lower() for kw in [k.lower() for k in power_keywords]):
                analysis.is_power_critical = True
            if any(kw in comp_str.lower() for kw in [k.lower() for k in rf_keywords]):
                analysis.has_rf = True

        # 估算引脚数
        analysis.estimated_pins = analysis.component_count * 4

        # 检测是否是高密度设计
        if analysis.component_count > self.THRESHOLDS["components_50"]:
            analysis.is_high_density = True

    def _determine_complexity(self, analysis: CircuitAnalysis) -> CircuitComplexity:
        """确定电路复杂度"""
        # 检查高级需求
        if (analysis.high_speed_signal_ghz > self.THRESHOLDS["high_speed_5g"] or
                analysis.differential_pair_count > self.THRESHOLDS["diff_pair_4"]):
            return CircuitComplexity.ADVANCED

        # 检查高速需求
        if (analysis.high_speed_signal_ghz > self.THRESHOLDS["high_speed_1g"] or
                analysis.high_speed_io_count > self.THRESHOLDS["high_io_count"] or
                analysis.has_impedance_control):
            return CircuitComplexity.HIGH_SPEED

        # 检查电源需求
        if (analysis.power_rails_count > self.THRESHOLDS["power_rails_3"] or
                analysis.max_current_ma > self.THRESHOLDS["current_10a"]):
            return CircuitComplexity.COMPLEX

        # 检查普通数字电路
        if analysis.component_count > 10:
            return CircuitComplexity.STANDARD

        return CircuitComplexity.SIMPLE

    def calculate_layers(self, circuit: CircuitAnalysis) -> LayerRecommendation:
        """
        根据电路分析结果计算推荐层数

        Args:
            circuit: 电路分析结果

        Returns:
            LayerRecommendation: 层数推荐结果
        """
        reasons = []
        warnings = []
        confidence = 0.9
        base_layers = 2  # 默认双面板

        # === 优先级1: 极高频/差分对 → 6层 ===
        if circuit.high_speed_signal_ghz >= self.THRESHOLDS["high_speed_5g"]:
            reasons.append(f"超高频信号 ({circuit.high_speed_signal_ghz:.1f} GHz >= 5 GHz)")
            base_layers = max(base_layers, 6)
            confidence = 0.95

        if circuit.differential_pair_count >= self.THRESHOLDS["diff_pair_4"]:
            reasons.append(f"差分对数量 ({circuit.differential_pair_count} 对 >= 4 对)")
            base_layers = max(base_layers, 6)
            confidence = 0.95

        # === 优先级2: 高速/多IO → 4层 ===
        if circuit.high_speed_signal_ghz > self.THRESHOLDS["high_speed_1g"]:
            reasons.append(f"高频信号 ({circuit.high_speed_signal_ghz:.1f} GHz > 1 GHz)")
            base_layers = max(base_layers, 4)
            confidence = 0.9

        if circuit.high_speed_io_count > self.THRESHOLDS["high_io_count"]:
            reasons.append(f"高速 IO 数量 ({circuit.high_speed_io_count} > 20)")
            base_layers = max(base_layers, 4)
            confidence = 0.9
        elif circuit.high_speed_io_count >= 8:
            # USB/Ethernet 等高速接口即使 IO 数量不多也需要 4 层
            reasons.append(f"高速接口 (USB/Ethernet 等)")
            base_layers = max(base_layers, 4)
            confidence = 0.85

        if circuit.has_impedance_control:
            reasons.append("需要阻抗控制")
            base_layers = max(base_layers, 4)
            confidence = 0.85

        # === 优先级3: 电源完整性 → 4层 ===
        if circuit.power_rails_count > self.THRESHOLDS["power_rails_3"]:
            reasons.append(f"多电源设计 ({circuit.power_rails_count} 路电源)")
            base_layers = max(base_layers, 4)
            confidence = 0.9

        if circuit.max_current_ma > self.THRESHOLDS["current_10a"]:
            reasons.append(f"高电流设计 ({circuit.max_current_ma:.0f} mA > 10A)")
            base_layers = max(base_layers, 4)
            confidence = 0.9
            warnings.append("高电流电路建议使用电源平面和更宽的走线")

        # === 优先级4: 复杂度和类型调整 ===
        if circuit.complexity == CircuitComplexity.SIMPLE and circuit.component_count <= 5:
            # 极简单电路可以用单面板，但高速接口除外
            if circuit.high_speed_io_count < 8 and circuit.high_speed_signal_ghz == 0:
                base_layers = min(base_layers, 1)
                reasons.append("简单电路，可使用单面板降低成本")

        if circuit.has_rf:
            reasons.append("RF 电路需要专门的布局考虑")
            base_layers = max(base_layers, 4)
            warnings.append("RF 电路建议使用专门的RF板材")

        if circuit.has_analog_mixed:
            reasons.append("模拟混合信号电路")
            base_layers = max(base_layers, 4)
            warnings.append("建议使用独立的模拟和数字地平面")

        # === 检查替代方案 ===
        alternatives = {}
        if base_layers > 2:
            alternatives[2] = "降低性能要求，减少高速IO，使用低速协议"
        if base_layers > 4:
            alternatives[4] = "降低信号频率要求，使用并行总线替代高速串行"

        # === 生成警告 ===
        if circuit.is_high_density and base_layers < 4:
            warnings.append("高密度设计建议使用4层或更多层以提高布线灵活性")

        if circuit.is_power_critical and base_layers < 4:
            warnings.append("电源关键电路建议使用4层以获得更好的电源完整性")

        # 确定主要原因
        primary_reason = reasons[0] if reasons else "标准双层板设计"

        return LayerRecommendation(
            layer_count=base_layers,
            primary_reason=primary_reason,
            reasons=reasons,
            confidence=confidence,
            alternatives=alternatives,
            warnings=warnings,
            analysis=circuit
        )

    def calculate_layers_from_dict(self, circuit_data: Dict[str, Any]) -> LayerRecommendation:
        """
        从电路数据字典直接计算层数

        Args:
            circuit_data: 电路数据字典

        Returns:
            LayerRecommendation: 层数推荐结果
        """
        analysis = self.analyze_circuit(circuit_data)
        return self.calculate_layers(analysis)

    def get_layer_config(self, layer_count: int) -> Dict[str, Any]:
        """
        获取层数配置信息

        Args:
            layer_count: 层数

        Returns:
            Dict: 层数配置信息
        """
        return self.LAYER_CONFIGS.get(layer_count, {
            "name": f"{layer_count}层板",
            "cost": layer_count * 1.2,
            "best_for": ["自定义设计"]
        })

    def estimate_cost_factor(self, layer_count: int) -> float:
        """
        估算层数对成本的影响因子

        Args:
            layer_count: 层数

        Returns:
            float: 成本因子 (相对于双面板)
        """
        configs = {
            1: 0.6,   # 单面板最便宜
            2: 1.0,   # 双面板基准
            4: 2.5,   # 四层板
            6: 4.5,   # 六层板
            8: 7.0,   # 八层板
        }
        return configs.get(layer_count, layer_count * 1.0)
