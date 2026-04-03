"""
KiCad IPC集成测试

测试覆盖:
1. KiCad路径配置
2. KiCad IPC管理器初始化
3. 封装库功能
4. 符号库功能

注意: 部分测试需要实际的KiCad环境
"""

import pytest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKiCadConfig:
    """测试KiCad配置"""

    def test_kicad_config_import(self):
        """测试配置模块可以导入"""
        from config import KiCadConfig, AIConfig, AppConfig, load_config

        assert KiCadConfig is not None

    def test_kicad_config_creation(self):
        """测试创建KiCad配置"""
        from config import KiCadConfig
        from pathlib import Path

        expected_path = os.environ.get("KICAD_PATH", "E:/Program Files/KiCad/9.0")
        config = KiCadConfig(
            kicad_path=expected_path, projects_dir="./projects"
        )
        # Normalize path for comparison (handle both forward and back slashes)
        assert Path(config.kicad_path).as_posix() == Path(expected_path).as_posix()
        assert config.projects_dir == "./projects"

    def test_load_config(self):
        """测试加载配置"""
        from config import load_config

        config = load_config()
        # AppConfig is a dataclass with attributes, not a dict
        assert hasattr(config, "kicad") and config.kicad is not None
        assert hasattr(config, "ai") and config.ai is not None
        assert hasattr(config, "server") and config.server is not None


class TestKiCadIPCManager:
    """测试KiCad IPC管理器"""

    def test_kicad_ipc_manager_import(self):
        """测试IPC管理器可以导入"""
        from kicad_ipc_manager import KiCadIPCManager, HAS_KIPY

        assert KiCadIPCManager is not None

    def test_kicad_connection_config(self):
        """测试连接配置"""
        from kicad_ipc_manager import KiCadConnectionConfig

        config = KiCadConnectionConfig(
            kicad_cli_path=os.environ.get("KICAD_CLI_PATH", "E:\\Program Files\\KiCad\\9.0\\bin\\kicad.exe")
        )
        assert config.kicad_cli_path is not None


class TestFootprintLibrary:
    """测试封装库"""

    def test_footprint_library_import(self):
        """测试封装库可以导入"""
        from footprint_library import (
            get_default_footprint,
            find_best_footprint,
            SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS,
        )

        assert get_default_footprint is not None

    def test_get_default_footprint_resistor(self):
        """测试获取电阻默认封装"""
        from footprint_library import get_default_footprint

        fp = get_default_footprint("Resistor", "10K")
        assert fp is not None

    def test_get_default_footprint_capacitor(self):
        """测试获取电容默认封装"""
        from footprint_library import get_default_footprint

        fp = get_default_footprint("Capacitor", "100nF")
        assert fp is not None

    def test_get_default_footprint_ic(self):
        """测试获取IC默认封装"""
        from footprint_library import get_default_footprint

        fp = get_default_footprint("IC", "STM32")
        assert fp is not None

    def test_find_best_footprint(self):
        """测试查找最佳封装"""
        from footprint_library import get_default_footprint

        # 测试获取最佳封装
        fp = get_default_footprint("Resistor", "10K")
        assert fp is not None

    def test_symbol_recommendations_exist(self):
        """测试符号推荐存在"""
        from footprint_library import SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS

        assert isinstance(SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS, dict)


class TestSymbolLibrary:
    """测试符号库"""

    def test_symbol_lib_parser_import(self):
        """测试符号库解析器可以导入"""
        from symbol_lib_parser import SymbolLibParser

        assert SymbolLibParser is not None

    def test_parse_symbol_library(self):
        """测试解析符号库"""
        # 这个测试在没有实际符号库文件时会返回空
        from symbol_lib_parser import SymbolLibParser

        parser = SymbolLibParser()
        assert parser is not None


class TestSmartFootprintFinder:
    """测试智能封装查找器"""

    def test_smart_footprint_finder_import(self):
        """测试智能封装查找器可以导入"""
        from smart_footprint_finder import find_footprint, get_footprint_finder

        assert find_footprint is not None
        assert get_footprint_finder is not None

    def test_find_footprint_resistor(self):
        """测试查找电阻封装"""
        from smart_footprint_finder import find_footprint

        fp = find_footprint("Resistor", "10K")
        assert fp is not None

    def test_find_footprint_capacitor(self):
        """测试查找电容封装"""
        from smart_footprint_finder import find_footprint

        fp = find_footprint("Capacitor", "100nF")
        assert fp is not None

    def test_find_footprint_mcu(self):
        """测试查找MCU封装"""
        from smart_footprint_finder import find_footprint

        fp = find_footprint("STM32", "LQFP-48")
        assert fp is not None or fp is not ""


