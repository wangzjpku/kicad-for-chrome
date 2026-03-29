"""
DeepSeek 大模型客户端
"""

import os

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek 客户端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"

        if not self.api_key:
            logger.warning("未设置 DEEPSEEK_API_KEY 环境变量，DeepSeek AI 功能将不可用")

    def is_available(self) -> bool:
        """检查 API 是否可用"""
        if not self.api_key:
            return False
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"DeepSeek API 测试失败: {e}")
            return False

    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None, **kwargs) -> Dict[str, Any]:
        """发送聊天消息"""
        if not self.api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY")

        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "temperature": kwargs.get("temperature", 0.7),
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=kwargs.get("timeout", 60)
        )

        if response.status_code != 200:
            raise Exception(f"DeepSeek API 错误: {response.text}")

        result = response.json()
        return {
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {}),
        }

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

{attachments_info}

请生成完整的项目方案，包括：
1. 项目名称和描述
2. 元器件清单（名称、型号、封装、数量）
3. 技术参数
4. 原理图布局

请直接输出JSON格式。"""

        system_prompt = system_prompt_template.replace("{attachments_info}", attachments_info)

        # 调用 chat 方法获取响应
        chat_result = self.chat(
            user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=4096,
        )

        result = chat_result.get("content", "")
        usage = chat_result.get("usage", {})

        # 解析 JSON 响应
        import json as json_module

        original_result = result
        result = result.strip()

        logger.info(f"DeepSeek 返回原始响应长度: {len(result)} 字符")

        # 从 markdown 代码块中提取
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            first = result.find("```")
            last = result.rfind("```")
            if first != last:
                result = result[first + 3: last]

        result = result.strip()

        def _normalize_component(comp):
            """归一化单个组件的键名（支持中英文）"""
            if not isinstance(comp, dict):
                return comp
            return {
                "name": comp.get("name") or comp.get("名称", ""),
                "model": comp.get("model") or comp.get("型号", ""),
                "package": comp.get("package") or comp.get("封装", ""),
                "quantity": comp.get("quantity") or comp.get("数量", 1),
                "footprint": comp.get("footprint") or comp.get("封装", ""),
                "备注": comp.get("备注", ""),  # 保留备注信息
            }

        def _normalize_components(components):
            """归一化组件列表"""
            if not isinstance(components, list):
                return []
            return [_normalize_component(c) for c in components]

        def _normalize_response(project_spec, usage):
            """归一化 DeepSeek 的各种响应格式（支持中英文键名）"""
            # 处理中文格式 "项目方案"
            if "项目方案" in project_spec:
                scheme = project_spec["项目方案"]
                components = scheme.get("元器件清单", scheme.get("components", []))
                return {
                    "name": scheme.get("项目名称") or scheme.get("name", ""),
                    "description": scheme.get("项目描述") or scheme.get("description", ""),
                    "components": _normalize_components(components),
                    "parameters": scheme.get("技术参数", scheme.get("parameters", {})),
                    "schematic": scheme.get("原理图布局", scheme.get("schematic", {})),
                    "usage": usage,
                }
            # 处理 project_scheme 包装
            if "project_scheme" in project_spec:
                scheme = project_spec["project_scheme"]
                return {
                    "name": scheme.get("name", ""),
                    "description": scheme.get("description", ""),
                    "components": _normalize_components(scheme.get("components_list", scheme.get("components", []))),
                    "parameters": scheme.get("technical_parameters", scheme.get("parameters", [])),
                    "schematic": scheme.get("schematic_layout", scheme.get("schematic", {})),
                    "usage": usage,
                }
            # 处理 project 包装
            if "project" in project_spec:
                proj = project_spec["project"]
                components = project_spec.get("bill_of_materials", proj.get("bill_of_materials", []))
                return {
                    "name": proj.get("name", ""),
                    "description": proj.get("description", ""),
                    "components": _normalize_components(components),
                    "parameters": project_spec.get("technical_parameters", proj.get("technical_parameters", [])),
                    "schematic": project_spec.get("schematic_layout", proj.get("schematic_layout", {})),
                    "usage": usage,
                }
            # 直接返回，但确保组件格式正确
            result = {**project_spec, "usage": usage}
            if "components" in result:
                result["components"] = _normalize_components(result["components"])
            return result

        # 尝试直接解析
        try:
            project_spec = json_module.loads(result)
            logger.info("DeepSeek JSON 解析成功")
            return _normalize_response(project_spec, usage)
        except json_module.JSONDecodeError:
            pass

        # 尝试修复常见问题
        result = result.replace("```json", "").replace("```", "")

        try:
            project_spec = json_module.loads(result)
            logger.info("DeepSeek JSON 解析成功 (修复代码块)")
            return _normalize_response(project_spec, usage)
        except json_module.JSONDecodeError:
            pass

        # 尝试提取 JSON 对象
        start = result.find('{')
        end = result.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = result[start:end+1]
            try:
                project_spec = json_module.loads(json_str)
                logger.info("DeepSeek JSON 解析成功 (提取)")
                return _normalize_response(project_spec, usage)
            except json_module.JSONDecodeError:
                pass

        # 暴力修复 - 移除单引号
        if result.count("{") > 5 and result.count("}") > 5:
            result_brute = result.replace("'", '"')
            try:
                project_spec = json_module.loads(result_brute)
                logger.info("DeepSeek JSON 解析成功 (暴力修复)")
                return _normalize_response(project_spec, usage)
            except json_module.JSONDecodeError:
                pass

        logger.error(f"解析 DeepSeek 响应失败")
        logger.error(f"原始响应前800字符: {original_result[:800]}")
        raise Exception(f"AI返回的格式不正确，无法解析JSON")


# 全局客户端实例
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """获取 DeepSeek 客户端实例"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client


def is_deepseek_available() -> bool:
    """检查 DeepSeek 是否可用"""
    return get_deepseek_client().is_available()
