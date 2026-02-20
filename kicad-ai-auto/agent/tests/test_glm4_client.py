"""
GLM-4 Client 单元测试
测试大模型客户端的功能
"""

import pytest
from unittest.mock import patch, Mock
import json

from glm4_client import (
    GLM4Client,
    get_glm4_client,
    is_glm4_available,
)


class TestGLM4ClientInit:
    """测试GLM-4客户端初始化"""

    def test_init_with_api_key(self):
        """测试使用API Key初始化"""
        client = GLM4Client(api_key="test_api_key_123")
        assert client.api_key == "test_api_key_123"
        assert client.model == "glm-4"

    def test_init_with_env_var(self):
        """测试使用环境变量初始化"""
        with patch.dict("os.environ", {"ZHIPU_API_KEY": "env_api_key"}):
            client = GLM4Client()
            assert client.api_key == "env_api_key"

    def test_init_without_api_key(self):
        """测试无API Key初始化"""
        with patch.dict("os.environ", {}, clear=True):
            client = GLM4Client()
            assert client.api_key is None

    def test_default_model(self):
        """测试默认模型"""
        client = GLM4Client("test_key")
        assert client.model == "glm-4"


class TestGLM4ClientChat:
    """测试聊天功能"""

    @patch("glm4_client.requests.post")
    def test_chat_success(self, mock_post):
        """测试成功聊天"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello, I'm GLM-4!"}}]
        }
        mock_post.return_value = mock_response

        client = GLM4Client("test_api_key")
        result = client.chat("Hello")

        assert result == "Hello, I'm GLM-4!"
        mock_post.assert_called_once()

    @patch("glm4_client.requests.post")
    def test_chat_with_system_prompt(self, mock_post):
        """测试带系统提示的聊天"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_post.return_value = mock_response

        client = GLM4Client("test_api_key")
        result = client.chat(
            "User prompt", system_prompt="You are a helpful assistant."
        )

        assert result == "Response"

        # 验证调用参数
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"

    def test_chat_without_api_key(self):
        """测试无API Key聊天"""
        with patch.dict("os.environ", {}, clear=True):
            client = GLM4Client()
            with pytest.raises(ValueError, match="未设置 API Key"):
                client.chat("Hello")

    @patch("glm4_client.requests.post")
    def test_chat_api_error(self, mock_post):
        """测试API错误"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        client = GLM4Client("invalid_key")
        with pytest.raises(Exception, match="API调用失败"):
            client.chat("Hello")


class TestGLM4GenerateProjectSpec:
    """测试项目方案生成"""

    @patch("glm4_client.requests.post")
    def test_generate_project_spec_success(self, mock_post):
        """测试成功生成项目方案"""
        project_spec = {
            "name": "LED Blinker",
            "description": "A simple LED blinker circuit",
            "components": [
                {"name": "R1", "model": "10K", "package": "0805", "quantity": 1}
            ],
            "parameters": [],
            "schematic": {"components": [], "wires": [], "nets": []},
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(project_spec)}}]
        }
        mock_post.return_value = mock_response

        client = GLM4Client("test_api_key")
        result = client.generate_project_spec("Make an LED blinker")

        assert result["name"] == "LED Blinker"
        assert result["description"] == "A simple LED blinker circuit"

    @patch("glm4_client.requests.post")
    def test_generate_project_spec_with_json_code_block(self, mock_post):
        """测试从JSON代码块解析"""
        project_spec = {"name": "Test", "description": "Test"}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "```json\n" + json.dumps(project_spec) + "\n```"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = GLM4Client("test_api_key")
        result = client.generate_project_spec("test")

        assert result["name"] == "Test"

    @patch("glm4_client.requests.post")
    def test_generate_project_spec_parse_error(self, mock_post):
        """测试JSON解析失败"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Invalid JSON {["}}]
        }
        mock_post.return_value = mock_response

        client = GLM4Client("test_api_key")
        with pytest.raises(Exception, match="AI返回的格式不正确"):
            client.generate_project_spec("test")


class TestGetGLM4Client:
    """测试获取客户端实例"""

    def test_get_client_first_time(self):
        """测试首次获取客户端"""
        with patch.dict("os.environ", {"ZHIPU_API_KEY": "test_key"}):
            client = get_glm4_client()
            assert client is not None

    def test_get_client_with_param(self):
        """测试带参数获取客户端"""
        with patch.dict("os.environ", {}, clear=True):
            client1 = get_glm4_client("key1")
            client2 = get_glm4_client("key2")
            assert client1.api_key == "key1"
            assert client2.api_key == "key2"

    def test_singleton_behavior(self):
        """测试单例行为"""
        with patch.dict("os.environ", {"ZHIPU_API_KEY": "test_key"}):
            client1 = get_glm4_client()
            client2 = get_glm4_client()
            assert client1 is client2


class TestIsGLM4Available:
    """测试GLM-4可用性检查"""

    def test_available_with_key(self):
        """测试有API Key时可用"""
        import glm4_client

        glm4_client._glm4_client = None  # Reset singleton
        with patch.dict("os.environ", {"ZHIPU_API_KEY": "test_key"}):
            assert is_glm4_available() is True

    def test_not_available_without_key(self):
        """测试无API Key时不可用"""
        import glm4_client

        glm4_client._glm4_client = None  # Reset singleton
        with patch.dict("os.environ", {}, clear=True):
            # Need to also remove any existing client
            assert is_glm4_available() is False
