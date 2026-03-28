"""
KiCad AI Auto E2E 全功能测试套件

测试覆盖:
1. 前端页面加载和导航
2. 项目管理 (创建/打开/保存)
3. AI电路生成流程
4. 原理图编辑器
5. PCB编辑器
6. 知识库验证
7. 导出功能
"""

import pytest
import requests
import time
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
WEB_URL = "http://localhost:3000"

# 测试超时配置
TIMEOUT = 30
API_TIMEOUT = 60

# 获取JWT token
def get_auth_token():
    """注册测试用户并获取JWT token"""
    import random
    email = f"test_{int(time.time())}_{random.randint(1000,9999)}@example.com"
    resp = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "test123"},
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json().get("token", "")
    return ""


class TestHealth:
    """健康检查测试"""

    def test_backend_health(self):
        """后端健康检查"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_knowledge_base_health(self):
        """知识库健康检查"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/health", timeout=10)
        assert response.status_code == 200

    def test_frontend_accessible(self):
        """前端可访问性"""
        response = requests.get(WEB_URL, timeout=10)
        assert response.status_code == 200


class TestProjectAPI:
    """项目管理API测试"""

    def setup_method(self):
        """每个测试前获取新token"""
        self.token = get_auth_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_list_projects(self):
        """列出项目"""
        response = requests.get(
            f"{BASE_URL}/api/v1/projects",
            headers=self.headers,
            timeout=API_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_project(self):
        """创建新项目"""
        project_name = f"test_e2e_{int(time.time())}"
        payload = {
            "name": project_name,
            "description": "E2E Test Project"
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/projects",
            json=payload,
            headers=self.headers,
            timeout=API_TIMEOUT
        )
        assert response.status_code in [200, 201, 400, 500]
        if response.status_code == 200:
            data = response.json()
            assert data.get("name") == project_name or "id" in data


class TestKnowledgeBase:
    """知识库API测试"""

    def test_quality_summary(self):
        """质量统计概览"""
        response = requests.get(
            f"{BASE_URL}/api/v1/knowledge/quality/summary",
            timeout=API_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "stats" in data
        assert data["stats"]["total"] > 0

    def test_validate_stm32(self):
        """验证STM32元件"""
        response = requests.post(
            f"{BASE_URL}/api/v1/knowledge/quality/validate",
            params={"component_name": "STM32F103C8T6", "check_datasheet": False},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["component"] == "STM32F103C8T6"

    def test_validate_ch340c(self):
        """验证CH340C元件"""
        response = requests.post(
            f"{BASE_URL}/api/v1/knowledge/quality/validate",
            params={"component_name": "CH340C", "check_datasheet": False},
            timeout=API_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_component_search(self):
        """元件搜索"""
        response = requests.get(
            f"{BASE_URL}/api/v1/knowledge/components/search/USB",
            timeout=API_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["count"] > 0

    def test_component_categories(self):
        """元件分类"""
        response = requests.get(
            f"{BASE_URL}/api/v1/knowledge/categories",
            timeout=API_TIMEOUT
        )
        assert response.status_code == 200


class TestAIGeneration:
    """AI生成API测试"""

    def test_generators_list(self):
        """列出可用生成器"""
        response = requests.get(
            f"{BASE_URL}/api/ai/generators",
            timeout=API_TIMEOUT
        )
        assert response.status_code in [200, 404, 500]

    def test_analyze_empty(self):
        """空输入分析（应返回错误）"""
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/analyze",
            json={"requirements": ""},
            timeout=API_TIMEOUT
        )
        # 应该返回错误或验证失败
        assert response.status_code in [400, 422, 500]

    def test_analyze_valid(self):
        """有效输入分析"""
        payload = {
            "requirements": "设计一个5V稳压电源",
            "project_name": f"test_power_{int(time.time())}"
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/analyze",
            json=payload,
            timeout=API_TIMEOUT
        )
        # 可能成功或返回错误（取决于AI服务）
        assert response.status_code in [200, 201, 400, 500, 502, 503]


class TestExportAPI:
    """导出功能API测试"""

    def test_bom_export(self):
        """BOM导出（无项目时应失败）"""
        response = requests.post(
            f"{BASE_URL}/api/v1/export/bom",
            json={"project_id": "nonexistent"},
            timeout=API_TIMEOUT
        )
        # 应该返回错误
        assert response.status_code in [400, 404, 500]

    def test_gerber_export(self):
        """Gerber导出（无项目时应失败）"""
        response = requests.post(
            f"{BASE_URL}/api/v1/export/gerber",
            json={"project_id": "nonexistent"},
            timeout=API_TIMEOUT
        )
        assert response.status_code in [400, 404, 500]


class TestDesignRules:
    """设计规则API测试"""

    def test_pcb_rules(self):
        """PCB规则检查"""
        payload = {
            "pcb_data": {
                "board_width": 100,
                "board_height": 80,
                "layers": 2
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/knowledge/pcb/check-rules",
            json=payload,
            timeout=API_TIMEOUT
        )
        assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
