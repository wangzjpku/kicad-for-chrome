"""
电路特征相似度匹配器

基于电路特征而非关键词匹配，实现更精确的相似案例检索
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import re
from enum import Enum


class ComponentType(Enum):
    """元件类型枚举"""
    MCU = "mcu"
    CPU = "cpu"
    FPGA = "fpga"
    DSP = "dsp"
    MEMORY = "memory"
    POWER_IC = "power_ic"
    RF_MODULE = "rf_module"
    SENSOR = "sensor"
    DRIVER = "driver"
    AMPLIFIER = "amplifier"
    CONNECTOR = "connector"
    PASSIVE = "passive"
    CRYSTAL = "crystal"
    LED = "led"
    DISPLAY = "display"
    UNKNOWN = "unknown"


class InterfaceType(Enum):
    """接口类型枚举"""
    USB = "usb"
    UART = "uart"
    SPI = "spi"
    I2C = "i2c"
    CAN = "can"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    NFC = "nfc"
    GPS = "gps"
    HDMI = "hdmi"
    SDIO = "sdio"
    I2S = "i2s"
    ADC = "adc"
    DAC = "dac"
    PWM = "pwm"
    GPIO = "gpio"
    JTAG = "jtag"
    SWD = "swd"


class ApplicationDomain(Enum):
    """应用领域枚举"""
    IOT = "iot"
    INDUSTRIAL = "industrial"
    AUTOMOTIVE = "automotive"
    CONSUMER = "consumer"
    MEDICAL = "medical"
    AEROSPACE = "aerospace"
    COMMUNICATION = "communication"
    POWER_MANAGEMENT = "power_management"
    AUDIO = "audio"
    VIDEO = "video"
    MOTOR_CONTROL = "motor_control"
    SENSOR_INTERFACE = "sensor_interface"


class FrequencyBand(Enum):
    """频段枚举"""
    DC = "dc"           # 直流/低频 (<1MHz)
    LOW = "low"         # 低频 (1-10MHz)
    MEDIUM = "medium"   # 中频 (10-100MHz)
    HIGH = "high"       # 高频 (100MHz-1GHz)
    RF = "rf"           # 射频 (1-10GHz)
    MICROWAVE = "microwave"  # 微波 (>10GHz)


class PowerLevel(Enum):
    """功率等级枚举"""
    LOW = "low"         # <1W
    MEDIUM = "medium"   # 1-10W
    HIGH = "high"       # 10-100W
    VERY_HIGH = "very_high"  # >100W


@dataclass
class CircuitFeatures:
    """电路特征"""
    # 元件类型 (类型: 数量)
    components: Dict[ComponentType, int] = field(default_factory=dict)

    # 接口类型 (类型: 数量)
    interfaces: Dict[InterfaceType, int] = field(default_factory=dict)

    # 应用领域 (领域: 权重)
    application_domains: Dict[ApplicationDomain, float] = field(default_factory=dict)

    # 频段
    frequency_band: FrequencyBand = FrequencyBand.DC

    # 功率等级
    power_level: PowerLevel = PowerLevel.LOW

    # 设计难度
    difficulty: str = "medium"

    # 关键特征标签
    feature_tags: Set[str] = field(default_factory=set)

    # 质量分数
    quality_score: float = 0.0


class FeatureExtractor:
    """电路特征提取器"""

    # 元件关键词映射
    COMPONENT_KEYWORDS = {
        ComponentType.MCU: ["stm32", "esp32", "arduino", "atmega", "avr", "mcu", "microcontroller",
                           "nrf52", "nrf52832", "rp2040", "pic", "msp430", " cortex"],
        ComponentType.CPU: ["cpu", "processor", "bcm", "allwinner", "rockchip", "mediatek"],
        ComponentType.FPGA: ["fpga", "cyclone", "spartan", "zynq", "lattice"],
        ComponentType.DSP: ["dsp", "digital signal"],
        ComponentType.MEMORY: ["sdram", "ddr", "flash", "eeprom", "sram", "nor", "nand"],
        ComponentType.POWER_IC: ["buck", "boost", "ldo", "dc-dc", "lm2596", "tps", "ltc",
                                 "charger", "tp4056", "power management"],
        ComponentType.RF_MODULE: ["wifi", "bluetooth", "ble", "nfc", "rf", "antenna", "lora",
                                  "zigbee", "433mhz", "2.4ghz", "sub-ghz"],
        ComponentType.SENSOR: ["sensor", "accelerometer", "gyroscope", "temperature", "humidity",
                              "pressure", "imu", "mpu6050", "hall"],
        ComponentType.DRIVER: ["driver", "h-bridge", "l298n", "motor driver", "led driver",
                              "gate driver", "mosfet driver"],
        ComponentType.AMPLIFIER: ["amplifier", "opa", "tpa", "audio amp", "class d",
                                  "instrumentation amp", "ad623"],
        ComponentType.CONNECTOR: ["usb", "hdmi", "rj45", "sd card", "fpc", "header",
                                  "connector", "jst", "molex"],
        ComponentType.CRYSTAL: ["crystal", "oscillator", "xtal", "mhz", "rtc"],
        ComponentType.LED: ["led", "ws2812", "rgb", "neopixel"],
        ComponentType.DISPLAY: ["lcd", "oled", "tft", "display", "screen", "e-ink"],
    }

    # 接口关键词映射
    INTERFACE_KEYWORDS = {
        InterfaceType.USB: ["usb", "usb-c", "usb2.0", "usb3.0", "micro usb"],
        InterfaceType.UART: ["uart", "serial", "rs232", "rs485", "ttl"],
        InterfaceType.SPI: ["spi", "miso", "mosi", "sck", "ss"],
        InterfaceType.I2C: ["i2c", "iic", "sda", "scl", "twi"],
        InterfaceType.CAN: ["can", "can bus", "can-bus", "can h", "can l"],
        InterfaceType.ETHERNET: ["ethernet", "rj45", "phy", "mac", "rmii", "rgmii"],
        InterfaceType.WIFI: ["wifi", "wi-fi", "802.11", "esp8266", "esp32"],
        InterfaceType.BLUETOOTH: ["bluetooth", "ble", "bt", "nrf"],
        InterfaceType.NFC: ["nfc", "pn532", "13.56mhz", "rfid"],
        InterfaceType.GPS: ["gps", "gnss", "neo-m8", "ublox"],
        InterfaceType.HDMI: ["hdmi", "displayport", "dp"],
        InterfaceType.SDIO: ["sdio", "sd card", "microsd", "emmc"],
        InterfaceType.I2S: ["i2s", "pcm", "audio interface"],
        InterfaceType.ADC: ["adc", "analog input", "ads1115"],
        InterfaceType.DAC: ["dac", "analog output"],
        InterfaceType.PWM: ["pwm", "pulse width"],
        InterfaceType.GPIO: ["gpio", "digital io", "pin"],
        InterfaceType.JTAG: ["jtag", "debug"],
        InterfaceType.SWD: ["swd", "swclk", "swdio"],
    }

    # 应用领域关键词映射
    DOMAIN_KEYWORDS = {
        ApplicationDomain.IOT: ["iot", "internet of things", "smart home", "wearable",
                                "connected", "mqtt", "cloud"],
        ApplicationDomain.INDUSTRIAL: ["industrial", "plc", "automation", "factory",
                                        "modbus", "profibus", "4-20ma"],
        ApplicationDomain.AUTOMOTIVE: ["automotive", "car", "vehicle", "can bus", "obd"],
        ApplicationDomain.CONSUMER: ["consumer", "gadget", "portable", "battery powered"],
        ApplicationDomain.MEDICAL: ["medical", "healthcare", "patient", "biometric"],
        ApplicationDomain.AEROSPACE: ["aerospace", "aviation", "satellite", "radar"],
        ApplicationDomain.COMMUNICATION: ["communication", "telecom", "base station",
                                          "antenna", "transceiver"],
        ApplicationDomain.POWER_MANAGEMENT: ["power supply", "charger", "battery management",
                                              "bms", "dc-dc", "inverter"],
        ApplicationDomain.AUDIO: ["audio", "speaker", "microphone", "amplifier",
                                  "dac", "codec"],
        ApplicationDomain.VIDEO: ["video", "camera", "display", "hdmi", "mipi"],
        ApplicationDomain.MOTOR_CONTROL: ["motor", "driver", "pwm", "h-bridge",
                                          "bldc", "stepper"],
        ApplicationDomain.SENSOR_INTERFACE: ["sensor", "daq", "data acquisition",
                                              "signal conditioning"],
    }

    # 频率关键词映射
    FREQUENCY_KEYWORDS = {
        FrequencyBand.DC: ["dc", "battery", "power supply", "low frequency"],
        FrequencyBand.LOW: ["1mhz", "2mhz", "8mhz", "10mhz", "crystal"],
        FrequencyBand.MEDIUM: ["16mhz", "25mhz", "26mhz", "48mhz", "100mhz"],
        FrequencyBand.HIGH: ["usb3", "hdmi", "ddr", "high speed", "100mhz+", "ghz"],
        FrequencyBand.RF: ["wifi", "bluetooth", "2.4ghz", "5ghz", "rf", "antenna", "lte", "4g"],
        FrequencyBand.MICROWAVE: ["microwave", "radar", "satellite", "5g"],
    }

    # 功率关键词映射
    POWER_KEYWORDS = {
        PowerLevel.LOW: ["battery", "low power", "coin cell", "wearable", "iot", "<1w"],
        PowerLevel.MEDIUM: ["usb powered", "5v", "3.3v", "adapter", "1w", "10w"],
        PowerLevel.HIGH: ["motor", "amplifier", "50w", "100w", "high power"],
        PowerLevel.VERY_HIGH: ["inverter", "psu", "power supply unit", "100w+", "kw"],
    }

    # 难度关键词映射
    DIFFICULTY_KEYWORDS = {
        "easy": ["simple", "basic", "beginner", "minimal", "easy"],
        "medium": ["standard", "typical", "medium", "intermediate"],
        "hard": ["complex", "advanced", "professional", "high speed", "rf",
                 "multilayer", "impedance", "emc"]
    }

    def extract_features(self, description: str) -> CircuitFeatures:
        """
        从项目描述中提取电路特征

        Args:
            description: 项目描述文本

        Returns:
            CircuitFeatures: 提取的电路特征
        """
        text = description.lower()
        features = CircuitFeatures()

        # 提取元件类型
        for comp_type, keywords in self.COMPONENT_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > 0:
                features.components[comp_type] = count

        # 提取接口类型
        for iface_type, keywords in self.INTERFACE_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > 0:
                features.interfaces[iface_type] = count

        # 提取应用领域
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text) / len(keywords)
            if score > 0:
                features.application_domains[domain] = score

        # 提取频段
        for freq_band, keywords in self.FREQUENCY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                features.frequency_band = freq_band
                break

        # 提取功率等级
        for power_level, keywords in self.POWER_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                features.power_level = power_level
                break

        # 提取难度
        for difficulty, keywords in self.DIFFICULTY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                features.difficulty = difficulty
                break

        # 提取特征标签
        feature_patterns = [
            r'decoupling|bypass\s*cap',
            r'differential\s*pair',
            r'impedance\s*match',
            r'ground\s*plane',
            r'power\s*plane',
            r'shield',
            r'esd\s*protect',
            r'thermal\s*via',
            r'heat\s*sink',
            r'via\s*stitch',
            r'copper\s*pour',
            r'signal\s*integrity',
            r'emi|emc',
            r'rf\s*routing',
            r'antenna\s*tuning',
            r'crystal\s*oscillator',
            r'reset\s*circuit',
            r'boot\s*mode',
            r'jtag|swd',
            r'power\s*sequencing',
        ]

        for pattern in feature_patterns:
            if re.search(pattern, text):
                features.feature_tags.add(pattern.replace(r'\s*', '_').replace(r'|', '_'))

        return features

    def extract_from_case(self, case) -> CircuitFeatures:
        """
        从DesignCase对象提取特征

        Args:
            case: DesignCase对象

        Returns:
            CircuitFeatures: 提取的电路特征
        """
        # 组合描述和关键特征
        full_text = f"{case.name} {case.description} "
        full_text += " ".join(f"{k} {v}" for k, v in case.key_features.items())
        full_text += " ".join(case.design_patterns)

        features = self.extract_features(full_text)
        features.difficulty = case.difficulty
        features.quality_score = case.quality_score

        return features


class SimilarityScorer:
    """相似度计算器"""

    def __init__(self):
        # 各维度的权重
        self.weights = {
            "component": 0.25,      # 元件相似度权重
            "interface": 0.20,      # 接口相似度权重
            "domain": 0.20,         # 应用领域相似度权重
            "frequency": 0.10,      # 频段相似度权重
            "power": 0.10,          # 功率等级相似度权重
            "difficulty": 0.10,     # 难度相似度权重
            "features": 0.05,       # 特征标签相似度权重
        }

    def compute_similarity(self,
                          features1: CircuitFeatures,
                          features2: CircuitFeatures) -> Tuple[float, Dict[str, float]]:
        """
        计算两个电路特征的综合相似度

        Args:
            features1: 第一个电路特征
            features2: 第二个电路特征

        Returns:
            Tuple[float, Dict[str, float]]: (综合相似度, 各维度相似度)
        """
        scores = {}

        # 1. 元件相似度 (Jaccard相似度)
        scores["component"] = self._jaccard_similarity(
            set(features1.components.keys()),
            set(features2.components.keys())
        )

        # 2. 接口相似度 (Jaccard相似度)
        scores["interface"] = self._jaccard_similarity(
            set(features1.interfaces.keys()),
            set(features2.interfaces.keys())
        )

        # 3. 应用领域相似度 (加权Jaccard)
        scores["domain"] = self._weighted_dict_similarity(
            features1.application_domains,
            features2.application_domains
        )

        # 4. 频段相似度 (枚举距离)
        scores["frequency"] = self._enum_similarity(
            features1.frequency_band,
            features2.frequency_band
        )

        # 5. 功率等级相似度 (枚举距离)
        scores["power"] = self._enum_similarity(
            features1.power_level,
            features2.power_level
        )

        # 6. 难度相似度
        scores["difficulty"] = 1.0 if features1.difficulty == features2.difficulty else 0.5

        # 7. 特征标签相似度 (Jaccard)
        scores["features"] = self._jaccard_similarity(
            features1.feature_tags,
            features2.feature_tags
        )

        # 计算加权综合相似度
        total_similarity = sum(
            scores[dim] * self.weights[dim]
            for dim in self.weights
        )

        return total_similarity, scores

    def _jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """计算Jaccard相似度"""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _weighted_dict_similarity(self,
                                  dict1: Dict,
                                  dict2: Dict) -> float:
        """计算加权字典相似度"""
        if not dict1 and not dict2:
            return 1.0
        if not dict1 or not dict2:
            return 0.0

        all_keys = set(dict1.keys()) | set(dict2.keys())
        similarity = 0.0

        for key in all_keys:
            v1 = dict1.get(key, 0)
            v2 = dict2.get(key, 0)
            # 归一化差异
            max_val = max(v1, v2)
            if max_val > 0:
                similarity += 1 - abs(v1 - v2) / max_val

        return similarity / len(all_keys) if all_keys else 0.0

    def _enum_similarity(self, enum1: Enum, enum2: Enum) -> float:
        """计算枚举类型相似度 (基于顺序距离)"""
        if enum1 == enum2:
            return 1.0

        # 获取枚举值列表
        enum_class = type(enum1)
        values = list(enum_class)

        # 计算归一化距离
        idx1 = values.index(enum1)
        idx2 = values.index(enum2)
        distance = abs(idx1 - idx2)
        max_distance = len(values) - 1

        return 1.0 - (distance / max_distance) if max_distance > 0 else 1.0


class EnhancedCaseMatcher:
    """增强版案例匹配器"""

    def __init__(self, case_library):
        """
        初始化匹配器

        Args:
            case_library: DesignCaseLibrary实例
        """
        self.case_library = case_library
        self.extractor = FeatureExtractor()
        self.scorer = SimilarityScorer()

        # 缓存已提取的案例特征
        self._case_features_cache: Dict[str, CircuitFeatures] = {}

    def _get_case_features(self, case_id: str, case) -> CircuitFeatures:
        """获取案例特征 (带缓存)"""
        if case_id not in self._case_features_cache:
            self._case_features_cache[case_id] = self.extractor.extract_from_case(case)
        return self._case_features_cache[case_id]

    def query_similar_cases(self,
                           project_description: str,
                           top_k: int = 3,
                           min_similarity: float = 0.3) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        查询相似案例 (返回多个)

        Args:
            project_description: 项目描述
            top_k: 返回的案例数量
            min_similarity: 最低相似度阈值

        Returns:
            List[Tuple[str, float, Dict[str, float]]]: [(案例ID, 相似度, 详细分数), ...]
        """
        # 提取查询特征
        query_features = self.extractor.extract_features(project_description)

        # 计算与所有案例的相似度
        results = []
        for case_id, case in self.case_library.cases.items():
            case_features = self._get_case_features(case_id, case)
            similarity, detail_scores = self.scorer.compute_similarity(
                query_features, case_features
            )

            if similarity >= min_similarity:
                results.append((case_id, similarity, detail_scores))

        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def query_best_case(self,
                        project_description: str,
                        min_similarity: float = 0.3) -> Optional[Tuple[str, float, Dict[str, float]]]:
        """
        查询最相似的案例

        Args:
            project_description: 项目描述
            min_similarity: 最低相似度阈值

        Returns:
            Optional[Tuple[str, float, Dict[str, float]]]: (案例ID, 相似度, 详细分数) 或 None
        """
        results = self.query_similar_cases(project_description, top_k=1, min_similarity=min_similarity)
        return results[0] if results else None

    def explain_similarity(self,
                          project_description: str,
                          case_id: str) -> Dict:
        """
        解释相似度计算结果

        Args:
            project_description: 项目描述
            case_id: 案例ID

        Returns:
            Dict: 详细解释
        """
        query_features = self.extractor.extract_features(project_description)
        case = self.case_library.cases.get(case_id)

        if not case:
            return {"error": f"Case {case_id} not found"}

        case_features = self._get_case_features(case_id, case)
        similarity, detail_scores = self.scorer.compute_similarity(query_features, case_features)

        return {
            "total_similarity": similarity,
            "detail_scores": detail_scores,
            "query_features": {
                "components": {c.value: n for c, n in query_features.components.items()},
                "interfaces": {i.value: n for i, n in query_features.interfaces.items()},
                "domains": {d.value: w for d, w in query_features.application_domains.items()},
                "frequency": query_features.frequency_band.value,
                "power": query_features.power_level.value,
                "difficulty": query_features.difficulty,
                "feature_tags": list(query_features.feature_tags),
            },
            "case_features": {
                "components": {c.value: n for c, n in case_features.components.items()},
                "interfaces": {i.value: n for i, n in case_features.interfaces.items()},
                "domains": {d.value: w for d, w in case_features.application_domains.items()},
                "frequency": case_features.frequency_band.value,
                "power": case_features.power_level.value,
                "difficulty": case_features.difficulty,
                "feature_tags": list(case_features.feature_tags),
            },
            "match_analysis": self._analyze_match(query_features, case_features, detail_scores),
        }

    def _analyze_match(self,
                      query: CircuitFeatures,
                      case: CircuitFeatures,
                      scores: Dict[str, float]) -> List[str]:
        """分析匹配情况"""
        analysis = []

        # 分析元件匹配
        common_components = set(query.components.keys()) & set(case.components.keys())
        if common_components:
            analysis.append(f"共同元件类型: {', '.join(c.value for c in common_components)}")

        # 分析接口匹配
        common_interfaces = set(query.interfaces.keys()) & set(case.interfaces.keys())
        if common_interfaces:
            analysis.append(f"共同接口: {', '.join(i.value for i in common_interfaces)}")

        # 分析应用领域匹配
        common_domains = set(query.application_domains.keys()) & set(case.application_domains.keys())
        if common_domains:
            analysis.append(f"共同应用领域: {', '.join(d.value for d in common_domains)}")

        # 指出低分维度
        for dim, score in scores.items():
            if score < 0.3:
                dim_names = {
                    "component": "元件类型",
                    "interface": "接口类型",
                    "domain": "应用领域",
                    "frequency": "频段",
                    "power": "功率等级",
                    "difficulty": "设计难度",
                    "features": "特征标签",
                }
                analysis.append(f"差异较大: {dim_names.get(dim, dim)} (相似度: {score:.1%})")

        return analysis


# 便捷函数
def create_enhanced_matcher(case_library) -> EnhancedCaseMatcher:
    """创建增强版案例匹配器"""
    return EnhancedCaseMatcher(case_library)
