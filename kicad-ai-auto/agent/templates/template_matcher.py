"""
Template Matcher - 模板智能匹配器

Phase 7D: 从自然语言需求匹配已有模板

功能:
- 关键词提取与模板标签匹配
- 置信度评分 (0-1)
- 模板定制 (电压/电流/接口调整)
- 混合生成策略选择

Author: Claude Code
Date: 2026-03-31
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from .template_data import (
    ProjectTemplate,
    TemplateCategory,
    TemplateSchematic,
    TemplatePCB,
    PREDEFINED_TEMPLATES,
)

logger = logging.getLogger(__name__)


# ============== 匹配规则 ==============

# 需求关键词 → 模板ID 的强映射
_EXACT_MATCH_RULES: Dict[str, List[str]] = {
    # USB 充电类
    "usb充电器": ["usbc_pd_charger", "usb_charger", "usb_serial_adapter"],
    "usb-c充电器": ["usbc_pd_charger"],
    "usb充电": ["usbc_pd_charger", "usb_charger"],
    "pd充电器": ["usbc_pd_charger"],
    "快充": ["usbc_pd_charger"],
    "charger": ["usbc_pd_charger", "usb_charger", "battery_charger"],

    # 电池类
    "锂电池充电": ["battery_charger"],
    "tp4056": ["battery_charger"],
    "电池保护": ["battery_protection"],
    "电池充电": ["battery_charger"],
    "lipo": ["battery_charger"],

    # MCU 类
    "esp32": ["esp32_board"],
    "stm32": ["stm32_minimal"],
    "arduino": ["arduino_shield"],
    "树莓派": ["rpi_pico"],
    "raspberry pi": ["rpi_pico"],

    # 通信类
    "rs485": ["rs485_module"],
    "usb转串口": ["usb_serial_adapter"],
    "ch340": ["usb_serial_adapter"],
    "cp2102": ["usb_serial_adapter"],

    # 驱动类
    "电机驱动": ["motor_driver"],
    "l298n": ["motor_driver"],
    "led驱动": ["led_driver_buck"],
    "led矩阵": ["led_matrix"],
    "ws2812": ["ws2812_controller"],
    "rgb": ["ws2812_controller"],

    # 音频
    "音频放大": ["audio_amplifier"],
    "音频功放": ["audio_amplifier"],

    # 传感器
    "温湿度": ["dht11_sensor"],
    "dht11": ["dht11_sensor"],
    "gps": ["gps_module"],

    # 无线
    "nrf24": ["nrf24l01_wireless"],
    "无线": ["nrf24l01_wireless"],

    # 显示
    "oled": ["oled_display"],
    "显示屏": ["oled_display"],

    # 其他
    "电平转换": ["level_shifter"],
    "继电器": ["relay_module"],
    "电源": ["power_module"],
    "双电源": ["power_module"],
}

# 同义词扩展
_SYNONYMS: Dict[str, List[str]] = {
    "充电": ["charger", "charging", "充"],
    "电池": ["battery", "lipo", "li-ion", "锂电池"],
    "电机": ["motor", "马达", "驱动"],
    "传感器": ["sensor", "检测", "感应"],
    "放大": ["amplifier", "amp", "功放"],
    "无线": ["wireless", "wifi", "ble", "蓝牙"],
    "显示": ["display", "oled", "lcd", "屏幕"],
    "转换": ["converter", "adapter", "adapter"],
}

# 类别关键词映射
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "mcu_board": ["mcu", "开发板", "单片机", "最小系统", "board"],
    "power": ["电源", "power", "ldo", "稳压", "dcdc", "供电", "charger", "充电"],
    "sensor": ["传感器", "sensor", "检测", "温湿度", "dht", "gps"],
    "interface": ["接口", "interface", "转接", "adapter", "串口", "uart"],
    "wireless": ["无线", "wireless", "wifi", "ble", "bluetooth", "nrf"],
    "display": ["显示", "display", "oled", "lcd", "led", "screen"],
    "motor": ["电机", "motor", "驱动", "driver"],
    "battery": ["电池", "battery", "充电", "lipo", "protection"],
    "led_driver": ["led", "驱动", "照明", "灯"],
    "communication": ["通信", "rs485", "串口", "uart", "spi", "i2c"],
}


@dataclass
class TemplateMatch:
    """模板匹配结果"""
    template: ProjectTemplate
    confidence: float
    match_reasons: List[str] = field(default_factory=list)

    @property
    def template_id(self) -> str:
        return self.template.template_id

    @property
    def name(self) -> str:
        return self.template.name


@dataclass
class MatchResult:
    """完整匹配结果"""
    matches: List[TemplateMatch]
    best_match: Optional[TemplateMatch] = None
    strategy: str = "ai_generate"  # template_direct, template_customized, ai_generate

    def __post_init__(self):
        if self.matches and self.best_match is None:
            self.best_match = self.matches[0]


class TemplateMatcher:
    """
    从自然语言需求匹配已有模板

    匹配策略:
    1. 精确关键词 → 模板 ID 映射
    2. 模板标签 + 描述模糊匹配
    3. 类别推断
    4. 综合置信度评分

    生成策略:
    - confidence > 0.8 → 直接使用模板
    - 0.5 < confidence <= 0.8 → 模板 + LLM 微调
    - confidence <= 0.5 → 纯 AI 生成
    """

    def __init__(self, templates: Optional[List[ProjectTemplate]] = None):
        self.templates = templates or PREDEFINED_TEMPLATES

    def match(self, requirements: str) -> MatchResult:
        """
        从需求文本匹配最合适的模板

        Args:
            requirements: 自然语言需求描述

        Returns:
            MatchResult 包含匹配列表和推荐策略
        """
        if not requirements or not requirements.strip():
            return MatchResult(matches=[], strategy="ai_generate")

        req_lower = requirements.lower()
        matches: Dict[str, TemplateMatch] = {}

        # 阶段 1: 精确规则匹配
        for keyword, template_ids in _EXACT_MATCH_RULES.items():
            if keyword in req_lower:
                for tid in template_ids:
                    template = self._find_template(tid)
                    if template and tid not in matches:
                        score, reasons = self._score_exact(keyword, template)
                        if tid in matches:
                            # 合并评分
                            existing = matches[tid]
                            existing.confidence = min(1.0, existing.confidence + score * 0.3)
                            existing.match_reasons.extend(reasons)
                        else:
                            matches[tid] = TemplateMatch(
                                template=template,
                                confidence=score,
                                match_reasons=reasons,
                            )

        # 阶段 2: 同义词扩展匹配
        for syn_group, syns in _SYNONYMS.items():
            if syn_group in req_lower:
                for syn in syns:
                    if syn in req_lower:
                        for keyword, template_ids in _EXACT_MATCH_RULES.items():
                            if syn in keyword or keyword in syn:
                                for tid in template_ids:
                                    template = self._find_template(tid)
                                    if template:
                                        if tid in matches:
                                            matches[tid].confidence = min(
                                                1.0, matches[tid].confidence + 0.1
                                            )
                                            matches[tid].match_reasons.append(
                                                f"同义词匹配: {syn_group} → {syn}"
                                            )
                                        else:
                                            matches[tid] = TemplateMatch(
                                                template=template,
                                                confidence=0.5,
                                                match_reasons=[f"同义词匹配: {syn_group}"],
                                            )

        # 阶段 3: 标签/描述模糊匹配
        for template in self.templates:
            if template.template_id in matches:
                continue
            score, reasons = self._score_fuzzy(req_lower, template)
            if score > 0.2:
                matches[template.template_id] = TemplateMatch(
                    template=template,
                    confidence=score,
                    match_reasons=reasons,
                )

        # 排序
        sorted_matches = sorted(matches.values(), key=lambda m: m.confidence, reverse=True)

        # 确定策略
        strategy = "ai_generate"
        if sorted_matches:
            best = sorted_matches[0]
            if best.confidence > 0.8:
                strategy = "template_direct"
            elif best.confidence > 0.5:
                strategy = "template_customized"

        result = MatchResult(
            matches=sorted_matches[:5],  # 返回前5个
            strategy=strategy,
        )
        return result

    def customize(
        self,
        template: ProjectTemplate,
        requirements: str,
    ) -> Dict[str, Any]:
        """
        根据需求定制模板

        支持:
        - 调整电压: 3.3V → 5V (更换 LDO)
        - 调整接口数量: 4口USB → 6口USB
        - 增加/减少功能模块

        Args:
            template: 基础模板
            requirements: 定制需求

        Returns:
            定制后的模板数据
        """
        from dataclasses import asdict

        result = asdict(template)
        customizations = []

        req_lower = requirements.lower()

        # 电压调整
        voltage = self._extract_voltage(requirements)
        if voltage:
            result = self._adjust_voltage(result, voltage)
            customizations.append(f"电压调整为 {voltage}V")

        # USB 口数量调整
        usb_count = self._extract_usb_count(requirements)
        if usb_count:
            result = self._adjust_usb_ports(result, usb_count)
            customizations.append(f"USB 接口调整为 {usb_count} 个")

        # 层数调整
        if "4层" in requirements or "四层" in requirements:
            result["pcb"]["layers"] = 4
            customizations.append("PCB 层数调整为 4 层")
        elif "6层" in requirements or "六层" in requirements:
            result["pcb"]["layers"] = 6
            customizations.append("PCB 层数调整为 6 层")

        return {
            "template_id": template.template_id,
            "customized": True,
            "customizations": customizations,
            "data": result,
        }

    # ============== 内部方法 ==============

    def _find_template(self, template_id: str) -> Optional[ProjectTemplate]:
        """根据 ID 查找模板"""
        for t in self.templates:
            if t.template_id == template_id:
                return t
        return None

    def _score_exact(
        self, keyword: str, template: ProjectTemplate
    ) -> Tuple[float, List[str]]:
        """精确匹配评分"""
        score = 0.75  # 基础分
        reasons = [f"精确匹配: '{keyword}'"]

        # 标签加成
        if any(keyword in tag for tag in template.tags):
            score += 0.15
            reasons.append(f"标签命中: {keyword}")

        # 描述加成
        if keyword in template.description.lower():
            score += 0.1
            reasons.append(f"描述命中")

        return min(1.0, score), reasons

    def _score_fuzzy(
        self, req_lower: str, template: ProjectTemplate
    ) -> Tuple[float, List[str]]:
        """模糊匹配评分"""
        score = 0.0
        reasons = []

        # 标签匹配
        for tag in template.tags:
            if tag.lower() in req_lower:
                score += 0.25
                reasons.append(f"标签匹配: {tag}")

        # 名称匹配
        if template.name.lower() in req_lower:
            score += 0.3
            reasons.append(f"名称匹配: {template.name}")
        if template.name_cn in req_lower:
            score += 0.3
            reasons.append(f"中文名匹配: {template.name_cn}")

        # 描述关键词匹配
        desc_words = template.description.lower().split()
        for word in desc_words:
            if len(word) >= 3 and word in req_lower:
                score += 0.1
                reasons.append(f"描述匹配: {word}")

        # 类别匹配
        for cat_kw, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in req_lower for kw in keywords):
                if template.category.value == cat_kw:
                    score += 0.15
                    reasons.append(f"类别匹配: {cat_kw}")

        return min(1.0, score), reasons

    def _extract_voltage(self, requirements: str) -> Optional[float]:
        """从需求中提取电压值"""
        patterns = [
            r"(\d+\.?\d*)\s*v",
            r"(\d+\.?\d*)\s*伏",
            r"(\d+\.?\d*)\s*volt",
        ]
        for pattern in patterns:
            match = re.search(pattern, requirements.lower())
            if match:
                v = float(match.group(1))
                if 0.5 <= v <= 48:  # 合理的 PCB 电压范围
                    return v
        return None

    def _extract_usb_count(self, requirements: str) -> Optional[int]:
        """从需求中提取 USB 口数量"""
        patterns = [
            r"(\d+)\s*个?\s*usb",
            r"usb[^\d]*(\d+)",
            r"(\d+)\s*口\s*usb",
            r"(\d+)口充电",
        ]
        for pattern in patterns:
            match = re.search(pattern, requirements.lower())
            if match:
                count = int(match.group(1))
                if 1 <= count <= 20:
                    return count
        return None

    def _adjust_voltage(self, data: Dict[str, Any], target_voltage: float) -> Dict[str, Any]:
        """调整模板电压"""
        # 替换 LDO 器件
        ldo_map = {
            3.3: ("AMS1117-3.3", "3.3V LDO"),
            5.0: ("AMS1117-5.0", "5V LDO"),
            1.8: ("AMS1117-1.8", "1.8V LDO"),
            12.0: ("LM7812", "12V 线性稳压"),
        }

        for comp in data.get("schematic", {}).get("components", []):
            symbol = comp.get("symbol", "").upper()
            if "AMS1117" in symbol or "LDO" in symbol or "LM78" in symbol:
                if target_voltage in ldo_map:
                    new_symbol, desc = ldo_map[target_voltage]
                    comp["symbol"] = new_symbol
                    comp["properties"] = comp.get("properties", {})
                    comp["properties"]["Value"] = f"{target_voltage}V"
                    comp["properties"]["Description"] = desc

        return data

    def _adjust_usb_count(self, data: Dict[str, Any], count: int) -> Dict[str, Any]:
        """调整 USB 接口数量"""
        schem = data.get("schematic", {})
        components = schem.get("components", [])

        # 找到现有 USB 连接器
        usb_connectors = [
            c for c in components
            if "usb" in c.get("symbol", "").lower() or "usb" in c.get("reference", "").lower()
        ]

        existing_count = len(usb_connectors)
        if existing_count == 0 or count == existing_count:
            return data

        if count > existing_count:
            # 复制现有 USB 连接器增加数量
            template_connector = usb_connectors[0]
            for i in range(existing_count, count):
                new_ref = f"USB{i + 1}"
                new_comp = dict(template_connector)
                new_comp["reference"] = new_ref
                new_comp["x"] = template_connector.get("x", 0) + (i * 20)
                components.append(new_comp)
        elif count < existing_count:
            # 移除多余的 USB 连接器 (保留前 N 个)
            to_remove = [c for c in usb_connectors[count:]]
            for comp in to_remove:
                components.remove(comp)

        return data
