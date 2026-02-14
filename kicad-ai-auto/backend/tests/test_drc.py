"""
DRC服务测试
测试设计规则检查功能
"""

import pytest
import math
from unittest.mock import Mock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.api.v1.endpoints.drc import (
    calculate_distance,
    calculate_track_length,
    run_drc_check,
    DRC_RULES,
)


class TestDistanceCalculation:
    """距离计算测试"""

    def test_calculate_distance_same_point(self):
        """测试相同点的距离为0"""
        p1 = {"x": 0, "y": 0}
        p2 = {"x": 0, "y": 0}
        assert calculate_distance(p1, p2) == 0

    def test_calculate_distance_horizontal(self):
        """测试水平距离"""
        p1 = {"x": 0, "y": 0}
        p2 = {"x": 10, "y": 0}
        assert calculate_distance(p1, p2) == 10

    def test_calculate_distance_vertical(self):
        """测试垂直距离"""
        p1 = {"x": 0, "y": 0}
        p2 = {"x": 0, "y": 10}
        assert calculate_distance(p1, p2) == 10

    def test_calculate_distance_diagonal(self):
        """测试对角线距离"""
        p1 = {"x": 0, "y": 0}
        p2 = {"x": 3, "y": 4}
        assert calculate_distance(p1, p2) == 5  # 3-4-5直角三角形

    def test_calculate_distance_negative_coordinates(self):
        """测试负坐标"""
        p1 = {"x": -5, "y": -5}
        p2 = {"x": 5, "y": 5}
        expected = math.sqrt(10**2 + 10**2)
        assert abs(calculate_distance(p1, p2) - expected) < 0.001


class TestTrackLengthCalculation:
    """走线长度计算测试"""

    def test_track_length_single_point(self):
        """测试单点长度为0"""
        points = [{"x": 0, "y": 0}]
        assert calculate_track_length(points) == 0

    def test_track_length_two_points(self):
        """测试两点直线"""
        points = [{"x": 0, "y": 0}, {"x": 10, "y": 0}]
        assert calculate_track_length(points) == 10

    def test_track_length_multiple_points(self):
        """测试多点路径"""
        points = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
        ]
        assert calculate_track_length(points) == 20

    def test_track_length_empty(self):
        """测试空列表"""
        points = []
        assert calculate_track_length(points) == 0


class TestDRCRules:
    """DRC规则测试"""

    def test_drc_rules_exist(self):
        """测试DRC规则存在"""
        assert "minTrackWidth" in DRC_RULES
        assert "minViaSize" in DRC_RULES
        assert "minClearance" in DRC_RULES

    def test_drc_rules_values(self):
        """测试DRC规则值合理"""
        assert DRC_RULES["minTrackWidth"] > 0
        assert DRC_RULES["minViaSize"] > 0
        assert DRC_RULES["minClearance"] > 0
        assert DRC_RULES["minViaSize"] > DRC_RULES["minViaDrill"]


class TestDRCCheck:
    """DRC检查功能测试"""

    def test_drc_check_empty_pcb(self):
        """测试空PCB检查通过"""
        pcb_data = {"footprints": [], "tracks": [], "vias": []}
        result = run_drc_check(pcb_data)
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    def test_drc_check_valid_track(self):
        """测试有效走线"""
        pcb_data = {
            "footprints": [],
            "tracks": [
                {
                    "id": "track-001",
                    "width": 0.2,  # 大于minTrackWidth
                    "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}],
                }
            ],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        assert len(result["errors"]) == 0

    def test_drc_check_too_narrow_track(self):
        """测试线宽不足的走线"""
        pcb_data = {
            "footprints": [],
            "tracks": [
                {
                    "id": "track-001",
                    "width": 0.05,  # 小于minTrackWidth
                    "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}],
                }
            ],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        assert len(result["errors"]) > 0
        assert result["errors"][0]["type"] == "track_width"

    def test_drc_check_valid_via(self):
        """测试有效过孔"""
        pcb_data = {
            "footprints": [],
            "tracks": [],
            "vias": [
                {
                    "id": "via-001",
                    "size": 0.8,  # 大于minViaSize
                    "drill": 0.4,  # 大于minViaDrill
                    "position": {"x": 10, "y": 10},
                }
            ],
        }
        result = run_drc_check(pcb_data)
        via_errors = [e for e in result["errors"] if "via" in e["type"]]
        assert len(via_errors) == 0

    def test_drc_check_too_small_via(self):
        """测试尺寸不足的过孔"""
        pcb_data = {
            "footprints": [],
            "tracks": [],
            "vias": [
                {
                    "id": "via-001",
                    "size": 0.3,  # 小于minViaSize
                    "drill": 0.1,  # 小于minViaDrill
                    "position": {"x": 10, "y": 10},
                }
            ],
        }
        result = run_drc_check(pcb_data)
        via_errors = [e for e in result["errors"] if "via" in e["type"]]
        assert len(via_errors) == 2  # size和drill两个错误

    def test_drc_check_clearance_violation(self):
        """测试间距违规"""
        pcb_data = {
            "footprints": [
                {"id": "fp-001", "reference": "R1", "position": {"x": 0, "y": 0}},
                {
                    "id": "fp-002",
                    "reference": "R2",
                    "position": {"x": 0.05, "y": 0},  # 太近
                },
            ],
            "tracks": [],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        clearance_errors = [e for e in result["errors"] if e["type"] == "clearance"]
        assert len(clearance_errors) > 0

    def test_drc_check_valid_clearance(self):
        """测试有效间距"""
        pcb_data = {
            "footprints": [
                {"id": "fp-001", "reference": "R1", "position": {"x": 0, "y": 0}},
                {
                    "id": "fp-002",
                    "reference": "R2",
                    "position": {"x": 1.0, "y": 0},  # 足够远
                },
            ],
            "tracks": [],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        clearance_errors = [e for e in result["errors"] if e["type"] == "clearance"]
        assert len(clearance_errors) == 0

    def test_drc_check_long_track_warning(self):
        """测试长走线警告"""
        pcb_data = {
            "footprints": [],
            "tracks": [
                {
                    "id": "track-001",
                    "width": 0.2,
                    "points": [{"x": 0, "y": 0}, {"x": 200, "y": 0}],  # 超长
                }
            ],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        length_warnings = [w for w in result["warnings"] if w["type"] == "track_length"]
        assert len(length_warnings) > 0


class TestDRCErrorMessages:
    """DRC错误消息测试"""

    def test_drc_error_contains_position(self):
        """测试错误包含位置信息"""
        pcb_data = {
            "footprints": [],
            "tracks": [
                {"id": "track-001", "width": 0.05, "points": [{"x": 5, "y": 10}]}
            ],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        if result["errors"]:
            error = result["errors"][0]
            assert "position" in error
            assert "x" in error["position"]
            assert "y" in error["position"]

    def test_drc_error_contains_item_id(self):
        """测试错误包含项目ID"""
        pcb_data = {
            "footprints": [],
            "tracks": [
                {"id": "track-001", "width": 0.05, "points": [{"x": 0, "y": 0}]}
            ],
            "vias": [],
        }
        result = run_drc_check(pcb_data)
        if result["errors"]:
            error = result["errors"][0]
            assert "itemId" in error
            assert error["itemId"] == "track-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
