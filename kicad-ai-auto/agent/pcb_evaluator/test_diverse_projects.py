"""
多样化的真实项目模拟测试
模拟从 oshwhub.com 获取的各种类型的真实项目
"""

import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcb_evaluator.pcb_models import (
    PCBBoard,
    Component,
    Track,
    Via,
    Zone,
    Net,
    Point2D,
)
from pcb_evaluator.ralph_loop import RalphLoopOptimizer


# 各种类型的真实项目模拟
def create_stm32_board() -> PCBBoard:
    """STM32 开发板 - 模拟 oshwhub 热门项目"""
    board = PCBBoard(name="STM32F103C8T6开发板", width=70.0, height=50.0)

    # 网络定义 - 模拟真实项目
    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
        Net(
            "net3",
            "USB_DP",
            is_differential_pair=True,
            differential_pair_partner="net4",
        ),
        Net(
            "net4",
            "USB_DM",
            is_differential_pair=True,
            differential_pair_partner="net3",
        ),
        Net("net5", "SWDIO"),
        Net("net6", "SWCLK"),
        Net("net7", "NRST"),
    ]
    board.nets = nets

    # MCU
    board.components.append(
        Component(
            "U1",
            "U1",
            "STM32F103C8T6",
            "LQFP-48",
            Point2D(35, 25),
            is_mcu=True,
            is_ic=True,
        )
    )

    # 晶振 - 距离可能不合适
    board.components.append(
        Component(
            "Y1",
            "Y1",
            "8MHz",
            "HC-49",
            Point2D(55, 35),
            is_crystal=True,  # 距离较远
        )
    )

    # 去耦电容 - 位置可能不合适
    board.components.append(
        Component(
            "C1",
            "C1",
            "100nF",
            "0805",
            Point2D(10, 40),  # 距离较远
        )
    )
    board.components.append(
        Component(
            "C2",
            "C2",
            "10uF",
            "1206",
            Point2D(60, 10),  # 距离较远
        )
    )

    # USB 连接器
    board.components.append(
        Component(
            "J1", "J1", "USB-Micro", "USB-Micro-B", Point2D(68, 25), is_connector=True
        )
    )

    # 电源走线 - 可能过窄
    board.tracks.append(
        Track(
            "track1",
            "net1",
            [Point2D(10, 45), Point2D(20, 35), Point2D(35, 25)],
            width=0.15,
            layer="F.Cu",  # 偏窄
        )
    )

    # USB 差分对
    board.tracks.append(
        Track(
            "track2",
            "net3",
            [Point2D(68, 23), Point2D(60, 25), Point2D(50, 25), Point2D(35, 25)],
            width=0.2,
            layer="F.Cu",
        )
    )
    board.tracks.append(
        Track(
            "track3",
            "net4",
            [Point2D(68, 27), Point2D(55, 25), Point2D(35, 25)],
            width=0.2,
            layer="F.Cu",  # 长度差异较大
        )
    )

    # 过孔
    board.vias.append(Via("V1", "net2", Point2D(35, 25), 0.5, 0.3))

    return board


def create_esp32_board() -> PCBBoard:
    """ESP32 开发板 - 模拟 RF 相关项目"""
    board = PCBBoard(name="ESP32-WROOM开发板", width=50.0, height=30.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
        Net("net3", "ANT", is_high_speed=True),
    ]
    board.nets = nets

    # ESP32 模块
    board.components.append(
        Component("U1", "U1", "ESP32-WROOM", "Module", Point2D(25, 15), is_mcu=True)
    )

    # 天线
    board.components.append(
        Component("ANT1", "ANT1", "PCB Antenna", "Chip", Point2D(45, 15))
    )

    # 金属屏蔽罩 - 靠近天线
    board.components.append(
        Component(
            "FH1",
            "FH1",
            "Shield",
            "Shield",
            Point2D(35, 15),  # 太靠近天线
        )
    )

    # RF 走线 - 可能过细
    board.tracks.append(
        Track(
            "track1",
            "net3",
            [Point2D(45, 15), Point2D(35, 15), Point2D(25, 15)],
            width=0.1,
            layer="F.Cu",  # RF走线过细
        )
    )

    return board


def create_power_module() -> PCBBoard:
    """电源模块 - 模拟高电流设计"""
    board = PCBBoard(name="12V转5V降压模块", width=40.0, height=30.0)

    nets = [
        Net("net1", "VIN", is_power_supply=True),
        Net("net2", "VOUT", is_power_supply=True),
        Net("net3", "GND", is_ground=True),
    ]
    board.nets = nets

    # 电容
    board.components.append(Component("C1", "C1", "100uF", "CAP", Point2D(5, 15)))
    board.components.append(Component("C2", "C2", "470uF", "CAP", Point2D(35, 15)))

    # 芯片
    board.components.append(
        Component("U1", "U1", "LM2596", "TO-263", Point2D(20, 15), is_heatsink=True)
    )

    # 电源走线 - 模拟高电流走线过窄
    for i in range(3):
        board.tracks.append(
            Track(
                f"track{i}",
                "net1",
                [Point2D(5, 15), Point2D(10 + i * 3, 15), Point2D(20, 15)],
                width=0.2,
                layer="F.Cu",  # 过窄
            )
        )

    board.tracks.append(
        Track(
            "track_out",
            "net2",
            [Point2D(20, 15), Point2D(35, 15)],
            width=0.25,
            layer="F.Cu",  # 对于2A输出来说偏窄
        )
    )

    return board


