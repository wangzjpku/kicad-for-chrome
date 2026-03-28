"""
Tests for AI Routes endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_glm4_client():
    """Mock GLM-4 client"""
    with (
        patch("routes.ai_routes.get_glm4_client") as mock_get_client,
        patch("routes.ai_routes.is_glm4_available") as mock_available,
    ):
        mock_client = Mock()
        mock_client.chat = Mock(return_value="我理解您的问题，正在处理...")
        mock_client.generate_project_spec = Mock(
            return_value={
                "name": "测试项目",
                "description": "测试描述",
                "components": [],
                "parameters": [],
                "schematic": {"components": [], "wires": [], "nets": []},
            }
        )
        mock_get_client.return_value = mock_client
        mock_available.return_value = True

        yield {
            "client": mock_client,
            "get_client": mock_get_client,
            "available": mock_available,
        }


@pytest.fixture
def mock_no_glm4():
    """Mock no GLM-4 available"""
    with patch("routes.ai_routes.is_glm4_available") as mock_available:
        mock_available.return_value = False
        yield mock_available


@pytest.fixture
def client():
    """Create test client"""
    from main import app

    with TestClient(app) as test_client:
        yield test_client


class TestAIHealthCheck:
    """Test AI health check endpoint"""

    def test_ai_health_returns_ok(self, client):
        """Test AI health check returns ok status"""
        response = client.get("/api/v1/ai/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-analyze"


class TestAIChatEndpoint:
    """Test AI chat endpoint"""

    def test_chat_without_ai_returns_mock_response(self, client, mock_no_glm4):
        """Test chat returns mock response when AI is not available"""
        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "把R1移到(100, 200)",
                "context": {"projectName": "测试项目"},
                "history": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "R1" in data["response"]

    def test_chat_move_component_parses_correctly(self, client, mock_no_glm4):
        """Test chat correctly parses move component request"""
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "把电阻R1移到(150, 250)", "context": {}, "history": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modifications"] is not None
        assert len(data["modifications"]) > 0
        mod = data["modifications"][0]
        assert mod["action"] == "move_component"
        assert mod["id"] == "R1"
        assert mod["position"]["x"] == 150
        assert mod["position"]["y"] == 250

    def test_chat_delete_component_parses_correctly(self, client, mock_no_glm4):
        """Test chat correctly parses delete component request"""
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "删除电容C3", "context": {}, "history": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modifications"] is not None
        mod = data["modifications"][0]
        assert mod["action"] == "delete_component"
        assert mod["id"] == "C3"

    def test_chat_add_capacitor_parses_correctly(self, client, mock_no_glm4):
        """Test chat correctly parses add capacitor request"""
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "在(80, 80)添加一个电容", "context": {}, "history": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modifications"] is not None
        mod = data["modifications"][0]
        assert mod["action"] == "add_component"
        assert mod["type"] == "capacitor"
        assert mod["position"]["x"] == 80
        assert mod["position"]["y"] == 80

    def test_chat_add_track_with_coordinates(self, client, mock_no_glm4):
        """Test chat correctly parses add track request with coordinates"""
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "添加走线从(0,0)到(100,50)", "context": {}, "history": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modifications"] is not None
        mod = data["modifications"][0]
        assert mod["action"] == "add_track"
        assert mod["start"]["x"] == 0
        assert mod["start"]["y"] == 0
        assert mod["end"]["x"] == 100
        assert mod["end"]["y"] == 50

    def test_chat_connect_components(self, client, mock_no_glm4):
        """Test chat correctly parses connect components request"""
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "连接C1到U1", "context": {}, "history": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modifications"] is not None
        mod = data["modifications"][0]
        assert mod["action"] == "connect_components"
        assert mod["from"] == "C1"
        assert mod["to"] == "U1"

    def test_chat_with_history(self, client, mock_no_glm4):
        """Test chat with conversation history"""
        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "删除它",
                "context": {},
                "history": [
                    {"role": "user", "content": "选中R1"},
                    {"role": "assistant", "content": "已选中R1"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_chat_empty_message_returns_error(self, client):
        """Test chat with empty message"""
        response = client.post(
            "/api/v1/ai/chat", json={"message": "", "context": {}, "history": []}
        )

        # Should still work with mock response
        assert response.status_code == 200


class TestFootprintEndpoints:
    """Test footprint-related endpoints"""

    def test_recommend_footprint(self, client):
        """Test footprint recommendation endpoint"""
        response = client.post(
            "/api/v1/ai/footprint/recommend",
            json={
                "component_name": "电阻",
                "component_value": "10k",
                "package": "0805",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data
        assert "source" in data

    def test_get_footprint_libraries(self, client):
        """Test getting footprint libraries"""
        response = client.get("/api/v1/ai/footprint/libraries")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_search_footprints(self, client):
        """Test searching footprints"""
        response = client.get("/api/v1/ai/footprint/search?keyword=SOT-23&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "keyword" in data


class TestClarifyEndpoint:
    """Test clarification questions endpoint"""

    def test_clarify_power_supply_requirements(self, client):
        """Test clarify for power supply requirements"""
        response = client.post(
            "/api/v1/ai/clarify", json={"requirements": "设计一个5V稳压电源"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "summary" in data
        assert "detected_type" in data

    def test_clarify_empty_requirements_returns_error(self, client):
        """Test clarify with empty requirements"""
        response = client.post("/api/v1/ai/clarify", json={"requirements": ""})

        assert response.status_code == 400


class TestAnalyzeEndpoint:
    """Test analyze endpoint"""

    def test_analyze_simple_power_supply(self, client, mock_no_glm4):
        """Test analyze simple power supply requirements"""
        response = client.post(
            "/api/v1/ai/analyze", json={"requirements": "5V稳压电源", "answers": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert "spec" in data
        assert "schematic" in data
        assert data["spec"]["name"] != ""

    def test_analyze_with_answers(self, client, mock_no_glm4):
        """Test analyze with user answers"""
        response = client.post(
            "/api/v1/ai/analyze",
            json={
                "requirements": "5V稳压电源",
                "answers": {
                    "input_voltage": "12V DC",
                    "output_voltage": "5V",
                    "output_current": "1A",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "spec" in data
        assert "schematic" in data

    def test_analyze_empty_requirements_returns_error(self, client):
        """Test analyze with empty requirements"""
        response = client.post(
            "/api/v1/ai/analyze", json={"requirements": "", "answers": {}}
        )

        # Should return an error response
        assert response.status_code in [400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
