"""
智能封装查找器 v1.0

功能：
1. 从 155 个 KiCad 本地封装库中查找元件封装
2. 支持按型号搜索（如 LM7805、MB6S）
3. 支持按关键词搜索（如 TO-220、SOP-4）
4. 自动匹配最佳封装

作者：AI Assistant
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 封装库根目录
FOOTPRINT_LIBS_ROOT = Path(__file__).parent.parent.parent / "kicad-footprints"


@dataclass
class FootprintInfo:
    """封装信息"""
    library: str           # 库名 (如 Package_TO_SOT_SMD)
    name: str              # 封装名 (如 SOT-23)
    full_path: str         # 完整路径
    description: str = ""  # 描述
    tags: List[str] = None # 标签

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class SmartFootprintFinder:
    """智能封装查找器"""

    # 常用元件型号到封装的映射
    MODEL_TO_FOOTPRINT = {
        # ===== 稳压器 =====
        "LM7805": ("Package_TO_SOT_SMD", "TO-252-2"),
        "LM7805CT": ("Package_TO_SOT_THT", "TO-220-3_Vertical"),
        "LM7812": ("Package_TO_SOT_SMD", "TO-252-2"),
        "LM317": ("Package_TO_SOT_SMD", "TO-252-2"),
        "LM317T": ("Package_TO_SOT_THT", "TO-220-3_Vertical"),
        "AMS1117": ("Package_TO_SOT_SMD", "SOT-223"),
        "AMS1117-3.3": ("Package_TO_SOT_SMD", "SOT-223"),
        "AMS1117-5.0": ("Package_TO_SOT_SMD", "SOT-223"),
        "XC6206": ("Package_TO_SOT_SMD", "SOT-23"),
        "RT9193": ("Package_TO_SOT_SMD", "SOT-23-5"),
        "MP1584": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),
        "LM2596": ("Package_TO_SOT_SMD", "TO-263-5"),

        # ===== 整流桥 =====
        "MB6S": ("Package_SO", "SOIC-4_4.55x3.7mm_P2.54mm"),
        "MB10S": ("Package_SO", "SOIC-4_4.55x3.7mm_P2.54mm"),
        "KBPC1010": ("Package_Bridge", "Bridge_William_WI-1"),
        "GBU4K": ("Package_Bridge", "Bridge_GBU-4K"),

        # ===== MCU =====
        "ESP32C3": ("RF_Module", "ESP32-C3"),
        "ESP32-WROOM-32": ("RF_Module", "ESP32-WROOM-32"),
        "ESP8266": ("RF_Module", "ESP-12E"),
        "STM32F103C8T6": ("Package_QFP", "LQFP-48_7x7mm_P0.5mm"),
        "STM32F407VGT6": ("Package_QFP", "LQFP-100_14x14mm_P0.15mm"),
        "ATmega328P": ("Package_DIP", "DIP-28_W7.62mm"),
        "ATmega328P-AU": ("Package_QFP", "TQFP-32_7x7mm_P0.8mm"),
        "RP2040": ("Package_DFN_QFN", "QFN-56-1EP_7x7mm_P0.4mm_EP5.6x5.6mm"),
        "CH32V003": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),

        # ===== USB转串口 =====
        "CH340G": ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm"),
        "CH340C": ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm"),
        "CP2102": ("Package_DFN_QFN", "QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm"),
        "CP2104": ("Package_DFN_QFN", "QFN-24-1EP_4x4mm_P0.5mm"),
        "FT232RL": ("Package_SO", "SSOP-28_5.3x10.2mm_P0.65mm"),

        # ===== 二极管 =====
        "1N4007": ("Diode_THT", "D_DO-41_SOD81_P7.62mm_Vertical_AnodeUp"),
        "1N4148": ("Diode_THT", "D_DO-35_SOD27_P7.62mm_Vertical_AnodeUp"),
        "SS34": ("Diode_SMD", "D_SMC"),
        "SS54": ("Diode_SMD", "D_SMC"),
        "BAT54C": ("Package_TO_SOT_SMD", "SOT-23"),
        "B5819W": ("Diode_SMD", "D_SOD-123"),

        # ===== LED =====
        "LED0603": ("LED_SMD", "LED_0603_1608Metric"),
        "LED0805": ("LED_SMD", "LED_0805_2012Metric"),
        "LED1206": ("LED_SMD", "LED_1206_3216Metric"),
        "WS2812B": ("LED_SMD", "LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm"),
        "WS2812B-2020": ("LED_SMD", "LED_WS2812-2020_PLCC4_2.0x2.0mm"),

        # ===== 晶振 =====
        "HC49": ("Crystal", "Crystal_HC49-4H_Vertical"),
        "HC49S": ("Crystal", "Crystal_HC49-SD_SMD_Horizontal"),
        "NX3225": ("Crystal", "Crystal_SMD_3225-4Pin_3.2x2.5mm"),
        "NX5032": ("Crystal", "Crystal_SMD_5032-4Pin_5.0x3.2mm"),

        # ===== 电容 =====
        "C0603": ("Capacitor_SMD", "C_0603_1608Metric"),
        "C0805": ("Capacitor_SMD", "C_0805_2012Metric"),
        "C1206": ("Capacitor_SMD", "C_1206_3216Metric"),
        "CD60": ("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm"),
        "CD110": ("Capacitor_THT", "CP_Radial_D6.3mm_P2.50mm"),
        "1206": ("Capacitor_SMD", "C_1206_3216Metric"),

        # ===== 电阻 =====
        "R0603": ("Resistor_SMD", "R_0603_1608Metric"),
        "R0805": ("Resistor_SMD", "R_0805_2012Metric"),
        "R1206": ("Resistor_SMD", "R_1206_3216Metric"),

        # ===== 连接器 =====
        "USB-C": ("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12"),
        "USB-Micro": ("Connector_USB", "USB_Micro-B_Molex-105017-0001"),
        "USB-A": ("Connector_USB", "USB_A_Molex_105057_Vertical"),
        "PH-2.0": ("Connector_JST", "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"),
        "PH-2.5": ("Connector_JST", "JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.50mm_Horizontal"),
        "XH-2.5": ("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
        "PinHeader-2.54": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
        "TerminalBlock-5mm": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),

        # ===== 开关 =====
        "SKQGAFE010": ("Button_Switch_SMD", "SW_SPST_SKQG_WithStem"),
        "TS-022": ("Button_Switch_THT", "SW_PUSH_6mm"),

        # ===== 传感器 =====
        "DHT11": ("Sensor_Humidity", "Digital_Humidity_Temperature_Sensortech_DHT11"),
        "DS18B20": ("Sensor_Temperature", "Temperature_TO-92_3Pin_Horizontal"),
        "LM35": ("Sensor_Temperature", "Temperature_TO-92_3Pin_Horizontal"),

        # ===== 无线模块 =====
        "NRF24L01": ("RF_Module", "NRF24L01"),
        "CC1101": ("RF_Module", "CC1101_Module"),
        "SX1278": ("RF_Module", "SX1278_Module"),
    }

    # 封装类型关键词映射
    PACKAGE_KEYWORDS = {
        "SOT-23": ("Package_TO_SOT_SMD", "SOT-23"),
        "SOT23": ("Package_TO_SOT_SMD", "SOT-23"),
        "SOT-223": ("Package_TO_SOT_SMD", "SOT-223"),
        "SOT223": ("Package_TO_SOT_SMD", "SOT-223"),
        "SOT-89": ("Package_TO_SOT_SMD", "SOT-89-3"),
        "SOT89": ("Package_TO_SOT_SMD", "SOT-89-3"),
        "TO-220": ("Package_TO_SOT_THT", "TO-220-3_Vertical"),
        "TO220": ("Package_TO_SOT_THT", "TO-220-3_Vertical"),
        "TO-252": ("Package_TO_SOT_SMD", "TO-252-2"),
        "TO252": ("Package_TO_SOT_SMD", "TO-252-2"),
        "TO-263": ("Package_TO_SOT_SMD", "TO-263-5"),
        "TO263": ("Package_TO_SOT_SMD", "TO-263-5"),
        "SOIC-8": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),
        "SOIC8": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),
        "SOIC-16": ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm"),
        "SOIC16": ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm"),
        "SOP-4": ("Package_SO", "SOIC-4_4.55x3.7mm_P2.54mm"),
        "SOP4": ("Package_SO", "SOIC-4_4.55x3.7mm_P2.54mm"),
        "SOP-8": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),
        "SOP8": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),
        "SSOP-28": ("Package_SO", "SSOP-28_5.3x10.2mm_P0.65mm"),
        "TQFP-32": ("Package_QFP", "TQFP-32_7x7mm_P0.8mm"),
        "LQFP-48": ("Package_QFP", "LQFP-48_7x7mm_P0.5mm"),
        "QFN-24": ("Package_DFN_QFN", "QFN-24-1EP_4x4mm_P0.5mm"),
        "QFN-32": ("Package_DFN_QFN", "QFN-32_5x5mm_P0.5mm"),
        "DIP-8": ("Package_DIP", "DIP-8_W7.62mm"),
        "DIP8": ("Package_DIP", "DIP-8_W7.62mm"),
        "DIP-16": ("Package_DIP", "DIP-16_W7.62mm"),
        "DIP16": ("Package_DIP", "DIP-16_W7.62mm"),
        "DIP-28": ("Package_DIP", "DIP-28_W15.24mm"),
        "DIP28": ("Package_DIP", "DIP-28_W15.24mm"),
        "0603": ("Resistor_SMD", "R_0603_1608Metric"),
        "0805": ("Resistor_SMD", "R_0805_2012Metric"),
        "1206": ("Resistor_SMD", "R_1206_3216Metric"),
        "DO-41": ("Diode_THT", "D_DO-41_SOD81_P7.62mm_Vertical_AnodeUp"),
        "DO-35": ("Diode_THT", "D_DO-35_SOD27_P7.62mm_Vertical_AnodeUp"),
        "SOD-123": ("Diode_SMD", "D_SOD-123"),
        "SOD123": ("Diode_SMD", "D_SOD-123"),
        "SOD-323": ("Diode_SMD", "D_SOD-323"),
    }

    # 默认封装（按元件类型）
    DEFAULT_FOOTPRINTS = {
        "resistor": ("Resistor_SMD", "R_0603_1608Metric"),
        "电阻": ("Resistor_SMD", "R_0603_1608Metric"),
        "capacitor": ("Capacitor_SMD", "C_0603_1608Metric"),
        "电容": ("Capacitor_SMD", "C_0603_1608Metric"),
        "电容电解": ("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm"),
        "electrolytic": ("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm"),
        "inductor": ("Inductor_SMD", "L_0603_1608Metric"),
        "电感": ("Inductor_SMD", "L_0603_1608Metric"),
        "diode": ("Diode_SMD", "D_SOD-123"),
        "二极管": ("Diode_SMD", "D_SOD-123"),
        "led": ("LED_SMD", "LED_0603_1608Metric"),
        "led灯": ("LED_SMD", "LED_0603_1608Metric"),
        "transistor": ("Package_TO_SOT_SMD", "SOT-23"),
        "三极管": ("Package_TO_SOT_SMD", "SOT-23"),
        "mosfet": ("Package_TO_SOT_SMD", "SOT-23"),
        "regulator": ("Package_TO_SOT_SMD", "SOT-223"),
        "稳压器": ("Package_TO_SOT_SMD", "SOT-223"),
        "电源": ("Package_TO_SOT_SMD", "SOT-223"),
        "mcu": ("Package_QFP", "LQFP-48_7x7mm_P0.5mm"),
        "ic": ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm"),
        "connector": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
        "连接器": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
        "crystal": ("Crystal", "Crystal_HC49-4H_Vertical"),
        "晶振": ("Crystal", "Crystal_HC49-4H_Vertical"),
        "usb": ("Connector_USB", "USB_Micro-B_Molex-105017-0001"),
        "switch": ("Button_Switch_SMD", "SW_SPST_SKQG_WithStem"),
        "开关": ("Button_Switch_SMD", "SW_SPST_SKQG_WithStem"),
        "passive": ("Resistor_SMD", "R_0603_1608Metric"),  # 默认电阻
        "other": ("Resistor_SMD", "R_0603_1608Metric"),
        "power": ("Package_TO_SOT_SMD", "SOT-223"),
        "interface": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
        "active": ("Package_TO_SOT_SMD", "SOT-23"),
    }

    def __init__(self):
        self._libs_cache: Dict[str, List[str]] = {}
        self._build_libs_cache()

    def _build_libs_cache(self):
        """构建封装库缓存"""
        if not FOOTPRINT_LIBS_ROOT.exists():
            logger.warning(f"封装库目录不存在: {FOOTPRINT_LIBS_ROOT}")
            return

        for lib_dir in FOOTPRINT_LIBS_ROOT.iterdir():
            if lib_dir.is_dir() and lib_dir.name.endswith('.pretty'):
                lib_name = lib_dir.name.replace('.pretty', '')
                footprints = []
                for fp_file in lib_dir.glob('*.kicad_mod'):
                    footprints.append(fp_file.stem)
                self._libs_cache[lib_name] = footprints

        logger.info(f"已加载 {len(self._libs_cache)} 个封装库")

    def find_footprint(self, model: str, component_type: str = "", package_hint: str = "") -> Tuple[str, str]:
        """
        查找元件封装

        Args:
            model: 元件型号 (如 LM7805, MB6S)
            component_type: 元件类型 (如 resistor, capacitor)
            package_hint: 封装提示 (如 TO-220, SOP-8)

        Returns:
            (库名, 封装名) 如 ("Package_TO_SOT_SMD", "SOT-23")
        """
        model_upper = model.upper().strip()
        model_lower = model.lower().strip()
        package_upper = package_hint.upper().strip() if package_hint else ""
        component_type_lower = component_type.lower() if component_type else ""

        # 0. 如果 component_type 是 passive，根据 model 推断具体类型
        # 这个必须在型号匹配之前执行，避免像 "Red" 被错误识别为 "R" (电阻)
        if component_type_lower == "passive":
            model_keywords = [
                # LED (最具体)
                (["led", "red", "green", "blue", "yellow", "white", "灯"], "led"),
                # 电容
                (["电容", "uf", "nf", "pf", "cap"], "capacitor"),
                # 电阻
                (["电阻", "ohm", "res", "r_"], "resistor"),
                # 电感
                (["电感", "uh", "mh", "l_", "inductor"], "inductor"),
                # 二极管
                (["diode", "二极管", "1n", "bav"], "diode"),
            ]
            for keywords, comp_type in model_keywords:
                if any(kw in model_lower for kw in keywords):
                    for type_key, footprint in self.DEFAULT_FOOTPRINTS.items():
                        if type_key in comp_type:
                            logger.info(f"Passive类型推断: {model} -> {comp_type} -> {footprint[0]}:{footprint[1]}")
                            return footprint

        # 0.1. 如果有 component_type 且模型是简单名称，优先使用类型默认封装
        # 避免像 "Red" 这样的简单型号误匹配到不相关的库
        simple_names = ['led', 'red', 'green', 'blue', 'yellow', 'white',
                       'r', 'res', 'resistor',
                       'c', 'cap', 'capacitor',
                       'l', 'inductor',
                       'd', 'diode']
        if component_type_lower and model_lower in simple_names:
            for type_key, footprint in self.DEFAULT_FOOTPRINTS.items():
                if type_key in component_type_lower:
                    logger.info(f"简单名称+类型匹配: {model} -> {footprint[0]}:{footprint[1]}")
                    return footprint

        # 1. 先检查型号映射表
        for model_key, footprint in self.MODEL_TO_FOOTPRINT.items():
            if model_key.upper() == model_upper or model_key.upper() in model_upper:
                logger.info(f"型号匹配: {model} -> {footprint[0]}:{footprint[1]}")
                return footprint

        # 2. 检查封装关键词
        if package_upper:
            for keyword, footprint in self.PACKAGE_KEYWORDS.items():
                if keyword in package_upper:
                    logger.info(f"封装关键词匹配: {package_hint} -> {footprint[0]}:{footprint[1]}")
                    return footprint

        # 3. 智能搜索封装库
        result = self._search_in_libs(model)
        if result:
            logger.info(f"库搜索匹配: {model} -> {result[0]}:{result[1]}")
            return result

        # 4. 根据元件类型使用默认封装
        for type_key, footprint in self.DEFAULT_FOOTPRINTS.items():
            if type_key in component_type_lower:
                logger.info(f"类型默认封装: {component_type} -> {footprint[0]}:{footprint[1]}")
                return footprint

        # 5. 最终默认
        default = ("Resistor_SMD", "R_0603_1608Metric")
        logger.warning(f"未找到匹配封装，使用默认: {model} -> {default[0]}:{default[1]}")
        return default

    def _search_in_libs(self, model: str) -> Optional[Tuple[str, str]]:
        """在封装库中搜索"""
        model_lower = model.lower()

        # 关键词提取
        keywords = []

        # 提取数字+字母组合
        patterns = [
            r'\d{4}',           # 4位数字 (如 7805)
            r'[A-Z]+\d+[A-Z]*', # 字母+数字 (如 LM7805)
            r'SOT[-]?\d+',      # SOT封装
            r'TO[-]?\d+',       # TO封装
            r'SOIC[-]?\d+',     # SOIC封装
            r'DIP[-]?\d+',      # DIP封装
            r'QFP',             # QFP封装
            r'QFN',             # QFN封装
        ]

        for pattern in patterns:
            matches = re.findall(pattern, model, re.IGNORECASE)
            keywords.extend(matches)

        # 如果没有提取到关键词，且模型是简单名称（电容、电阻、LED等），不进行库搜索
        # 避免误匹配到不相关的封装
        simple_passives = ['led', 'r', 'c', 'l', 'd', 'u', 'resistor', 'capacitor', 'inductor', 'diode']
        if not keywords and model_lower in simple_passives:
            return None

        # 在库中搜索
        for lib_name, footprints in self._libs_cache.items():
            for fp_name in footprints:
                fp_lower = fp_name.lower()

                # 精确匹配
                if model_lower in fp_lower:
                    return (lib_name, fp_name)

                # 关键词匹配
                for kw in keywords:
                    if kw.lower() in fp_lower:
                        return (lib_name, fp_name)

        return None

    def get_footprint_info(self, lib_name: str, fp_name: str) -> Optional[FootprintInfo]:
        """获取封装详细信息"""
        fp_path = FOOTPRINT_LIBS_ROOT / f"{lib_name}.pretty" / f"{fp_name}.kicad_mod"

        if not fp_path.exists():
            return None

        # 读取封装文件获取描述
        description = ""
        tags = []

        try:
            content = fp_path.read_text(encoding='utf-8', errors='ignore')

            # 提取描述
            desc_match = re.search(r'\(descr\s+"([^"]+)"\)', content)
            if desc_match:
                description = desc_match.group(1)

            # 提取标签
            tags_match = re.search(r'\(tags\s+"([^"]+)"\)', content)
            if tags_match:
                tags = tags_match.group(1).split()
        except Exception as e:
            logger.warning(f"读取封装文件失败: {e}")

        return FootprintInfo(
            library=lib_name,
            name=fp_name,
            full_path=str(fp_path),
            description=description,
            tags=tags
        )

    def list_available_libraries(self) -> List[str]:
        """列出所有可用的封装库"""
        return list(self._libs_cache.keys())

    def search_footprints(self, keyword: str, limit: int = 20) -> List[Tuple[str, str]]:
        """搜索封装"""
        results = []
        keyword_lower = keyword.lower()

        for lib_name, footprints in self._libs_cache.items():
            for fp_name in footprints:
                if keyword_lower in fp_name.lower():
                    results.append((lib_name, fp_name))
                    if len(results) >= limit:
                        return results

        return results


# 全局实例
_finder = None

def get_footprint_finder() -> SmartFootprintFinder:
    """获取全局封装查找器实例"""
    global _finder
    if _finder is None:
        _finder = SmartFootprintFinder()
    return _finder

def find_footprint(model: str, component_type: str = "", package_hint: str = "") -> Tuple[str, str]:
    """便捷函数：查找封装"""
    return get_footprint_finder().find_footprint(model, component_type, package_hint)


if __name__ == "__main__":
    # 测试
    finder = SmartFootprintFinder()

    print("=" * 60)
    print("智能封装查找器测试")
    print("=" * 60)

    test_models = [
        "LM7805",
        "MB6S",
        "ESP32C3",
        "CH340G",
        "1N4007",
        "未知元件",
    ]

    for model in test_models:
        lib, fp = finder.find_footprint(model)
        print(f"{model:20} -> {lib}:{fp}")
