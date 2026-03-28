"""添加被动元件到知识库"""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 读取现有知识库
with open('component_knowledge/component_db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

components = db.get('components', {})

# 添加常见被动元件
new_components = {
    # ===== 电容 =====
    "10uF 25V": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "电解电容 10uF 25V",
        "symbol_library": "Device:C_Polarized",
        "symbol_name": "Capacitor_Polarized",
        "pins": [
            {"number": "1", "name": "+", "type": "passive", "description": "正极"},
            {"number": "2", "name": "-", "type": "passive", "description": "负极/接GND"}
        ],
        "footprint": "Capacitor_SMD:CP_Radial_D5.0mm_P2.00mm"
    },
    "22uF 10V": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "电解电容 22uF 10V",
        "symbol_library": "Device:C_Polarized",
        "symbol_name": "Capacitor_Polarized",
        "pins": [
            {"number": "1", "name": "+", "type": "passive", "description": "正极"},
            {"number": "2", "name": "-", "type": "passive", "description": "负极/接GND"}
        ],
        "footprint": "Capacitor_SMD:CP_Radial_D5.0mm_P2.00mm"
    },
    "100uF 25V": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "电解电容 100uF 25V",
        "symbol_library": "Device:C_Polarized",
        "symbol_name": "Capacitor_Polarized",
        "pins": [
            {"number": "1", "name": "+", "type": "passive", "description": "正极"},
            {"number": "2", "name": "-", "type": "passive", "description": "负极/接GND"}
        ],
        "footprint": "Capacitor_SMD:CP_Radial_D6.3mm_P2.50mm"
    },
    "100nF 50V": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "陶瓷电容 100nF 50V",
        "symbol_library": "Device:C",
        "symbol_name": "Capacitor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Capacitor_SMD:C_0805_2012Metric"
    },
    "10nF 50V": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "陶瓷电容 10nF 50V",
        "symbol_library": "Device:C",
        "symbol_name": "Capacitor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Capacitor_SMD:C_0805_2012Metric"
    },
    # ===== 电阻 =====
    "10kΩ 5%": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "贴片电阻 10kΩ 5%",
        "symbol_library": "Device:R",
        "symbol_name": "Resistor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Resistor_SMD:R_0805_2012Metric"
    },
    "4.7kΩ 5%": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "贴片电阻 4.7kΩ 5%",
        "symbol_library": "Device:R",
        "symbol_name": "Resistor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Resistor_SMD:R_0805_2012Metric"
    },
    "1kΩ 5%": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "贴片电阻 1kΩ 5%",
        "symbol_library": "Device:R",
        "symbol_name": "Resistor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Resistor_SMD:R_0805_2012Metric"
    },
    "330Ω 5%": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "贴片电阻 330Ω 5%",
        "symbol_library": "Device:R",
        "symbol_name": "Resistor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Resistor_SMD:R_0805_2012Metric"
    },
    "100Ω 5%": {
        "category": "passive",
        "manufacturer": "Various",
        "status": "active",
        "description": "贴片电阻 100Ω 5%",
        "symbol_library": "Device:R",
        "symbol_name": "Resistor",
        "pins": [
            {"number": "1", "name": "1", "type": "passive", "description": "引脚1"},
            {"number": "2", "name": "2", "type": "passive", "description": "引脚2"}
        ],
        "footprint": "Resistor_SMD:R_0805_2012Metric"
    },
    # ===== 二极管 =====
    "1N4148": {
        "category": "diode",
        "manufacturer": "Various",
        "status": "active",
        "description": "开关二极管 1N4148",
        "symbol_library": "Device:D",
        "symbol_name": "Diode",
        "pins": [
            {"number": "1", "name": "A", "type": "passive", "description": "阳极 (Anode)"},
            {"number": "2", "name": "K", "type": "passive", "description": "阴极 (Kathode)"}
        ],
        "footprint": "Diode_SMD:D_SOD-123"
    },
    "SMBJ5.0A": {
        "category": "diode",
        "manufacturer": "Various",
        "status": "active",
        "description": "TVS二极管 5V 600W",
        "symbol_library": "Device:D_TVS",
        "symbol_name": "TVS_Diode",
        "pins": [
            {"number": "1", "name": "A", "type": "passive", "description": "阳极 (Anode)"},
            {"number": "2", "name": "K", "type": "passive", "description": "阴极 (Kathode)"}
        ],
        "footprint": "Diode_SMD:D_SMB"
    },
    "SS34": {
        "category": "diode",
        "manufacturer": "Various",
        "status": "active",
        "description": "肖特基二极管 3A 40V",
        "symbol_library": "Device:D_Schottky",
        "symbol_name": "Diode_Schottky",
        "pins": [
            {"number": "1", "name": "A", "type": "passive", "description": "阳极 (Anode)"},
            {"number": "2", "name": "K", "type": "passive", "description": "阴极 (Kathode)"}
        ],
        "footprint": "Diode_SMD:D_SMB"
    },
    # ===== LED =====
    "0603 Red": {
        "category": "led",
        "manufacturer": "Various",
        "status": "active",
        "description": "0603红色LED",
        "symbol_library": "Device:LED",
        "symbol_name": "LED",
        "pins": [
            {"number": "1", "name": "A", "type": "passive", "description": "阳极 (Anode)"},
            {"number": "2", "name": "K", "type": "passive", "description": "阴极 (Kathode)"}
        ],
        "footprint": "LED_SMD:LED_0603"
    },
    "0603 Green": {
        "category": "led",
        "manufacturer": "Various",
        "status": "active",
        "description": "0603绿色LED",
        "symbol_library": "Device:LED",
        "symbol_name": "LED",
        "pins": [
            {"number": "1", "name": "A", "type": "passive", "description": "阳极 (Anode)"},
            {"number": "2", "name": "K", "type": "passive", "description": "阴极 (Kathode)"}
        ],
        "footprint": "LED_SMD:LED_0603"
    },
    # ===== 连接器 =====
    "Micro-USB": {
        "category": "connector",
        "manufacturer": "Various",
        "status": "active",
        "description": "Micro USB 接口",
        "symbol_library": "Connector:USB_Micro-B",
        "symbol_name": "USB_Micro_B",
        "pins": [
            {"number": "1", "name": "VBUS", "type": "power_in", "description": "电源输入"},
            {"number": "2", "name": "D-", "type": "bidirectional", "description": "数据负"},
            {"number": "3", "name": "D+", "type": "bidirectional", "description": "数据正"},
            {"number": "4", "name": "ID", "type": "passive", "description": "识别引脚"},
            {"number": "5", "name": "GND", "type": "power_in", "description": "地"}
        ],
        "footprint": "Connector_USB:USB_Micro-B"
    },
    "USB-C-SMD": {
        "category": "connector",
        "manufacturer": "Various",
        "status": "active",
        "description": "USB Type-C 接口",
        "symbol_library": "Connector_USB:USB_C_Receptacle",
        "symbol_name": "USB_C_Receptacle",
        "pins": [
            {"number": "1", "name": "VBUS", "type": "power_in", "description": "电源输入"},
            {"number": "2", "name": "D-", "type": "bidirectional", "description": "数据负"},
            {"number": "3", "name": "D+", "type": "bidirectional", "description": "数据正"},
            {"number": "4", "name": "CC1", "type": "bidirectional", "description": "配置通道"},
            {"number": "5", "name": "CC2", "type": "bidirectional", "description": "配置通道"},
            {"number": "6", "name": "GND", "type": "power_in", "description": "地"}
        ],
        "footprint": "Connector_USB:USB_C_Receptacle_16P"
    }
}

# 添加到知识库
components.update(new_components)
db['components'] = components

# 保存
with open('component_knowledge/component_db.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f'添加了 {len(new_components)} 个被动元件到知识库')
print(f'知识库现在共有 {len(components)} 个元件')
