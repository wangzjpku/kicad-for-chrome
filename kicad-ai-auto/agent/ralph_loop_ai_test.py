#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ralph Loop AI 生成功能迭代测试
- 模拟用户使用 AI 生成电路
- 评估原理图、PCB封装、网络连接
- 迭代修复直到符合规范
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import io

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加agent目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果"""

    test_name: str
    passed: bool
    score: float
    issues: List[str]
    details: Dict[str, Any]


class AIGeneratorEvaluator:
    """AI生成功能评估器"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.iteration = 0

    def evaluate_schematic(self, schematic_data: Dict) -> TestResult:
        """评估原理图数据"""
        issues = []
        score = 100.0

        components = schematic_data.get("components", [])
        wires = schematic_data.get("wires", [])
        nets = schematic_data.get("nets", [])

        # 1. 检查元件数量
        if len(components) == 0:
            issues.append("❌ 没有元件")
            score -= 50
        else:
            logger.info(f"  ✅ 元件数量: {len(components)}")

        # 2. 检查元件必要字段
        for i, comp in enumerate(components):
            required_fields = ["name", "reference", "position"]
            for field in required_fields:
                if field not in comp:
                    issues.append(f"❌ 元件 {i} 缺少字段: {field}")
                    score -= 5

            # 检查位置是否有效
            pos = comp.get("position", {})
            if isinstance(pos, dict):
                if pos.get("x") is None or pos.get("y") is None:
                    issues.append(f"❌ 元件 {comp.get('name', i)} 位置无效")
                    score -= 5
            elif isinstance(pos, (list, tuple)):
                if len(pos) < 2:
                    issues.append(f"❌ 元件 {comp.get('name', i)} 位置格式错误")
                    score -= 5

        # 3. 检查引脚
        for comp in components:
            pins = comp.get("pins", [])
            if len(pins) == 0:
                name = comp.get("name", "unknown")
                # 某些元件可能没有引脚（如测试点）
                if name not in ["测试点", "TestPoint"]:
                    issues.append(f"⚠️ 元件 {name} 没有引脚")
                    score -= 2

        # 4. 检查导线
        if len(wires) == 0:
            issues.append("⚠️ 没有导线连接")
            score -= 10
        else:
            logger.info(f"  ✅ 导线数量: {len(wires)}")
            # 检查导线是否有有效坐标
            for i, wire in enumerate(wires):
                points = wire.get("points", [])
                if len(points) < 2:
                    issues.append(f"❌ 导线 {i} 点数不足")
                    score -= 5

        # 5. 检查网络
        if len(nets) == 0:
            issues.append("⚠️ 没有定义网络")
            score -= 10
        else:
            logger.info(f"  ✅ 网络数量: {len(nets)}")
            # 检查是否有 VCC 和 GND
            net_names = [n.get("name", "").upper() for n in nets]
            if (
                "VCC" not in net_names
                and "+5V" not in net_names
                and "3.3V" not in net_names
            ):
                issues.append("⚠️ 缺少电源网络 (VCC/+5V/3.3V)")
                score -= 5
            if "GND" not in net_names:
                issues.append("⚠️ 缺少地网络 (GND)")
                score -= 5

        return TestResult(
            test_name="原理图评估",
            passed=len(issues) == 0,
            score=max(0, score),
            issues=issues,
            details={
                "component_count": len(components),
                "wire_count": len(wires),
                "net_count": len(nets),
            },
        )

    def evaluate_pcb(self, pcb_data: Dict) -> TestResult:
        """评估PCB数据"""
        issues = []
        score = 100.0

        footprints = pcb_data.get("footprints", [])
        tracks = pcb_data.get("tracks", [])
        vias = pcb_data.get("vias", [])
        zones = pcb_data.get("zones", [])
        nets = pcb_data.get("nets", [])

        # 1. 检查封装数量
        if len(footprints) == 0:
            issues.append("❌ 没有PCB封装")
            score -= 50
        else:
            logger.info(f"  ✅ 封装数量: {len(footprints)}")

        # 2. 检查封装必要字段
        for i, fp in enumerate(footprints):
            required_fields = ["reference", "position"]
            for field in required_fields:
                if field not in fp:
                    issues.append(f"❌ 封装 {i} 缺少字段: {field}")
                    score -= 5

            # 检查位置
            pos = fp.get("position", {})
            if isinstance(pos, dict):
                if pos.get("x") is None or pos.get("y") is None:
                    issues.append(f"❌ 封装 {fp.get('reference', i)} 位置无效")
                    score -= 5

            # 检查封装名称
            footprint_name = fp.get("footprint", "")
            if not footprint_name:
                issues.append(f"⚠️ 封装 {fp.get('reference', i)} 没有指定封装名称")
                score -= 3
            elif ":" not in footprint_name:
                issues.append(
                    f"⚠️ 封装 {fp.get('reference', i)} 封装名称格式不标准: {footprint_name}"
                )
                score -= 2

            # 检查焊盘
            pads = fp.get("pad", fp.get("pads", []))
            if len(pads) == 0:
                name = fp.get("reference", "unknown")
                # 连接器可能没有焊盘
                if "Connector" not in footprint_name:
                    issues.append(f"⚠️ 封装 {name} 没有焊盘")
                    score -= 2

        # 3. 检查网络
        if len(nets) == 0:
            issues.append("❌ PCB没有定义网络")
            score -= 20
        else:
            logger.info(f"  ✅ PCB网络数量: {len(nets)}")

        # 4. 检查走线（可选，但最好有）
        if len(tracks) > 0:
            logger.info(f"  ✅ 走线数量: {len(tracks)}")

        # 5. 检查铜皮（可选）
        if len(zones) > 0:
            logger.info(f"  ✅ 铜皮数量: {len(zones)}")

        return TestResult(
            test_name="PCB评估",
            passed=len([i for i in issues if i.startswith("❌")]) == 0,
            score=max(0, score),
            issues=issues,
            details={
                "footprint_count": len(footprints),
                "track_count": len(tracks),
                "via_count": len(vias),
                "zone_count": len(zones),
                "net_count": len(nets),
            },
        )

    def evaluate_schematic_pcb_consistency(
        self, schematic_data: Dict, pcb_data: Dict
    ) -> TestResult:
        """评估原理图和PCB一致性"""
        issues = []
        score = 100.0

        schematic_components = schematic_data.get("components", [])
        pcb_footprints = pcb_data.get("footprints", [])

        # 1. 检查元件数量一致
        if len(schematic_components) != len(pcb_footprints):
            issues.append(
                f"❌ 元件数量不一致: 原理图 {len(schematic_components)} vs PCB {len(pcb_footprints)}"
            )
            score -= 20

        # 2. 检查位号一致
        sch_refs = set()
        for comp in schematic_components:
            ref = comp.get("reference", "")
            if ref:
                sch_refs.add(ref)

        pcb_refs = set()
        for fp in pcb_footprints:
            ref = fp.get("reference", "")
            if ref:
                pcb_refs.add(ref)

        missing_in_pcb = sch_refs - pcb_refs
        if missing_in_pcb:
            issues.append(f"❌ PCB缺少位号: {missing_in_pcb}")
            score -= 10

        extra_in_pcb = pcb_refs - sch_refs
        if extra_in_pcb:
            issues.append(f"⚠️ PCB多余位号: {extra_in_pcb}")
            score -= 5

        # 3. 检查网络一致
        sch_nets = set(n.get("name", "") for n in schematic_data.get("nets", []))
        pcb_nets = set(n.get("name", "") for n in pcb_data.get("nets", []))

        # 过滤空网络名
        sch_nets = set(n for n in sch_nets if n)
        pcb_nets = set(n for n in pcb_nets if n)

        # VCC 和 +5V 应该被视为等效
        if "+5V" in sch_nets:
            sch_nets.discard("+5V")
            sch_nets.add("VCC")
        if "VCC" in pcb_nets:
            pcb_nets.discard("VCC")
            pcb_nets.add("VCC")

        missing_nets = sch_nets - pcb_nets
        if missing_nets:
            issues.append(f"⚠️ PCB缺少网络: {missing_nets}")
            score -= 5

        return TestResult(
            test_name="原理图-PCB一致性",
            passed=len([i for i in issues if i.startswith("❌")]) == 0,
            score=max(0, score),
            issues=issues,
            details={
                "schematic_refs": list(sch_refs),
                "pcb_refs": list(pcb_refs),
                "schematic_nets": list(sch_nets),
                "pcb_nets": list(pcb_nets),
            },
        )