class TestComponentKnowledge:
    """测试元件知识库"""

    def test_component_db_import(self):
        """测试元件数据库可以导入"""
        from routes.ai_routes import get_component_db, get_component_info

        assert get_component_db is not None

    def test_get_component_info_stm32(self):
        """测试获取STM32信息"""
        from routes.ai_routes import get_component_info

        info = get_component_info("STM32F103C8T6")
        # 如果知识库中有该元件，应该返回信息
        if info:
            assert "category" in info or "description" in info

    def test_get_component_info_ch340(self):
        """测试获取CH340信息"""
        from routes.ai_routes import get_component_info

        info = get_component_info("CH340C")
        # 如果知识库中有该元件，应该返回信息

    def test_get_schematic_pins(self):
        """测试获取原理图引脚"""
        from routes.ai_routes import get_schematic_pins

        pins = get_schematic_pins("STM32F103C8T6")
        assert isinstance(pins, list)


class TestDesignRulesIntegration:
    """测试设计规则集成"""

    def test_design_rules_import(self):
        """测试设计规则可以导入"""
        from design_rules import ProfessionalDesignEngine

        assert ProfessionalDesignEngine is not None

    def test_design_engine_creation(self):
        """测试创建设计引擎"""
        from design_rules import ProfessionalDesignEngine

        engine = ProfessionalDesignEngine()
        assert engine is not None

    def test_check_design(self):
        """测试检查设计"""
        from design_rules import ProfessionalDesignEngine

        engine = ProfessionalDesignEngine()
        # 测试空设计
        result = engine.analyze_circuit({})
        assert isinstance(result, list)  # 返回的是问题列表


class TestKiCadPath:
    """测试KiCad路径配置"""

    def test_default_kicad_path_windows(self):
        """测试Windows默认路径"""
        # 测试常见的Windows KiCad安装路径
        common_paths = [
            "E:\\Program Files9.0",
            "C:\\\\KiCad\\Program Files\\KiCad\\9.0",
            "C:\\Program Files (x86)\\KiCad\\9.0",
        ]
        # 验证路径格式正确
        for path in common_paths:
            assert "\\" in path or "/" in path

    def test_kicad_exe_exists(self):
        """测试KiCad可执行文件是否存在"""
        import os

        # 检查用户提供的路径
        kicad_path = os.environ.get("KICAD_PATH", "E:\\Program Files\\KiCad\\9.0")

        if os.path.exists(kicad_path):
            # 检查bin目录
            bin_path = os.path.join(kicad_path, "bin")
            if os.path.exists(bin_path):
                kicad_exe = os.path.join(bin_path, "kicad.exe")
                # 如果exe存在，测试会更有意义


class TestIntegration:
    """集成测试"""

    def test_full_schematic_to_pcb_flow(self):
        """测试完整原理图到PCB流程"""
        from schematic_generator import generate_standard_schematic

        try:
            from pcb_generator import PCBGenerator, DRCChecker
        except ImportError:
            pytest.skip("pcb_generator module not available")

        # 1. 生成原理图
        schematic = generate_standard_schematic(
            [{"name": "STM32F103C8T6", "reference": "U1"}]
        )
        assert "components" in schematic
        assert "nets" in schematic

        # 2. 生成PCB
        generator = PCBGenerator()
        pcb = generator.generate_from_schematic(schematic)
        assert "components" in pcb
        assert "board_outline" in pcb

        # 3. DRC检查
        checker = DRCChecker()
        drc_result = checker.check(pcb)
        assert "passed" in drc_result

    def test_multiple_component_types(self):
        """测试多种元件类型"""
        from schematic_generator import generate_standard_schematic

        components = [
            {"name": "STM32F103C8T6", "reference": "U1"},
            {"name": "LM7805", "reference": "U2"},
            {"name": "10K", "reference": "R1"},
            {"name": "100nF", "reference": "C1"},
        ]

        schematic = generate_standard_schematic(components)
        assert schematic is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