def create_usb_hub() -> PCBBoard:
    """USB Hub - 模拟高速信号设计"""
    board = PCBBoard(name="USB Hub 4端口", width=60.0, height=40.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
    ]

    # USB 差分对
    for i in range(4):
        nets.append(
            Net(
                f"dp{i}",
                f"USB{i}_DP",
                is_differential_pair=True,
                differential_pair_partner=f"dm{i}",
            )
        )
        nets.append(
            Net(
                f"dm{i}",
                f"USB{i}_DM",
                is_differential_pair=True,
                differential_pair_partner=f"dp{i}",
            )
        )

    board.nets = nets

    # USB 连接器
    for i in range(4):
        board.components.append(
            Component(
                f"J{i + 1}",
                f"J{i + 1}",
                "USB-A",
                "USB-A",
                Point2D(10 + i * 12, 35),
                is_connector=True,
            )
        )

    # USB 差分走线 - 模拟长度不匹配
    for i in range(4):
        # 长走线
        board.tracks.append(
            Track(
                f"dp{i}",
                f"dp{i}",
                [Point2D(10 + i * 12, 35), Point2D(10 + i * 12, 20), Point2D(30, 20)],
                width=0.2,
                layer="F.Cu",
            )
        )
        # 短走线 - 长度差异
        board.tracks.append(
            Track(
                f"dm{i}",
                f"dm{i}",
                [Point2D(10 + i * 12, 33), Point2D(30, 20)],
                width=0.2,
                layer="F.Cu",
            )
        )

    return board


def create_bluetooth_board() -> PCBBoard:
    """蓝牙模块 - 模拟 2.4G RF 设计"""
    board = PCBBoard(name="蓝牙音频接收板", width=45.0, height=25.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
        Net("net3", "RF", is_high_speed=True),
    ]
    board.nets = nets

    # 蓝牙芯片
    board.components.append(
        Component("U1", "U1", "CSR8670", "QFN", Point2D(20, 12), is_mcu=True)
    )

    # 天线
    board.components.append(
        Component("ANT1", "ANT1", "Chip Antenna", "0603", Point2D(40, 12))
    )

    # 金属元件
    board.components.append(
        Component(
            "L1",
            "L1",
            "Inductor",
            "0603",
            Point2D(35, 12),  # 靠近天线
        )
    )

    # RF 走线
    board.tracks.append(
        Track(
            "track1",
            "net3",
            [Point2D(40, 12), Point2D(30, 12), Point2D(20, 12)],
            width=0.15,
            layer="F.Cu",  # 偏细
        )
    )

    return board


def create_mcu_board() -> PCBBoard:
    """单片机开发板"""
    board = PCBBoard(name="51单片机开发板", width=80.0, height=60.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
    ]
    board.nets = nets

    # MCU
    board.components.append(
        Component(
            "U1", "U1", "STC89C52", "DIP-40", Point2D(40, 30), is_mcu=True, is_ic=True
        )
    )

    # 晶振 - 位置不当
    board.components.append(
        Component(
            "Y1",
            "Y1",
            "11.0592MHz",
            "HC-49",
            Point2D(10, 10),
            is_crystal=True,  # 太远
        )
    )

    # 去耦电容 - 位置不当
    board.components.append(
        Component(
            "C1",
            "C1",
            "30pF",
            "0805",
            Point2D(70, 50),  # 太远
        )
    )

    # 走线 - 可能有问题
    board.tracks.append(
        Track(
            "track1",
            "net1",
            [Point2D(10, 10), Point2D(40, 30)],
            width=0.1,
            layer="F.Cu",
        )
    )

    return board


# 更多项目类型...
def create_audio_amp() -> PCBBoard:
    """音频放大器"""
    board = PCBBoard(name="音频功率放大器", width=50.0, height=35.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
    ]
    board.nets = nets

    # 功放芯片
    board.components.append(
        Component("U1", "U1", "TDA2030", "TO-220", Point2D(25, 17), is_heatsink=True)
    )

    # 输入电容
    board.components.append(
        Component("C1", "C1", "1uF", " electrolytic", Point2D(10, 17))
    )

    # 发热元件间距问题
    board.components.append(
        Component("U2", "U2", "LM7805", "TO-220", Point2D(25, 25), is_heatsink=True)
    )

    return board


