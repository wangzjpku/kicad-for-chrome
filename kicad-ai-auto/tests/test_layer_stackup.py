"""
多层板层叠管理测试用例

测试 Phase 4 功能：
1. 层叠模板加载 (2层/4层/6层)
2. 阻抗计算
3. 层叠结构查询
4. 推荐线宽计算
"""

import pytest
import sys
import math
from pathlib import Path

# 添加 agent 目录到路径
agent_path = Path(__file__).parent.parent / "agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from pcb.layer_stackup import (
    StackupManager,
    LayerStackup,
    CopperLayer,
    DielectricLayer,
    DielectricMaterial,
    LayerType,
    PlaneType,
    create_2layer_stackup,
    create_4layer_stackup,
    create_6layer_stackup,
    get_recommended_stackup,
    calculate_crosstalk,
)


class TestStackupTemplates:
    """测试层叠模板"""

    def test_2layer_template(self):
        """测试2层板模板"""
        manager = StackupManager()
        stackup = manager.load_template("2layer")

        assert stackup.layer_count == 2
        assert stackup.total_thickness == 1.6
        assert len(stackup.copper_layers) == 2
        assert len(stackup.dielectric_layers) == 1

        # 检查层名称
        layer_names = [l.name for l in stackup.copper_layers]
        assert "F.Cu" in layer_names
        assert "B.Cu" in layer_names

    def test_4layer_standard_template(self):
        """测试4层板标准模板"""
        manager = StackupManager()
        stackup = manager.load_template("4layer_standard")

        assert stackup.layer_count == 4
        assert stackup.total_thickness == 1.6
        assert len(stackup.copper_layers) == 4

        # 检查电源/地平面
        plane_layers = stackup.get_plane_layers()
        assert len(plane_layers) == 2

        gnd_layer = [l for l in plane_layers if l.plane_type == PlaneType.GND]
        pwr_layer = [l for l in plane_layers if l.plane_type == PlaneType.POWER]
        assert len(gnd_layer) == 1
        assert len(pwr_layer) == 1

    def test_4layer_thin_template(self):
        """测试4层板薄型模板"""
        manager = StackupManager()
        stackup = manager.load_template("4layer_thin")

        assert stackup.layer_count == 4
        assert stackup.total_thickness == 1.0  # 比标准薄

    def test_6layer_standard_template(self):
        """测试6层板标准模板"""
        manager = StackupManager()
        stackup = manager.load_template("6layer_standard")

        assert stackup.layer_count == 6
        assert len(stackup.copper_layers) == 6

        signal_layers = stackup.get_signal_layers()
        assert len(signal_layers) >= 4  # 至少有4个信号层

    def test_6layer_optimized_template(self):
        """测试6层板优化模板"""
        manager = StackupManager()
        stackup = manager.load_template("6layer_optimized")

        assert stackup.layer_count == 6
        # 优化层叠的信号层更靠近参考平面
        layer_names = [l.name for l in stackup.copper_layers]
        assert "In1.Cu" in layer_names
        assert "In2.Cu" in layer_names


class TestImpedanceCalculation:
    """测试阻抗计算"""

    def test_impedance_calculation_2layer(self):
        """测试2层板阻抗计算"""
        manager = StackupManager()
        manager.load_template("2layer")

        # 计算50欧姆微带线
        result = manager.calculate_impedance(
            trace_width=0.3,
            layer_name="F.Cu",
            reference_layer="B.Cu",
            coupling="single"
        )

        assert "impedance" in result
        assert result["impedance"] > 0
        assert result["coupling"] == "single"
        assert result["dk"] > 0

    def test_differential_impedance(self):
        """测试差分阻抗计算"""
        manager = StackupManager()
        manager.load_template("4layer_standard")

        result = manager.calculate_impedance(
            trace_width=0.15,
            layer_name="F.Cu",
            reference_layer="GND",
            coupling="diff",
            diff_spacing=0.2
        )

        assert result["coupling"] == "diff"
        assert result["diff_spacing"] == 0.2
        # 差分阻抗应该比单端高

    def test_impedance_vs_width_relationship(self):
        """测试阻抗与线宽的反比关系"""
        manager = StackupManager()
        manager.load_template("2layer")

        # 窄走线应该阻抗更高
        narrow = manager.calculate_impedance(0.1, "F.Cu", "B.Cu")
        wide = manager.calculate_impedance(0.5, "F.Cu", "B.Cu")

        assert narrow["impedance"] > wide["impedance"]


class TestOptimalTraceWidth:
    """测试最佳线宽计算"""

    def test_calculate_optimal_width(self):
        """测试计算达到目标阻抗的线宽"""
        manager = StackupManager()
        manager.load_template("2layer")

        optimal_width = manager.get_optimal_trace_width(
            target_impedance=50,
            layer_name="F.Cu",
            reference_layer="B.Cu"
        )

        assert 0.05 < optimal_width < 5.0  # 合理范围

        # 验证计算出的阻抗接近目标
        result = manager.calculate_impedance(
            optimal_width, "F.Cu", "B.Cu"
        )
        assert abs(result["impedance"] - 50) < 5.0  # 容差5欧姆

    def test_different_target_impedances(self):
        """测试不同目标阻抗"""
        manager = StackupManager()
        manager.load_template("4layer_standard")

        # 90欧姆 (USB差分)
        width_90 = manager.get_optimal_trace_width(
            target_impedance=90,
            layer_name="F.Cu",
            reference_layer="GND"
        )

        # 50欧姆 (单端)
        width_50 = manager.get_optimal_trace_width(
            target_impedance=50,
            layer_name="F.Cu",
            reference_layer="GND"
        )

        # 90欧姆应该比50欧姆细
        assert width_90 < width_50


