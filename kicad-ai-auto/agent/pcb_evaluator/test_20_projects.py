"""
20种不同类型PCB项目的真实缺陷模拟测试

基于立创开源平台(oshwhub.com)常见项目类型:
1. STM32开发板 - 电源/晶振问题
2. ESP32开发板 - RF天线问题
3. USB Hub - 阻抗匹配
4. 电源模块 - 走线/电流
5. HDMI屏幕 - 高速信号
6. 电机控制器 - 隔离
7. 蓝牙设备 - 天线
8. 功率计 - 大电流
9. 电压电流表 - ADC
10. 无线开关 - 共地
11. 音频设备 - 噪声
12. LED驱动 - 发热
13. LiPo充电器 - 保护
14. 传感器板 - 去耦
15. 显示屏接口 - 背光
16. I2C设备 - 上拉
17. SPI设备 - 时序
18. CAN总线 - 终端
19. RS485 - 隔离
20. 物联网设备 - 功耗
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


def create_stm32_board():
    """1. STM32开发板 - 常见缺陷"""
    board = PCBBoard(name="STM32F103开发板", width=70, height=50)

    # 网络
    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_OSC", "OSC", is_high_speed=True),
    ]
    board.nets = nets

    # MCU
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="STM32F103",
            footprint="LQFP-48",
            position=Point2D(35, 25),
            is_mcu=True,
            power_pins=["VDD"],
            gnd_pins=["VSS"],
        )
    )

    # 晶振 - 距离MCU过远 (常见缺陷!)
    board.components.append(
        Component(
            id="Y1",
            reference="Y1",
            value="8MHz",
            footprint="HC-49S",
            position=Point2D(60, 40),
            is_crystal=True,
        )
    )

    # 去耦电容 - 距离远
    board.components.append(
        Component(
            id="C1",
            reference="C1",
            value="100nF",
            footprint="0805",
            position=Point2D(10, 40),
        )
    )

    # VCC走线 - 过窄!
    board.tracks.append(
        Track(
            id="track_vcc",
            net_id="net_VCC",
            points=[Point2D(10, 45), Point2D(35, 25)],
            width=0.1,
            layer="F.Cu",  # 缺陷: 太窄
        )
    )

    # 晶振走线 - 过细
    board.tracks.append(
        Track(
            id="track_osc",
            net_id="net_OSC",
            points=[Point2D(60, 40), Point2D(35, 25)],
            width=0.1,
            layer="F.Cu",  # 缺陷: 晶振走线应更粗
        )
    )

    # 过孔 - 孔径太小
    board.vias.append(
        Via(
            id="via1",
            net_id="net_GND",
            position=Point2D(35, 25),
            diameter=0.4,
            drill=0.15,  # 缺陷: 太小
        )
    )

    return board


def create_esp32_board():
    """2. ESP32开发板 - RF天线问题"""
    board = PCBBoard(name="ESP32-WROOM开发板", width=50, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_ANT", "ANT", is_high_speed=True),
    ]
    board.nets = nets

    # ESP32模块
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="ESP32-WROOM",
            footprint="Module",
            position=Point2D(25, 15),
            is_mcu=True,
        )
    )

    # 天线
    board.components.append(
        Component(
            id="ANT1",
            reference="ANT1",
            value="PCB Antenna",
            footprint="Chip",
            position=Point2D(45, 15),
        )
    )

    # 金属屏蔽罩 - 靠近天线!
    board.components.append(
        Component(
            id="FH1",
            reference="FH1",
            value="Shield",
            footprint="Shield",
            position=Point2D(38, 15),  # 缺陷: 靠近天线
        )
    )

    # RF走线 - 过细
    board.tracks.append(
        Track(
            id="track_rf",
            net_id="net_ANT",
            points=[Point2D(45, 15), Point2D(25, 15)],
            width=0.15,
            layer="F.Cu",  # 缺陷: RF走线应更宽
        )
    )

    return board


def create_usb_hub():
    """3. USB Hub - 阻抗匹配问题"""
    board = PCBBoard(name="USB Hub", width=60, height=40)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_DP", "DP", is_differential_pair=True),
        Net(
            "net_DM",
            "DM",
            is_differential_pair=True,
            differential_pair_partner="net_DP",
        ),
    ]
    board.nets = nets

    # USB芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="USB2512",
            footprint="QFN-36",
            position=Point2D(30, 20),
            is_ic=True,
        )
    )

    # USB接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="USB-A",
            footprint="USB-A",
            position=Point2D(10, 20),
            is_connector=True,
        )
    )

    # 差分对 - 长度差异大 (缺陷!)
    board.tracks.append(
        Track(
            id="track_dp",
            net_id="net_DP",
            points=[
                Point2D(10, 20),
                Point2D(15, 18),
                Point2D(20, 16),
                Point2D(25, 14),
                Point2D(30, 20),
            ],
            width=0.2,
            layer="F.Cu",
        )
    )
    board.tracks.append(
        Track(
            id="track_dm",
            net_id="net_DM",
            points=[Point2D(10, 22), Point2D(30, 20)],
            width=0.2,
            layer="F.Cu",  # 缺陷: 长度差异太大
        )
    )

    # 电源走线 - 过窄
    board.tracks.append(
        Track(
            id="track_vcc",
            net_id="net_VCC",
            points=[Point2D(5, 20), Point2D(30, 20)],
            width=0.15,
            layer="F.Cu",  # 缺陷: USB需要至少0.3mm
        )
    )

    return board


def create_power_module():
    """4. 电源模块 - 大电流走线"""
    board = PCBBoard(name="12V转5V降压模块", width=40, height=30)

    nets = [
        Net("net_VIN", "VIN", is_power_supply=True),
        Net("net_VOUT", "VOUT", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
    ]
    board.nets = nets

    # 芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="LM2596",
            footprint="TO-263",
            position=Point2D(20, 15),
            is_heatsink=True,
        )
    )

    # 电容
    board.components.append(
        Component(
            id="C1",
            reference="C1",
            value="100uF",
            footprint="CAP-ELec",
            position=Point2D(5, 15),
        )
    )
    board.components.append(
        Component(
            id="C2",
            reference="C2",
            value="470uF",
            footprint="CAP-ELec",
            position=Point2D(35, 15),
        )
    )

    # 输入走线 - 极窄! (缺陷: 12V/2A输入应>1.5mm)
    for i in range(3):
        board.tracks.append(
            Track(
                id=f"track_vin_{i}",
                net_id="net_VIN",
                points=[Point2D(5, 15), Point2D(20, 15)],
                width=0.15,
                layer="F.Cu",  # 严重缺陷
            )
        )

    # 输出走线 - 也过窄
    board.tracks.append(
        Track(
            id="track_vout",
            net_id="net_VOUT",
            points=[Point2D(20, 15), Point2D(35, 15)],
            width=0.2,
            layer="F.Cu",  # 缺陷
        )
    )

    return board


def create_hdmi_screen():
    """5. HDMI屏幕 - 高速信号"""
    board = PCBBoard(name="HDMI显示屏", width=100, height=60)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_HDMIP", "HDMI_P", is_differential_pair=True),
        Net(
            "net_HDMIN",
            "HDMI_N",
            is_differential_pair=True,
            differential_pair_partner="net_HDMIP",
        ),
    ]
    board.nets = nets

    # HDMI接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="HDMI-A",
            footprint="HDMI-A",
            position=Point2D(10, 30),
            is_connector=True,
        )
    )

    # 芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="TFP401",
            footprint="QFN-64",
            position=Point2D(50, 30),
            is_ic=True,
        )
    )

    # 差分对 - 长度严重不匹配 (缺陷!)
    board.tracks.append(
        Track(
            id="track_hdmi_p",
            net_id="net_HDMIP",
            points=[
                Point2D(10, 30),
                Point2D(20, 28),
                Point2D(30, 26),
                Point2D(40, 24),
                Point2D(50, 30),
            ],
            width=0.15,
            layer="F.Cu",
        )
    )
    board.tracks.append(
        Track(
            id="track_hdmi_n",
            net_id="net_HDMIN",
            points=[Point2D(10, 32), Point2D(50, 30)],  # 缺陷: 长度差异太大
            width=0.15,
            layer="F.Cu",
        )
    )

    return board


def create_motor_controller():
    """6. 电机控制器 - 隔离问题"""
    board = PCBBoard(name="电机驱动板", width=80, height=60)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_MOTOR", "MOTOR", is_power_supply=True),
    ]
    board.nets = nets

    # 主控
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="STM32F103",
            footprint="LQFP-48",
            position=Point2D(20, 30),
            is_mcu=True,
        )
    )

    # 电机驱动
    board.components.append(
        Component(
            id="U2",
            reference="U2",
            value="L298N",
            footprint="MultiWatt",
            position=Point2D(60, 30),
            is_heatsink=True,
        )
    )

    # 大电流走线 - 极窄 (缺陷!)
    board.tracks.append(
        Track(
            id="track_motor",
            net_id="net_MOTOR",
            points=[Point2D(60, 25), Point2D(60, 50)],
            width=0.2,
            layer="F.Cu",  # 缺陷: 电机驱动需要更宽
        )
    )

    # 铺铜 - 有孤岛
    board.zones.append(
        Zone(
            id="zone_gnd",
            net_id="net_GND",
            layer="F.Cu",
            points=[Point2D(2, 2), Point2D(78, 2), Point2D(78, 58), Point2D(2, 58)],
            filled=True,
        )
    )

    return board


def create_bluetooth_device():
    """7. 蓝牙设备 - 天线"""
    board = PCBBoard(name="蓝牙模块", width=40, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_BT", "BT", is_high_speed=True),
    ]
    board.nets = nets

    # 蓝牙芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="BLE5.0",
            footprint="QFN-32",
            position=Point2D(20, 15),
            is_ic=True,
        )
    )

    # 天线 - 靠近边缘
    board.components.append(
        Component(
            id="ANT1",
            reference="ANT1",
            value="Chip Antenna",
            footprint="0402",
            position=Point2D(35, 15),
        )
    )

    # 天线走线 - 过细且没有净空
    board.tracks.append(
        Track(
            id="track_bt",
            net_id="net_BT",
            points=[Point2D(35, 15), Point2D(25, 15)],
            width=0.1,
            layer="F.Cu",  # 缺陷
        )
    )

    return board


def create_power_meter():
    """8. 功率计 - 大电流"""
    board = PCBBoard(name="功率计", width=60, height=40)

    nets = [
        Net("net_VIN", "VIN", is_power_supply=True),
        Net("net_VOUT", "VOUT", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
    ]
    board.nets = nets

    # 采样芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="INA228",
            footprint="TSSOP-14",
            position=Point2D(30, 20),
            is_ic=True,
        )
    )

    # MOS管
    board.components.append(
        Component(
            id="Q1",
            reference="Q1",
            value="NMOS",
            footprint="TO-252",
            position=Point2D(45, 20),
            is_heatsink=True,
        )
    )

    # 电流走线 - 极窄! (缺陷: 20A需要>3mm)
    board.tracks.append(
        Track(
            id="track_curr",
            net_id="net_VIN",
            points=[Point2D(5, 20), Point2D(45, 20)],
            width=0.3,
            layer="F.Cu",  # 严重缺陷
        )
    )

    # 添加更多走线模拟
    for y in [18, 22]:
        board.tracks.append(
            Track(
                id=f"track_curr_{y}",
                net_id="net_VIN",
                points=[Point2D(5, y), Point2D(45, y)],
                width=0.3,
                layer="F.Cu",
            )
        )

    return board


def create_voltage_meter():
    """9. 电压电流表"""
    board = PCBBoard(name="电压电流表", width=50, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_ADC", "ADC", is_high_speed=True),
    ]
    board.nets = nets

    # MCU
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="CW32F030",
            footprint="LQFP-48",
            position=Point2D(25, 15),
            is_mcu=True,
        )
    )

    # 分压电阻 - 精度不足
    board.components.append(
        Component(
            id="R1",
            reference="R1",
            value="220K",
            footprint="0805",
            position=Point2D(10, 15),
        )
    )
    board.components.append(
        Component(
            id="R2",
            reference="R2",
            value="10K",
            footprint="0805",
            position=Point2D(15, 15),  # 缺陷: 比例可能不准确
        )
    )

    # ADC走线 - 过细
    board.tracks.append(
        Track(
            id="track_adc",
            net_id="net_ADC",
            points=[Point2D(15, 15), Point2D(25, 15)],
            width=0.15,
            layer="F.Cu",  # 缺陷
        )
    )

    return board


def create_wireless_switch():
    """10. 无线开关 - 共地问题"""
    board = PCBBoard(name="无线开关", width=40, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_12V", "12V", is_power_supply=True),
    ]
    board.nets = nets

    # 主控
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="ESP32C3",
            footprint="QFN-32",
            position=Point2D(20, 15),
            is_mcu=True,
        )
    )

    # 继电器
    board.components.append(
        Component(
            id="K1",
            reference="K1",
            value="Relay",
            footprint="Relay",
            position=Point2D(35, 20),
            is_heatsink=True,
        )
    )

    # 控制走线 - 可能存在共地问题
    board.tracks.append(
        Track(
            id="track_ctrl",
            net_id="net_12V",
            points=[Point2D(20, 18), Point2D(35, 20)],
            width=0.2,
            layer="F.Cu",
        )
    )

    # 电源走线 - 隔离不足
    board.tracks.append(
        Track(
            id="track_gnd",
            net_id="net_GND",
            points=[Point2D(5, 10), Point2D(35, 25)],
            width=0.15,
            layer="F.Cu",  # 缺陷: 共地可能导致噪声
        )
    )

    return board


def create_audio_device():
    """11. 音频设备 - 噪声"""
    board = PCBBoard(name="音频放大器", width=60, height=40)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_AIN", "AIN", is_high_speed=True),
    ]
    board.nets = nets

    # 运放
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="LM386",
            footprint="DIP-8",
            position=Point2D(30, 20),
            is_ic=True,
        )
    )

    # 输入电容
    board.components.append(
        Component(
            id="C1",
            reference="C1",
            value="1uF",
            footprint="0805",
            position=Point2D(15, 20),
        )
    )

    # 音频走线 - 靠近电源 (缺陷!)
    board.tracks.append(
        Track(
            id="track_ain",
            net_id="net_AIN",
            points=[Point2D(15, 20), Point2D(30, 20)],
            width=0.2,
            layer="F.Cu",
        )
    )

    # 电源走线 - 靠近音频
    board.tracks.append(
        Track(
            id="track_vcc",
            net_id="net_VCC",
            points=[Point2D(5, 25), Point2D(30, 20)],
            width=0.2,
            layer="F.Cu",  # 缺陷: 应该远离音频信号
        )
    )

    return board


def create_led_driver():
    """12. LED驱动 - 发热"""
    board = PCBBoard(name="LED驱动", width=45, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_LED", "LED", is_power_supply=True),
    ]
    board.nets = nets

    # LED驱动
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="PT4115",
            footprint="SOT-89",
            position=Point2D(22, 15),
            is_heatsink=True,
        )
    )

    # LED
    board.components.append(
        Component(
            id="LED1",
            reference="LED1",
            value="LED",
            footprint="LED",
            position=Point2D(40, 15),
        )
    )

    # 限流电阻
    board.components.append(
        Component(
            id="R1",
            reference="R1",
            value="1R",
            footprint="1206",
            position=Point2D(35, 15),
        )
    )

    # 电流走线 - 过窄 (缺陷!)
    board.tracks.append(
        Track(
            id="track_led",
            net_id="net_LED",
            points=[Point2D(40, 15), Point2D(22, 15)],
            width=0.2,
            layer="F.Cu",  # 350mA需要至少0.5mm
        )
    )

    # 发热元件靠近
    board.components.append(
        Component(
            id="U2",
            reference="U2",
            value="LM7805",
            footprint="TO-263",
            position=Point2D(22, 22),
            is_heatsink=True,
        )
    )

    return board


def create_lipo_charger():
    """13. LiPo充电器"""
    board = PCBBoard(name="LiPo充电器", width=50, height=35)

    nets = [
        Net("net_VIN", "VIN", is_power_supply=True),
        Net("net_VOUT", "VOUT", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
    ]
    board.nets = nets

    # 充电芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="TP4056",
            footprint="ESOP-8",
            position=Point2D(25, 17),
            is_ic=True,
        )
    )

    # 保护芯片
    board.components.append(
        Component(
            id="U2",
            reference="U2",
            value="DW01",
            footprint="SOT-23-6",
            position=Point2D(35, 17),
            is_ic=True,
        )
    )

    # 电池接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="JST-XH",
            footprint="JST-XH-2P",
            position=Point2D(45, 17),
            is_connector=True,
        )
    )

    # 充电电流走线 - 过窄 (缺陷!)
    board.tracks.append(
        Track(
            id="track_charge",
            net_id="net_VOUT",
            points=[Point2D(25, 15), Point2D(45, 17)],
            width=0.2,
            layer="F.Cu",  # 1A充电需要约0.5mm
        )
    )

    return board


def create_sensor_board():
    """14. 传感器板"""
    board = PCBBoard(name="传感器模块", width=30, height=20)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_SIG", "SIG"),
    ]
    board.nets = nets

    # 传感器
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="BME280",
            footprint="BGA",
            position=Point2D(15, 10),
            is_ic=True,
        )
    )

    # 去耦电容 - 距离远 (缺陷!)
    board.components.append(
        Component(
            id="C1",
            reference="C1",
            value="100nF",
            footprint="0603",
            position=Point2D(5, 15),  # 缺陷: 距离IC太远
        )
    )

    # 信号走线
    board.tracks.append(
        Track(
            id="track_sig",
            net_id="net_SIG",
            points=[Point2D(15, 10), Point2D(25, 10)],
            width=0.15,
            layer="F.Cu",
        )
    )

    return board


def create_display_interface():
    """15. 显示屏接口"""
    board = PCBBoard(name="显示屏接口", width=70, height=50)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_RGB", "RGB", is_high_speed=True),
    ]
    board.nets = nets

    # 接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="FPC-40P",
            footprint="FPC-40P",
            position=Point2D(10, 25),
            is_connector=True,
        )
    )

    # 驱动IC
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="ILI9488",
            footprint="LQFP-48",
            position=Point2D(45, 25),
            is_ic=True,
        )
    )

    # RGB走线 - 长度不匹配 (缺陷!)
    for i in range(5):
        board.tracks.append(
            Track(
                id=f"track_rgb_{i}",
                net_id="net_RGB",
                points=[Point2D(10, 20 + i), Point2D(45, 25)],
                width=0.15,
                layer="F.Cu",
            )
        )

    # 背光走线 - 过窄
    board.tracks.append(
        Track(
            id="track_bl",
            net_id="net_VCC",
            points=[Point2D(10, 30), Point2D(45, 25)],
            width=0.2,
            layer="F.Cu",  # 缺陷: 背光需要较大电流
        )
    )

    return board


def create_i2c_device():
    """16. I2C设备"""
    board = PCBBoard(name="I2C模块", width=25, height=15)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_SDA", "SDA"),
        Net("net_SCL", "SCL"),
    ]
    board.nets = nets

    # I2C芯片
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="EEPROM",
            footprint="SOP-8",
            position=Point2D(12, 7),
            is_ic=True,
        )
    )

    # 上拉电阻 - 缺失 (缺陷!) - 实际不应该添加电阻，而是检查是否存在

    # I2C走线 - 过细
    board.tracks.append(
        Track(
            id="track_sda",
            net_id="net_SDA",
            points=[Point2D(5, 5), Point2D(12, 7)],
            width=0.1,
            layer="F.Cu",  # 缺陷: I2C建议0.2mm以上
        )
    )
    board.tracks.append(
        Track(
            id="track_scl",
            net_id="net_SCL",
            points=[Point2D(5, 10), Point2D(12, 7)],
            width=0.1,
            layer="F.Cu",
        )
    )

    return board


def create_spi_device():
    """17. SPI设备"""
    board = PCBBoard(name="SPI模块", width=35, height=25)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_SCK", "SCK", is_high_speed=True),
        Net("net_MISO", "MISO", is_high_speed=True),
        Net("net_MOSI", "MOSI", is_high_speed=True),
    ]
    board.nets = nets

    # SPI Flash
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="W25Q128",
            footprint="SOP-8",
            position=Point2D(17, 12),
            is_ic=True,
        )
    )

    # SPI走线 - 长度差异大 (缺陷!)
    board.tracks.append(
        Track(
            id="track_sck",
            net_id="net_SCK",
            points=[Point2D(5, 8), Point2D(17, 10), Point2D(17, 12)],
            width=0.15,
            layer="F.Cu",
        )
    )
    board.tracks.append(
        Track(
            id="track_miso",
            net_id="net_MISO",
            points=[Point2D(5, 12), Point2D(17, 12)],
            width=0.15,
            layer="F.Cu",  # 缺陷: 长度差异大
        )
    )
    board.tracks.append(
        Track(
            id="track_mosi",
            net_id="net_MOSI",
            points=[Point2D(5, 16), Point2D(17, 14), Point2D(17, 12)],
            width=0.15,
            layer="F.Cu",
        )
    )

    return board


def create_can_bus():
    """18. CAN总线"""
    board = PCBBoard(name="CAN模块", width=50, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_CANH", "CANH", is_differential_pair=True),
        Net(
            "net_CANL",
            "CANL",
            is_differential_pair=True,
            differential_pair_partner="net_CANH",
        ),
    ]
    board.nets = nets

    # CAN收发器
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="SN65HVD230",
            footprint="SOIC-8",
            position=Point2D(25, 15),
            is_ic=True,
        )
    )

    # 接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="CAN",
            footprint="Terminal-2P",
            position=Point2D(45, 15),
            is_connector=True,
        )
    )

    # CAN走线 - 长度不匹配 (缺陷!)
    board.tracks.append(
        Track(
            id="track_canh",
            net_id="net_CANH",
            points=[Point2D(25, 13), Point2D(45, 15)],
            width=0.25,
            layer="F.Cu",
        )
    )
    board.tracks.append(
        Track(
            id="track_canl",
            net_id="net_CANL",
            points=[Point2D(25, 17), Point2D(40, 15), Point2D(45, 15)],  # 缺陷
            width=0.25,
            layer="F.Cu",
        )
    )

    # 终端电阻 - 缺失 (缺陷!) - 检查时不添加

    return board


def create_rs485_device():
    """19. RS485"""
    board = PCBBoard(name="RS485模块", width=45, height=30)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
        Net("net_A", "A", is_differential_pair=True),
        Net("net_B", "B", is_differential_pair=True, differential_pair_partner="net_A"),
    ]
    board.nets = nets

    # RS485收发器
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="MAX485",
            footprint="SOIC-8",
            position=Point2D(22, 15),
            is_ic=True,
        )
    )

    # 接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="RS485",
            footprint="Terminal-4P",
            position=Point2D(40, 15),
            is_connector=True,
        )
    )

    # 差分对走线
    board.tracks.append(
        Track(
            id="track_a",
            net_id="net_A",
            points=[Point2D(22, 13), Point2D(40, 14)],
            width=0.2,
            layer="F.Cu",
        )
    )
    board.tracks.append(
        Track(
            id="track_b",
            net_id="net_B",
            points=[Point2D(22, 17), Point2D(40, 16)],
            width=0.2,
            layer="F.Cu",
        )
    )

    # 隔离光耦 - 可能缺失

    return board


def create_iot_device():
    """20. 物联网设备 - 功耗"""
    board = PCBBoard(name="物联网设备", width=40, height=28)

    nets = [
        Net("net_VCC", "VCC", is_power_supply=True),
        Net("net_GND", "GND", is_ground=True),
    ]
    board.nets = nets

    # 主控
    board.components.append(
        Component(
            id="U1",
            reference="U1",
            value="ESP32-S3",
            footprint="QFN-56",
            position=Point2D(20, 14),
            is_mcu=True,
        )
    )

    # 锂电池保护
    board.components.append(
        Component(
            id="U2",
            reference="U2",
            value="DW01",
            footprint="SOT-23-6",
            position=Point2D(32, 14),
            is_ic=True,
        )
    )

    # 电池接口
    board.components.append(
        Component(
            id="J1",
            reference="J1",
            value="Battery",
            footprint="JST-PH-2P",
            position=Point2D(38, 14),
            is_connector=True,
        )
    )

    # 电源走线 - 宽度不足
    board.tracks.append(
        Track(
            id="track_pwr",
            net_id="net_VCC",
            points=[Point2D(38, 14), Point2D(20, 14)],
            width=0.15,
            layer="F.Cu",  # 缺陷: 功耗敏感设备需要更宽的电源走线降低压降
        )
    )

    return board


def run_all_tests():
    """运行20种项目的综合测试"""
    print("\n" + "#" * 70)
    print("#" + " " * 15 + "20种PCB项目真实缺陷测试" + " " * 17 + "#")
    print("#" * 70)

    test_cases = [
        ("1. STM32开发板", create_stm32_board),
        ("2. ESP32开发板", create_esp32_board),
        ("3. USB Hub", create_usb_hub),
        ("4. 电源模块", create_power_module),
        ("5. HDMI屏幕", create_hdmi_screen),
        ("6. 电机控制器", create_motor_controller),
        ("7. 蓝牙设备", create_bluetooth_device),
        ("8. 功率计", create_power_meter),
        ("9. 电压电流表", create_voltage_meter),
        ("10. 无线开关", create_wireless_switch),
        ("11. 音频设备", create_audio_device),
        ("12. LED驱动", create_led_driver),
        ("13. LiPo充电器", create_lipo_charger),
        ("14. 传感器板", create_sensor_board),
        ("15. 显示屏接口", create_display_interface),
        ("16. I2C设备", create_i2c_device),
        ("17. SPI设备", create_spi_device),
        ("18. CAN总线", create_can_bus),
        ("19. RS485设备", create_rs485_device),
        ("20. 物联网设备", create_iot_device),
    ]

    results = []

    for name, create_func in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试: {name}")
        print(f"{'=' * 60}")

        board = create_func()

        # 运行优化器 - 20次迭代
        optimizer = RalphLoopOptimizer(max_iterations=20)
        result = optimizer.optimize(board)

        # 打印关键结果
        print(f"迭代次数: {result.total_iterations}/20")
        print(f"初始问题: {len(result.initial_issues)}")
        print(f"最终问题: {len(result.final_issues)}")
        print(f"收敛: {'是' if result.converged else '否'}")

        # 统计问题类型
        if result.final_issues:
            issue_types = {}
            for issue in result.final_issues:
                issue_types[issue.type.value] = issue_types.get(issue.type.value, 0) + 1
            print(f"剩余问题类型: {issue_types}")

        results.append(
            {
                "name": name,
                "initial": len(result.initial_issues),
                "final": len(result.final_issues),
                "iterations": result.total_iterations,
                "converged": result.converged,
                "issues": [i.type.value for i in result.final_issues],
            }
        )

    # 总结
    print("\n" + "#" * 70)
    print("#" * 25 + "测试总结" + " " * 30 + "#")
    print("#" * 70)

    total_initial = sum(r["initial"] for r in results)
    total_final = sum(r["final"] for r in results)
    total_fixed = total_initial - total_final

    print(f"\n总共测试: {len(results)} 个项目")
    print(f"初始问题总数: {total_initial}")
    print(f"修复后问题总数: {total_final}")
    print(f"已修复问题数: {total_fixed}")
    print(f"修复率: {total_fixed / total_initial * 100:.1f}%")

    # 显示未完全修复的项目
    print(f"\n未完全修复的项目:")
    for r in results:
        if r["final"] > 0:
            print(f"  - {r['name']}: 初始{r['initial']}个 → 剩余{r['final']}个")

    return results


if __name__ == "__main__":
    run_all_tests()
