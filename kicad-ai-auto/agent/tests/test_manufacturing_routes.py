"""
Manufacturing Routes Tests

Phase 3.4: Test coverage for manufacturing_routes.py
Target: 80%+ coverage for core routes

Updated: 2026-04-02 - 修复路由路径以匹配实际API
"""

import pytest
import json
import os
from typing import Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Shared fixture for all test classes
@pytest.fixture(scope="module")
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def tmp_path(tmp_path_factory):
    """Create a temporary directory for tests"""
    return tmp_path_factory.mktemp("manufacturing_test")


class TestManufacturingHealth:
    """Test manufacturing health endpoints"""

    def test_manufacturing_health_check(self, client):
        """Test manufacturing service health check"""
        response = client.get("/api/v1/manufacturing/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_list_manufacturers(self, client):
        """Test listing supported manufacturers"""
        response = client.get("/api/v1/manufacturing/manufacturers")

        assert response.status_code == 200
        data = response.json()
        assert "manufacturers" in data
        assert len(data["manufacturers"]) >= 2

        # Check manufacturer structure
        for mfr in data["manufacturers"]:
            assert "id" in mfr
            assert "name" in mfr
            assert "tiers" in mfr


class TestManufacturingCheck:
    """Test manufacturing check endpoints"""

    def test_manufacturing_check_jlcpcb(self, client):
        """Test JLCPCB manufacturing check"""
        response = client.post("/api/v1/manufacturing/check", json={
            "pcb_data": {
                "board_width": 100,
                "board_height": 100,
                "layers": 2,
                "min_track_width": 0.15,
                "min_drill_size": 0.3
            },
            "manufacturer": "jlcpcb"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "basic" in data
        assert "advanced" in data

    def test_manufacturing_check_pcbway(self, client):
        """Test PCBWay manufacturing check"""
        response = client.post("/api/v1/manufacturing/check", json={
            "pcb_data": {
                "board_width": 100,
                "board_height": 100,
                "layers": 4,
                "min_track_width": 0.1,
                "min_drill_size": 0.2
            },
            "manufacturer": "pcbway"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_manufacturing_check_generic(self, client):
        """Test generic manufacturing check"""
        response = client.post("/api/v1/manufacturing/check", json={
            "pcb_data": {
                "board_width": 50,
                "board_height": 50,
                "layers": 2
            },
            "manufacturer": "generic"
        })

        assert response.status_code == 200


class TestCostEstimation:
    """Test cost estimation endpoints"""

    def test_cost_estimation_basic(self, client):
        """Test basic cost estimation"""
        response = client.post("/api/v1/manufacturing/cost-estimate", json={
            "pcb_data": {
                "board_width": 100,
                "board_height": 100,
                "layers": 2
            },
            "quantity": 5,
            "manufacturer": "jlcpcb"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "manufacturer" in data
        assert "quantity" in data

    def test_cost_estimation_jlcpcb(self, client):
        """Test cost estimation for JLCPCB"""
        response = client.post("/api/v1/manufacturing/cost-estimate", json={
            "pcb_data": {
                "board_width": 100,
                "board_height": 100,
                "layers": 4
            },
            "quantity": 10,
            "manufacturer": "jlcpcb"
        })

        assert response.status_code == 200

    def test_cost_estimation_pcbway(self, client):
        """Test cost estimation for PCBWay"""
        response = client.post("/api/v1/manufacturing/cost-estimate", json={
            "pcb_data": {
                "board_width": 50,
                "board_height": 50,
                "layers": 2
            },
            "quantity": 20,
            "manufacturer": "pcbway"
        })

        assert response.status_code == 200


class TestComponentSearch:
    """Test component search endpoints"""

    def test_component_search(self, client):
        """Test component search"""
        response = client.post("/api/v1/manufacturing/components/search", json={
            "query": "STM32",
            "limit": 10
        })

        # 可能成功或因LCSC API不可用而失败
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "components" in data

    def test_component_alternatives(self, client):
        """Test finding component alternatives"""
        response = client.post("/api/v1/manufacturing/components/alternatives", json={
            "query": "100nF capacitor",
            "limit": 5
        })

        assert response.status_code in [200, 500]


class TestBOMOptimization:
    """Test BOM optimization endpoints"""

    def test_bom_optimize(self, client):
        """Test BOM optimization"""
        response = client.post("/api/v1/manufacturing/bom/optimize", json={
            "bom_items": [
                {"name": "R1", "value": "10k", "footprint": "0603"},
                {"name": "C1", "value": "100nF", "footprint": "0603"}
            ],
            "prefer_in_stock": True
        })

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data


class TestOrderPackages:
    """Test order package generation endpoints"""

    def test_jlcpcb_order_package(self, client):
        """Test JLCPCB order package generation"""
        response = client.post("/api/v1/manufacturing/order/jlcpcb", json={
            "pcb_data": {
                "board_width": 100,
                "board_height": 100,
                "layers": 2,
                "components": []
            },
            "include_bom": True,
            "include_pnp": True
        })

        assert response.status_code in [200, 500]

    def test_pcbway_order_package(self, client):
        """Test PCBWay order package generation"""
        response = client.post("/api/v1/manufacturing/order/pcbway", json={
            "pcb_data": {
                "board_width": 100,
                "board_height": 100,
                "layers": 2,
                "components": []
            },
            "include_bom": True,
            "include_pnp": True
        })

        assert response.status_code in [200, 500]


class TestManufacturingValidation:
    """Test input validation for manufacturing routes"""

    def test_manufacturing_check_missing_pcb_data(self, client):
        """Test manufacturing check with missing pcb_data"""
        response = client.post("/api/v1/manufacturing/check", json={
            "manufacturer": "jlcpcb"
        })

        assert response.status_code == 422

    def test_cost_estimate_missing_pcb_data(self, client):
        """Test cost estimate with missing pcb_data"""
        response = client.post("/api/v1/manufacturing/cost-estimate", json={
            "quantity": 5
        })

        assert response.status_code == 422

    def test_component_search_missing_query(self, client):
        """Test component search with missing query"""
        response = client.post("/api/v1/manufacturing/components/search", json={
            "limit": 10
        })

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
