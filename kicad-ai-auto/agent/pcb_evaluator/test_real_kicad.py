"""
真实 KiCad 项目测试
从 GitHub 获取真实项目，运行 Ralph Loop 分析
"""

import sys
import os
import json
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcb_evaluator.kicad_parser import KiCadPCBParser, load_kicad_project
from pcb_evaluator.ralph_loop import RalphLoopOptimizer
from pcb_evaluator.checkers import PCBChecker, DesignRules


def test_parser_on_real_project(project_path: str) -> dict:
    """测试解析器在真实项目上的表现"""
    print(f"\n{'=' * 60}")
    print(f"测试项目: {project_path}")
    print(f"{'=' * 60}")

    try:
        # 解析项目
        parser = KiCadPCBParser()
        board = parser.parse_file(project_path)

        print(f"✓ 解析成功!")
        print(f"  - 板尺寸: {board.width} x {board.height} mm")
        print(f"  - 元件数: {len(board.components)}")
        print(f"  - 走线数: {len(board.tracks)}")
        print(f"  - 过孔数: {len(board.vias)}")
        print(f"  - 网络数: {len(board.nets)}")

        # 显示元件列表
        if board.components:
            print(f"\n元件列表:")
            for comp in board.components[:10]:
                print(
                    f"  - {comp.reference}: {comp.value} @ ({comp.position.x:.1f}, {comp.position.y:.1f})"
                )

        # 检查是否有问题
        checker = PCBChecker()
        result = checker.evaluate(board)

        print(f"\n质量问题分析:")
        print(f"  - 总问题数: {len(result.issues)}")
        print(f"    - 错误: {result.error_count}")
        print(f"    - 警告: {result.warning_count}")

        if result.issues:
            print(f"\n问题详情:")
            for issue in result.issues[:10]:
                print(f"  [{issue.severity.value.upper()}] {issue.message}")

        return {
            "success": True,
            "board": board,
            "issues": result.issues,
            "scores": result.scores,
        }

    except Exception as e:
        print(f"✗ 解析失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def run_ralph_loop_on_project(project_path: str, max_iterations: int = 20) -> dict:
    """在真实项目上运行 Ralph Loop"""
    print(f"\n{'=' * 60}")
    print(f"Ralph Loop 优化: {project_path}")
    print(f"{'=' * 60}")

    try:
        # 解析项目
        parser = KiCadPCBParser()
        board = parser.parse_file(project_path)

        # 运行优化器
        optimizer = RalphLoopOptimizer(max_iterations=max_iterations)
        result = optimizer.optimize(board)

        # 打印结果
        optimizer.print_result(result)

        return {
            "success": True,
            "initial_issues": len(result.initial_issues),
            "final_issues": len(result.final_issues),
            "iterations": result.total_iterations,
            "converged": result.converged,
        }

    except Exception as e:
        print(f"✗ Ralph Loop 失败: {e}")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
        }


def run_batch_tests(project_paths: list, max_iterations: int = 20) -> dict:
    """批量测试多个项目"""
    print("\n" + "#" * 70)
    print("#" + " " * 20 + "批量真实项目测试" + " " * 22 + "#")
    print("#" * 70)

    results = []
    total_initial = 0
    total_final = 0
    total_fixed = 0

    for i, path in enumerate(project_paths, 1):
        print(f"\n{'=' * 60}")
        print(f"项目 {i}/{len(project_paths)}")
        print(f"{'=' * 60}")

        result = run_ralph_loop_on_project(path, max_iterations)

        if result["success"]:
            total_initial += result["initial_issues"]
            total_final += result["final_issues"]
            total_fixed += result["initial_issues"] - result["final_issues"]

        results.append(
            {
                "path": path,
                "result": result,
            }
        )

    # 总结
    print("\n" + "#" * 70)
    print("#" + " " * 20 + "测试总结" + " " * 29 + "#")
    print("#" * 70)

    fix_rate = (total_fixed / total_initial * 100) if total_initial > 0 else 0

    print(f"\n总项目数: {len(project_paths)}")
    print(f"总初始问题: {total_initial}")
    print(f"总修复问题: {total_fixed}")
    print(f"总剩余问题: {total_final}")
    print(f"修复率: {fix_rate:.1f}%")

    return {
        "total_projects": len(project_paths),
        "total_initial_issues": total_initial,
        "total_fixed": total_fixed,
        "total_final": total_final,
        "fix_rate": fix_rate,
        "results": results,
    }


def demo_with_sample_data():
    """使用示例数据演示"""
    print("\n" + "=" * 60)
    print("使用示例数据演示 Ralph Loop")
    print("=" * 60)

    from pcb_evaluator.pcb_models import PCBMockDataGenerator

    # 生成有问题的板子
    board = PCBMockDataGenerator.generate_test_board_1()

    print(f"\n原始板子信息:")
    print(f"  - 板尺寸: {board.width} x {board.height} mm")
    print(f"  - 元件数: {len(board.components)}")
    print(f"  - 走线数: {len(board.tracks)}")

    # 运行 Ralph Loop
    optimizer = RalphLoopOptimizer(max_iterations=20)
    result = optimizer.optimize(board)

    optimizer.print_result(result)

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="真实 KiCad 项目测试")
    parser.add_argument("--project", "-p", help="项目路径")
    parser.add_argument("--demo", "-d", action="store_true", help="运行演示")
    parser.add_argument("--batch", "-b", action="store_true", help="批量测试")

    args = parser.parse_args()

    if args.demo:
        demo_with_sample_data()
    elif args.project:
        test_parser_on_real_project(args.project)
    elif args.batch:
        # 批量测试需要先获取项目
        print("请先运行 fetch_kicad_projects.py 获取项目")
    else:
        # 默认运行演示
        demo_with_sample_data()
