"""
优秀PCB设计案例库

基于AutoResearch概念, 为AI提供优秀设计参考
避免AI凭空猜测, 减少参数游戏
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
import json
from pathlib import Path

# 条件导入增强匹配器
try:
    from iteration.core.similarity_matcher import (
        EnhancedCaseMatcher,
        FeatureExtractor,
        CircuitFeatures,
        create_enhanced_matcher
    )
    HAS_ENHANCED_MATCHER = True
except ImportError:
    HAS_ENHANCED_MATCHER = False
    EnhancedCaseMatcher = None
    FeatureExtractor = None
    CircuitFeatures = None


@dataclass
class DesignFeature:
    """设计特征"""
    name: str
    description: str
    implementation: str  # 如何实现
    benefit: str  # 效果说明


@dataclass
class AvoidPattern:
    """应避免的模式"""
    pattern: str
    reason: str  # 为什么不好
    consequence: str  # 后果


@dataclass
class DesignCase:
    """优秀设计案例"""
    name: str
    description: str
    quality_score: float  # 0-100
    difficulty: str  # easy/medium/hard
    key_features: Dict[str, str]  # 关键特征
    design_patterns: List[str]  # 设计模式
    avoid_patterns: List[AvoidPattern]
    dimension_scores: Dict[str, float]  # 各维度分数


    lessons_learned: List[str]  # 经验教训


class DesignCaseLibrary:
    """优秀PCB设计案例库"""

    def __init__(self):
        self.cases: Dict[str, DesignCase] = {}
        self._initialize_builtin_cases()

    def _initialize_builtin_cases(self):
        """初始化内置优秀案例"""

        # 案例1: STM32F103C8T6最小系统板 (92分, A+级)
        self.cases["stm32_minimal"] = DesignCase(
            name="STM32F103C8T6最小系统板",
            description="基于STM32F103C8T6的最小系统板，包含电源、晶振、复位、USB接口",
            quality_score=92.0,
            difficulty="medium",
            key_features={
                "layout_strategy": "模块化布局（电源/MCU/接口分区分隔）",
                "decoupling": "每个VCC引脚附近放置0.1μF + 10μF电容",
                "crystal_oscillator": "晶振远离高速信号，下方铺地屏蔽",
                "usb_routing": "差分对等长匹配，长度差<5mil，阻抗90Ω",
                "power_routing": "电源走线加宽（VCC: 0.3mm, GND: 铺铜）",
                "reset_circuit": "RC复位电路（10kΩ+100nF），去抖动",
                "bootloader": "BOOT0/BOOT1引脚上拉电阻10kΩ"
            },
            design_patterns=[
                "功能模块分区布局",
                "去耦电容就近放置",
                "晶振下方铺地屏蔽",
                "电源走线加宽处理",
                "差分对等长匹配"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="晶振下方走高速信号",
                    reason="晶振振荡会干扰高速信号",
                    consequence="信号完整性下降，误码率上升"
                ),
                AvoidPattern(
                    pattern="电源走线形成环路",
                    reason="环路天线效应",
                    consequence="EMI辐射增强，不符合FCC标准"
                ),
                AvoidPattern(
                    pattern="模拟地和数字地直接短接",
                    reason="数字噪声会耦合到模拟电路",
                    consequence="ADC精度下降，噪声增加"
                ),
                AvoidPattern(
                    pattern="去耦电容远离IC",
                    reason="去耦电容距离太远无效",
                    consequence="电源纹波大，IC工作不稳定"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 10.0,
                "信号完整性": 9.5,
                "EMC合规": 4.5,
                "热设计": 4.0
            },
            lessons_learned=[
                "模块化布局可以显著改善信号完整性",
                "去耦电容的位置比数量更重要",
                "晶振布局需要特别关注"
            ]
        )

        # 案例2: ESP32 WiFi蓝牙模块 (88分, A级)
        self.cases["esp32_wifi"] = DesignCase(
            name="ESP32 WiFi蓝牙模块",
            description="基于ESP32的WiFi+蓝牙物联网模块，包含天线、RF匹配、电源管理",
            quality_score=88.0,
            difficulty="hard",
            key_features={
                "antenna_layout": "天线下方无铜皮，保持净空区≥15mm",
                "rf_routing": "RF走线阻抗控制50Ω，采用π型匹配",
                "power_separation": "模拟电源(3.3V)和数字电源(3.3V)通过磁珠分开",
                "crystal_oscillator": "26MHz晶振靠近芯片，走线短且直",
                "usb_uart": "USB转UART芯片(CP2102)靠近接口",
                "led_indicators": "电源LED(红)+状态LED(蓝)+WiFi LED(绿)"
            },
            design_patterns=[
                "天线净空区设计",
                "RF阻抗匹配",
                "模拟数字电源分离",
                "晶振短直走线",
                "状态指示LED"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="天线下方有铜皮或走线",
                    reason="影响天线辐射特性",
                    consequence="WiFi信号弱，通信距离短"
                ),
                AvoidPattern(
                    pattern="RF走线有分支或过孔",
                    reason="阻抗不连续",
                    consequence="信号反射，通信质量差"
                ),
                AvoidPattern(
                    pattern="晶振走线过长或弯曲",
                    reason="寄生电容和电感增加",
                    consequence="频率偏移，通信不稳定"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.5,
                "信号完整性": 9.0,
                "EMC合规": 4.5,
                "热设计": 3.5
            },
            lessons_learned=[
                "RF走线必须保持阻抗连续性",
                "天线净空区对WiFi性能至关重要",
                "电源分离可以降低噪声"
            ]
        )

        # 案例3: Arduino Uno R3 (85分, A级)
        self.cases["arduino_uno_r3"] = DesignCase(
            name="Arduino Uno R3",
            description="基于ATmega328P的Arduino兼容板,包含USB-Serial转换、电源选择",
            quality_score=85.0,
            difficulty="easy",
            key_features={
                "usb_serial": "ATmega16U2-MU接USB转Serial芯片(CH340)",
                "power_selection": "USB/外部电源自动切换(理想二极管)",
                "crystal_oscillator": "16MHz晶振 + 32.768kHz RTC可选",
                "led_builtin": "内置LED on Pin 13 (可编程)",
                "icsp_header": "标准ICSP排针，支持编程器",
                "reset_button": "复位按钮 + 去抖电容"
            },
            design_patterns=[
                "USB-Serial转换芯片",
                "电源自动切换",
                "双时钟源设计",
                "内置LED指示",
                "ICSP编程接口"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="USB D- D+ 直接短接",
                    reason="USB通信需要D-/D+差分信号",
                    consequence="USB通信失败"
                ),
                AvoidPattern(
                    pattern="复位按钮无去抖动",
                    reason="机械抖动会触发多次复位",
                    consequence="系统不稳定，用户体验差"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.5,
                "EMC合规": 4.0,
                "热设计": 3.5
            },
            lessons_learned=[
                "电源切换电路需要仔细设计",
                "用户接口需要去抖动处理",
                "双时钟源增加灵活性"
            ]
        )

        # 案例4: 树莓派Zero (87分, A级)
        self.cases["raspberry_pi_zero"] = DesignCase(
            name="树莓派Zero",
            description="基于BCM2835的树莓派Zero,包含HDMI、USB、SD卡、摄像头接口",
            quality_score=87.0,
            difficulty="hard",
            key_features={
                "hdmi_interface": "HDMI接口(19pin) + ESD保护",
                "usb_power": "USB供电 + 电源保护(自恢复保险丝)",
                "sd_card": "MicroSD卡槽 + 卡检测开关",
                "camera_interface": "CSI摄像头接口(15pin FPC)",
                "power_management": "多路电源管理(3.3V/1.8V)",
                "led_activity": "ACT LED + PWR LED指示"
            },
            design_patterns=[
                "HDMI ESD保护",
                "USB电源保护",
                "SD卡热插拔设计",
                "CSI高速接口",
                "多路电源管理"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="HDMI走线过长或无屏蔽",
                    reason="高速信号衰减和EMI辐射",
                    consequence="HDMI信号不稳定，不符合EMC标准"
                ),
                AvoidPattern(
                    pattern="USB无过流保护",
                    reason="USB短路会烧毁芯片",
                    consequence="设备损坏,安全风险"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 9.0,
                "EMC合规": 4.0,
                "热设计": 3.5
            },
            lessons_learned=[
                "高速接口需要ESD保护",
                "电源保护对可靠性至关重要",
                "热插拔设计提升用户体验"
            ]
        )

        # 案例5: USB Hub控制器 (86分, A级)
        self.cases["usb_hub_controller"] = DesignCase(
            name="USB Hub控制器",
            description="基于USB2514的4口USB Hub,包含电源管理、ESD保护、LED指示",
            quality_score=86.0,
            difficulty="easy",
            key_features={
                "hub_chip": "USB2514 Hub芯片 + 晶振(12MHz)",
                "power_switch": "每个USB口独立电源开关(MOSFET)",
                "esd_protection": "每个USB口TVS二极管ESD保护",
                "led_indicator": "每个USB口独立LED指示(速度/活动)",
                "upstream_port": "USB-C输入口 + 过流保护",
                "data_leds": "数据LED (TX/RX) + 电源LED"
            },
            design_patterns=[
                "独立电源开关",
                "TVS二极管ESD保护",
                "独立LED指示",
                "过流保护设计",
                "数据LED指示"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="USB口无ESD保护",
                    reason="热插拔会损坏芯片",
                    consequence="设备损坏,维修成本高"
                ),
                AvoidPattern(
                    pattern="所有USB口共享电源开关",
                    reason="一个口短路影响所有口",
                    consequence="可靠性低,故障扩散"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.5,
                "信号完整性": 8.5,
                "EMC合规": 4.5,
                "热设计": 3.5
            },
            lessons_learned=[
                "ESD保护对USB设备至关重要",
                "独立开关提升可靠性",
                "LED指示改善用户体验"
            ]
        )

        # 案例6: LED驱动器 (84分, A级)
        self.cases["led_driver"] = DesignCase(
            name="LED驱动器",
            description="基于WS2812B的RGB LED驱动器,包含PWM调光、电源滤波、信号放大",
            quality_score=84.0,
            difficulty="easy",
            key_features={
                "led_driver": "WS2812B LED驱动芯片(集成恒流源)",
                "power_filter": "输入电源LC滤波(100μF+0.1μF)",
                "signal_amplifier": "74HC245缓冲器放大数据信号",
                "connector": "JST-XH 4pin连接器(信号+电源)",
                "pwm_frequency": "PWM频率800Hz(可调)",
                "protection": "输出过压保护(稳压二极管)"
            },
            design_patterns=[
                "集成恒流源驱动",
                "LC π型滤波",
                "信号缓冲放大",
                "过压保护设计"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="电源滤波电容过小",
                    reason="纹波大会影响LED亮度稳定性",
                    consequence="LED闪烁,显示效果差"
                ),
                AvoidPattern(
                    pattern="数据线无缓冲直接驱动",
                    reason="驱动能力不足",
                    consequence="信号衰减,通信失败"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 4.0,
                "热设计": 3.5
            },
            lessons_learned=[
                "电源滤波对LED驱动至关重要",
                "信号缓冲可以提升驱动能力",
                "过压保护可以延长LED寿命"
            ]
        )

        # 案例7: 电池充电器 (83分, A-级)
        self.cases["battery_charger"] = DesignCase(
            name="锂电池充电器",
            description="基于TP4056的单节锂电池充电器,包含CC/CV充电、温度检测、状态指示",
            quality_score=83.0,
            difficulty="medium",
            key_features={
                "charger_ic": "TP4056充电管理芯片(开关型)",
                "power_inductor": "功率电感(10μH,饱和电流3A)",
                "current_sense": "电流检测电阻(0.1Ω/1W)",
                "temperature": "NTC热敏电阻(10kΩ@25°C)温度检测",
                "led_status": "充电状态LED(红)+满电LED(绿)+错误LED(黄)",
                "protection": "输入反接保护(肖特基)+输出过流保护"
            },
            design_patterns=[
                "开关型充电管理",
                "电流检测反馈",
                "温度检测保护",
                "状态LED指示",
                "多重保护设计"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="电感饱和电流过小",
                    reason="电感饱和导致充电电流不稳定",
                    consequence="充电效率低,电感发热"
                ),
                AvoidPattern(
                    pattern="无温度检测",
                    reason="电池过热会爆炸",
                    consequence="安全风险.产品责任"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 3.5,
                "热设计": 4.0
            },
            lessons_learned=[
                "温度检测对锂电池充电至关重要",
                "电流检测可以精确控制充电",
                "多重保护提升安全性"
            ]
        )

        # 案例8: 音频放大器 (82分, A-级)
        self.cases["audio_amplifier"] = DesignCase(
            name="音频放大器",
            description="基于TPA3116的D类音频放大器,包含音量控制、滤波器/保护电路",
            quality_score=82.0,
            difficulty="medium",
            key_features={
                "amplifier_ic": "TPA3116 D类音频放大器(双声道)",
                "volume_control": "数字电位器(10kΩ)音量控制",
                "input_filter": "RC低通滤波器(截止频率20kHz)",
                "output_filter": "LC低通滤波器(截止频率20kHz)",
                "protection": "输出过流保护 + 直流阻断",
                "power_decoupling": "每个VCC引脚0.1μF + 47μF电容"
            },
            design_patterns=[
                "D类放大器高效低失真",
                "数字电位器精确控制",
                "输入输出滤波",
                "模拟电源去耦"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="无输入输出滤波",
                    reason="高频噪声会放大",
                    consequence="音质差.噪声大"
                ),
                AvoidPattern(
                    pattern="模拟地数字地混合",
                    reason="数字噪声耦合到模拟电路",
                    consequence="信噪比低.音质下降"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 3.5,
                "热设计": 3.0
            },
            lessons_learned=[
                "滤波对音频质量至关重要",
                "数字电位器比模拟电位器更可靠",
                "模拟地需要特别处理"
            ]
        )

        # 案例9: 电机驱动器 (85分, A级)
        self.cases["motor_driver"] = DesignCase(
            name="电机驱动器",
            description="基于L298N的双H桥电机驱动器,包含PWM输入/电流检测/保护电路",
            quality_score=85.0,
            difficulty="medium",
            key_features={
                "driver_ic": "L298N双H桥驱动器(2个电机)",
                "current_sense": "电流检测电阻(0.5Ω/2W)",
                "protection": "续流二极管 + 去耦电容",
                "heat_sink": "驱动IC散热片 + 导热硅脂",
                "decoupling": "每个电源引脚100μF + 0.1μF电容",
                "pwm_input": "PWM输入上拉电阻10kΩ + 滤波"
            },
            design_patterns=[
                "双H桥驱动",
                "电流检测保护",
                "续流二极管保护",
                "散热设计"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="无续流二极管",
                    reason="电机反电动势会烧毁驱动器",
                    consequence="驱动器损坏.电机失控"
                ),
                AvoidPattern(
                    pattern="驱动IC无散热",
                    reason="驱动电流大发热严重",
                    consequence="过热保护.性能下降"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 4.0,
                "热设计": 4.5
            },
            lessons_learned=[
                "续流二极管对电机驱动必不可少",
                "散热设计对可靠性至关重要",
                "电流检测可以实现精确控制"
            ]
        )

        # 案例10: 电源模块 (88分, A级)
        self.cases["power_module"] = DesignCase(
            name="多路电源模块",
            description="包含3.3V/5V/12V三路输出的开关电源模块/包含过流保护/软启动",
            quality_score=88.0,
            difficulty="hard",
            key_features={
                "buck_converter": "3路Buck转换器(LM2596 + 电感)",
                "soft_start": "软启动电路(SS引脚 + 电容)",
                "protection": "过流保护(检测电阻) + 过温保护(NTC)",
                "power_good": "每路电源PG信号(LED指示)",
                " sequencing": "电源时序控制(3.3V→5V→12V)",
                "emi_filter": "输入EMI滤波器(共模扼流圈)"
            },
            design_patterns=[
                "多路Buck转换",
                "软启动设计",
                "过流过温双重保护",
                "电源时序控制",
                "EMI滤波"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="无软启动直接上电",
                    reason="浪涌电流烧毁电路",
                    consequence="器件损坏.可靠性低"
                ),
                AvoidPattern(
                    pattern="无EMI滤波",
                    reason="开关噪声传导到电网",
                    consequence="不符合EMC标准.干扰其他设备"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.5,
                "信号完整性": 8.5,
                "EMC合规": 4.5,
                "热设计": 4.0
            },
            lessons_learned=[
                "软启动对电源模块至关重要",
                "EMI滤波是强制要求",
                "电源时序可以避免冲突"
            ]
        )

        # 案例11: CAN总线通信模块 (85分, A级)
        self.cases["can_bus_module"] = DesignCase(
            name="CAN总线通信模块",
            description="基于CAN控制器的工业通信模块，包含隔离保护、终端电阻、ESD防护",
            quality_score=85.0,
            difficulty="medium",
            key_features={
                "can_controller": "CAN控制器(SJA1000) + 收发器(TJA1050)",
                "isolation": "数字隔离器(ADuM1201)隔离CAN总线",
                "termination": "终端电阻(120Ω)可跳线配置",
                "esd_protection": "TVS二极管ESD保护(CAN_H/CAN_L)",
                "status_leds": "TX/RX/ERROR状态LED指示",
                "filter": "共模滤波器减少EMI"
            },
            design_patterns=[
                "CAN总线隔离设计",
                "终端电阻配置",
                "ESD保护",
                "状态LED指示",
                "共模滤波"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="CAN总线无终端电阻",
                    reason="信号反射导致通信错误",
                    consequence="通信不稳定，误码率高"
                ),
                AvoidPattern(
                    pattern="无ESD保护",
                    reason="工业环境ESD干扰严重",
                    consequence="器件损坏，可靠性低"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.5,
                "EMC合规": 4.5,
                "热设计": 3.5
            },
            lessons_learned=[
                "终端电阻对CAN总线通信至关重要",
                "隔离设计提升抗干扰能力",
                "ESD保护是工业应用必需"
            ]
        )

        # 案例12: 无线充电接收器 (84分, A级)
        self.cases["wireless_charger_rx"] = DesignCase(
            name="无线充电接收器",
            description="基于Qi标准的无线充电接收器，包含整流桥、稳压、异物检测",
            quality_score=84.0,
            difficulty="hard",
            key_features={
                "rectifier": "全桥整流器(肖特基二极管)",
                "voltage_regulator": "LDO稳压器(5V输出)",
                "coil_tuning": "LC谐振电路(调谐到110-205kHz)",
                "foreign_object": "异物检测(温度传感器+电流检测)",
                "led_status": "充电状态LED(红)+满电LED(绿)",
                "protection": "过压保护(Zener) + 过流保护(PTC)"
            },
            design_patterns=[
                "全桥整流",
                "LC谐振调谐",
                "异物检测",
                "过压过流保护",
                "状态LED指示"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="LC电路未调谐",
                    reason="谐振频率偏差导致效率低",
                    consequence="充电效率低，发热严重"
                ),
                AvoidPattern(
                    pattern="无异物检测",
                    reason="金属异物会发热",
                    consequence="安全风险，可能起火"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 4.0,
                "热设计": 4.0
            },
            lessons_learned=[
                "LC调谐对无线充电效率至关重要",
                "异物检测是安全必需",
                "保护电路提升可靠性"
            ]
        )

        # 案例13: 传感器信号调理模块 (86分, A级)
        self.cases["sensor_signal_conditioning"] = DesignCase(
            name="传感器信号调理模块",
            description="多路传感器信号调理模块，包含放大、滤波、ADC转换",
            quality_score=86.0,
            difficulty="medium",
            key_features={
                "instrumentation_amp": "仪表放大器(AD623)高共模抑制比",
                "low_pass_filter": "有源低通滤波器(截止频率10Hz)",
                "adc": "16位ADC(ADS1115) I2C接口",
                "reference": "精密基准电压源(2.5V)",
                "protection": "输入保护(串联电阻+TVS)",
                "shielding": "模拟信号屏蔽走线"
            },
            design_patterns=[
                "仪表放大器设计",
                "有源滤波",
                "高精度ADC",
                "输入保护",
                "屏蔽设计"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="模拟数字地混合",
                    reason="数字噪声耦合到模拟电路",
                    consequence="信噪比低，精度下降"
                ),
                AvoidPattern(
                    pattern="无输入保护",
                    reason="过压会烧毁放大器",
                    consequence="器件损坏，不可靠"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 9.0,
                "EMC合规": 4.0,
                "热设计": 3.5
            },
            lessons_learned=[
                "模拟数字地分离对精度至关重要",
                "输入保护提升可靠性",
                "屏蔽设计减少干扰"
            ]
        )

        # 案例14: 蓝牙音频模块 (83分, A级)
        self.cases["bluetooth_audio"] = DesignCase(
            name="蓝牙音频模块",
            description="基于蓝牙芯片的音频模块，包含音频编解码、功放、天线",
            quality_score=83.0,
            difficulty="hard",
            key_features={
                "bluetooth_chip": "蓝牙音频芯片(BK3254) + 天线",
                "audio_codec": "I2S音频编解码器(PCM5102)",
                "audio_amp": "D类音频功放(TPA2016) 3W输出",
                "antenna": "PCB天线(2.4GHz) + 阻抗匹配",
                "crystal": "26MHz晶振 + 负载电容(12pF)",
                "filter": "音频滤波器(20Hz-20kHz)"
            },
            design_patterns=[
                "I2S音频接口",
                "D类功放高效",
                "PCB天线设计",
                "阻抗匹配",
                "音频滤波"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="天线附近有金属",
                    reason="影响天线辐射特性",
                    consequence="通信距离短，音质差"
                ),
                AvoidPattern(
                    pattern="音频走线无屏蔽",
                    reason="数字噪声耦合到音频",
                    consequence="底噪大，音质差"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 4.0,
                "热设计": 3.0
            },
            lessons_learned=[
                "天线布局对蓝牙性能至关重要",
                "音频走线需要屏蔽",
                "阻抗匹配减少信号反射"
            ]
        )

        # 案例15: GPS定位模块 (87分, A级)
        self.cases["gps_module"] = DesignCase(
            name="GPS定位模块",
            description="基于GPS芯片的定位模块，包含天线、RTC、备用电池",
            quality_score=87.0,
            difficulty="medium",
            key_features={
                "gps_chip": "GPS接收芯片(UBLOX NEO-M8N)",
                "antenna": "有源GPS天线(1575.42MHz) + LNA",
                "rtc": "RTC实时时钟(32.768kHz晶振)",
                "backup_battery": "备用电池(CR2032)保持RTC",
                "led_status": "定位状态LED(PPS信号)",
                "uart": "UART接口(9600bps)输出NMEA数据"
            },
            design_patterns=[
                "GPS天线设计",
                "RTC备用电池",
                "LNA低噪声放大",
                "PPS信号指示",
                "NMEA数据输出"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="天线附近有干扰源",
                    reason="干扰GPS微弱信号",
                    consequence="定位慢，精度差"
                ),
                AvoidPattern(
                    pattern="无RTC备用电池",
                    reason="断电后RTC丢失",
                    consequence="冷启动慢，TTFF长"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 9.0,
                "EMC合规": 4.0,
                "热设计": 3.5
            },
            lessons_learned=[
                "天线布局对GPS性能至关重要",
                "RTC备用电池改善冷启动",
                "LNA提升接收灵敏度"
            ]
        )

        # 案例16: 以太网PHY模块 (86分, A级)
        self.cases["ethernet_phy"] = DesignCase(
            name="以太网PHY模块",
            description="基于以太网PHY芯片的网络模块，包含RJ45、隔离变压器、LED",
            quality_score=86.0,
            difficulty="hard",
            key_features={
                "phy_chip": "以太网PHY芯片(DP83848) + MAC接口(RMII)",
                "magnetics": "隔离变压器(H1102) + 共模扼流圈",
                "rj45": "RJ45连接器(带LED) + ESD保护",
                "crystal": "25MHz晶振 + 负载电容(22pF)",
                "led_status": "Link/Activity LED指示",
                "termination": "差分对终端电阻(49.9Ω)"
            },
            design_patterns=[
                "以太网PHY设计",
                "隔离变压器保护",
                "ESD保护",
                "差分对布线",
                "LED状态指示"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="无隔离变压器",
                    reason="无电气隔离",
                    consequence="ESD损坏，不安全"
                ),
                AvoidPattern(
                    pattern="差分对不等长",
                    reason="阻抗不连续",
                    consequence="信号完整性差，误码率高"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 9.0,
                "EMC合规": 4.5,
                "热设计": 3.5
            },
            lessons_learned=[
                "隔离变压器对以太网必不可少",
                "差分对等长对信号完整性至关重要",
                "ESD保护提升可靠性"
            ]
        )

        # 案例17: LCD显示模块 (84分, A级)
        self.cases["lcd_display"] = DesignCase(
            name="LCD显示模块",
            description="基于LCD控制器的显示模块，包含背光驱动、触摸屏接口",
            quality_score=84.0,
            difficulty="medium",
            key_features={
                "lcd_controller": "LCD控制器(ILI9341) + SPI接口",
                "backlight": "LED背光驱动(恒流源) + PWM调光",
                "touch_screen": "电容触摸屏控制器(FT6236) + I2C",
                "connector": "FPC连接器(40pin) + 锁扣",
                "level_shifter": "电平转换器(3.3V↔5V)",
                "filter": "RGB信号滤波器(EMI减少)"
            },
            design_patterns=[
                "SPI高速接口",
                "LED背光驱动",
                "电容触摸屏",
                "电平转换",
                "EMI滤波"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="背光无恒流驱动",
                    reason="LED亮度不稳定",
                    consequence="亮度不均，寿命短"
                ),
                AvoidPattern(
                    pattern="无电平转换",
                    reason="电压不匹配",
                    consequence="通信失败，器件损坏"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.0,
                "EMC合规": 4.0,
                "热设计": 3.0
            },
            lessons_learned=[
                "恒流驱动对背光稳定性至关重要",
                "电平转换避免电压不匹配",
                "EMI滤波减少干扰"
            ]
        )

        # 案例18: NFC读写器模块 (85分, A级)
        self.cases["nfc_reader"] = DesignCase(
            name="NFC读写器模块",
            description="基于NFC芯片的读写器模块，包含天线匹配、ESD保护、LED指示",
            quality_score=85.0,
            difficulty="medium",
            key_features={
                "nfc_chip": "NFC控制器(PN532) + SPI/I2C接口",
                "antenna": "PCB天线(13.56MHz) + 阻抗匹配",
                "matching": "LC匹配电路(调谐到13.56MHz)",
                "esd_protection": "TVS二极管ESD保护天线",
                "led_status": "读/写状态LED指示",
                "crystal": "27.12MHz晶振 + 负载电容"
            },
            design_patterns=[
                "NFC天线设计",
                "LC匹配电路",
                "ESD保护",
                "多接口支持",
                "状态LED指示"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="天线未调谐",
                    reason="谐振频率偏差",
                    consequence="读取距离短，失败率高"
                ),
                AvoidPattern(
                    pattern="无ESD保护",
                    reason="ESD会损坏NFC芯片",
                    consequence="器件损坏，可靠性低"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.5,
                "EMC合规": 4.0,
                "热设计": 3.0
            },
            lessons_learned=[
                "天线调谐对NFC性能至关重要",
                "ESD保护是必需的",
                "多接口提供灵活性"
            ]
        )

        # 案例19: 4-20mA电流环模块 (86分, A级)
        self.cases["current_loop"] = DesignCase(
            name="4-20mA电流环模块",
            description="工业标准4-20mA电流环接口模块，包含DAC、V/I转换、隔离",
            quality_score=86.0,
            difficulty="medium",
            key_features={
                "dac": "12位DAC(DAC8551) + SPI接口",
                "v_i_converter": "V/I转换器(XTR115) 4-20mA输出",
                "isolation": "数字隔离器(ISO7140)隔离通信",
                "protection": "过流保护(检测电阻) + TVS",
                "loop_power": "环路供电(24V) + 本地LDO",
                "calibration": "校准EEPROM(存储校准参数)"
            },
            design_patterns=[
                "V/I转换设计",
                "数字隔离",
                "过流保护",
                "环路供电",
                "校准存储"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="无过流保护",
                    reason="短路会烧毁器件",
                    consequence="器件损坏，不安全"
                ),
                AvoidPattern(
                    pattern="无校准",
                    reason="精度漂移",
                    consequence="测量不准，误差大"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 8.5,
                "EMC合规": 4.5,
                "热设计": 3.5
            },
            lessons_learned=[
                "过流保护对工业应用必不可少",
                "校准提升精度",
                "隔离设计增强安全性"
            ]
        )

        # 案例20: RS485通信模块 (87分, A级)
        self.cases["rs485_module"] = DesignCase(
            name="RS485通信模块",
            description="基于RS485的工业通信模块，包含隔离保护、终端电阻、ESD防护",
            quality_score=87.0,
            difficulty="medium",
            key_features={
                "transceiver": "RS485收发器(MAX485) + 自动方向控制",
                "isolation": "数字隔离器(ADuM1201)隔离RS485",
                "termination": "终端电阻(120Ω)可跳线配置",
                "esd_protection": "TVS二极管ESD保护(A/B线)",
                "bias_resistor": "偏置电阻(上拉/下拉)防止悬浮",
                "led_status": "TX/RX状态LED指示"
            },
            design_patterns=[
                "RS485收发器设计",
                "自动方向控制",
                "终端电阻配置",
                "ESD保护",
                "偏置电阻"
            ],
            avoid_patterns=[
                AvoidPattern(
                    pattern="无终端电阻",
                    reason="信号反射导致通信错误",
                    consequence="通信不稳定，误码率高"
                ),
                AvoidPattern(
                    pattern="无偏置电阻",
                    reason="总线悬浮",
                    consequence="通信失败，误判"
                )
            ],
            dimension_scores={
                "功能正确性": 15.0,
                "可制造性": 9.0,
                "信号完整性": 9.0,
                "EMC合规": 4.5,
                "热设计": 3.5
            },
            lessons_learned=[
                "终端电阻对RS485通信至关重要",
                "偏置电阻防止总线悬浮",
                "ESD保护提升可靠性"
            ]
        )

    def query_similar_case(self, project_description: str,
                           use_enhanced: bool = True) -> Optional[DesignCase]:
        """
        查询相似案例

        Args:
            project_description: 项目描述
            use_enhanced: 是否使用增强版匹配器 (默认True)

        Returns:
            最相似的案例, 如果没有则返回None
        """
        # 尝试使用增强版匹配器
        if use_enhanced and HAS_ENHANCED_MATCHER:
            try:
                matcher = create_enhanced_matcher(self)
                result = matcher.query_best_case(project_description, min_similarity=0.2)
                if result:
                    case_id, similarity, _ = result
                    return self.cases.get(case_id)
            except Exception:
                pass  # 回退到简单匹配

        # 简单关键词匹配 (回退方案)
        keywords = project_description.lower()

        # 关键词到案例的映射
        keyword_to_case = {
            "stm32": "stm32_minimal",
            "mcu": "stm32_minimal",
            "microcontroller": "stm32_minimal",
            "esp32": "esp32_wifi",
            "wifi": "esp32_wifi",
            "bluetooth": "bluetooth_audio",
            "iot": "esp32_wifi",
            "arduino": "arduino_uno_r3",
            "atmega": "arduino_uno_r3",
            "usb": "usb_hub_controller",
            "hub": "usb_hub_controller",
            "power": "power_module",
            "supply": "power_module",
            "buck": "power_module",
            "charger": "battery_charger",
            "battery": "battery_charger",
            "motor": "motor_driver",
            "driver": "motor_driver",
            "h-bridge": "motor_driver",
            "audio": "audio_amplifier",
            "amplifier": "audio_amplifier",
            "speaker": "audio_amplifier",
            "led": "led_driver",
            "pwm": "led_driver",
            "can": "can_bus_module",
            "rs485": "rs485_module",
            "ethernet": "ethernet_phy",
            "gps": "gps_module",
            "nfc": "nfc_reader",
            "lcd": "lcd_display",
            "display": "lcd_display",
            "sensor": "sensor_signal_conditioning",
            "wireless": "wireless_charger_rx",
            "qi": "wireless_charger_rx",
        }

        # 查找匹配的案例
        best_case_id = None
        best_score = 0

        for keyword, case_id in keyword_to_case.items():
            if keyword in keywords:
                # 简单计数匹配
                score = keywords.count(keyword)
                if score > best_score:
                    best_score = score
                    best_case_id = case_id

        if best_case_id and best_case_id in self.cases:
            return self.cases[best_case_id]

        # 如果没有匹配，返回第一个案例作为默认
        return next(iter(self.cases.values())) if self.cases else None

    def query_similar_cases(self, project_description: str,
                           top_k: int = 3) -> List[Tuple[DesignCase, float, Dict[str, float]]]:
        """
        查询相似案例 (返回多个)

        Args:
            project_description: 项目描述
            top_k: 返回的案例数量

        Returns:
            List[Tuple[DesignCase, float, Dict[str, float]]]: [(案例, 相似度, 详细分数), ...]
        """
        if HAS_ENHANCED_MATCHER:
            try:
                matcher = create_enhanced_matcher(self)
                results = matcher.query_similar_cases(project_description, top_k=top_k, min_similarity=0.2)
                return [
                    (self.cases[case_id], similarity, detail)
                    for case_id, similarity, detail in results
                    if case_id in self.cases
                ]
            except Exception:
                pass

        # 回退方案：返回前top_k个案例
        cases = list(self.cases.values())[:top_k]
        return [(case, 1.0 / (i + 1), {}) for i, case in enumerate(cases)]

    def explain_similarity(self, project_description: str,
                          case_id: str) -> Optional[Dict]:
        """
        解释相似度计算结果

        Args:
            project_description: 项目描述
            case_id: 案例ID

        Returns:
            Dict: 详细解释
        """
        if HAS_ENHANCED_MATCHER:
            try:
                matcher = create_enhanced_matcher(self)
                return matcher.explain_similarity(project_description, case_id)
            except Exception:
                pass

        return {"error": "Enhanced matcher not available"}

    def get_design_principles(self, dimension: str) -> List[str]:
        """
        获取特定维度的设计原则

        Args:
            dimension: 维度名称 (如 "信号完整性")、"热设计"等)

        Returns:
            该维度的最佳实践原则列表
        """
        principles = []

        for case in self.cases.values():
            if dimension in case.dimension_scores:
                # 如果该维度得分>8分， 说明是最佳实践
                if case.dimension_scores[dimension] > 8:
                    for feature_name, feature_value in case.key_features.items():
                        principles.append(
                            f"[{case.name}] {feature_name}: {feature_value}"
                        )

        # 巻加应避免的模式
        for case in self.cases.values():
            for avoid in case.avoid_patterns:
                if dimension.lower() in avoid.pattern.lower() or dimension.lower() in avoid.consequence.lower():
                    principles.append(
                        f"[避免] {avoid.pattern} - 原因: {avoid.reason}"
                        )

        return principles

    def get_successful_actions(self, dimension: str, min_success_rate: float = 0.0) -> List[str]:
        """
        获取某维度成功率高的动作

        Args:
            dimension: 维度名称
            min_success_rate: 最低成功率要求 (0-1)

        Returns:
            成功动作列表
        """
        actions = []

        for case in self.cases.values():
            if dimension in case.dimension_scores and case.dimension_scores[dimension] >= 8:
                # 从关键特征中提取动作
                for feature_name, feature_value in case.key_features.items():
                    # 简化特征为动作
                    action = feature_name.lower().replace(" ", "_")
                    actions.append(action)

        return actions

    def get_avoid_patterns(self, dimension: str) -> List[str]:
        """
        获取某维度应避免的模式

        Args:
            dimension: 维度名称

        Returns:
            应避免的模式列表
        """
        patterns = []

        for case in self.cases.values():
            for avoid in case.avoid_patterns:
                # 如果与维度相关
                if dimension.lower() in avoid.pattern.lower() or dimension.lower() in avoid.consequence.lower():
                    patterns.append(avoid.pattern)

        return patterns

    def export_to_json(self, output_path: str):
        """导出案例库到JSON文件"""
        data = {}

        for case_id, case in self.cases.items():
            data[case_id] = {
                "name": case.name,
                "description": case.description,
                "quality_score": case.quality_score,
                "difficulty": case.difficulty,
                "key_features": case.key_features,
                "design_patterns": case.design_patterns,
                "avoid_patterns": [
                    {
                        "pattern": ap.pattern,
                        "reason": ap.reason,
                        "consequence": ap.consequence
                    }
                    for ap in case.avoid_patterns
                ],
                "dimension_scores": case.dimension_scores,
                "lessons_learned": case.lessons_learned
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# 单例模式
_library_instance = None


def get_case_library() -> DesignCaseLibrary:
    """获取案例库单例"""
    global _library_instance
    if _library_instance is None:
        _library_instance = DesignCaseLibrary()
    return _library_instance
