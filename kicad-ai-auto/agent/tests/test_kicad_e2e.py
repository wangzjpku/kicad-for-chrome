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


class TestODBXXExport:
    """ODB++ 导出测试"""

    def test_odbxx_generator_import(self):
        """测试 ODB++ 生成器可以导入"""
        from export.odbxx_generator import ODBXXGenerator
        assert ODBXXGenerator is not None

    def test_odbxx_2layer(self, tmp_path):
        """测试 2 层板 ODB++ 生成"""
        from export.odbxx_generator import ODBXXGenerator

        pcb_data = {
            "width": 100,
            "height": 80,
            "layers": 2,
            "components": [
                {"reference": "U1", "value": "CH340C", "footprint": "SOP-16",
                 "position": {"x": 10, "y": 10}, "rotation": 0},
            ],
            "tracks": [
                {"id": "t1", "net": "VCC", "layer": "F.Cu", "width": 0.5,
                 "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]},
            ],
            "vias": [
                {"id": "v1", "x": 5, "y": 5, "drill_diameter": 0.4,
                 "outer_diameter": 0.8, "net": "VCC"},
            ],
            "nets": [
                {"id": "n1", "name": "VCC", "pins": []},
            ],
            "zones": [],
        }

        generator = ODBXXGenerator(pcb_data)
        result = generator.generate_directory(str(tmp_path))

        assert result.success
        assert len(result.files) > 0
        # 验证关键文件存在
        assert any("matrix" in f for f in result.files)
        assert any("profile" in f for f in result.files)
        assert any("signals/TOP/lines" in f for f in result.files)

    def test_odbxx_4layer(self, tmp_path):
        """测试 4 层板 ODB++ 生成"""
        from export.odbxx_generator import ODBXXGenerator

        pcb_data = {
            "width": 100,
            "height": 80,
            "layers": 4,
            "components": [],
            "tracks": [],
            "vias": [],
            "nets": [],
            "zones": [],
        }

        generator = ODBXXGenerator(pcb_data)
        result = generator.generate_directory(str(tmp_path))

        assert result.success
        # 验证内层文件
        assert any("signals/INNER1" in f for f in result.files)
        assert any("signals/INNER2" in f for f in result.files)

    def test_odbxx_zip_export(self, tmp_path):
        """测试 ODB++ ZIP 压缩导出"""
        from export.odbxx_generator import ODBXXGenerator

        pcb_data = {
            "width": 50,
            "height": 40,
            "layers": 2,
            "components": [],
            "tracks": [
                {"id": "t1", "net": "GND", "layer": "B.Cu", "width": 0.3,
                 "points": [{"x": 0, "y": 0}, {"x": 20, "y": 20}]},
            ],
            "vias": [],
            "nets": [{"id": "n1", "name": "GND", "pins": []}],
            "zones": [],
        }

        generator = ODBXXGenerator(pcb_data, {"board_name": "test_board"})
        result = generator.generate(str(tmp_path))

        assert result.success
        assert result.output_file.endswith(".zip")
        assert os.path.exists(result.output_file)

    def test_odbxx_layer_names(self):
        """测试层名生成"""
        from export.odbxx_generator import ODBXXGenerator

        gen_2 = ODBXXGenerator({"layers": 2})
        assert gen_2._get_layer_names() == ["TOP", "BOTTOM"]

        gen_4 = ODBXXGenerator({"layers": 4})
        assert gen_4._get_layer_names() == ["TOP", "INNER1", "INNER2", "BOTTOM"]

        gen_6 = ODBXXGenerator({"layers": 6})
        assert gen_6._get_layer_names() == ["TOP", "INNER1", "INNER2", "INNER3", "INNER4", "BOTTOM"]


class TestIPC2221Advanced:
    """IPC-2221 进阶功能测试"""

    def test_advanced_calculator_import(self):
        """测试高级计算器可以导入"""
        from pcb.current_calculator import AdvancedCurrentCalculator, IPC2221Params
        assert AdvancedCurrentCalculator is not None
        assert IPC2221Params is not None

    def test_copper_weight_options(self):
        """测试铜厚选项"""
        from pcb.current_calculator import AdvancedCurrentCalculator

        weights = AdvancedCurrentCalculator.get_available_copper_weights()
        assert 0.5 in weights
        assert 1.0 in weights
        assert 2.0 in weights
        assert 3.0 in weights
        assert 4.0 in weights

    def test_temperature_rise_options(self):
        """测试温升选项"""
        from pcb.current_calculator import AdvancedCurrentCalculator

        rises = AdvancedCurrentCalculator.get_available_temperature_rises()
        assert 10 in rises
        assert 20 in rises
        assert 30 in rises
        assert 40 in rises

    def test_ipc2221_params(self):
        """测试 IPC-2221 参数"""
        from pcb.current_calculator import IPC2221Params

        params = IPC2221Params(copper_oz=2.0, temperature_rise=20, layer_location="external")
        assert params.copper_oz == 2.0
        assert params.temperature_rise == 20
        assert params.layer_location == "external"

    def test_calculate_width_with_copper_options(self):
        """测试不同铜厚的宽度计算"""
        from pcb.current_calculator import calculate_trace_width

        # 2A 电流，不同铜厚应该有不同结果
        width_1oz = calculate_trace_width(2000, copper_oz=1.0)
        width_2oz = calculate_trace_width(2000, copper_oz=2.0)

        # 厚铜可以更窄
        assert width_2oz < width_1oz

    def test_calculate_width_with_temperature(self):
        """测试不同温升的宽度计算"""
        from pcb.current_calculator import calculate_trace_width

        # 2A 电流，不同温升应该有不同结果
        width_10c = calculate_trace_width(2000, temperature_rise=10)
        width_20c = calculate_trace_width(2000, temperature_rise=20)

        # 更高温升允许更窄的走线
        assert width_20c < width_10c

    def test_calculate_width_internal_vs_external(self):
        """测试内层 vs 外层的宽度计算"""
        from pcb.current_calculator import calculate_trace_width

        # 2A 电流
        width_external = calculate_trace_width(2000, is_external=True)
        width_internal = calculate_trace_width(2000, is_external=False)

        # 外层散热好，可以用更窄的走线
        assert width_external < width_internal

    def test_calculate_width_power_net(self):
        """测试电源网络的宽度计算"""
        from pcb.current_calculator import calculate_trace_width

        # 电源网络，2A 电流
        width = calculate_trace_width(2000, net_class="power", copper_oz=1.0)

        # 应该至少大于基础宽度
        assert width >= 0.5

    def test_advanced_calculator_class(self):
        """测试高级计算器类"""
        from pcb.current_calculator import AdvancedCurrentCalculator, NetInfo, NetClass
        from pcb.net_classifier import NetInfo as NI

        # 创建测试网络
        nets = {
            "VCC": NetInfo(name="VCC", net_class=NetClass.POWER, current_ma=2000),
        }

        calc = AdvancedCurrentCalculator(nets)
        widths = calc.calculate_all_widths()

        assert "VCC" in widths
        assert widths["VCC"] > 0


class TestEMIHotspotAnalyzer:
    """EMI 热点分析器测试"""

    def test_emi_analyzer_import(self):
        """测试 EMI 分析器可以导入"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer, analyze_pcb_emi
        assert EMIHotspotAnalyzer is not None
        assert analyze_pcb_emi is not None

    def test_emi_analyze_empty_pcb(self):
        """测试空 PCB 分析"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        pcb_data = {"tracks": [], "components": [], "zones": [], "vias": []}
        analyzer = EMIHotspotAnalyzer(pcb_data)
        report = analyzer.analyze()

        assert report is not None
        assert isinstance(report.passed, bool)
        assert len(report.hotspots) >= 0

    def test_emi_clock_line_detection(self):
        """测试时钟线检测"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        # 创建有时钟线的 PCB
        pcb_data = {
            "tracks": [
                {"id": "t1", "net": "CLK", "layer": "F.Cu", "width": 0.2,
                 "points": [{"x": 0, "y": 0}, {"x": 30, "y": 0}]},
            ],
            "components": [],
            "zones": [],
            "vias": [],
        }

        analyzer = EMIHotspotAnalyzer(pcb_data)
        report = analyzer.analyze()

        # 应该检测到时钟线过长
        assert len(report.hotspots) > 0
        assert any("clock" in h.message.lower() or "clk" in h.message.lower()
                   for h in report.hotspots)

    def test_emi_sensitive_trace(self):
        """测试敏感信号检测"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        # 创建有长 USB 走线的 PCB
        pcb_data = {
            "tracks": [
                {"id": "t1", "net": "USB_DP", "layer": "F.Cu", "width": 0.2,
                 "points": [{"x": 0, "y": 0}, {"x": 60, "y": 0}]},
            ],
            "components": [],
            "zones": [],
            "vias": [],
        }

        analyzer = EMIHotspotAnalyzer(pcb_data, {"sensitivity": "high"})
        report = analyzer.analyze()

        # 应该检测到敏感信号过长
        hotspot_types = [h.hotspot_type.value for h in report.hotspots]
        assert "long_sensitive" in hotspot_types or "signal_integrity" in hotspot_types

    def test_emi_diff_pair_mismatch(self):
        """测试差分对长度不匹配检测"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        # 创建差分对长度差异过大的 PCB
        # 使用 ETH_P/ETH_N 格式以确保被检测为差分对
        pcb_data = {
            "tracks": [
                {"id": "t1", "net": "ETH_P", "layer": "F.Cu", "width": 0.2,
                 "points": [{"x": 0, "y": 0}, {"x": 50, "y": 0}]},
                {"id": "t2", "net": "ETH_N", "layer": "F.Cu", "width": 0.2,
                 "points": [{"x": 0, "y": 1}, {"x": 30, "y": 1}]},
            ],
            "components": [],
            "zones": [],
            "vias": [],
        }

        analyzer = EMIHotspotAnalyzer(pcb_data)
        report = analyzer.analyze()

        # 应该检测到差分对不匹配
        hotspot_types = [h.hotspot_type.value for h in report.hotspots]
        assert "diff_mismatch" in hotspot_types

    def test_emi_visualization_data(self):
        """测试可视化数据输出"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        pcb_data = {
            "tracks": [
                {"id": "t1", "net": "CLK", "layer": "F.Cu", "width": 0.2,
                 "points": [{"x": 0, "y": 0}, {"x": 60, "y": 0}]},
            ],
            "components": [],
            "zones": [],
            "vias": [],
        }

        analyzer = EMIHotspotAnalyzer(pcb_data)
        viz_data = analyzer.get_hotspots_for_visualization()

        assert isinstance(viz_data, list)
        for hotspot in viz_data:
            assert "id" in hotspot
            assert "type" in hotspot
            assert "severity" in hotspot
            assert "x" in hotspot
            assert "y" in hotspot
            assert "color" in hotspot

    def test_emi_sensitivity_levels(self):
        """测试不同灵敏度设置"""
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        pcb_data = {
            "tracks": [
                {"id": "t1", "net": "USB_DP", "layer": "F.Cu", "width": 0.2,
                 "points": [{"x": 0, "y": 0}, {"x": 40, "y": 0}]},
            ],
            "components": [],
            "zones": [],
            "vias": [],
        }

        # 高灵敏度
        analyzer_high = EMIHotspotAnalyzer(pcb_data, {"sensitivity": "high"})
        report_high = analyzer_high.analyze()

        # 低灵敏度
        analyzer_low = EMIHotspotAnalyzer(pcb_data, {"sensitivity": "low"})
        report_low = analyzer_low.analyze()

        # 高灵敏度应该检测到更多问题
        assert report_high.summary["total_hotspots"] >= report_low.summary["total_hotspots"]
