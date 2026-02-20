"""
立创开源项目真实缺陷模拟测试

模拟 oshwhub.com 上常见 PCB 项目的真实缺陷:
1. STM32 开发板 - 晶振位置不当,去耦电容距离过远
2. 电源模块 - 走线过窄,电流承载不足
3. ESP32 开发板 - RF天线问题,差分对长度不匹配
4. USB 设备 - 阻抗匹配问题,ESD保护缺失
5. 高速数字电路 - 信号完整性问题
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcb_evaluator.pcb_models import (
    PCBBoard,
    Component,
    Track,
    Via,
    Zone,
    Net,
    Point2D,
    IssueType,
    Severity,
)
from pcb_evaluator.checkers import PCBChecker, DesignRules
from pcb_evaluator.ralph_loop import RalphLoopOptimizer


def create_stm32_board_with_defects():
    """STM32 开发板 - 常见缺陷"""
    board = PCBBoard(name="STM32F103C8T6 开发板", width=70.0, height=50.0)

    # 网络
    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_OSC", "OSC", is_high_speed=True),
        Net("net_USB_DP", "USB_DP", is_differential_pair=True),
        Net(
            "net_USB_DM",
            "USB_DM",
            is_differential_pair=True,
            differential_pair_partner="net_USB_DP",
        ),
    ]
    board.nets = nets

    # MCU - STM32F103
    mcu = Component(
        id="U1",
        reference="U1",
        value="STM32F103C8T6",
        footprint="LQFP-48",
        position=Point2D(35, 25),
        is_mcu=True,
        power_pins=["VDD", "VDDA"],
        gnd_pins=["VSS", "VSSA"],
    )
    board.components.append(mcu)

    # 晶振 - 距离MCU过远 (常见缺陷!)
    crystal = Component(
        id="Y1",
        reference="Y1",
        value="8MHz",
        footprint="HC-49S",
        position=Point2D(60, 40),  # 距离MCU 30mm+, 超过 MAX_CRYSTAL_DISTANCE=15mm
        is_crystal=True,
    )
    board.components.append(crystal)

    # 去耦电容 - 距离MCU过远 (常见缺陷!)
    cap1 = Component(
        id="C1",
        reference="C1",
        value="100nF",
        footprint="0805",
        position=Point2D(10, 40),  # 距离MCU 25mm, 超过 MAX_DECOUPLING_CAP_DISTANCE=5mm
    )
    board.components.append(
        cap2 := Component(
            id="C2",
            reference="C2",
            value="10uF",
            footprint="1206",
            position=Point2D(60, 10),  # 更远
        )
    )
    board.components.append(cap1)

    # USB 连接器
    usb = Component(
        id="J1",
        reference="J1",
        value="USB-Micro",
        footprint="USB-Micro-B",
        position=Point2D(10, 45),  # 靠近边缘
        is_connector=True,
    )
    board.components.append(usb)

    # 走线 - 电源走线过窄 (常见缺陷!)
    # VCC 走线应该 >= 0.3mm, 但这里只有 0.1mm
    vcc_track = Track(
        id="track_vcc_1",
        net_id="net_VCC",
        points=[Point2D(10, 45), Point2D(20, 35), Point2D(35, 25)],
        width=0.1,  # 缺陷: 太窄!
        layer="F.Cu",
    )
    board.tracks.append(vcc_track)

    # 晶振走线 - 过细且没有包地
    osc_track = Track(
        id="track_osc_1",
        net_id="net_OSC",
        points=[Point2D(60, 40), Point2D(50, 35), Point2D(35, 25)],
        width=0.15,  # 缺陷: 晶振走线应该更粗
        layer="F.Cu",
    )
    board.tracks.append(osc_track)

    # USB 差分对 - 长度不匹配 (常见缺陷!)
    # USB差分对需要长度匹配,但这里差异很大
    usb_dp = Track(
        id="track_usb_dp",
        net_id="net_USB_DP",
        points=[
            Point2D(10, 45),
            Point2D(15, 40),
            Point2D(20, 35),
            Point2D(25, 30),
            Point2D(30, 25),
            Point2D(35, 25),
        ],
        width=0.2,
        layer="F.Cu",
    )
    usb_dm = Track(
        id="track_usb_dm",
        net_id="net_USB_DM",
        points=[Point2D(10, 43), Point2D(15, 38), Point2D(20, 33), Point2D(35, 25)],
        width=0.2,
        layer="F.Cu",
    )
    board.tracks.append(usb_dp)
    board.tracks.append(usb_dm)

    # 过孔 - 孔径过小 (常见缺陷!)
    via = Via(
        id="via_1",
        net_id="net_GND",
        position=Point2D(35, 25),
        diameter=0.4,
        drill=0.15,  # 缺陷: 太小,最小应该是 0.3mm
    )
    board.vias.append(via)

    return board


def create_power_module_with_defects():
    """电源模块 - 常见缺陷"""
    board = PCBBoard(name="12V to 5V 降压模块", width=40.0, height=30.0)

    # 网络
    nets = [
        Net("net_VIN", "VIN", is_power_supply=True),
        Net("net_VOUT", "VOUT", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
    ]
    board.nets = nets

    # 输入电容
    cin = Component(
        id="CIN",
        reference="C1",
        value="100uF",
        footprint="CAP-ELec",
        position=Point2D(5, 15),
        is_heatsink=True,
    )
    board.components.append(cin)

    # 输出电容
    cout = Component(
        id="COUT",
        reference="C2",
        value="470uF",
        footprint="CAP-ELec",
        position=Point2D(35, 15),
    )
    board.components.append(cout)

    # 芯片
    chip = Component(
        id="U1",
        reference="U1",
        value="LM2596",
        footprint="TO-263",
        position=Point2D(20, 15),
        is_heatsink=True,
    )
    board.components.append(chip)

    # 电源走线 - 过窄! (严重缺陷)
    # 12V/2A 输入, 走线应该 >= 1.5mm
    for i in range(5):
        track = Track(
            id=f"track_vin_{i}",
            net_id="net_VIN",
            points=[Point2D(5, 15), Point2D(10 + i * 2, 15), Point2D(20, 15)],
            width=0.2,  # 缺陷: 太窄!
            layer="F.Cu",
        )
        board.tracks.append(track)

    # 输出走线 - 也过窄
    track_out = Track(
        id="track_vout",
        net_id="net_VOUT",
        points=[Point2D(20, 15), Point2D(25, 15), Point2D(35, 15)],
        width=0.25,  # 缺陷: 对于2A输出来说太窄
        layer="F.Cu",
    )
    board.tracks.append(track_out)

    # 铺铜 - 有孤岛 (缺陷)
    zone = Zone(
        id="zone_gnd",
        net_id="net_GND",
        layer="F.Cu",
        points=[Point2D(2, 2), Point2D(38, 2), Point2D(38, 28), Point2D(2, 28)],
        filled=True,
    )
    board.zones.append(zone)

    return board


def create_esp32_board_with_defects():
    """ESP32 开发板 - RF相关缺陷"""
    board = PCBBoard(name="ESP32-WROOM 开发板", width=50.0, height=30.0)

    # 网络
    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_ANT", "ANT", is_high_speed=True),
    ]
    board.nets = nets

    # ESP32 模块
    esp = Component(
        id="U1",
        reference="U1",
        value="ESP32-WROOM",
        footprint="Module",
        position=Point2D(25, 15),
        is_mcu=True,
    )
    board.components.append(esp)

    # 天线 - 靠近金属 (缺陷!)
    antenna = Component(
        id="ANT1",
        reference="ANT1",
        value="PCB Antenna",
        footprint="Chip",
        position=Point2D(45, 15),
    )
    board.components.append(antenna)

    # 金属屏蔽罩 - 靠近天线 (缺陷!)
    shield = Component(
        id="FH1",
        reference="FH1",
        value="Shield",
        footprint="Shield",
        position=Point2D(35, 15),  # 距离天线太近!
    )
    board.components.append(shield)

    # RF 走线 - 过细
    rf_track = Track(
        id="track_rf",
        net_id="net_ANT",
        points=[Point2D(45, 15), Point2D(35, 15), Point2D(25, 15)],
        width=0.15,  # 缺陷: RF走线应该更宽
        layer="F.Cu",
    )
    board.tracks.append(rf_track)

    return board


def run_real_world_test():
    """运行真实世界缺陷测试"""
    print("\n" + "=" * 70)
    print("立创开源项目真实缺陷模拟测试")
    print("=" * 70)

    test_cases = [
        ("STM32F103 开发板 (常见缺陷)", create_stm32_board_with_defects),
        ("LM2596 电源模块 (常见缺陷)", create_power_module_with_defects),
        ("ESP32 开发板 (RF缺陷)", create_esp32_board_with_defects),
    ]

    all_results = []

    for name, create_func in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试: {name}")
        print(f"{'=' * 60}")

        board = create_func()

        print(f"板尺寸: {board.width}x{board.height}mm")
        print(f"元件数: {len(board.components)}")
        print(f"走线数: {len(board.tracks)}")
        print(f"过孔数: {len(board.vias)}")

        # 运行优化器
        optimizer = RalphLoopOptimizer(max_iterations=20)
        result = optimizer.optimize(board)

        # 打印结果
        optimizer.print_result(result)

        all_results.append((name, result))

    # 总结
    print("\n" + "#" * 70)
    print("#" + " " * 20 + "测试总结" + " " * 29 + "#")
    print("#" * 70)

    for name, result in all_results:
        print(f"\n{name}:")
        print(f"  迭代次数: {result.total_iterations}/20")
        print(f"  初始问题数: {len(result.initial_issues)}")
        print(f"  最终问题数: {len(result.final_issues)}")
        print(f"  收敛: {'是' if result.converged else '否'}")
        print(f"  达到最大迭代: {'是' if result.max_iterations_reached else '否'}")

        # 显示问题类型分布
        if result.final_issues:
            issue_types = {}
            for issue in result.final_issues:
                issue_type = issue.type.value
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            print(f"  最终问题类型分布:")
            for itype, count in issue_types.items():
                print(f"    - {itype}: {count}")

    return all_results


if __name__ == "__main__":
    run_real_world_test()
