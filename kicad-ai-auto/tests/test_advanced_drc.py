"""
Advanced DRC Engine 测试用例

测试 Phase 3 扩展DRC规则：
1. 规则初始化 (30+条)
2. 间距检查
3. 尺寸检查
4. 网络类规则
5. 差分对检查
6. 制造约束
7. 高速信号检查
"""

import pytest
import sys
from pathlib import Path

# 添加 agent 目录到路径
agent_path = Path(__file__).parent.parent / "agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from drc.advanced_drc import (
    AdvancedDRCEngine,
    DRCRule,
    NetClass,
    RuleType,
    RuleSeverity,
    PCBComponent,
    PCBTrack,
    PCBVia,
    PCBPad,
    create_jlcpcb_drc,
)


class TestDRCEngineInitialization:
    """测试DRC引擎初始化"""

    def test_standard_jlcpcb_init(self):
        """测试标准JLCPCB DRC引擎"""
        engine = create_jlcpcb_drc(level="standard")

        assert engine.manufacturer == "jlcpcb"
        assert engine.level == "standard"
        assert len(engine.rules) >= 30  # 至少30条规则

    def test_advanced_jlcpcb_init(self):
        """测试高级JLCPCB DRC引擎"""
        engine = create_jlcpcb_drc(level="advanced")

        assert engine.level == "advanced"
        # 高级工艺应该允许更小的线宽
        assert engine.capabilities["min_trace_width"] <= 0.12

    def test_rule_types_present(self):
        """测试所有规则类型都存在"""
        engine = create_jlcpcb_drc()

        rule_types = set(r.rule_type for r in engine.rules)
        assert RuleType.CLEARANCE in rule_types
        assert RuleType.TRACK_WIDTH in rule_types
        assert RuleType.VIA_SIZE in rule_types
        assert RuleType.DIFFERENTIAL_PAIR in rule_types
        assert RuleType.MANUFACTURING in rule_types

    def test_net_classes_initialized(self):
        """测试网络类已初始化"""
        engine = create_jlcpcb_drc()

        assert "Default" in engine.net_classes
        assert "Power" in engine.net_classes
        assert "Signal" in engine.net_classes
        assert "HighSpeed" in engine.net_classes
        assert "RF" in engine.net_classes

    def test_power_net_class_values(self):
        """测试电源网络类参数"""
        engine = create_jlcpcb_drc()
        power = engine.net_classes["Power"]

        assert power.track_width == 0.50
        assert power.clearance == 0.30
        assert power.via_diameter == 0.80


class TestTrackChecking:
    """测试走线检查"""

    def test_track_width_too_small(self):
        """测试线宽过小的检测"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [
                {"net": "VCC", "layer": "F.Cu", "width": 0.10, "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]}
            ],
            "components": [],
            "vias": [],
            "nets": []
        }

        result = engine.check(pcb_data)

        width_violations = [v for v in result.violations if v.rule_type == RuleType.TRACK_WIDTH]
        assert len(width_violations) >= 1

    def test_track_width_ok(self):
        """测试正常线宽通过"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [
                {"net": "VCC", "layer": "F.Cu", "width": 0.30, "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]}
            ],
            "components": [],
            "vias": [],
            "nets": []
        }

        result = engine.check(pcb_data)

        width_violations = [v for v in result.violations if v.rule_type == RuleType.TRACK_WIDTH]
        assert len(width_violations) == 0


class TestViaChecking:
    """测试过孔检查"""

    def test_via_drill_too_small(self):
        """测试钻孔过小检测"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [
                {"x": 10, "y": 10, "net": "VCC", "outer_diameter": 0.6, "drill_diameter": 0.20}
            ],
            "nets": []
        }

        result = engine.check(pcb_data)

        via_violations = [v for v in result.violations if v.rule_type == RuleType.VIA_SIZE]
        assert len(via_violations) >= 1

    def test_annular_ring_too_small(self):
        """测试焊环过小检测"""
        engine = create_jlcpcb_drc()

        # 外径0.6，钻孔0.5，焊环只有0.05
        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [
                {"x": 10, "y": 10, "net": "VCC", "outer_diameter": 0.6, "drill_diameter": 0.5}
            ],
            "nets": []
        }

        result = engine.check(pcb_data)

        annular_violations = [v for v in result.violations if v.rule_name == "min_annular_ring"]
        assert len(annular_violations) >= 1


class TestClearanceChecking:
    """测试间距检查"""

    def test_via_to_via_clearance(self):
        """测试过孔间距检测"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [
                {"x": 10, "y": 10, "net": "VCC", "outer_diameter": 0.8, "drill_diameter": 0.4},
                {"x": 10.1, "y": 10, "net": "GND", "outer_diameter": 0.8, "drill_diameter": 0.4},  # 太近了
            ],
            "nets": [{"name": "VCC"}, {"name": "GND"}]
        }

        result = engine.check(pcb_data)

        clearance_violations = [v for v in result.violations if v.rule_name == "via_to_via"]
        assert len(clearance_violations) >= 1


class TestNetClassRules:
    """测试网络类规则"""

    def test_power_net_width_check(self):
        """测试电源网络走线宽度检查"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [
                {"net": "VCC", "layer": "F.Cu", "width": 0.20, "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]}
            ],
            "components": [],
            "vias": [],
            "nets": [{"name": "VCC", "class": "Power"}]  # 电源类要求0.50mm
        }

        result = engine.check(pcb_data)

        net_class_violations = [v for v in result.violations if v.rule_type == RuleType.NET_CLASS]
        assert len(net_class_violations) >= 1

    def test_signal_net_ok(self):
        """测试信号网络正常"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [
                {"net": "SIGNAL", "layer": "F.Cu", "width": 0.25, "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]}
            ],
            "components": [],
            "vias": [],
            "nets": [{"name": "SIGNAL", "class": "Signal"}]  # 信号类要求0.20mm
        }

        result = engine.check(pcb_data)

        net_class_violations = [v for v in result.violations if v.rule_type == RuleType.NET_CLASS]
        assert len(net_class_violations) == 0


