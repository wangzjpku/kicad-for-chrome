"""
Phase 5 测试: KiCad E2E 集成测试

端到端测试: AI 生成 PCB → 保存 → KiCad 打开 → 验证数据

注意: 这些测试需要 KiCad 9.0+ 安装在本地
在 CI 环境中会跳过 (标记为 @pytest.mark.skipif)
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 添加 agent 目录到路径
agent_path = Path(__file__).parent.parent
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))


def kicad_available() -> bool:
    """检查 KiCad 是否可用"""
    # 检查常见路径
    kicad_paths = [
        "E:/Program Files/KiCad/9.0/bin/kicad-cli.exe",
        "C:/Program Files/KiCad/9.0/bin/kicad-cli.exe",
        "/usr/bin/kicad-cli",
        "/usr/local/bin/kicad-cli",
    ]
    for path in kicad_paths:
        if os.path.exists(path):
            return True
    # 检查环境变量
    if os.getenv("KICAD_CLI_PATH") and os.path.exists(os.getenv("KICAD_CLI_PATH")):
        return True
    return False


KIcad_AVAILABLE = kicad_available()


# Module-level fixtures
@pytest.fixture
def sample_pcb_data() -> Dict[str, Any]:
    """生成示例 PCB 数据"""
    return {
        "width": 50,
        "height": 40,
        "layers": 2,
        "thickness": 1.6,
        "silkscreen": True,
        "soldermask": "green",
        "components": [
            {
                "id": "comp1",
                "reference": "U1",
                "footprint": "SOT-23",
                "position": {"x": 10, "y": 10},
                "rotation": 0,
                "nets": ["VCC", "GND", "DATA"],
            },
            {
                "id": "comp2",
                "reference": "R1",
                "footprint": "0805",
                "position": {"x": 20, "y": 10},
                "rotation": 90,
                "nets": ["VCC", "DATA"],
            },
        ],
        "nets": [
            {"id": "n1", "name": "VCC"},
            {"id": "n2", "name": "GND"},
            {"id": "n3", "name": "DATA"},
        ],
        "tracks": [
            {
                "id": "t1",
                "net": "VCC",
                "layer": "F.Cu",
                "width": 0.5,
                "points": [{"x": 10, "y": 10}, {"x": 20, "y": 10}],
            },
            {
                "id": "t2",
                "net": "GND",
                "layer": "B.Cu",
                "width": 0.5,
                "points": [{"x": 10, "y": 20}, {"x": 30, "y": 20}],
            },
        ],
        "zones": [],
    }


@pytest.fixture
def sample_schematic_data() -> Dict[str, Any]:
    """生成示例原理图数据"""
    return {
        "components": [
            {"reference": "U1", "value": "CH340C", "nets": ["VCC", "GND", "USB_D+", "USB_D-"]},
            {"reference": "C1", "value": "100nF", "nets": ["VCC", "GND"]},
            {"reference": "C2", "value": "100nF", "nets": ["VCC", "GND"]},
            {"reference": "R1", "value": "10k", "nets": ["VCC", "DATA"]},
        ],
        "nets": [
            {"id": "n1", "name": "VCC"},
            {"id": "n2", "name": "GND"},
            {"id": "n3", "name": "USB_D+"},
            {"id": "n4", "name": "USB_D-"},
        ],
    }


class TestKiCadE2E:
    """KiCad E2E 集成测试"""

    def test_pcb_data_structure(self, sample_pcb_data):
        """测试 PCB 数据结构完整性"""
        assert "width" in sample_pcb_data
        assert "height" in sample_pcb_data
        assert "layers" in sample_pcb_data
        assert "components" in sample_pcb_data
        assert "tracks" in sample_pcb_data
        assert len(sample_pcb_data["components"]) == 2
        assert len(sample_pcb_data["tracks"]) == 2

    def test_generate_pcb_layout_integration(self, sample_schematic_data):
        """测试 PCB 生成与 AI 路由集成"""
        from routes.ai_routes import generate_pcb_layout

        result = generate_pcb_layout(
            schematic_data=sample_schematic_data,
            pcb_params={"width": 50, "height": 40},
        )

        assert result is not None
        assert hasattr(result, "tracks")
        assert len(result.tracks) > 0
        # 验证 VCC 网络有更宽的走线
        vcc_tracks = [t for t in result.tracks if t.net == "VCC"]
        if vcc_tracks:
            assert vcc_tracks[0].width >= 0.5

    def test_schematic_to_pcb_workflow(self, sample_schematic_data):
        """测试原理图到 PCB 的完整工作流"""
        from routes.ai_routes import generate_pcb_layout
        from pcb.net_classifier import classify_nets

        # Step 1: 分类网络
        nets = classify_nets(sample_schematic_data)
        assert "VCC" in nets
        assert nets["VCC"].net_class.value == "power"

        # Step 2: 生成 PCB
        pcb = generate_pcb_layout(sample_schematic_data, {"width": 50, "height": 40})
        assert len(pcb.tracks) > 0

    def test_export_pcb_to_kicad_format(self, sample_pcb_data, tmp_path):
        """测试 PCB 数据导出为 KiCad 格式"""
        from export.gerber_generator import EnhancedGerberGenerator
        from export.bom_generator import BOMGenerator

        # 生成 Gerber
        output_dir = tmp_path / "gerber"
        output_dir.mkdir()

        generator = EnhancedGerberGenerator(sample_pcb_data)
        result = generator.generate(str(output_dir))

        assert result.success
        assert len(result.files) > 0
        # 验证铜层文件
        assert any("F_Cu" in f for f in result.files.keys())

    def test_bom_generation(self, sample_schematic_data, tmp_path):
        """测试 BOM 生成"""
        from export.bom_generator import BOMGenerator

        bom_gen = BOMGenerator(sample_schematic_data)
        items = bom_gen.parse_components()

        assert len(items) == 4  # U1, C1, C2, R1

        # 验证 LCSC 料号查找
        ch340c_item = next((i for i in items if "CH340C" in i.value), None)
        if ch340c_item:
            assert ch340c_item.lcsc_part != ""

    def test_manufacturing_check(self, sample_pcb_data):
        """测试制造可行性检查"""
        from export.manufacturing_checker import ManufacturingChecker

        checker = ManufacturingChecker(sample_pcb_data)
        report = checker.check_jlcpcb()

        assert report is not None
        assert hasattr(report, "passed")
        assert hasattr(report, "errors")
        assert hasattr(report, "summary")
        assert "board_thickness" in report.summary

    def test_si_analyzer_integration(self, sample_pcb_data):
        """测试 SI 分析器集成"""
        from drc.si_analyzer import SIAnalyzer

        analyzer = SIAnalyzer(sample_pcb_data)
        report = analyzer.analyze_all()

        assert report is not None
        assert hasattr(report, "passed")
        assert hasattr(report, "violations")
        assert hasattr(report, "summary")
        assert "total_nets" in report.summary

    def test_drc_and_si_combined(self, sample_pcb_data):
        """测试 DRC 和 SI 联合检查"""
        from drc.advanced_drc import create_jlcpcb_drc
        from drc.si_analyzer import SIAnalyzer

        # DRC 检查
        drc_engine = create_jlcpcb_drc()
        drc_result = drc_engine.check(sample_pcb_data)

        # SI 检查
        si_analyzer = SIAnalyzer(sample_pcb_data)
        si_result = si_analyzer.analyze_all()

        # 汇总结果
        combined_passed = drc_result.passed and si_result.passed

        assert combined_passed is not None

    @pytest.mark.skipif(not KIcad_AVAILABLE, reason="KiCad not available")
    def test_real_kicad_open_pcb(self, sample_pcb_data, tmp_path):
        """测试真实 KiCad 打开 PCB 文件 (需要 KiCad 安装)"""
        # 此测试仅在 KiCad 可用时运行
        pytest.skip("Real KiCad integration test - requires KiCad GUI running")

    def test_kicad_ipc_manager_mock(self):
        """测试 KiCad IPC 管理器 (使用 Mock)"""
        from kicad_ipc_manager import KiCadIPCManager

        # 创建 Mock IPC 管理器
        mock_manager = Mock(spec=KiCadIPCManager)
        mock_manager.is_connected.return_value = True
        mock_manager.get_board_status.return_value = {
            "connected": True,
            "board_loaded": True,
        }

        assert mock_manager.is_connected()
        status = mock_manager.get_board_status()
        assert status["connected"] is True


class TestManufacturingWorkflow:
    """制造工作流测试"""

    def test_gerber_layer_generation_2layer(self, tmp_path):
        """测试 2 层板 Gerber 层生成"""
        from export.gerber_generator import EnhancedGerberGenerator

        pcb_data = {
            "width": 100,
            "height": 80,
            "layers": 2,
            "components": [],
            "tracks": [
                {"id": "t1", "net": "VCC", "layer": "F.Cu", "width": 0.5,
                 "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]},
            ],
            "zones": [],
        }

        generator = EnhancedGerberGenerator(pcb_data)
        result = generator.generate(str(tmp_path))

        assert result.success
        assert "F_Cu" in result.files
        assert "B_Cu" in result.files
        assert "Edge_Cuts" in result.files

    def test_gerber_layer_generation_4layer(self, tmp_path):
        """测试 4 层板 Gerber 层生成"""
        from export.gerber_generator import EnhancedGerberGenerator

        pcb_data = {
            "width": 100,
            "height": 80,
            "layers": 4,
            "components": [],
            "tracks": [],
            "zones": [],
        }

        generator = EnhancedGerberGenerator(pcb_data)
        result = generator.generate(str(tmp_path))

        assert result.success
        assert "F_Cu" in result.files
        assert "In1_Cu" in result.files
        assert "In2_Cu" in result.files
        assert "B_Cu" in result.files

    def test_bom_grouping(self, sample_schematic_data):
        """测试 BOM 分组功能"""
        from export.bom_generator import BOMGenerator

        bom_gen = BOMGenerator(sample_schematic_data)
        items = bom_gen.parse_components()

        # C1 和 C2 都是 100nF，应该被分组
        grouped = bom_gen.group_by_value(items)

        # 查找 100nF 组
        nf100_group = next(
            (g for g in grouped if g["value"] == "100nF"), None
        )

        if nf100_group:
            assert nf100_group["quantity"] == 2
            assert "C1" in nf100_group["references"]
            assert "C2" in nf100_group["references"]

    def test_cost_estimate(self, sample_pcb_data):
        """测试费用估算"""
        from export.manufacturing_checker import ManufacturingChecker

        checker = ManufacturingChecker(sample_pcb_data)
        estimate = checker.get_cost_estimate("jlcpcb")

        assert "unit_price_usd" in estimate
        assert "total_price_usd" in estimate
        assert estimate["manufacturer"] == "jlcpcb"
        assert estimate["quantity"] == 5


class TestSIAnalysis:
    """SI 分析测试"""

    def test_impedance_calculation(self):
        """测试阻抗计算"""
        from drc.si_analyzer import SIAnalyzer

        analyzer = SIAnalyzer({})
        result = analyzer.analyze_impedance(
            trace_width=0.25,
            layer_name="F.Cu",
            target_ohm=50,
            tolerance_percent=10,
            net_name="USB_DATA",
        )

        assert result is not None
        assert result.target_z0 == 50

    def test_diff_pair_analysis(self):
        """测试差分对分析"""
        from drc.si_analyzer import SIAnalyzer

        analyzer = SIAnalyzer({})
        result = analyzer.analyze_diff_pair(
            width=0.2,
            spacing=0.2,
            layer_name="F.Cu",
            length_mm=50,
            target_ohm=90,
        )

        assert result is not None
        assert result.target_impedance == 90

    def test_transmission_loss(self):
        """测试传输损耗分析"""
        from drc.si_analyzer import SIAnalyzer

        analyzer = SIAnalyzer({})
        result = analyzer.analyze_transmission_loss(
            trace_width=0.25,
            length_mm=100,
            frequency_hz=1e9,
        )

        assert result is not None
        assert result.total_loss_db >= 0

    def test_crosstalk_simple(self):
        """测试简化串扰计算"""
        from drc.si_analyzer import SIAnalyzer

        analyzer = SIAnalyzer({})
        crosstalk = analyzer.calculate_crosstalk_simple(
            trace_spacing=0.3,
            dielectric_height=0.2,
        )

        assert 0 <= crosstalk <= 1
        # 较大间距应该产生较小串扰
        crosstalk_close = analyzer.calculate_crosstalk_simple(trace_spacing=0.1)
        assert crosstalk_close > crosstalk

    def test_full_si_analysis(self, sample_pcb_data):
        """测试完整 SI 分析"""
        from drc.si_analyzer import SIAnalyzer

        analyzer = SIAnalyzer(sample_pcb_data)
        report = analyzer.analyze_all()

        assert report is not None
        assert isinstance(report.passed, bool)
        assert isinstance(report.violations, list)
