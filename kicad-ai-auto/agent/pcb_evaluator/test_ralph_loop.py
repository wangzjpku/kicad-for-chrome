"""
Ralph Loop 测试文件
测试迭代优化功能，确保最大迭代次数 20 次
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcb_evaluator.pcb_models import PCBMockDataGenerator
from pcb_evaluator.checkers import PCBChecker, DesignRules
from pcb_evaluator.ralph_loop import RalphLoopOptimizer


def test_with_problematic_board():
    """测试有问题的 PCB 板"""
    print("\n" + "=" * 70)
    print("测试 1: 有多种问题的 PCB 板")
    print("=" * 70)

    # 生成测试板
    board = PCBMockDataGenerator.generate_test_board_1()
    print(f"测试板: {board.name}")
    print(f"板尺寸: {board.width}x{board.height}mm")
    print(f"元件数: {len(board.components)}")
    print(f"走线数: {len(board.tracks)}")
    print(f"过孔数: {len(board.vias)}")
    print(f"铺铜数: {len(board.zones)}")

    # 创建优化器 (最大迭代 20 次)
    optimizer = RalphLoopOptimizer(max_iterations=20)

    # 运行优化
    result = optimizer.optimize(board)

    # 打印结果
    optimizer.print_result(result)

    return result


def test_with_clean_board():
    """测试干净的 PCB 板"""
    print("\n" + "=" * 70)
    print("测试 2: 干净的 PCB 板")
    print("=" * 70)

    # 生成干净板
    board = PCBMockDataGenerator.generate_clean_board()
    print(f"测试板: {board.name}")

    # 创建优化器
    optimizer = RalphLoopOptimizer(max_iterations=20)

    # 运行优化
    result = optimizer.optimize(board)

    # 打印结果
    optimizer.print_result(result)

    return result


def test_with_random_board():
    """测试随机有问题的 PCB 板"""
    print("\n" + "=" * 70)
    print("测试 3: 随机有问题的 PCB 板")
    print("=" * 70)

    # 生成随机板
    board = PCBMockDataGenerator.generate_random_board(num_issues=10)
    print(f"测试板: {board.name}")
    print(f"板尺寸: {board.width}x{board.height}mm")
    print(f"元件数: {len(board.components)}")
    print(f"走线数: {len(board.tracks)}")
    print(f"过孔数: {len(board.vias)}")

    # 创建优化器
    optimizer = RalphLoopOptimizer(max_iterations=20)

    # 运行优化
    result = optimizer.optimize(board)

    # 打印结果
    optimizer.print_result(result)

    return result


def run_all_tests():
    """运行所有测试"""
    print("\n" + "#" * 70)
    print("#" + " " * 20 + "Ralph Loop 迭代优化测试" + " " * 21 + "#")
    print("#" * 70)

    results = []

    # 测试 1: 有问题的板
    result1 = test_with_problematic_board()
    results.append(("问题板", result1))

    # 测试 2: 干净板
    result2 = test_with_clean_board()
    results.append(("干净板", result2))

    # 测试 3: 随机板
    result3 = test_with_random_board()
    results.append(("随机板", result3))

    # 打印总结
    print("\n" + "#" * 70)
    print("#" + " " * 25 + "测试总结" + " " * 28 + "#")
    print("#" * 70)

    for name, result in results:
        print(f"\n{name}:")
        print(f"  迭代次数: {result.total_iterations}/20")
        print(f"  初始问题: {len(result.initial_issues)}")
        print(f"  最终问题: {len(result.final_issues)}")
        print(f"  收敛: {'是' if result.converged else '否'}")
        print(f"  达到最大迭代: {'是' if result.max_iterations_reached else '否'}")
        print(f"  最终评分: {result.final_scores.get('总体', 0):.1f}")

    print("\n" + "#" * 70)
    print("#" + " " * 30 + "测试完成" + " " * 29 + "#")
    print("#" * 70 + "\n")

    return results


def test_iteration_count():
    """测试迭代次数是否达到 20 次"""
    print("\n" + "=" * 70)
    print("测试: 验证迭代次数")
    print("=" * 70)

    # 生成一个有足够多问题的板，确保会进行多次迭代
    board = PCBMockDataGenerator.generate_test_board_1()

    # 确保有很多走线问题
    for i in range(30):
        from pcb_models import Track, Point2D, Net

        net = Net(f"net_test_{i}", f"TEST_{i}")
        board.nets.append(net)
        track = Track(
            f"track_extra_{i}",
            net.id,
            [Point2D(10 + i, 10), Point2D(20 + i, 20)],
            0.05,  # 很细的走线
            "F.Cu",
        )
        board.tracks.append(track)

    print(f"添加额外走线后，总走线数: {len(board.tracks)}")

    # 创建优化器
    optimizer = RalphLoopOptimizer(max_iterations=20)

    # 运行优化
    result = optimizer.optimize(board)

    print(f"\n迭代次数: {result.total_iterations}")
    print(f"是否达到最大迭代: {result.max_iterations_reached}")

    return result


if __name__ == "__main__":
    # 运行所有测试
    run_all_tests()

    # 测试迭代次数
    test_iteration_count()