def run_ralph_loop_test():
    """运行 Ralph Loop 迭代测试"""
    from routes.ai_routes import mock_ai_analyze, AnalyzeRequest

    evaluator = AIGeneratorEvaluator()
    test_cases = [
        "5V稳压电源",
        "12V直流输入5V输出的稳压电源",
        "3.3V稳压电源 AMS1117",
        "LED驱动电路",
    ]

    print("=" * 80)
    print("Ralph Loop AI 生成功能迭代测试")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 80)

    all_passed = True
    iteration = 1
    max_iterations = 3

    while iteration <= max_iterations:
        print(f"\n{'=' * 40}")
        print(f"迭代 {iteration}/{max_iterations}")
        print(f"{'=' * 40}")

        iteration_passed = True
        iteration_issues = []

        for test_input in test_cases:
            print(f"\n--- 测试用例: {test_input} ---")

            # 调用 AI 分析
            try:
                result = mock_ai_analyze(test_input)
                schematic_data = result.schematic.model_dump()

                # 模拟从原理图生成 PCB 数据
                pcb_data = generate_mock_pcb_from_schematic(schematic_data)

                # 评估原理图
                print("\n[评估原理图]")
                sch_result = evaluator.evaluate_schematic(schematic_data)
                print(f"  分数: {sch_result.score:.1f}")
                print(f"  通过: {'✅' if sch_result.passed else '❌'}")
                if sch_result.issues:
                    for issue in sch_result.issues:
                        print(f"    {issue}")
                if not sch_result.passed:
                    iteration_passed = False
                    iteration_issues.extend(sch_result.issues)

                # 评估 PCB
                print("\n[评估PCB]")
                pcb_result = evaluator.evaluate_pcb(pcb_data)
                print(f"  分数: {pcb_result.score:.1f}")
                print(f"  通过: {'✅' if pcb_result.passed else '❌'}")
                if pcb_result.issues:
                    for issue in pcb_result.issues:
                        print(f"    {issue}")
                if not pcb_result.passed:
                    iteration_passed = False
                    iteration_issues.extend(pcb_result.issues)

                # 评估一致性
                print("\n[评估一致性]")
                consistency_result = evaluator.evaluate_schematic_pcb_consistency(
                    schematic_data, pcb_data
                )
                print(f"  分数: {consistency_result.score:.1f}")
                print(f"  通过: {'✅' if consistency_result.passed else '❌'}")
                if consistency_result.issues:
                    for issue in consistency_result.issues:
                        print(f"    {issue}")
                if not consistency_result.passed:
                    iteration_passed = False
                    iteration_issues.extend(consistency_result.issues)

                # 输出详细信息
                print("\n[生成数据详情]")
                spec = (
                    result.spec.model_dump()
                    if hasattr(result.spec, "model_dump")
                    else result.spec
                )
                print(f"  项目名称: {spec.get('name', 'N/A')}")
                comps = spec.get("components", [])
                print(f"  元件列表: {len(comps)} 个")
                for comp in comps[:5]:  # 只显示前5个
                    print(
                        f"    - {comp.get('name', 'N/A')}: {comp.get('model', 'N/A')} x{comp.get('quantity', 1)}"
                    )
                if len(comps) > 5:
                    print(f"    ... 还有 {len(comps) - 5} 个")

            except Exception as e:
                print(f"❌ 测试失败: {e}")
                import traceback

                traceback.print_exc()
                iteration_passed = False
                iteration_issues.append(f"测试异常: {str(e)}")

        if iteration_passed:
            print(f"\n{'=' * 40}")
            print(f"✅ 迭代 {iteration} 全部通过!")
            print(f"{'=' * 40}")
            all_passed = True
            break
        else:
            print(f"\n{'=' * 40}")
            print(f"❌ 迭代 {iteration} 有问题，需要修复")
            print(f"问题列表:")
            for issue in iteration_issues:
                print(f"  - {issue}")
            print(f"{'=' * 40}")
            all_passed = False
            # 这里应该自动修复问题，然后再次迭代
            # 但由于这是演示，我们只是记录问题
            iteration += 1

    print("\n" + "=" * 80)
    print("Ralph Loop 测试结束")
    print(f"结束时间: {datetime.now().isoformat()}")
    print(f"最终状态: {'✅ 全部通过' if all_passed else '❌ 仍有问题'}")
    print("=" * 80)

    return all_passed


