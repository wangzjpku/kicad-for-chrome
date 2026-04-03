"""
Kimi 大模型客户端 (Moonshot AI)
用于连接 Kimi API 生成电路项目方案
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)


class KimiClient:
    """Moonshot AI Kimi 客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Kimi 客户端

        Args:
            api_key: Moonshot AI API Key
        """
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        self.base_url = "https://api.moonshot.cn/v1"
        # 使用 Kimi2.5 模型
        self.model = "moonshot-v1-8k-vision-preview"

        if not self.api_key:
            logger.warning("未设置 MOONSHOT_API_KEY 环境变量，AI功能将不可用")

    def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        调用 Kimi API

        Args:
            messages: 消息列表
            **kwargs: 其他参数如 temperature, max_tokens 等

        Returns:
            API 响应结果
        """
        if not self.api_key:
            raise ValueError("未设置 API Key，请设置 MOONSHOT_API_KEY 环境变量")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            raise Exception(f"API调用失败: {response.status_code} - {response.text}")

        result = response.json()
        return result

    def chat(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        发送聊天请求

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 其他参数

        Returns:
            包含content和usage的字典
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = self._call_api(messages, **kwargs)

        # 返回内容和使用量信息
        return {
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {}),
        }

    def generate_project_spec(self, requirements: str, attachments: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        根据用户需求生成电路项目方案

        Args:
            requirements: 用户输入的项目需求描述
            attachments: 可选的附件列表，包含参考资料路径

        Returns:
            包含项目方案、原理图数据的字典
        """
        # 构建附件信息
        attachments_info = ""
        if attachments and len(attachments) > 0:
            attachments_info = "\n\n## User provided reference materials:\n"
            for att in attachments:
                att_type = att.get('type', 'unknown')
                att_name = att.get('name', 'unknown')
                att_path = att.get('path', '')
                attachments_info += f"- {att_name} ({att_type}): {att_path}\n"
            attachments_info += "\nPlease analyze the circuit requirements based on the above reference materials."

        system_prompt_template = """You are a professional electronic circuit design assistant.

Your tasks are:
1. Understand user requirements
2. Analyze provided reference materials (if any)
3. Determine required components
4. Define technical parameters
5. Generate schematic layout
6. Output structured project specification

IMPORTANT CIRCUIT SELECTION RULES (CRITICAL - MUST FOLLOW EXACTLY):
- If user mentions "ne555" or "555" or "定时器" or "振荡器" with "led" or "led" nearby, you MUST use NE555 timer chip with NE555P symbol. DO NOT use ATtiny85, ATmega, STM32, or any microcontroller instead
- If user mentions "ch340c" or "ch340" or "usb转串口" or "usb to serial", you MUST use CH340C chip. DO NOT substitute with FT232, PL2303, or any other USB-UART chip
- If user mentions "esp32-wroom" or "esp32-wrover" or "esp32-c3" or "esp32-s3", you MUST use that specific ESP32 module variant
- If user mentions "stm32", use STM32 microcontroller
- If user mentions "attiny85" or "attiny", use ATtiny85
- If user mentions "7805" or "lm7805", use 7805 linear regulator
- If user mentions "ams1117", use AMS1117
- If user mentions "tp4056", use TP4056 charging IC

MOST IMPORTANT: When a user explicitly names a chip (e.g., "NE555", "CH340C", "ESP32-WROOM-32E"), you MUST include that exact chip in your design. Never substitute with a different chip unless the user asks for alternatives.

IMPORTANT COMPONENT QUANTITY RULES:
- Use the EXACT component quantities that user specifies
- If user says "10k and 1k resistors", include exactly 1x 10k and 1x 1k resistor
- If user says "10uF capacitor", include exactly 1x 10uF capacitor
- If user says "1 LED", include exactly 1 LED

NE555 LED Blink Circuit Example (user likely wants this when they say "ne555 led blink"):
- NE555P (DIP-8 or SOIC-8)
- 10kΩ resistor (for timing)
- 1kΩ resistor (for LED current limit)
- 10uF capacitor (timing)
- 100nF capacitor (power decoupling)
- 1x LED
- 330Ω resistor (LED limit)

{attachments_info}

CRITICAL REQUIREMENTS - You MUST include ALL of these fields:
1. components - array of components with pins
2. wires - array of wire connections (NEVER empty!)
3. powerSymbols - array of VCC/GND symbols
4. labels - array of net labels
5. nets - array of net definitions

Example for NE555 LED Blink:
{
  "project_name": "NE555 LED Blinker",
  "description": "Simple LED blink circuit using NE555 timer",
  "components": [
    {"reference": "U1", "name": "NE555P", "value": "NE555P", "symbol_library": "Timer:NE555P", "footprint": "Package_DIP:DIP-8_W7.62mm", "position": {"x": 100, "y": 100}, "pins": [{"number": "1", "name": "GND"}, {"number": "2", "name": "TRIG"}, {"number": "3", "name": "OUT"}, {"number": "4", "name": "RESET"}, {"number": "5", "name": "CTRL"}, {"number": "6", "name": "THRES"}, {"number": "7", "name": "DISCH"}, {"number": "8", "name": "VCC"}]},
    {"reference": "R1", "name": "Resistor", "value": "10k", "symbol_library": "Device:R", "footprint": "Resistor_SMD:R_0603_1608Metric", "position": {"x": 130, "y": 110}, "pins": [{"number": "1", "name": "1"}, {"number": "2", "name": "2"}]},
    {"reference": "R2", "name": "Resistor", "value": "1k", "symbol_library": "Device:R", "footprint": "Resistor_SMD:R_0603_1608Metric", "position": {"x": 130, "y": 90}, "pins": [{"number": "1", "name": "1"}, {"number": "2", "name": "2"}]},
    {"reference": "C1", "name": "Capacitor", "value": "10uF", "symbol_library": "Device:C", "footprint": "Capacitor_SMD:C_0805_2012Metric", "position": {"x": 70, "y": 100}, "pins": [{"number": "1", "name": "1"}, {"number": "2", "name": "2"}]},
    {"reference": "D1", "name": "LED", "value": "LED", "symbol_library": "Device:LED", "footprint": "LED_SMD:LED_0805_2012Metric", "position": {"x": 160, "y": 100}, "pins": [{"number": "1", "name": "K"}, {"number": "2", "name": "A"}]}
  ],
  "wires": [
    {"from": "U1.8", "to": "R1.1", "net": "VCC"},
    {"from": "U1.4", "to": "R1.1", "net": "VCC"},
    {"from": "U1.7", "to": "R1.2", "net": "DISCH"},
    {"from": "U1.6", "to": "R1.2", "net": "THRES"},
    {"from": "U1.2", "to": "C1.1", "net": "TRIG"},
    {"from": "U1.6", "to": "C1.1", "net": "THRES"},
    {"from": "U1.3", "to": "R2.1", "net": "OUT"},
    {"from": "R2.2", "to": "D1.2", "net": "LED_A"},
    {"from": "U1.1", "to": "C1.2", "net": "GND"},
    {"from": "D1.1", "to": "C1.2", "net": "GND"}
  ],
  "powerSymbols": [
    {"type": "vcc", "name": "VCC", "position": {"x": 100, "y": 130}, "net": "VCC"},
    {"type": "gnd", "name": "GND", "position": {"x": 70, "y": 70}, "net": "GND"}
  ],
  "labels": [
    {"net": "VCC", "position": {"x": 100, "y": 135}},
    {"net": "GND", "position": {"x": 70, "y": 65}},
    {"net": "OUT", "position": {"x": 120, "y": 95}}
  ],
  "nets": [
    {"id": "net_vcc", "name": "VCC"},
    {"id": "net_gnd", "name": "GND"},
    {"id": "net_trig", "name": "TRIG"},
    {"id": "net_out", "name": "OUT"}
  ]
}

Output strictly in this JSON format:"""

        system_prompt = system_prompt_template.replace("{attachments_info}", attachments_info)

        user_prompt = f"""Please generate a circuit project proposal:

{requirements}

{attachments_info}

Please generate complete project proposal including:
1. Project name and description
2. Component list (name, model, package, quantity)
3. Technical parameters
4. Schematic layout

Please output JSON format directly."""

        try:
            chat_result = self.chat(
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Lower temperature for more deterministic output
                max_tokens=4096,
            )

            # 提取内容和usage
            result = chat_result["content"]
            usage = chat_result.get("usage", {})

            # 解析 JSON 响应
            original_result = result
            result = result.strip()
            logger.info(f"Kimi 返回原始响应长度: {len(result)} 字符")

            # 从 markdown 代码块中提取
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                first = result.find("```")
                last = result.rfind("```")
                if first != last:
                    result = result[first + 3: last]

            result = result.strip()

            # 尝试直接解析
            try:
                project_spec = json.loads(result)
                logger.info("JSON 解析成功")
                return {**project_spec, "usage": usage}
            except json.JSONDecodeError:
                pass

            # 尝试修复常见问题
            # 1. 移除 markdown 代码块标记
            result = result.replace("```json", "").replace("```", "")

            try:
                project_spec = json.loads(result)
                logger.info("JSON 解析成功 (修复代码块)")
                return {**project_spec, "usage": usage}
            except json.JSONDecodeError:
                pass

            # 2. 尝试提取 JSON 对象
            start = result.find('{')
            end = result.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = result[start:end+1]
                try:
                    project_spec = json.loads(json_str)
                    logger.info("JSON 解析成功 (提取)")
                    return {**project_spec, "usage": usage}
                except json.JSONDecodeError as e:
                    logger.debug(f"提取方式解析JSON失败: {e}")

            # 3. 暴力修复 - 移除单引号
            if result.count("{") > 5 and result.count("}") > 5:
                result_brute = result.replace("'", '"')
                try:
                    project_spec = json.loads(result_brute)
                    logger.info("JSON 解析成功 (暴力修复)")
                    return {**project_spec, "usage": usage}
                except json.JSONDecodeError as e:
                    logger.debug(f"暴力方式解析JSON失败: {e}")

            logger.error(f"解析 Kimi 响应失败")
            logger.error(f"原始响应前800字符: {original_result[:800]}")
            raise Exception(f"AI返回的格式不正确，无法解析JSON")

        except Exception as e:
            if "AI返回的格式不正确" not in str(e):
                logger.error(f"调用 Kimi API 失败: {e}")
            raise


# 全局客户端实例
_kimi_client: Optional[KimiClient] = None


def get_kimi_client() -> KimiClient:
    """获取 Kimi 客户端单例"""
    global _kimi_client
    if _kimi_client is None:
        import os
        api_key = os.environ.get("KIMI_API_KEY", "")
        if not api_key:
            logger.warning("KIMI_API_KEY not set. Kimi AI features will be disabled.")
        _kimi_client = KimiClient(api_key=api_key)
    return _kimi_client


def is_kimi_available() -> bool:
    """检查 Kimi API 是否可用"""
    try:
        client = get_kimi_client()
        return client.api_key is not None
    except Exception as e:
        logger.debug(f"Kimi可用性检查失败: {e}")
        return False
