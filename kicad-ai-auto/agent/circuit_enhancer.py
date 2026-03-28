"""
电路增强器 - 根据芯片自动添加必要电路

功能:
1. 根据芯片的required_circuits自动添加必要元件
2. 连接到正确的网络
3. 放置在合理位置
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class CircuitEnhancer:
    """电路增强器 - 自动添加必要电路"""

    def __init__(self, db_path: Optional[Path] = None):
        """初始化"""
        if db_path is None:
            db_path = (
                Path(__file__).parent / "component_knowledge" / "component_db.json"
            )

        self.db_path = db_path
        self.component_db: Dict[str, Any] = {}
        self.templates: Dict[str, Any] = {}
        self._load_database()

        # 元件计数器
        self._counters = {
            "C": 0,  # 电容
            "R": 0,  # 电阻
            "L": 0,  # 电感
            "D": 0,  # 二极管
            "Y": 0,  # 晶振
            "J": 0,  # 连接器
            "LED": 0,  # LED
        }

    def _load_database(self):
        """加载数据库"""
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.component_db = data.get("components", {})
                self.templates = data.get("templates", {})
                logger.info(f"已加载电路模板: {len(self.templates)} 个")
        except Exception as e:
            logger.error(f"加载电路模板失败: {e}")

    def _get_next_ref(self, component_type: str) -> str:
        """获取下一个元件编号"""
        prefix = component_type
        if component_type == "Capacitor":
            prefix = "C"
        elif component_type == "Resistor":
            prefix = "R"
        elif component_type == "Inductor":
            prefix = "L"
        elif component_type == "Diode" or component_type == "TVS Diode":
            prefix = "D"
        elif component_type == "Crystal":
            prefix = "Y"
        elif component_type == "LED":
            prefix = "LED"

        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]}"

    def _get_typical_value(self, value_str: str) -> str:
        """获取典型值"""
        # 处理 "330Ω-1kΩ" 这种范围, 取中间值或第一个
        if "-" in value_str:
            parts = value_str.split("-")
            return parts[0].strip()
        return value_str

    def _resolve_template_name(self, circuit_name: str) -> str:
        """解析模板名称 - 处理别名映射"""
        # 模板名称映射
        aliases = {
            "usb_decoupling": "decoupling",
            "input_capacitor": "decoupling",
            "output_capacitor": "decoupling",
            "bypass_capacitors": "decoupling",
            "bypass_capacitor": "decoupling",
            "pullup_resistor": "current_limit_resistor",
            "pullup_resistors": "current_limit_resistor",
            "crystal": "crystal_oscillator",
            "antenna_matching": "antenna",
        }
        return aliases.get(circuit_name, circuit_name)

    def add_required_circuits(
        self, components: List[Dict[str, Any]], base_position: tuple = (500, 500)
    ) -> List[Dict[str, Any]]:
        """
        为芯片添加必要电路

        Args:
            components: 已有元件列表
            base_position: 基础位置

        Returns:
            添加了必要电路的元件列表
        """
        enhanced_components = list(components)

        # 构建已有元件去重键集合 (name|model|footprint)
        existing_keys = set()
        for c in enhanced_components:
            key = f"{c.get('name', '')}|{c.get('model', '')}|{c.get('footprint', '')}"
            existing_keys.add(key.lower())

        # 遍历所有芯片, 检查需要的必要电路
        for comp in components:
            chip_model = comp.get("model", "")

            # 查找芯片信息
            chip_info = self.component_db.get(chip_model, {})
            required_circuits = chip_info.get("required_circuits", [])

            if not required_circuits:
                continue

            logger.info(f"芯片 {chip_model} 需要电路: {required_circuits}")

            # 为每个需要的电路添加元件
            for circuit_name in required_circuits:
                # 解析模板名称(处理别名)
                resolved_name = self._resolve_template_name(circuit_name)
                template = self.templates.get(resolved_name, {})
                if not template:
                    # 尝试原始名称
                    template = self.templates.get(circuit_name, {})
                if not template:
                    logger.warning(f"未找到电路模板: {circuit_name}")
                    continue

                # 添加模板中的元件
                template_components = template.get("components", [])
                for tmpl_comp in template_components:
                    # 跳过主芯片(已经存在)
                    if "U1" in str(tmpl_comp.get("ref", "")):
                        continue

                    # 优先使用type, 其次使用value, 最后使用ref
                    comp_type = tmpl_comp.get("type") or tmpl_comp.get(
                        "value", "Component"
                    )
                    comp_model = self._get_typical_value(tmpl_comp.get("value", ""))
                    comp_footprint = self._get_footprint_for_type(
                        tmpl_comp.get("type", "")
                    )

                    # 检查是否已存在相同元件（去重）
                    dedup_key = f"{comp_type}|{comp_model}|{comp_footprint}".lower()
                    if dedup_key in existing_keys:
                        logger.info(f"跳过重复元件: {comp_type} ({comp_model})")
                        continue

                    new_comp = {
                        "name": comp_type,
                        "model": comp_model,
                        "reference": self._get_next_ref(comp_type),
                        "position": {
                            "x": base_position[0]
                            + (len(enhanced_components) * 50) % 300,
                            "y": base_position[1]
                            + (len(enhanced_components) * 30) % 200,
                        },
                        "footprint": comp_footprint,
                        "circuits": [circuit_name],  # 标记这个元件属于哪个电路
                    }
                    enhanced_components.append(new_comp)
                    existing_keys.add(dedup_key)
                    logger.info(
                        f"添加必要电路元件: {new_comp['reference']} ({circuit_name})"
                    )

        return enhanced_components

    def _get_footprint_for_type(self, component_type: str) -> str:
        """根据元件类型获取典型封装"""
        footprint_map = {
            "Capacitor": "Capacitor_SMD:C_0402",
            "Resistor": "Resistor_SMD:R_0402",
            "LED": "LED_SMD:LED_0603",
            "Inductor": "Inductor_SMD:L_0402",
            "Diode": "Diode_SMD:D_SOD-123",
            "TVS Diode": "Diode_SMD:D_SMB",
            "Crystal": "Crystal:Crystal_SMD_3225",
            "Capacitor_Electrolytic": "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-A",
        }
        return footprint_map.get(component_type, "")


# 全局实例
_enhancer: Optional[CircuitEnhancer] = None


def get_circuit_enhancer() -> CircuitEnhancer:
    """获取电路增强器"""
    global _enhancer
    if _enhancer is None:
        _enhancer = CircuitEnhancer()
    return _enhancer


def enhance_with_required_circuits(
    components: List[Dict[str, Any]], base_position: tuple = (500, 500)
) -> List[Dict[str, Any]]:
    """增强元件列表,添加必要电路"""
    enhancer = get_circuit_enhancer()
    return enhancer.add_required_circuits(components, base_position)