class TestDifferentialPairs:
    """测试差分对检查"""

    def test_diff_pair_length_mismatch(self):
        """测试差分对长度不匹配检测"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [],
            "nets": [],
            "differential_pairs": [
                {"positive": "DP+", "negative": "DP-", "positive_length": 50.0, "negative_length": 52.0}
            ]
        }

        result = engine.check(pcb_data)

        diff_violations = [v for v in result.violations if v.rule_type == RuleType.DIFFERENTIAL_PAIR]
        assert len(diff_violations) >= 1


class TestManufacturingRules:
    """测试制造规则"""

    def test_board_edge_clearance(self):
        """测试板边间距检测"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [],
            "components": [
                {"reference": "U1", "footprint": "QFN-48", "position": {"x": 5, "y": 5}, "width": 10, "height": 10}
            ],
            "vias": [],
            "nets": [],
            "board": {"width": 100, "height": 80, "thickness": 1.6}
        }

        result = engine.check(pcb_data)

        edge_violations = [v for v in result.violations if v.rule_name == "board_edge_clearance"]
        # U1在x=5，宽度10，左边缘在0，应该触发边距警告
        assert len(edge_violations) >= 1

    def test_aspect_ratio(self):
        """测试板厚孔径比检测"""
        engine = create_jlcpcb_drc()

        # 1.6mm板厚，0.15mm钻孔，孔径比超过10:1
        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [
                {"x": 10, "y": 10, "net": "VCC", "outer_diameter": 0.5, "drill_diameter": 0.15}
            ],
            "nets": [],
            "board": {"width": 100, "height": 80, "thickness": 1.6}
        }

        result = engine.check(pcb_data)

        aspect_violations = [v for v in result.violations if v.rule_name == "aspect_ratio"]
        assert len(aspect_violations) >= 1


class TestHighSpeedRules:
    """测试高速信号规则"""

    def test_max_via_count(self):
        """测试高速信号过孔数量检测"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [
                {"x": 10, "y": 10, "net": "HS_SIGNAL", "outer_diameter": 0.6, "drill_diameter": 0.3},
                {"x": 20, "y": 20, "net": "HS_SIGNAL", "outer_diameter": 0.6, "drill_diameter": 0.3},
                {"x": 30, "y": 30, "net": "HS_SIGNAL", "outer_diameter": 0.6, "drill_diameter": 0.3},
            ],
            "nets": [{"name": "HS_SIGNAL", "class": "HighSpeed"}]
        }

        result = engine.check(pcb_data)

        hs_violations = [v for v in result.violations if v.rule_name == "max_via_count"]
        assert len(hs_violations) >= 1


class TestDRCResult:
    """测试结果数据"""

    def test_result_statistics(self):
        """测试结果统计"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [
                {"net": "VCC", "layer": "F.Cu", "width": 0.05, "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]}
            ],
            "components": [
                {"reference": "U1", "footprint": "QFN-48", "position": {"x": 5, "y": 5}, "width": 10, "height": 10}
            ],
            "vias": [
                {"x": 10, "y": 10, "net": "VCC", "outer_diameter": 0.4, "drill_diameter": 0.2}
            ],
            "nets": [],
            "board": {"width": 100, "height": 80}
        }

        result = engine.check(pcb_data)

        assert result.error_count >= 1
        assert result.duration_ms > 0
        assert result.statistics["tracks_checked"] == 1
        assert result.statistics["components_checked"] == 1

    def test_empty_pcb_passes(self):
        """测试空PCB通过检查"""
        engine = create_jlcpcb_drc()

        pcb_data = {
            "tracks": [],
            "components": [],
            "vias": [],
            "nets": []
        }

        result = engine.check(pcb_data)

        assert result.passed is True
        assert result.error_count == 0


class TestRuleManagement:
    """测试规则管理"""

    def test_add_custom_rule(self):
        """测试添加自定义规则"""
        engine = create_jlcpcb_drc()

        initial_count = len(engine.rules)

        custom_rule = DRCRule(
            name="custom_clearance",
            rule_type=RuleType.CLEARANCE,
            value=1.0,
            description="自定义间距规则"
        )

        engine.add_custom_rule(custom_rule)

        assert len(engine.rules) == initial_count + 1

    def test_get_rules_summary(self):
        """测试获取规则摘要"""
        engine = create_jlcpcb_drc()

        summary = engine.get_rules_summary()

        assert summary["total_rules"] >= 30
        assert "by_type" in summary
        assert "by_severity" in summary
        assert "net_classes" in summary


class TestPCBDataClasses:
    """测试PCB数据类"""

    def test_track_length_calculation(self):
        """测试走线长度计算"""
        track = PCBTrack(
            net="TEST",
            layer="F.Cu",
            width=0.25,
            points=[
                {"x": 0, "y": 0},
                {"x": 3, "y": 4}  # 3-4-5 直角三角形，斜边5
            ]
        )

        assert track.length() == 5.0

    def test_via_creation(self):
        """测试过孔创建"""
        via = PCBVia(
            x=10,
            y=20,
            net="VCC",
            outer_diameter=0.8,
            drill_diameter=0.4
        )

        assert via.x == 10
        assert via.y == 20
        assert via.net == "VCC"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
