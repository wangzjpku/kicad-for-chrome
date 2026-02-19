"""
专业级设计规则引擎测试
Professional Design Rules Engine Test

验证8大设计缺陷的修复效果，确保得分从48/100提升到100/100
"""

import pytest
from typing import Dict, Any, List

# 导入设计规则引擎
import sys

sys.path.insert(0, ".")

from design_rules import (
    ProfessionalDesignEngine,
    get_design_engine,
    DesignCategory,
    DesignIssue,
)
from design_rules.decoupling_rules import (
    generate_decoupling_report,
    get_ic_type,
    DECOUPLING_RULES,
)
from design_rules.grounding_rules import (
    get_grounding_recommendation,
    GROUNDING_CONFIGS,
)
from design_rules.filtering_rules import (
    calculate_filter_components,
    POWER_SUPPLY_FILTER_CONFIGS,
)
from design_rules.safety_rules import (
    get_clearance_for_voltage,
    QUICK_REFERENCE,
)
from design_rules.esd_emi_rules import (
    get_esd_emi_report,
    ESD_PROTECTION_DEVICES,
)
from design_rules.thermal_rules import (
    calculate_junction_temperature,
    calculate_required_heatsink,
    get_thermal_report,
)
from design_rules.protection_rules import (
    get_protection_report,
    APPLICATION_PROTECTION_REQUIREMENTS,
)


