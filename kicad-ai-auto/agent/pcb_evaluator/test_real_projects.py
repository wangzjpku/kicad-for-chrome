"""
从立创开源硬件平台获取真实项目并进行测试
用于测试 Ralph Loop 迭代优化系统
"""

import json
import random
from pcb_evaluator.pcb_models import PCBMockDataGenerator
from pcb_evaluator.checkers import PCBChecker, DesignRules
from pcb_evaluator.ralph_loop import RalphLoopOptimizer


def analyze_real_project(project_name: str) -> dict:
    """
    分析一个真实项目
    模拟从立创开源平台获取的项目数据
    """
    print(f"\n{'=' * 60}")
    print(f"分析项目: {project_name}")
    print(f"{'=' * 60}")

    # 模拟不同类型的真实项目
    project_types = [
        "stm32开发板",
        "esp32物联网板",
        "电源模块",
        "Arduino兼容板",
        "蓝牙Mesh板",
    ]

    # 生成模拟数据
    board = PCBMockDataGenerator.generate_test_board_1()
    board.name = project_name

    # 根据项目类型调整一些参数
    if "电源" in project_name:
        # 电源板 - 宽走线
        for track in board.tracks:
            if track.width < 0.3:
                track.width = 0.5
    elif "esp32" in project_name.lower() or "物联网" in project_name:
        # ESP32板 - 高速信号
        for net in board.nets:
            if "WiFi" not in net.name and "BT" not in net.name:
                net.is_high_speed = True
    elif "stm32" in project_name.lower():
        # STM32板 - 晶振问题
        for comp in board.components:
            if comp.is_crystal:
                comp.position.x = 5  # 远离MCU

    return {"name": project_name, "type": random.choice(project_types), "board": board}


def run_ralph_loop_test(project_name: str, max_iterations: int = 20):
    """
    运行 Ralph Loop 测试
    """
    # 分析项目
    result = analyze_real_project(project_name)
    board = result["board"]

    print(f"\n项目类型: {result['type']}")
    print(f"板尺寸: {board.width}x{board.height}mm")
    print(f"元件数: {len(board.components)}")
    print(f"走线数: {len(board.tracks)}")
    print(f"过孔数: {len(board.vias)}")

    # 创建优化器并运行
    optimizer = RalphLoopOptimizer(max_iterations=max_iterations)
    loop_result = optimizer.optimize(board)

    # 打印结果
    optimizer.print_result(loop_result)

    return loop_result


def test_with_real_projects():
    """
    测试真实项目
    """
    print("\n" + "#" * 70)
    print("#" + " " * 20 + "立创开源项目测试" + " " * 24 + "#")
    print("#" * 70)

    # 测试项目列表 (模拟从立创获取)
    test_projects = [
        "EDA-Pager寻呼机",
        "Moji2.0小智AI机器人",
        "天空星筑基学习板",
        "立创泰山派RK3566",
        "立创梁山派开发板",
    ]

    results = []

    for project in test_projects:
        result = run_ralph_loop_test(project)
        results.append((project, result))

    # 打印总结
    print("\n" + "#" * 70)
    print("#" + " " * 25 + "测试总结" + " " * 29 + "#")
    print("#" * 70)

    for name, result in results:
        print(f"\n{name}:")
        print(f"  迭代次数: {result.total_iterations}/{20}")
        print(f"  初始问题: {len(result.initial_issues)}")
        print(f"  最终问题: {len(result.final_issues)}")
        print(f"  收敛: {'是' if result.converged else '否'}")
        print(f"  达到最大迭代: {'是' if result.max_iterations_reached else '否'}")
        print(f"  最终评分: {result.final_scores.get('总体', 0):.1f}")

    return results


def quick_test():
    """
    快速测试 - 单个项目
    """
    return run_ralph_loop_test("立创测试项目-STM32开发板")


if __name__ == "__main__":
    # 运行完整测试
    test_with_real_projects()

    # 或者运行快速测试
    # quick_test()
