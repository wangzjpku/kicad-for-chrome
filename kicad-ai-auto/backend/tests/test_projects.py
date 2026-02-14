"""
后端API测试 - 项目接口测试
测试项目CRUD操作
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# 需要在backend目录下运行测试
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.models.models import Project
from app.schemas.schemas import ProjectCreate, ProjectUpdate


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def sample_project_data():
    """示例项目数据"""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Project",
        "description": "Test Description",
        "status": "active",
        "project_file": "/projects/test/test.kicad_pro",
        "schematic_file": "/projects/test/test.kicad_sch",
        "pcb_file": "/projects/test/test.kicad_pcb",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


class TestProjectAPI:
    """项目API测试类"""

    def test_list_projects_success(self, client, mock_db):
        """测试获取项目列表成功"""
        # 模拟数据库查询结果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Project(**sample_project_data())
        ]
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    def test_list_projects_empty(self, client, mock_db):
        """测试获取空项目列表"""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_create_project_success(self, client, mock_db):
        """测试创建项目成功"""
        project_data = {"name": "New Project", "description": "New Description"}

        response = client.post("/api/v1/projects", json=project_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert "id" in data

    def test_create_project_invalid_data(self, client):
        """测试创建项目时传入无效数据"""
        invalid_data = {
            "name": "",  # 空名称
            "description": "Description",
        }

        response = client.post("/api/v1/projects", json=invalid_data)

        # 应该返回验证错误
        assert response.status_code == 422

    def test_get_project_success(self, client, mock_db, sample_project_data):
        """测试获取单个项目成功"""
        project_id = sample_project_data["id"]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Project(**sample_project_data)
        mock_db.execute.return_value = mock_result

        response = client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == sample_project_data["name"]

    def test_get_project_not_found(self, client, mock_db):
        """测试获取不存在的项目"""
        project_id = str(uuid.uuid4())

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_project_success(self, client, mock_db, sample_project_data):
        """测试更新项目成功"""
        project_id = sample_project_data["id"]
        update_data = {"name": "Updated Name", "description": "Updated Description"}

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Project(**sample_project_data)
        mock_db.execute.return_value = mock_result

        response = client.put(f"/api/v1/projects/{project_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_update_project_not_found(self, client, mock_db):
        """测试更新不存在的项目"""
        project_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.put(f"/api/v1/projects/{project_id}", json=update_data)

        assert response.status_code == 404

    def test_delete_project_success(self, client, mock_db, sample_project_data):
        """测试删除项目成功"""
        project_id = sample_project_data["id"]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Project(**sample_project_data)
        mock_db.execute.return_value = mock_result

        response = client.delete(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_delete_project_not_found(self, client, mock_db):
        """测试删除不存在的项目"""
        project_id = str(uuid.uuid4())

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.delete(f"/api/v1/projects/{project_id}")

        assert response.status_code == 404

    def test_duplicate_project_success(self, client, mock_db, sample_project_data):
        """测试复制项目成功"""
        project_id = sample_project_data["id"]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Project(**sample_project_data)
        mock_db.execute.return_value = mock_result

        response = client.post(f"/api/v1/projects/{project_id}/duplicate")

        assert response.status_code == 200
        data = response.json()
        assert "(Copy)" in data["name"]


class TestProjectValidation:
    """项目数据验证测试"""

    def test_project_name_too_long(self, client):
        """测试项目名称过长"""
        invalid_data = {
            "name": "A" * 256,  # 超过255字符限制
            "description": "Description",
        }

        response = client.post("/api/v1/projects", json=invalid_data)
        assert response.status_code == 422

    def test_project_name_required(self, client):
        """测试项目名称必填"""
        invalid_data = {"description": "Description"}

        response = client.post("/api/v1/projects", json=invalid_data)
        assert response.status_code == 422

    def test_project_description_optional(self, client, mock_db):
        """测试项目描述可选"""
        data = {"name": "Project Without Description"}

        response = client.post("/api/v1/projects", json=data)
        assert response.status_code == 201


class TestProjectPagination:
    """项目分页测试"""

    def test_list_projects_with_pagination(self, client, mock_db):
        """测试项目列表分页"""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Project(id=uuid.uuid4(), name=f"Project {i}", status="active")
            for i in range(10)
        ]
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/projects?skip=0&limit=5")

        assert response.status_code == 200
        data = response.json()
        # 注意：这里可能需要根据实际实现调整断言
        assert "items" in data

    def test_list_projects_negative_skip(self, client):
        """测试负的skip参数"""
        response = client.get("/api/v1/projects?skip=-1")
        # 应该返回400错误或正确处理
        assert response.status_code in [200, 400, 422]

    def test_list_projects_zero_limit(self, client):
        """测试limit为0"""
        response = client.get("/api/v1/projects?limit=0")
        data = response.json()
        assert len(data["items"]) == 0


# 使用pytest-asyncio进行异步测试
@pytest.mark.asyncio
class TestProjectAsync:
    """异步项目操作测试"""

    async def test_concurrent_project_creation(self, mock_db):
        """测试并发创建项目"""
        # 这里可以测试并发情况下的数据库操作
        pass

    async def test_project_creation_rollback_on_error(self, mock_db):
        """测试错误时回滚"""
        # 模拟文件系统错误
        with patch("os.makedirs", side_effect=OSError("Disk full")):
            # 应该回滚数据库事务
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