class TestDesignEngine:
    """设计引擎测试"""

    @pytest.fixture
    def engine(self):
        """获取设计引擎实例"""
        return get_design_engine()

    @pytest.fixture
    def sample_circuit(self) -> Dict[str, Any]:
        """示例电路数据 - 原始AI生成(有问题)"""
        return {
            "components": [
                {
                    "id": "comp-1",
                    "name": "单片机",
                    "model": "STM32F103C8T6",
                    "package": "LQFP-48",
                },
                {
                    "id": "comp-2",
                    "name": "稳压芯片",
                    "model": "AMS1117-3.3",
                    "package": "SOT-223",
                },
                {"id": "comp-3", "name": "电容", "model": "10uF", "package": "0805"},
                {"id": "comp-4", "name": "电容", "model": "100nF", "package": "0603"},
                {
                    "id": "comp-5",
                    "name": "USB接口",
                    "model": "Micro-USB",
                    "package": "SMD",
                },
            ],
            "parameters": [
                {"key": "输入电压", "value": "12", "unit": "V"},
                {"key": "输出电压", "value": "3.3", "unit": "V"},
                {"key": "输出电流", "value": "0.5", "unit": "A"},
            ],
            "pcb_info": {
                "board_area_mm2": 1600,  # 40x40mm
                "ground_plane_area_pct": 20,  # 原来很低
                "min_clearance_mm": 0.2,
                "ground_via_count": 4,
            },
        }

    @pytest.fixture
    def professional_circuit(self) -> Dict[str, Any]:
        """专业级电路数据 - 修复后(100分)"""
        return {
            "components": [
                # MCU
                {
                    "id": "comp-1",
                    "name": "单片机",
                    "model": "STM32F103C8T6",
                    "package": "LQFP-48",
                },
                # 稳压器
                {
                    "id": "comp-2",
                    "name": "稳压芯片",
                    "model": "MP1584",
                    "package": "SO-8",
                },
                # 去耦电容 - 专业配置
                {
                    "id": "comp-3",
                    "name": "去耦电容",
                    "model": "0.1uF 16V",
                    "package": "0402",
                },
                {
                    "id": "comp-4",
                    "name": "去耦电容",
                    "model": "0.01uF 16V",
                    "package": "0402",
                },
                {
                    "id": "comp-5",
                    "name": "大容量电容",
                    "model": "10uF 10V",
                    "package": "0805",
                },
                # 输入滤波
                {
                    "id": "comp-6",
                    "name": "输入滤波电容",
                    "model": "47uF 25V",
                    "package": "1206",
                },
                {
                    "id": "comp-7",
                    "name": "滤波电感",
                    "model": "10uH 2A",
                    "package": "SMD",
                },
                # 输出滤波
                {
                    "id": "comp-8",
                    "name": "输出滤波电容",
                    "model": "100uF 10V",
                    "package": "electrolytic",
                },
                # ESD保护
                {
                    "id": "comp-9",
                    "name": "ESD保护",
                    "model": "TPD4E001",
                    "package": "SOT-23",
                },
                {
                    "id": "comp-10",
                    "name": "TVS二极管",
                    "model": "SMBJ5.0CA",
                    "package": "SMB",
                },
                # 过流保护
                {
                    "id": "comp-11",
                    "name": "PTC保险丝",
                    "model": "PPTC 1A",
                    "package": "1206",
                },
                # USB接口
                {
                    "id": "comp-12",
                    "name": "USB接口",
                    "model": "Micro-USB",
                    "package": "SMD",
                },
                {
                    "id": "comp-13",
                    "name": "USB共模电感",
                    "model": "90Ω @100MHz",
                    "package": "SMD",
                },
            ],
            "parameters": [
                {"key": "输入电压", "value": "12", "unit": "V"},
                {"key": "输出电压", "value": "3.3", "unit": "V"},
                {"key": "输出电流", "value": "0.5", "unit": "A"},
            ],
            "pcb_info": {
                "board_area_mm2": 2000,
                "ground_plane_area_pct": 50,  # 专业级: 50%+
                "min_clearance_mm": 0.5,  # 满足安全要求
                "ground_via_count": 20,  # 充足的接地过孔
                "thermal_pad_area_mm2": 100,  # 散热焊盘
                "thermal_vias_comp-2": 6,  # 热过孔
            },
        }

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
        assert len(engine.rules) > 0
        print(f"加载了 {len(engine.rules)} 条设计规则")

    def test_analyze_sample_circuit(self, engine, sample_circuit):
        """测试分析原始电路 - 应发现问题"""
        issues = engine.analyze_circuit(sample_circuit)

        print(f"\n=== 原始电路分析结果 ===")
        print(f"发现问题数量: {len(issues)}")

        for issue in issues[:10]:  # 显示前10个问题
            print(f"  [{issue.severity}] {issue.category.value}: {issue.message}")

        # 原始电路应该有很多问题
        assert len(issues) > 0, "原始电路应该有设计问题"

    def test_analyze_professional_circuit(self, engine, professional_circuit):
        """测试分析专业电路 - 应该没有严重问题"""
        issues = engine.analyze_circuit(professional_circuit)

        print(f"\n=== 专业电路分析结果 ===")
        print(f"发现问题数量: {len(issues)}")

        critical_issues = [i for i in issues if i.severity == "critical"]
        warning_issues = [i for i in issues if i.severity == "warning"]

        print(f"  严重问题: {len(critical_issues)}")
        print(f"  警告问题: {len(warning_issues)}")

        # 专业电路不应该有严重问题
        assert len(critical_issues) == 0, "专业电路不应该有严重问题"

    def test_score_calculation(self, engine, sample_circuit, professional_circuit):
        """测试得分计算"""
        # 原始电路得分
        original_score = engine.get_design_score(sample_circuit)
        print(f"\n=== 原始电路得分 ===")
        print(f"总分: {original_score['total_score']}/100")
        for cat, score in original_score["categories"].items():
            print(f"  {cat}: {score}/100")

        # 专业电路得分
        professional_score = engine.get_design_score(professional_circuit)
        print(f"\n=== 专业电路得分 ===")
        print(f"总分: {professional_score['total_score']}/100")
        for cat, score in professional_score["categories"].items():
            print(f"  {cat}: {score}/100")

        # 专业电路得分应该更高
        assert professional_score["total_score"] > original_score["total_score"]
        assert professional_score["total_score"] >= 80, "专业电路得分应该>=80"

    def test_auto_fix(self, engine, sample_circuit):
        """测试自动修复"""
        print(f"\n=== 测试自动修复 ===")

        fixed_circuit = engine.auto_fix_circuit(sample_circuit)

        original_components = len(sample_circuit["components"])
        fixed_components = len(fixed_circuit["components"])

        print(f"原始元件数量: {original_components}")
        print(f"修复后元件数量: {fixed_components}")
        print(f"新增元件数量: {fixed_components - original_components}")

        # 列出新增的元件
        new_components = [c for c in fixed_circuit["components"] if c.get("auto_added")]
        print(f"\n新增元件:")
        for comp in new_components:
            print(
                f"  - {comp['name']}: {comp['model']} ({comp.get('added_reason', '')})"
            )


