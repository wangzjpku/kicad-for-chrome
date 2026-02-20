#!/usr/bin/env python
"""
Ralph Loop 自动化测试脚本
从KiCad demo项目循环测试，发现并修复解析bug
"""

import os
import sys
import json
import random
from pathlib import Path

# 添加agent目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcb_evaluator.kicad_parser import KiCadPCBParser
from pcb_evaluator.checkers import PCBChecker, DesignRules
from pcb_evaluator.ralph_loop import RalphLoopOptimizer


class RalphLoopTester:
    def __init__(self, demo_dir: str):
        self.demo_dir = demo_dir
        self.parser = KiCadPCBParser()
        self.checker = PCBChecker()
        self.projects = []
        self.bugs_found = []
        self.iteration_count = 0

    def scan_projects(self):
        """扫描所有KiCad demo项目"""
        for item in os.listdir(self.demo_dir):
            pcb_file = os.path.join(self.demo_dir, item, f"{item}.kicad_pcb")
            if os.path.exists(pcb_file):
                sch_file = os.path.join(self.demo_dir, item, f"{item}.kicad_sch")
                self.projects.append(
                    {
                        "name": item,
                        "pcb": pcb_file,
                        "sch": sch_file if os.path.exists(sch_file) else None,
                    }
                )
        print(f"找到 {len(self.projects)} 个项目")
        return self.projects

    def test_single_project(self, project: dict, max_iterations: int = 5) -> dict:
        """测试单个项目"""
        name = project["name"]
        pcb_path = project["pcb"]

        try:
            # 1. 解析PCB文件
            board = self.parser.parse_file(pcb_path)

            # 2. 检查问题
            result = self.checker.evaluate(board)

            # 3. 运行Ralph Loop
            optimizer = RalphLoopOptimizer(max_iterations=max_iterations)
            loop_result = optimizer.optimize(board)

            return {
                "success": True,
                "name": name,
                "components": len(board.components),
                "tracks": len(board.tracks),
                "vias": len(board.vias),
                "pads": len(board.pads),
                "nets": len(board.nets),
                "initial_issues": len(loop_result.initial_issues),
                "final_issues": len(loop_result.final_issues),
                "fix_rate": (
                    len(loop_result.initial_issues) - len(loop_result.final_issues)
                )
                / max(1, len(loop_result.initial_issues))
                * 100,
                "iterations": loop_result.total_iterations,
                "converged": loop_result.converged,
                "issue_types": self._count_issue_types(loop_result.initial_issues),
            }
        except Exception as e:
            return {"success": False, "name": name, "error": str(e)}

    def _count_issue_types(self, issues: list) -> dict:
        """统计问题类型"""
        from collections import Counter

        types = Counter(type(i).__name__ for i in issues)
        return dict(types)

    def run_loop_tests(self, num_iterations: int = 20, max_per_project: int = 3):
        """
        运行Ralph Loop循环测试
        """
        print(f"\n{'=' * 60}")
        print(f"Ralph Loop 循环测试开始")
        print(f"总迭代次数: {num_iterations}")
        print(f"{'=' * 60}\n")

        results = []

        for i in range(num_iterations):
            self.iteration_count = i + 1
            print(f"\n--- 循环 {i + 1}/{num_iterations} ---")

            # 随机选择一个项目
            project = random.choice(self.projects)

            # 测试该项目
            result = self.test_single_project(project, max_iterations=max_per_project)
            results.append(result)

            if result["success"]:
                print(f"  项目: {result['name']}")
                print(f"    元件: {result['components']}, 走线: {result['tracks']}")
                print(
                    f"    初始问题: {result['initial_issues']}, 最终问题: {result['final_issues']}"
                )
                print(f"    修复率: {result['fix_rate']:.1f}%")

                # 检查是否有解析问题
                if result["components"] == 0:
                    print(f"    [BUG] 元件数量为0！")
                    self.bugs_found.append(
                        {
                            "iteration": i + 1,
                            "project": result["name"],
                            "bug": "元件数量解析为0",
                        }
                    )

                if result["tracks"] == 0 and result["vias"] > 0:
                    print(f"    [WARNING] 无走线但有过孔")

                if result["initial_issues"] > 1000:
                    print(f"    [INFO] 问题数量较多: {result['initial_issues']}")
            else:
                print(f"  项目: {result['name']}")
                print(f"    [ERROR] {result.get('error', 'Unknown error')}")
                self.bugs_found.append(
                    {
                        "iteration": i + 1,
                        "project": result["name"],
                        "bug": result.get("error", "Unknown error"),
                    }
                )

        return results

    def print_summary(self, results: list):
        """打印测试总结"""
        print(f"\n{'=' * 60}")
        print("测试总结")
        print(f"{'=' * 60}")

        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        print(f"\n总测试次数: {len(results)}")
        print(f"成功: {len(successful)}")
        print(f"失败: {len(failed)}")

        if successful:
            total_issues = sum(r["initial_issues"] for r in successful)
            total_fixed = sum(
                r["initial_issues"] - r["final_issues"] for r in successful
            )
            avg_fix_rate = sum(r["fix_rate"] for r in successful) / len(successful)

            print(f"\n问题统计:")
            print(f"  总初始问题: {total_issues}")
            print(f"  总修复问题: {total_fixed}")
            print(f"  平均修复率: {avg_fix_rate:.1f}%")

        if self.bugs_found:
            print(f"\n发现 {len(self.bugs_found)} 个问题:")
            for bug in self.bugs_found:
                print(f"  [{bug['iteration']}] {bug['project']}: {bug['bug']}")

        return {
            "total": len(results),
            "success": len(successful),
            "failed": len(failed),
            "bugs": self.bugs_found,
        }


def main():
    # 项目目录
    demo_dir = "E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-source/demos"

    # 创建测试器
    tester = RalphLoopTester(demo_dir)

    # 扫描项目
    projects = tester.scan_projects()

    # 运行循环测试
    results = tester.run_loop_tests(num_iterations=20, max_per_project=3)

    # 打印总结
    summary = tester.print_summary(results)

    # 保存结果
    output_file = "ralph_loop_test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": summary, "results": results, "bugs": tester.bugs_found},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n结果已保存到: {output_file}")

    return summary


if __name__ == "__main__":
    main()
