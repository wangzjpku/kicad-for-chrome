"""
Phase 4 测试: 网络分类器和电流计算器
"""

import pytest
import sys
from pathlib import Path

# 添加 agent 目录到路径
agent_path = Path(__file__).parent.parent / "agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from pcb.net_classifier import (
    NetClassifier,
    NetInfo,
    NetClass,
    classify_nets,
)
from pcb.current_calculator import (
    CurrentCalculator,
    calculate_trace_width,
)


class TestNetClassifier:
    """网络分类器测试"""

    def test_classify_power_net(self):
        """测试电源网络分类"""
        data = {
            "components": [],
            "nets": [
                {"name": "VCC", "nodes": [{"ref": "U1", "pin": "VCC"}]},
            ]
        }
        result = classify_nets(data)
        assert "VCC" in result
        assert result["VCC"].net_class == NetClass.POWER

    def test_classify_ground_net(self):
        """测试地网络分类"""
        data = {
            "components": [],
            "nets": [
                {"name": "GND", "nodes": [{"ref": "U1", "pin": "GND"}]},
            ]
        }
        result = classify_nets(data)
        assert "GND" in result
        assert result["GND"].net_class == NetClass.GROUND
        assert result["GND"].is_pour is True  # 地网络默认铺铜

    def test_classify_usb_diff_pair(self):
        """测试USB差分对分类"""
        data = {
            "components": [],
            "nets": [
                {"name": "USB_D+", "nodes": [{"ref": "U1", "pin": "DM+"}]},
                {"name": "USB_D-", "nodes": [{"ref": "U1", "pin": "DM-"}]},
            ]
        }
        result = classify_nets(data)
        assert result["USB_D+"].net_class == NetClass.DIFF_PAIR
        assert result["USB_D-"].net_class == NetClass.DIFF_PAIR

    def test_classify_signal_net(self):
        """测试信号网络分类"""
        data = {
            "components": [],
            "nets": [
                {"name": "NET1", "nodes": [{"ref": "U1", "pin": "PA0"}, {"ref": "R1", "pin": "1"}]},
            ]
        }
        result = classify_nets(data)
        assert "NET1" in result
        # NET1 不是电源/地/高速，应该是 UNKNOWN 或 SIGNAL
        assert result["NET1"].trace_width > 0

    def test_user_annotation_override(self):
        """测试用户标注覆盖"""
        data = {
            "components": [],
            "nets": [
                {"name": "NET1", "nodes": []},
            ]
        }
        annotations = {
            "NET1": {"class": "power", "current_ma": 2000, "is_pour": True}
        }
        result = classify_nets(data, user_annotations=annotations)
        assert result["NET1"].net_class == NetClass.POWER
        assert result["NET1"].current_ma == 2000
        assert result["NET1"].is_pour is True


class TestCurrentCalculator:
    """电流计算器测试"""

    def test_power_net_width(self):
        """测试电源网络宽度"""
        width = calculate_trace_width(100, "power")
        assert width == 0.5  # 电源默认 0.5mm

    def test_signal_net_width(self):
        """测试信号网络宽度"""
        width = calculate_trace_width(10, "signal")
        assert width == 0.15  # 信号默认 0.15mm

    def test_high_current(self):
        """测试大电流计算"""
        # 2A 电流，IPC-2221 查表约 0.5mm
        width = calculate_trace_width(2000, "power")
        assert width >= 0.5

    def test_very_high_current(self):
        """测试超大电流（超过表格范围）"""
        # 30A 电流，应该返回对应宽度（约7.62mm = 300mil）
        width = calculate_trace_width(30000, "power")
        assert width >= 5.0  # 至少最大宽度

    def test_integration(self):
        """测试网络分类和电流计算集成"""
        data = {
            "components": [],
            "nets": [
                {"name": "VCC", "nodes": []},
                {"name": "GND", "nodes": []},
            ]
        }

        classifier = NetClassifier()
        nets = classifier.classify(data)

        calculator = CurrentCalculator(nets)
        widths = calculator.calculate_all_widths({"VCC": 3000})  # VCC @ 3A

        assert widths["VCC"] > widths["GND"]  # 大电流应该更宽


class TestPhase4Integration:
    """Phase 4 集成测试"""

    def test_generate_pcb_with_classification(self):
        """测试 PCB 生成时的网络分类"""
        from routes.ai_routes import generate_pcb_layout

        schematic = {
            "components": [
                {"reference": "U1", "nets": ["VCC", "GND", "PA0"]},
                {"reference": "C1", "nets": ["VCC", "GND"]},
            ],
            "nets": [
                {"id": "n1", "name": "VCC", "nodes": []},
                {"id": "n2", "name": "GND", "nodes": []},
            ]
        }

        result = generate_pcb_layout(schematic, {"width": 50, "height": 50})

        # 应该有走线生成
        assert len(result.tracks) > 0

        # VCC/GND 走线应该更宽
        vcc_tracks = [t for t in result.tracks if t.net == "VCC"]
        if vcc_tracks:
            assert vcc_tracks[0].width >= 0.5  # 电源网络至少 0.5mm
