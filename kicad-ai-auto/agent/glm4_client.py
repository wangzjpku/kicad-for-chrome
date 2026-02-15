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

    def generate_project_spec(self, requirements: str) -> Dict[str, Any]:
        """
        根据用户需求生成电路项目方案

        Args:
            requirements: 用户输入的项目需求描述

        Returns:
            包含项目方案、原理图数据的字典
        """
        system_prompt = """你是一个专业的电子电路设计助手，能够根据用户的需求描述，分析并生成完整的电路项目方案。

你的任务是：
1. 理解用户的需求描述
2. 分析需要哪些电子元器件
3. 确定电路的技术参数
4. 生成合理的原理图布局
5. 输出结构化的项目方案

请严格按照以下JSON格式输出，不要输出其他内容：
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
      {"id": "元件ID", "name": "元件名", "model": "型号", "position": {"x": X坐标, "y": Y坐标}, "pins": [{"number": "引脚号", "name": "引脚名"}]}
    ],
    "wires": [
      {"id": "导线ID", "points": [{"x": X, "y": Y}, {"x": X, "y": Y}], "net": "网络名"}
    ],
    "nets": [
      {"id": "网络ID", "name": "网络名"}
    ]
  }
}

重要提示：
- components中的封装请使用标准的KiCad封装格式，如0805, SOT-223, TO-220等
- schematic中的坐标请使用合理的布局，让原理图清晰易读
- 电源网络用VCC，地网络用GND
- 只需要输出JSON，不要输出任何解释或额外内容"""

        user_prompt = f"""请为以下电路项目生成方案：

{requirements}

请生成完整的项目方案，包括：
1. 项目名称和描述
2. 所需的元器件列表（名称、型号、封装、数量）
3. 技术参数
4. 原理图布局

请直接输出JSON格式的结果。"""

        try:
            result = self.chat(
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
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
                except:
                    pass

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
