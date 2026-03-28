"""
语义理解分析器
完全基于语义理解来分析用户需求，不使用关键词匹配
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ClarityLevel(Enum):
    """需求清晰度级别"""
    CLEAR = "clear"           # 清晰
    MOSTLY_CLEAR = "mostly_clear"  # 大部分清晰
    UNCLEAR = "unclear"       # 不清晰


@dataclass
class Semantic理解结果:
    """语义理解结果"""
    # 提取的关键信息
    desired_function: str = ""           # 期望功能
    input_voltage: str = ""              # 输入电压
    output_voltage: str = ""             # 输出电压
    communication_interface: str = ""    # 通信接口
    wireless_type: str = ""              # 无线类型
    sensor_type: str = ""                # 传感器类型
    mcu_type: str = ""                   # 微控制器类型
    power_level: str = ""                # 功率等级
    frequency: str = ""                  # 频率
    dimensions: str = ""                 # 尺寸

    # 清晰度评估
    clarity_level: ClarityLevel = ClarityLevel.UNCLEAR
    clarifying_questions: List[str] = None

    # 匹配的方案
    matched_projects: List[Dict] = None

    def __post_init__(self):
        if self.clarifying_questions is None:
            self.clarifying_questions = []
        if self.matched_projects is None:
            self.matched_projects = []


class SemanticAnalyzer:
    """语义分析器"""

    def __init__(self):
        self.knowledge_base_path = Path(__file__).parent / "semantic_knowledge_index.json"
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict:
        """加载知识库"""
        if self.knowledge_base_path.exists():
            with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        logger.warning(f"知识库文件不存在: {self.knowledge_base_path}")
        return {"categories": [], "chip_database": {}}

    def analyze(self, requirements: str) -> Semantic理解结果:
        """
        语义分析用户需求
        返回理解结果和需要询问的澄清问题
        """
        logger.info(f"开始语义分析: {requirements}")

        result = Semantic理解结果()

        # 调用LLM进行语义理解
        understanding = self._llm_semantic_understanding(requirements)

        if understanding:
            result.desired_function = understanding.get("desired_function", "")
            result.input_voltage = understanding.get("input_voltage", "")
            result.output_voltage = understanding.get("output_voltage", "")
            result.communication_interface = understanding.get("communication_interface", "")
            result.wireless_type = understanding.get("wireless_type", "")
            result.sensor_type = understanding.get("sensor_type", "")
            result.mcu_type = understanding.get("mcu_type", "")
            result.power_level = understanding.get("power_level", "")
            result.frequency = understanding.get("frequency", "")
            result.dimensions = understanding.get("dimensions", "")

        # 评估清晰度
        result.clarity_level = self._evaluate_clarity(result)

        # 如果不清晰，生成澄清问题
        if result.clarity_level != ClarityLevel.CLEAR:
            result.clarifying_questions = self._generate_clarifying_questions(result, requirements)

        # 从知识库搜索匹配方案
        result.matched_projects = self._semantic_search(result)

        logger.info(f"语义分析完成: 清晰度={result.clarity_level.value}, 匹配方案数={len(result.matched_projects)}")

        return result

    def _llm_semantic_understanding(self, requirements: str) -> Dict[str, str]:
        """
        使用LLM进行语义理解
        从用户描述中提取关键信息
        """
        # 检查是否有LLM客户端
        try:
            from kimi_client import get_kimi_client, is_kimi_available
            from glm4_client import get_glm4_client, is_glm4_available

            # 构建提示词
            prompt = f"""请分析以下用户需求，提取关键信息。以JSON格式返回：
{{
    "desired_function": "用户想要实现的主要功能",
    "input_voltage": "输入电压（如5V, 12V, 220V等）",
    "output_voltage": "输出电压（如3.3V, 5V, 12V等）",
    "communication_interface": "通信接口（如UART, I2C, SPI, USB, CAN等）",
    "wireless_type": "无线类型（如WiFi, 蓝牙, LoRa, 2.4G等）",
    "sensor_type": "传感器类型（如温湿度, 雷达, 加速度等）",
    "mcu_type": "微控制器类型（如ESP32, STM32, ATmega等）",
    "power_level": "功率等级（如1A, 2A, 大功率等）",
    "frequency": "频率（如12MHz, 2.4GHz, 5.8GHz等）",
    "dimensions": "尺寸（如25x20mm, 50x30mm等）"
}}

