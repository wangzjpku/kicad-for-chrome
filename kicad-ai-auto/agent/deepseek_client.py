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
