"""
AI Routes 测试文件
测试知识库加载、原理图生成等核心功能
"""

import sys
import os
from unittest.mock import Mock, patch

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from routes.ai_routes import (
    router,
    get_component_db,
    get_component_info,
    get_circuit_template,
)


def test_get_component_db():
    """测试元件数据库加载"""
    db = get_component_db()
    assert db is not None
    assert "components" in db
    assert "templates" in db
    print("[OK] Element database loaded successfully")


def test_get_component_info_known():
    """测试获取已知元件信息"""
    info = get_component_info("STM32F103C8T6")
    assert info is not None
    assert info["symbol_library"] == "MCU_ST_STM32"
    assert "pins" in info
    assert len(info["pins"]) > 0
    print(f"[OK] Get STM32F103C8T6 info: {len(info['pins'])} pins")


def test_get_component_info_fuzzy():
    """测试模糊匹配元件"""
    info = get_component_info("STM32")
    assert info is not None
    print("[OK] Fuzzy match success")


def test_get_component_info_unknown():
    """测试未知元件返回None"""
    info = get_component_info("UNKNOWN_COMPONENT_XYZ")
    assert info is None
    print("[OK] Unknown component correctly returns None")


def test_get_circuit_template():
    """测试获取电路模板"""
    template = get_circuit_template("decoupling")
    assert template is not None
    assert "description" in template
    assert "connections" in template
    print("[OK] Get decoupling circuit template success")


def test_get_circuit_template_unknown():
    """测试获取未知模板"""
    template = get_circuit_template("unknown_template_xyz")
    assert template is None
    print("[OK] Unknown template correctly returns None")


def test_knowledge_base_coverage():
    """测试知识库覆盖率"""
    db = get_component_db()
    components = db.get("components", {})
    templates = db.get("templates", {})

    print(f"\nKnowledge base statistics:")
    print(f"  Components: {len(components)}")
    print(f"  Templates: {len(templates)}")

    # Check key components
    key_components = [
        "STM32F103C8T6",
        "ATmega328P",
        "ESP32-WROOM",
        "AMS1117-3.3",
        "LM7805",
    ]
    for comp in key_components:
        if comp in components:
            print(f"  [OK] {comp}")
        else:
            print(f"  [FAIL] {comp} (missing)")

    # Check key templates
    key_templates = [
        "decoupling",
        "crystal_oscillator",
        "reset_circuit",
        "power_regulator",
    ]
    for template in key_templates:
        if template in templates:
            print(f"  [OK] {template}")
        else:
            print(f"  [FAIL] {template} (missing)")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AI Routes 知识库测试")
    print("=" * 60)

    test_get_component_db()
    test_get_component_info_known()
    test_get_component_info_fuzzy()
    test_get_component_info_unknown()
    test_get_circuit_template()
    test_get_circuit_template_unknown()
    test_knowledge_base_coverage()

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