用户需求: {requirements}

请只返回JSON，不要其他文字。"""

            # 优先使用Kimi
            if is_kimi_available():
                client = get_kimi_client()
                response = client.chat.completions.create(
                    model="kimi-pro",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                llm_result = response.choices[0].message.content
            elif is_glm4_available():
                client = get_glm4_client()
                response = client.chat.completions.create(
                    model="glm-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                llm_result = response.choices[0].message.content
            else:
                logger.warning("无可用LLM客户端，使用本地解析")
                return self._local_parse(requirements)

            # 解析JSON结果
            import re
            json_match = re.search(r'\{.*\}', llm_result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")

        # 如果LLM失败，使用本地解析作为后备
        return self._local_parse(requirements)

    def _local_parse(self, requirements: str) -> Dict[str, str]:
        """本地解析 - 作为LLM的后备方案"""
        req = requirements.lower()
        result = {
            "desired_function": "",
            "input_voltage": "",
            "output_voltage": "",
            "communication_interface": "",
            "wireless_type": "",
            "sensor_type": "",
            "mcu_type": "",
            "power_level": "",
            "frequency": "",
            "dimensions": ""
        }

        # 检测功能
        if any(k in req for k in ["usb", "串口", "uart", "serial"]):
            result["desired_function"] = "USB转串口通信"
            result["communication_interface"] = "USB/UART"
        if any(k in req for k in ["开发板", "开发", "devboard", "controller"]):
            result["desired_function"] = "开发板"
        if any(k in req for k in ["电源", "稳压", "power", "supply"]):
            result["desired_function"] = "电源管理"
        if any(k in req for k in ["传感器", "sensor", "感应"]):
            result["desired_function"] = "传感器"
        if any(k in req for k in ["无线", "wifi", "bluetooth", "lora"]):
            result["desired_function"] = "无线通信"
        if any(k in req for k in ["电机", "motor", "驱动"]):
            result["desired_function"] = "电机驱动"
        if any(k in req for k in ["定时", "timer", "555", "ne555"]):
            result["desired_function"] = "定时器电路"
        if any(k in req for k in ["led", "灯", "闪烁", "blink"]):
            result["desired_function"] = "LED控制"

        # 检测芯片/控制器
        if "esp32" in req:
            result["mcu_type"] = "ESP32"
        elif "stm32" in req:
            result["mcu_type"] = "STM32"
        elif "arduino" in req:
            result["mcu_type"] = "Arduino"
        elif "ch340" in req:
            result["mcu_type"] = "CH340"
        elif "ne555" in req or "555" in req:
            result["mcu_type"] = "NE555"
        elif "7805" in req:
            result["mcu_type"] = "7805"

        # 检测电压
        if "5v" in req:
            result["output_voltage"] = "5V"
        if "3.3v" in req:
            result["output_voltage"] = "3.3V"
        if "12v" in req:
            result["input_voltage"] = "12V"
        if "220v" in req or "220" in req:
            result["input_voltage"] = "220V"

        # 检测尺寸
        import re
        dim_match = re.search(r'(\d+)\s*[xX×]\s*(\d+)', requirements)
        if dim_match:
            result["dimensions"] = f"{dim_match.group(1)}x{dim_match.group(2)}mm"

        return result

    def _evaluate_clarity(self, result: Semantic理解结果) -> ClarityLevel:
        """评估需求清晰度"""
        # 至少要有主要功能
        if not result.desired_function and not result.mcu_type:
            return ClarityLevel.UNCLEAR

        # 检查关键信息是否完整
        has_function = bool(result.desired_function or result.mcu_type)
        has_power_info = bool(result.input_voltage or result.output_voltage or result.power_level)
        has_comms = bool(result.communication_interface or result.wireless_type)

        # 评分
        score = sum([has_function, has_power_info, has_comms])

        if score >= 2:
            return ClarityLevel.CLEAR
        elif score == 1:
            return ClarityLevel.MOSTLY_CLEAR
        else:
            return ClarityLevel.UNCLEAR

    def _generate_clarifying_questions(self, result: Semantic理解结果, original_requirements: str) -> List[str]:
        """生成澄清问题"""
        questions = []

        # 如果没有明确的功能
        if not result.desired_function and not result.mcu_type:
            questions.append("您希望实现什么功能？例如：电源管理、通信模块、传感器、电机驱动等")

        # 如果没有电压信息
        if not result.input_voltage and not result.output_voltage:
            questions.append("您需要什么输入/输出电压？例如：5V、12V、3.3V等")

        # 如果是通信相关但没有接口信息
        if result.desired_function in ["USB转串口通信", "无线通信"] and not result.communication_interface:
            questions.append("需要什么通信接口？例如：UART、I2C、SPI、USB等")

        # 如果是无线相关
        if "无线" in (result.desired_function or "") or result.wireless_type:
            if not result.wireless_type:
                questions.append("需要什么无线方式？例如：WiFi、蓝牙、LoRa、2.4G等")

        # 如果是传感器相关
        if "传感" in (result.desired_function or ""):
            if not result.sensor_type:
                questions.append("需要什么类型的传感器？例如：温湿度、距离雷达、加速度等")

        # 功率需求
        if result.desired_function == "电源管理" and not result.power_level:
            questions.append("需要多大的输出电流？例如：1A、2A、5A等")

        # 尺寸要求
        if not result.dimensions:
            questions.append("对PCB尺寸有要求吗？例如：25x20mm、50x30mm等")

        # 限制问题数量
        return questions[:3]

    def _semantic_search(self, result: Semantic理解结果) -> List[Dict]:
        """
        语义搜索知识库
        根据理解结果搜索最匹配的方案
        """
        matches = []

        # 提取搜索关键词
        search_keywords = []
        if result.desired_function:
            search_keywords.append(result.desired_function)
        if result.mcu_type:
            search_keywords.append(result.mcu_type)
        if result.communication_interface:
            search_keywords.append(result.communication_interface)
        if result.wireless_type:
            search_keywords.append(result.wireless_type)
        if result.sensor_type:
            search_keywords.append(result.sensor_type)

        # 遍历知识库搜索
        for category in self.knowledge_base.get("categories", []):
            for project in category.get("projects", []):
                score = self._calculate_match_score(project, search_keywords, result)
                if score > 0:
                    matches.append({
                        **project,
                        "match_score": score,
                        "category": category.get("name", "")
                    })

        # 按匹配度排序
        matches.sort(key=lambda x: x.get("match_score", 0), reverse=True)

        # 返回前5个最匹配的
        return matches[:5]

    def _calculate_match_score(self, project: Dict, keywords: List[str], result: Semantic理解结果) -> float:
        """计算项目匹配度分数"""
        score = 0.0

        project_keywords = [k.lower() for k in project.get("keywords", [])]
        project_name = project.get("name", "").lower()
        project_desc = project.get("description", "").lower()
        project_chips = [c.lower() for c in project.get("chips", [])]

        # 关键词匹配
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in project_keywords:
                score += 3.0
            if kw_lower in project_name:
                score += 2.0
            if kw_lower in project_desc:
                score += 1.0
            if any(kw_lower in chip.lower() for chip in project.get("chips", [])):
                score += 2.5

        # 特定匹配
        if result.mcu_type:
            if result.mcu_type.upper() in [c.upper() for c in project_chips]:
                score += 4.0

        if result.communication_interface:
            comms_lower = result.communication_interface.lower()
            if comms_lower in project.get("features", []):
                score += 2.0

        if result.wireless_type:
            wireless_lower = result.wireless_type.lower()
            if wireless_lower in project.get("features", []) or wireless_lower in project_keywords:
                score += 3.0

        return score

    def get_chip_info(self, chip_name: str) -> Optional[Dict]:
        """获取芯片信息"""
        chip_db = self.knowledge_base.get("chip_database", {})
        return chip_db.get(chip_name.upper())


# 全局实例
_semantic_analyzer = None


def get_semantic_analyzer() -> SemanticAnalyzer:
    """获取语义分析器实例"""
    global _semantic_analyzer
    if _semantic_analyzer is None:
        _semantic_analyzer = SemanticAnalyzer()
    return _semantic_analyzer