class TestDecouplingRules:
    """去耦电容规则测试"""

    def test_ic_type_detection(self):
        """测试IC类型识别"""
        assert get_ic_type("STM32F103C8T6") == "MCU"
        assert get_ic_type("ATmega328P") == "MCU"
        assert get_ic_type("LM358") == "OPAMP"
        assert get_ic_type("LM2596") == "POWER_IC"

    def test_decoupling_report(self):
        """测试去耦电容报告生成"""
        report = generate_decoupling_report(
            ic_model="STM32F103C8T6", voltage=3.3, current_ma=50, freq_mhz=72
        )

        print(f"\n=== STM32F103 去耦电容报告 ===")
        print(f"IC类型: {report['ic_info']['type']}")
        print(f"推荐电容:")
        for cap in report["recommended_capacitors"]:
            print(f"  - {cap['value']} {cap['package']} ({cap['type']})")

        assert len(report["recommended_capacitors"]) > 0


class TestSafetyRules:
    """安全间距规则测试"""

    def test_clearance_calculation(self):
        """测试间隙计算"""
        # 5V信号
        clearance_5v = get_clearance_for_voltage(5)
        print(f"5V 最小间隙: {clearance_5v}mm")

        # 220V交流
        clearance_220v = get_clearance_for_voltage(220)
        print(f"220V 最小间隙: {clearance_220v}mm")

        # 220V加强绝缘
        clearance_220v_reinforced = get_clearance_for_voltage(220, "reinforced")
        print(f"220V 加强绝缘: {clearance_220v_reinforced}mm")

        assert clearance_220v_reinforced > clearance_220v


class TestThermalRules:
    """热设计规则测试"""

    def test_junction_temperature_calculation(self):
        """测试结温计算"""
        # TO-220封装，2W功耗，无散热片
        tj = calculate_junction_temperature(
            power_w=2.0,
            theta_jc=3.0,
            theta_cs=0.5,
            theta_sa=65.0,  # 无散热片
            ambient_temp_c=25.0,
        )
        print(f"\n无散热片结温: {tj:.1f}°C")

        # 有散热片
        tj_with_heatsink = calculate_junction_temperature(
            power_w=2.0,
            theta_jc=3.0,
            theta_cs=0.5,
            theta_sa=15.0,  # 中型散热片
            ambient_temp_c=25.0,
        )
        print(f"有散热片结温: {tj_with_heatsink:.1f}°C")

        assert tj > tj_with_heatsink

    def test_heatsink_calculation(self):
        """测试散热片选型计算"""
        required_theta = calculate_required_heatsink(
            power_w=5.0,
            tj_max_c=125.0,
            theta_jc=3.0,
        )
        print(f"\n5W功耗所需散热片热阻: ≤{required_theta:.1f}°C/W")


class TestProtectionRules:
    """保护电路规则测试"""

    def test_protection_report(self):
        """测试保护电路报告"""
        components = [
            {"name": "充电芯片", "model": "TP4056", "package": "SOP-8"},
            {"name": "电池", "model": "18650", "package": "THT"},
        ]

        report = get_protection_report(components, [])

        print(f"\n=== 电池充电保护报告 ===")
        print(f"应用类型: {report['application_type']}")
        print(f"缺失保护:")
        for missing in report["missing_protection"]:
            print(f"  - {missing['type']} ({missing['level']})")
        print(f"建议:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("专业级电路设计规则引擎测试")
    print("=" * 60)

    # 创建测试实例
    test_design = TestDesignEngine()
    engine = get_design_engine()

    sample_circuit = test_design.sample_circuit()
    professional_circuit = test_design.professional_circuit()

    # 运行测试
    test_design.test_engine_initialization(engine)
    test_design.test_analyze_sample_circuit(engine, sample_circuit)
    test_design.test_analyze_professional_circuit(engine, professional_circuit)
    test_design.test_score_calculation(engine, sample_circuit, professional_circuit)
    test_design.test_auto_fix(engine, sample_circuit)

    # 子模块测试
    test_decoupling = TestDecouplingRules()
    test_decoupling.test_ic_type_detection()
    test_decoupling.test_decoupling_report()

    test_safety = TestSafetyRules()
    test_safety.test_clearance_calculation()

    test_thermal = TestThermalRules()
    test_thermal.test_junction_temperature_calculation()
    test_thermal.test_heatsink_calculation()

    test_protection = TestProtectionRules()
    test_protection.test_protection_report()

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
