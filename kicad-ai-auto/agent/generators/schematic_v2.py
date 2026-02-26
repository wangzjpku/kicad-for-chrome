"""
原理图生成器 V2
使用 kicad-sch-api 库实现

特性：
- 自动从 KiCad 符号库读取引脚位置
- 自动正交布线
- 内置 ERC 验证
- 字节级格式保证
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 检查 kicad-sch-api 是否可用
KICAD_SCH_API_AVAILABLE = False

try:
    import kicad_sch_api as ksa
    from kicad_sch_api.validation import ElectricalRulesChecker

    KICAD_SCH_API_AVAILABLE = True
    logger.info("kicad-sch-api 已加载")
except ImportError as e:
    logger.warning(f"kicad-sch-api 未安装: {e}")
    logger.info("请运行: pip install kicad-sch-api")

# Use absolute import for compatibility
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generators import SchematicGeneratorBase, GenerationResult, GeneratorVersion


class SchematicGeneratorV2(SchematicGeneratorBase):
    """
    原理图生成器 V2

    基于 kicad-sch-api 实现，完全消除硬编码引脚位置

    特性：
    - 自动从 KiCad 符号库读取引脚位置
    - 自动正交布线 (Manhattan routing)
    - 内置 ERC 验证
    - 字节级格式保证
    """

    def __init__(self, kicad_symbol_path: Optional[str] = None):
        """
        初始化生成器

        Args:
            kicad_symbol_path: KiCad 符号库路径
                              Windows: C:/Program Files/KiCad/9.0/share/kicad/symbols
                              Linux: /usr/share/kicad/symbols
                              如果为 None，使用系统默认路径
        """
        self.kicad_symbol_path = kicad_symbol_path
        self.schematic = None

        if not KICAD_SCH_API_AVAILABLE:
            raise ImportError("kicad-sch-api 未安装。请运行: pip install kicad-sch-api")

    @property
    def version(self) -> GeneratorVersion:
        return GeneratorVersion.V2

    def generate(self, json_data: Dict[str, Any], output_path: str) -> GenerationResult:
        """
        生成 KiCad 原理图

        Args:
            json_data: 电路 JSON 数据
            output_path: 输出文件路径

        Returns:
            GenerationResult: 生成结果
        """

        if not KICAD_SCH_API_AVAILABLE:
            return GenerationResult(
                success=False, output_path=output_path, errors=["kicad-sch-api 未安装"]
            )

        try:
            # 1. 创建新原理图
            title = json_data.get("title", "AI Generated Circuit")
            self.schematic = ksa.create_schematic(title)
            logger.info(f"Created schematic: {title}")

            # 2. 添加元件
            component_map = self._add_components(json_data.get("components", []))

            # 3. 添加连线
            wire_result = self._add_wires(
                json_data.get("wires", []), json_data.get("nets", []), component_map
            )

            # 4. 添加电源符号
            self._add_power_symbols(json_data.get("powerSymbols", []))

            # 5. 添加网络标签
            self._add_labels(json_data.get("labels", []))

            # 6. 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 7. 保存文件
            self.schematic.save(output_path)

            logger.info(f"Schematic saved to: {output_path}")

            return GenerationResult(
                success=True,
                output_path=output_path,
                warnings=wire_result.get("warnings", []),
                metadata={
                    "version": "v2",
                    "source": "kicad-sch-api",
                    "component_count": len(component_map),
                },
            )

        except Exception as e:
            logger.error(f"生成失败: {e}", exc_info=True)
            return GenerationResult(
                success=False, output_path=output_path, errors=[str(e)]
            )

    def _add_components(self, components: list) -> Dict[str, Any]:
        """添加元件到原理图"""
        component_map = {}

        for comp in components:
            try:
                lib_id = comp.get("symbol_library", "Device:R")
                reference = comp.get("reference", "R1")
                value = comp.get("name", comp.get("model", ""))

                # 位置转换: JSON 用 0.01 inch 单位，API 用 mil
                # 1 inch = 1000 mil
                # 0.01 inch = 10 mil
                pos = comp.get("position", {})
                x = float(pos.get("x", 0)) * 10  # 转换为 mil
                y = float(pos.get("y", 0)) * 10

                footprint = comp.get("footprint", "")

                # 添加元件
                instance = self.schematic.components.add(
                    lib_id=lib_id,
                    reference=reference,
                    value=value,
                    position=(x, y),
                    footprint=footprint if footprint else None,
                )

                component_map[reference] = {
                    "instance": instance,
                    "lib_id": lib_id,
                    "pins": comp.get("pins", []),
                }

                logger.debug(f"Added component: {reference} ({lib_id})")

            except Exception as e:
                logger.warning(f"Failed to add component {comp.get('reference')}: {e}")

        return component_map

    def _add_wires(
        self, wires: list, nets: list, component_map: Dict
    ) -> Dict[str, Any]:
        """添加连线"""
        result = {"warnings": []}

        # 构建网络查找表
        net_lookup = {net.get("id"): net.get("name") for net in nets}

        for wire in wires:
            try:
                # 解析连接: 支持 "U2.1" 格式
                from_conn = wire.get("from", "")
                to_conn = wire.get("to", "")

                if "." not in from_conn or "." not in to_conn:
                    result["warnings"].append(
                        f"Invalid connection format: {from_conn} -> {to_conn}"
                    )
                    continue

                ref1, pin1 = from_conn.split(".", 1)
                ref2, pin2 = to_conn.split(".", 1)

                # 使用 kicad-sch-api 的自动布线
                # 它会自动找到引脚位置并计算正交路由
                self.schematic.add_wire_between_pins(ref1, pin1, ref2, pin2)

            except Exception as e:
                # 如果自动布线失败，记录警告
                logger.warning(f"Wire connection failed: {e}")
                result["warnings"].append(f"Wire {from_conn} -> {to_conn}: {e}")

                # 回退: 添加原始线段(基于点)
                self._add_manual_wire(wire)

        return result

    def _add_manual_wire(self, wire: Dict) -> None:
        """手动添加线段(回退方案)"""
        points = wire.get("points", [])
        if len(points) < 2:
            return

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            x1 = float(p1.get("x", 0)) * 10
            y1 = float(p1.get("y", 0)) * 10
            x2 = float(p2.get("x", 0)) * 10
            y2 = float(p2.get("y", 0)) * 10

            self.schematic.wires.add(start=(x1, y1), end=(x2, y2))

    def _add_power_symbols(self, power_symbols: list) -> None:
        """添加电源符号"""
        seen_types = set()

        for power in power_symbols:
            power_type = power.get("type", "vcc")

            # 避免重复电源符号
            if power_type in seen_types:
                continue
            seen_types.add(power_type)

            try:
                pos = power.get("position", {})
                x = float(pos.get("x", 0)) * 10
                y = float(pos.get("y", 0)) * 10

                if power_type == "vcc":
                    self.schematic.powerSymbols.add(name="VCC", position=(x, y))
                elif power_type == "gnd":
                    self.schematic.powerSymbols.add(name="GND", position=(x, y))

            except Exception as e:
                logger.warning(f"Failed to add power symbol: {e}")

    def _add_labels(self, labels: list) -> None:
        """添加网络标签"""
        for label in labels:
            try:
                pos = label.get("position", {})
                x = float(pos.get("x", 0)) * 10
                y = float(pos.get("y", 0)) * 10

                net_name = label.get("net", label.get("text", ""))

                self.schematic.labels.add(text=net_name, position=(x, y))

            except Exception as e:
                logger.warning(f"Failed to add label: {e}")

    def validate(self, output_path: str) -> Dict[str, Any]:
        """
        运行 ERC 验证

        Args:
            output_path: 原理图文件路径

        Returns:
            ERC 验证结果
        """
        if not KICAD_SCH_API_AVAILABLE:
            return {"error": "kicad-sch-api 未安装"}

        try:
            # 加载原理图
            sch = ksa.load_schematic(output_path)

            # 运行 ERC
            erc = ElectricalRulesChecker(sch)
            result = erc.run_all_checks()

            return {
                "has_errors": result.has_errors(),
                "has_warnings": result.has_warnings(),
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "errors": [
                    {"type": e.error_type, "message": e.message} for e in result.errors
                ],
                "warnings": [
                    {"type": w.error_type, "message": w.message}
                    for w in result.warnings
                ],
                "summary": result.summary() if result.has_errors() else "Pass",
            }

        except Exception as e:
            logger.warning(f"ERC check failed: {e}")
            return {"error": str(e)}


def is_v2_available() -> bool:
    """检查 V2 生成器是否可用"""
    return KICAD_SCH_API_AVAILABLE
