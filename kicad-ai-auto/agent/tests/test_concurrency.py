"""
并发压力测试 - 验证锁保护是否生效
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


class TestConcurrency:
    """并发测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with (
            patch("main.KiCadController") as MockController,
            patch("main.StateMonitor"),
            patch("main.ExportManager"),
        ):
            mock_controller = MagicMock()
            mock_controller.is_running.return_value = True
            MockController.return_value = mock_controller

            with TestClient(app) as client:
                yield client

    def test_concurrent_project_creation(self, client):
        """测试并发创建项目 - 验证锁保护"""
        import threading
        import time

        results = []
        errors = []

        def create_project(project_name):
            """创建项目的辅助函数"""
            try:
                response = client.post(
                    "/api/v1/projects",
                    json={
                        "name": project_name,
                        "description": "Test project",
                        "schematicData": {
                            "components": [
                                {
                                    "id": "R1",
                                    "reference": "R1",
                                    "model": "1K",
                                    "footprint": "Resistor_SMD:R_0603_1608Metric",
                                }
                            ]
                        },
                    },
                )
                results.append(
                    {
                        "name": project_name,
                        "status": response.status_code,
                        "data": response.json()
                        if response.status_code == 201
                        else None,
                    }
                )
            except Exception as e:
                errors.append({"name": project_name, "error": str(e)})

        # 并发创建10个项目
        threads = []
        for i in range(10):
            t = threading.Thread(
                target=create_project, args=(f"ConcurrentTestProject_{i}",)
            )
            threads.append(t)

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发创建项目时出现错误: {errors}"
        assert len(results) == 10, f"应该有10个成功结果，实际有{len(results)}个"

        # 验证所有项目都成功创建
        success_count = sum(1 for r in results if r["status"] == 201)
        assert success_count == 10, f"应该有10个成功创建，实际{success_count}个"

        print(f"✅ 并发创建项目测试通过: 成功创建{success_count}个项目")

    def test_concurrent_project_reads(self, client):
        """测试并发读取项目 - 验证读锁保护"""
        import threading

        # 首先创建一个测试项目
        response = client.post(
            "/api/v1/projects",
            json={"name": "ReadTestProject", "description": "Test project for reading"},
        )
        assert response.status_code == 201
        project_id = response.json()["id"]

        results = []
        errors = []

        def read_project():
            """读取项目的辅助函数"""
            try:
                response = client.get(f"/api/v1/projects/{project_id}")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # 并发读取50次
        threads = []
        for i in range(50):
            t = threading.Thread(target=read_project)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发读取项目时出现错误: {errors}"
        assert len(results) == 50, f"应该有50个结果，实际有{len(results)}个"

        # 验证所有读取都成功
        success_count = sum(1 for r in results if r == 200)
        assert success_count == 50, f"应该有50个成功读取，实际{success_count}个"

        print(f"✅ 并发读取项目测试通过: 成功读取{success_count}次")

    def test_concurrent_pcb_operations(self, client):
        """测试并发PCB操作 - 验证PCB数据锁保护"""
        import threading

        # 首先创建项目和PCB数据
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "PCBTestProject",
                "description": "Test project for PCB operations",
                "pcbData": {"footprints": [], "tracks": [], "vias": []},
            },
        )
        assert response.status_code == 201
        project_id = response.json()["id"]

        results = []
        errors = []

        def create_footprint(index):
            """创建封装的辅助函数"""
            try:
                response = client.post(
                    f"/api/v1/projects/{project_id}/pcb/items/footprint",
                    json={
                        "reference": f"R{index}",
                        "value": "1K",
                        "libraryName": "Resistor_SMD",
                        "footprintName": "R_0603_1608Metric",
                        "position": {"x": index * 10, "y": index * 10},
                    },
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # 并发创建20个封装
        threads = []
        for i in range(20):
            t = threading.Thread(target=create_footprint, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发创建封装时出现错误: {errors}"
        assert len(results) == 20, f"应该有20个结果，实际有{len(results)}个"

        success_count = sum(1 for r in results if r == 200)
        assert success_count == 20, f"应该有20个成功创建，实际{success_count}个"

        print(f"✅ 并发PCB操作测试通过: 成功创建{success_count}个封装")


class TestRaceConditionPrevention:
    """竞态条件防护测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with (
            patch("main.KiCadController") as MockController,
            patch("main.StateMonitor"),
            patch("main.ExportManager"),
        ):
            mock_controller = MagicMock()
            mock_controller.is_running.return_value = True
            MockController.return_value = mock_controller

            with TestClient(app) as client:
                yield client

    def test_no_duplicate_projects(self, client):
        """测试并发创建同名项目时不会重复 - 验证锁保护"""
        import threading
        import time

        results = []

        def create_same_project():
            """创建同名项目的辅助函数"""
            try:
                response = client.post(
                    "/api/v1/projects",
                    json={"name": "DuplicateTestProject", "description": "Test"},
                )
                results.append(response.status_code)
            except Exception as e:
                results.append(f"error: {e}")

        # 并发创建同名项目10次
        threads = []
        for i in range(10):
            t = threading.Thread(target=create_same_project)
            threads.append(t)

        # 几乎同时启动
        for t in threads:
            t.start()
            time.sleep(0.001)  # 微小延迟模拟真实场景

        for t in threads:
            t.join()

        # 统计结果
        success_count = sum(1 for r in results if r == 201)
        conflict_count = sum(1 for r in results if r == 409)

        # 验证：只有一个能成功创建，其他都应该返回409冲突
        assert success_count == 1, f"应该只有1个项目创建成功，实际{success_count}个"
        assert conflict_count == 9, f"应该有9个冲突，实际{conflict_count}个"

        print(f"✅ 重复项目防护测试通过: 1个成功, {conflict_count}个冲突")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