class TestLayerQueries:
    """测试层查询功能"""

    def test_get_layer_by_name(self):
        """测试按名称获取层"""
        manager = StackupManager()
        stackup = manager.load_template("4layer_standard")

        layer = stackup.get_layer_by_name("F.Cu")
        assert layer is not None
        assert layer.name == "F.Cu"
        assert layer.layer_type == LayerType.SIGNAL

        gnd = stackup.get_layer_by_name("GND")
        assert gnd is not None
        assert gnd.plane_type == PlaneType.GND

    def test_get_signal_layers(self):
        """测试获取信号层"""
        manager = StackupManager()
        stackup = manager.load_template("6layer_standard")

        signal_layers = stackup.get_signal_layers()
        signal_names = [l.name for l in signal_layers]

        assert "F.Cu" in signal_names
        assert "B.Cu" in signal_names
        assert "In1.Cu" in signal_names or "In2.Cu" in signal_names

    def test_get_plane_layers(self):
        """测试获取平面层"""
        manager = StackupManager()
        stackup = manager.load_template("4layer_standard")

        plane_layers = stackup.get_plane_layers()
        assert len(plane_layers) == 2


class TestStackupSummary:
    """测试层叠摘要"""

    def test_summary_structure(self):
        """测试摘要结构"""
        manager = StackupManager()
        manager.load_template("4layer_standard")

        summary = manager.get_stackup_summary()

        assert summary["layer_count"] == 4
        assert summary["total_thickness"] == 1.6
        assert "signal_layers" in summary
        assert "plane_layers" in summary
        assert "copper_layers" in summary
        assert "dielectric_layers" in summary

    def test_kicad_format_export(self):
        """测试KiCad格式导出"""
        manager = StackupManager()
        manager.load_template("2layer")

        kicad_str = manager.to_kicad_format()

        assert "(layers" in kicad_str
        assert "F.Cu" in kicad_str


class TestFactoryFunctions:
    """测试工厂函数"""

    def test_create_2layer(self):
        """测试创建2层板"""
        stackup = create_2layer_stackup()
        assert stackup.layer_count == 2

    def test_create_4layer(self):
        """测试创建4层板"""
        stackup_standard = create_4layer_stackup(thin=False)
        assert stackup_standard.total_thickness == 1.6

        stackup_thin = create_4layer_stackup(thin=True)
        assert stackup_thin.total_thickness == 1.0

    def test_create_6layer(self):
        """测试创建6层板"""
        stackup_opt = create_6layer_stackup(optimized=True)
        assert stackup_opt.layer_count == 6

        stackup_std = create_6layer_stackup(optimized=False)
        assert stackup_std.layer_count == 6


class TestRecommendations:
    """测试推荐功能"""

    def test_recommended_stackup_2layer(self):
        """测试2层板推荐"""
        template = get_recommended_stackup(2)
        assert template == "2layer"

    def test_recommended_stackup_4layer(self):
        """测试4层板推荐"""
        template = get_recommended_stackup(4, "general")
        assert "4layer" in template

    def test_recommended_stackup_6layer_high_speed(self):
        """测试高速6层板推荐"""
        template = get_recommended_stackup(6, "high_speed")
        assert "6layer" in template


class TestCrosstalk:
    """测试串扰计算"""

    def test_crosstalk_spacing_ratio(self):
        """测试串扰与间距关系"""
        # 小间距高串扰
        high = calculate_crosstalk(0.1, 0.2, 0.25)
        # 大间距低串扰
        low = calculate_crosstalk(1.0, 0.2, 0.25)

        assert high > low

    def test_crosstalk_categories(self):
        """测试串扰分类"""
        very_close = calculate_crosstalk(0.1, 0.2, 0.25)  # spacing/thickness = 0.5
        close = calculate_crosstalk(0.4, 0.2, 0.25)       # spacing/thickness = 2
        far = calculate_crosstalk(1.0, 0.2, 0.25)         # spacing/thickness = 5

        assert very_close >= 0.2
        assert close >= 0.05
        assert far < 0.05


class TestDielectricMaterials:
    """测试介电材料"""

    def test_fr4_standard(self):
        """测试FR4标准材料"""
        material = DielectricMaterial.FR4_STANDARD
        assert material.dk == 4.5
        assert material.df == 0.02
        assert material.thickness == 1.6

    def test_rogers_materials(self):
        """测试Rogers材料"""
        ro4003 = DielectricMaterial.RO4003C
        assert ro4003.dk == 3.55  # 比FR4低
        assert ro4003.df == 0.0027  # 损耗更低


class TestEdgeCases:
    """测试边界情况"""

    def test_invalid_template(self):
        """测试无效模板"""
        manager = StackupManager()
        with pytest.raises(ValueError):
            manager.load_template("invalid_template")

    def test_no_stackup_loaded(self):
        """测试未加载层叠时的操作"""
        manager = StackupManager()
        with pytest.raises(ValueError):
            manager.calculate_impedance(0.3, "F.Cu", "B.Cu")

    def test_empty_stackup_summary(self):
        """测试空层叠摘要"""
        manager = StackupManager()
        summary = manager.get_stackup_summary()
        assert "error" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
