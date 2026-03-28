"""
GLM-4 大模型客户端
用于连接智谱AI的GLM-4 API生成电路项目方案
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)


class GLM4Client:
    """智谱AI GLM-4 客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化GLM-4客户端

        Args:
            api_key: 智谱AI API Key (可从环境变量 ZHIPU_API_KEY 获取)
        """
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "glm-4"  # 使用GLM-4模型

        if not self.api_key:
            logger.warning("未设置 ZHIPU_API_KEY 环境变量，AI功能将不可用")

    def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        调用GLM-4 API

        Args:
            messages: 消息列表
            **kwargs: 其他参数如temperature, max_tokens等

        Returns:
            API响应结果
        """
        if not self.api_key:
            raise ValueError("未设置 API Key，请设置 ZHIPU_API_KEY 环境变量")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {"model": self.model, "messages": messages, **kwargs}

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

    def chat(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        发送聊天请求

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 其他参数

        Returns:
            AI回复内容
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = self._call_api(messages, **kwargs)

        return result["choices"][0]["message"]["content"]

    def generate_project_spec(self, requirements: str, attachments: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Generate circuit project specification based on user requirements

        Args:
            requirements: User input project requirements
            attachments: Optional list of attachments (reference materials)

        Returns:
            Dict containing project specification and schematic data
        """
        # Build attachments info
        attachments_info = ""
        if attachments and len(attachments) > 0:
            attachments_info = "\n\n## Reference Materials Provided:\n"
            for att in attachments:
                att_type = att.get('type', 'unknown')
                att_name = att.get('name', 'unknown')
                att_path = att.get('path', '')
                attachments_info += f"- {att_name} ({att_type}): {att_path}\n"
            attachments_info += "\nPlease analyze circuit requirements based on reference materials."

        system_prompt_template = """You are a professional electronic circuit design assistant.

Your tasks are:
1. Understand user requirements
2. Analyze provided reference materials (if any)
3. Determine required components
4. Define technical parameters
5. Generate schematic layout
6. Output structured project specification

{attachments_info}

Output strictly in this JSON format:
{
  "name": "项目名称",
  "description": "项目描述",
  "components": [
    {"name": "元器件名称", "model": "型号/规格", "package": "封装", "quantity": 数量}
  ],
  "parameters": [
    {"key": "参数名", "value": "参数值", "unit": "单位"}
  ],
  "schematic": {
    "components": [
      {
        "id": "元件ID(如U1,R1,C1)", 
        "name": "元件名", 
        "model": "型号", 
        "footprint": "KiCad封装名称(如Resistor_SMD:R_0603_1608Metric)",
        "symbol_library": "符号库名(如Device)",
        "position": {"x": X坐标, "y": Y坐标}, 
        "pins": [{"number": "引脚号", "name": "引脚名", "type": "输入类型(input/output/power/passive)"}],
        "reference": "位号(如U1,R1,C1,D1)"
      }
    ],
    "wires": [
      {
        "id": "导线ID", 
        "start_component": "起始元件ID",
        "start_pin": "起始引脚号",
        "end_component": "终点元件ID",
        "end_pin": "终点引脚号",
        "points": [{"x": X, "y": Y}, {"x": X, "y": Y}], 
        "net": "网络名"
      }
    ],
    "nets": [
      {"id": "网络ID", "name": "网络名", "type": "power/signal/ground"}
    ]
  }
}

重要提示：

【关键芯片选择规则 - 必须严格遵守】：
- 如果用户提到"ne555"或"555"或"定时器"或"振荡器"，必须使用NE555定时器芯片（如NE555P），禁止使用ATtiny85、STM32等单片机替代
- 如果用户提到"ch340c"或"ch340"或"usb转串口"，必须使用CH340C芯片，禁止用FT232、PL2303等其他USB-UART芯片替代
- 如果用户提到"esp32-wroom"、"esp32-wrover"、"esp32-c3"、"esp32-s3"，必须使用该型号的ESP32模块
- 如果用户提到"ams1117"，必须使用AMS1117稳压器
- 最关键：当用户明确指定某个芯片时，方案中必须包含该芯片，不能用其他芯片替代

- components中的封装请使用标准的KiCad封装格式，如0805, SOT-223, TO-220等
- schematic.components中必须包含footprint字段，格式为"库名:封装名"，例如：
  - 电阻: Resistor_SMD:R_0603_1608Metric 或 Resistor_SMD:R_0805_2012Metric
  - 电容: Capacitor_SMD:C_0603_1608Metric 或 Capacitor_SMD:C_0805_2012Metric
  - LED: LED_SMD:LED_0603_1608Metric 或 LED_THT:LED_D5.0mm
  - 三极管: Package_TO_SOT_SMD:SOT-23
  - IC: Package_SO:SOIC-8_3.9x4.9mm_P1.27mm
  - 稳压器: Package_TO_SOT_SMD:SOT-223-3
  - 连接器: Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical
- schematic中的坐标请使用合理的布局，让原理图清晰易读，元件间距至少100单位
- 电源网络用VCC/3V3/5V，地网络用GND
- wires必须连接实际的元件引脚，不能是示意性的连接
- 每个元件的pins要列出所有引脚，包括电源(VCC/VDD)、地(GND/VSS)、信号引脚
- 只需要输出JSON，不要输出任何解释或额外内容"""

        user_prompt = f"""请为以下电路项目生成方案：

{requirements}

请生成完整的项目方案，包括：
1. 项目名称和描述
2. 所需的元器件列表（名称、型号、封装、数量）
3. 技术参数
4. 原理图布局

请直接输出JSON格式的结果。"""

        # Replace placeholder in system prompt
        system_prompt = system_prompt_template.replace("{attachments_info}", attachments_info)

        try:
            result = self.chat(
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Lower temperature for more deterministic output
                max_tokens=4096,
            )

            # 解析JSON响应 - 超级增强版解析器
            original_result = result
            result = result.strip()
            logger.info(f"GLM返回原始响应长度: {len(result)} 字符")

            # 方法1: 尝试从markdown代码块中提取
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
                logger.info("从json代码块提取")
            elif "```" in result:
                first = result.find("```")
                last = result.rfind("```")
                if first != last:
                    result = result[first + 3 : last]
                    logger.info("从代码块提取")

            result = result.strip()

            # 尝试直接解析
            try:
                project_spec = json.loads(result)
                logger.info("JSON解析成功 (直接解析)")
                return project_spec
            except json.JSONDecodeError as e1:
                logger.warning(f"直接解析失败: {e1}")

            # 方法2: 找到JSON开始和结束的大括号
            start = result.find("{")
            end = result.rfind("}")

            if start != -1 and end != -1 and end > start:
                json_str = result[start : end + 1]
                try:
                    project_spec = json.loads(json_str)
                    logger.info("JSON解析成功 (大括号提取)")
                    return project_spec
                except json.JSONDecodeError as e2:
                    logger.warning(f"大括号提取解析失败: {e2}")

            # 方法3: 移除尾随逗号和修复单引号
            import re

            result_fixed = re.sub(r",(\s*[}\]])", r"\1", result)
            # 简单的单引号替换（这会有问题，但试试看）
            # 只替换明显是JSON键的单引号

            try:
                project_spec = json.loads(result_fixed)
                logger.info("JSON解析成功 (修复格式)")
                return project_spec
            except json.JSONDecodeError as e3:
                logger.warning(f"修复格式后解析失败: {e3}")

            # 方法4: 暴力修复 - 移除所有单引号（非常危险但作为最后手段）
            # 只在JSON看起来相对完整时使用
            if result.count("{") > 5 and result.count("}") > 5:
                result_brute = result.replace("'", '"')
                try:
                    project_spec = json.loads(result_brute)
                    logger.info("JSON解析成功 (暴力修复单引号)")
                    return project_spec
                except json.JSONDecodeError as e:
                    logger.debug(f"暴力解析JSON失败: {e}")

            # 所有方法都失败
            logger.error(f"解析GLM-4响应失败 - 已尝试所有修复方法")
            logger.error(f"原始响应前800字符: {original_result[:800]}")
            raise Exception(f"AI返回的格式不正确，无法解析JSON")

        except Exception as e:
            if "AI返回的格式不正确" not in str(e):
                logger.error(f"调用GLM-4 API失败: {e}")
            raise


# 全局客户端实例
_glm4_client: Optional[GLM4Client] = None


def get_glm4_client(api_key: Optional[str] = None) -> GLM4Client:
    """获取GLM-4客户端实例"""
    global _glm4_client
    if _glm4_client is None or api_key is not None:
        _glm4_client = GLM4Client(api_key)
    return _glm4_client


def is_glm4_available() -> bool:
    """检查GLM-4是否可用"""
    client = get_glm4_client()
    return client.api_key is not None