def generate_mock_pcb_from_schematic(schematic_data: Dict) -> Dict:
    """从原理图数据生成模拟的 PCB 数据"""
    from footprint_library import infer_component_type, get_default_footprint

    components = schematic_data.get("components", [])
    wires = schematic_data.get("wires", [])
    nets = schematic_data.get("nets", [])

    # 生成封装
    footprints = []
    for i, comp in enumerate(components):
        name = comp.get("name", "")
        model = comp.get("model", "")
        ref = comp.get("reference", f"U{i + 1}")
        pos = comp.get("position", {"x": i * 50, "y": 0})

        # 获取封装
        footprint_name = comp.get("footprint", "")
        if not footprint_name:
            comp_type = infer_component_type(name, model)
            footprint_name = get_default_footprint(comp_type)

        footprints.append(
            {
                "id": f"fp-{i + 1}",
                "reference": ref,
                "value": model or name,
                "position": pos,
                "footprint": footprint_name,
                "pad": [],
                "layer": "F.Cu",
            }
        )

    # 生成网络
    pcb_nets = []
    for net in nets:
        pcb_nets.append(
            {
                "id": net.get("id", f"net-{net.get('name', '')}"),
                "name": net.get("name", ""),
            }
        )

    # 确保有 VCC 和 GND
    net_names = [n["name"] for n in pcb_nets]
    if "GND" not in net_names:
        pcb_nets.append({"id": "net-gnd", "name": "GND"})
    if "VCC" not in net_names and "+5V" not in net_names:
        pcb_nets.append({"id": "net-vcc", "name": "VCC"})

    # 生成走线（从原理图导线转换）
    tracks = []
    for i, wire in enumerate(wires):
        points = wire.get("points", [])
        if len(points) >= 2:
            tracks.append(
                {
                    "id": f"track-{i + 1}",
                    "net": wire.get("net", ""),
                    "layer": "F.Cu",
                    "width": 0.25,
                    "points": points,
                }
            )

    return {
        "id": "pcb-test",
        "projectId": "project-test",
        "boardOutline": {"type": "rect", "width": 100, "height": 80},
        "footprints": footprints,
        "tracks": tracks,
        "vias": [],
        "zones": [],
        "texts": [],
        "nets": pcb_nets,
        "netclasses": [],
        "designRules": {
            "minTrackWidth": 0.1,
            "minViaDiameter": 0.4,
            "minClearance": 0.1,
        },
    }


if __name__ == "__main__":
    success = run_ralph_loop_test()
    sys.exit(0 if success else 1)