def create_led_driver() -> PCBBoard:
    """LED 驱动板"""
    board = PCBBoard(name="LED调光驱动板", width=30.0, height=20.0)

    nets = [
        Net("net1", "VIN", is_power_supply=True),
        Net("net2", "LED+", is_power_supply=True),
        Net("net3", "GND", is_ground=True),
    ]
    board.nets = nets

    # 驱动芯片
    board.components.append(
        Component("U1", "U1", "PT4115", "SOT-89", Point2D(15, 10), is_heatsink=True)
    )

    # LED
    board.components.append(Component("D1", "D1", "LED", "5mm", Point2D(25, 10)))

    # 电感 - 发热
    board.components.append(
        Component("L1", "L1", "100uH", "CD32", Point2D(15, 5), is_heatsink=True)
    )

    return board


def create_sensor_board() -> PCBBoard:
    """传感器模块"""
    board = PCBBoard(name="温湿度传感器模块", width=25.0, height=15.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
        Net("net3", "DATA"),
    ]
    board.nets = nets

    # 传感器芯片
    board.components.append(
        Component("U1", "U1", "DHT22", "Module", Point2D(12, 7), is_ic=True)
    )

    # 去耦电容 - 距离太远
    board.components.append(
        Component(
            "C1",
            "C1",
            "100nF",
            "0603",
            Point2D(2, 12),  # 太远
        )
    )

    return board


def create_display_board() -> PCBBoard:
    """显示屏驱动板"""
    board = PCBBoard(name="OLED显示屏驱动", width=40.0, height=25.0)

    nets = [
        Net("net1", "VCC", is_power_supply=True),
        Net("net2", "GND", is_ground=True),
    ]
    board.nets = nets

    # OLED 屏幕
    board.components.append(
        Component(
            "J1", "J1", "OLED 0.96", "Connector", Point2D(30, 12), is_connector=True
        )
    )

    # 主控
    board.components.append(
        Component("U1", "U1", "ESP8266", "ESP-12F", Point2D(15, 12), is_mcu=True)
    )

    # 晶振
    board.components.append(
        Component(
            "Y1",
            "Y1",
            "26MHz",
            "3225",
            Point2D(5, 5),
            is_crystal=True,  # 距离较远
        )
    )

    return board


# 项目工厂
PROJECT_TYPES = [
    ("STM32开发板", create_stm32_board),
    ("ESP32开发板", create_esp32_board),
    ("电源模块", create_power_module),
    ("USB Hub", create_usb_hub),
    ("蓝牙模块", create_bluetooth_board),
    ("单片机开发板", create_mcu_board),
    ("音频放大器", create_audio_amp),
    ("LED驱动", create_led_driver),
    ("传感器模块", create_sensor_board),
    ("显示屏驱动", create_display_board),
]


def run_diverse_projects_test(num_projects: int = 20):
    """运行多样化项目测试"""
    print("\n" + "#" * 70)
    print("#" + " " * 15 + "多样化真实项目模拟测试" + " " * 17 + "#")
    print("#" * 70)

    # 生成多个不同类型的项目
    boards = []
    for i in range(num_proprojects):
        # 随机选择项目类型
        name, creator = random.choice(PROJECT_TYPES)
        board = creator()
        board.name = f"{name}_{i + 1}"
        boards.append((name, board))

    total_initial = 0
    total_final = 0
    results = []

    for i, (name, board) in enumerate(boards, 1):
        print(f"\n{'=' * 60}")
        print(f"项目 {i}/{num_projects}: {name}")
        print(f"{'=' * 60}")

        print(f"  原始: {len(board.components)} 器件, {len(board.tracks)} 走线")

        # 运行 Ralph Loop
        optimizer = RalphLoopOptimizer(max_iterations=20)
        result = optimizer.optimize(board)

        initial = len(result.initial_issues)
        final = len(result.final_issues)
        fixed = initial - final

        total_initial += initial
        total_final += final

        print(f"  迭代: {result.total_iterations}")
        print(f"  问题: {initial} -> {final} (修复 {fixed})")

        results.append(
            {
                "name": name,
                "initial": initial,
                "final": final,
                "fixed": fixed,
                "iterations": result.total_iterations,
                "converged": result.converged,
            }
        )

    # 总结
    print("\n" + "#" * 70)
    print("#" + " " * 20 + "测试总结" + " " * 29 + "#")
    print("#" * 70)

    total_fixed = total_initial - total_final
    fix_rate = (total_fixed / total_initial * 100) if total_initial > 0 else 0

    print(f"\n总项目数: {num_projects}")
    print(f"总初始问题: {total_initial}")
    print(f"总修复问题: {total_fixed}")
    print(f"总剩余问题: {total_final}")
    print(f"修复率: {fix_rate:.1f}%")

    # 按类型统计
    type_stats = {}
    for r in results:
        name = r["name"]
        if name not in type_stats:
            type_stats[name] = {"count": 0, "fixed": 0, "total": 0}
        type_stats[name]["count"] += 1
        type_stats[name]["fixed"] += r["fixed"]
        type_stats[name]["total"] += r["initial"]

    print(f"\n按项目类型:")
    for name, stats in type_stats.items():
        rate = (stats["fixed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {name}: {stats['fixed']}/{stats['total']} ({rate:.0f}%)")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=20, help="项目数量")
    args = parser.parse_args()

    random.seed(42)  # 可重复测试
    run_diverse_projects_test(args.num)
