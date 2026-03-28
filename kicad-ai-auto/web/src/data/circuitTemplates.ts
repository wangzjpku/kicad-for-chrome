/**
 * 电路模板系统
 * 提供常见电路的完整定义，包括元件、网络连接和封装信息
 */

import { PCBData, Footprint, Track, Net, Point2D } from '../types';

/** 电路模板接口 */
export interface CircuitTemplate {
  id: string;
  name: string;
  description: string;
  category: 'power' | 'amplifier' | 'mcu' | 'communication' | 'sensor' | 'interface';
  keywords: string[];

  /** 电路参数 */
  parameters: TemplateParameter[];

  /** 需要的元件列表 */
  components: TemplateComponent[];

  /** 网络连接定义 */
  nets: TemplateNet[];

  /** 默认布局建议 */
  layout?: TemplateLayout;
}

/** 模板参数 */
export interface TemplateParameter {
  name: string;
  symbol: string;
  defaultValue: string;
  description: string;
}

/** 模板元件 */
export interface TemplateComponent {
  id: string;
  reference: string; // 如 "U1", "C1"
  type: 'ic' | 'capacitor' | 'resistor' | 'inductor' | 'diode' | 'crystal' | 'connector';
  name: string; // 如 "AMS1117-3.3"
  footprint: string; // 如 "SOT-223"
  library: string;
  description?: string;

  /** 引脚定义 */
  pins?: ComponentPin[];

  /** 固定位置（可选） */
  position?: { x: number; y: number };

  /** 是否必选 */
  required: boolean;
}

/** 元件引脚 */
export interface ComponentPin {
  number: string;
  name: string;
  type: 'input' | 'output' | 'bidirectional' | 'power' | 'gnd';
}

/** 网络连接 */
export interface TemplateNet {
  name: string;
  color?: string;
  connections: NetConnection[];
}

/** 网络连接点 */
export interface NetConnection {
  componentId: string; // 对应 TemplateComponent.id
  pin: string; // 引脚编号
}

/** 布局建议 */
export interface TemplateLayout {
  /** 建议的 PCB 尺寸 */
  boardSize?: { width: number; height: number };

  /** 元件分组 */
  groups?: {
    name: string;
    componentIds: string[];
    position?: { x: number; y: number };
  }[];
}

/** 
 * 芯片引脚定义数据库 - 100+ 常用芯片的引脚定义
 * 用于原理图生成和PCB布局
 */
export const CHIP_PIN_DEFINITIONS: Record<string, TemplateComponent[]> = {
  /** 电源管理芯片 */
  'LM7805': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM7805', footprint: 'TO-220-3_Horizontal',
    library: 'Regulator_Linear', description: '5V线性稳压器',
    pins: [
      { number: '1', name: 'VIN', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'VOUT', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LM1117': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM1117', footprint: 'Package_TO_SOT_SMD:SOT-223',
    library: 'Regulator_Linear', description: '低压差稳压器',
    pins: [
      { number: '1', name: 'GND/ADJ', type: 'gnd' },
      { number: '2', name: 'VOUT', type: 'output' },
      { number: '3', name: 'VIN', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'AP2112K': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AP2112K-3.3', footprint: 'Package_SO:SOT-23-5',
    library: 'Regulator_Linear', description: '3.3V LDO稳压器(带使能)',
    pins: [
      { number: '1', name: 'VIN', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'EN', type: 'input' },
      { number: '4', name: 'NC', type: 'bidirectional' },
      { number: '5', name: 'VOUT', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'L298N': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'L298N', footprint: 'Package_Multiwatt:Multiwatt-15_Horizontal',
    library: 'Driver_Motor', description: '双H桥电机驱动',
    pins: [
      { number: '1', name: 'CURRENT SENSING A', type: 'input' },
      { number: '2', name: 'OUTPUT1', type: 'output' },
      { number: '3', name: 'OUTPUT2', type: 'output' },
      { number: '4', name: 'VS', type: 'power' },
      { number: '5', name: 'INPUT1', type: 'input' },
      { number: '6', name: 'ENABLE A', type: 'input' },
      { number: '7', name: 'INPUT2', type: 'input' },
      { number: '8', name: 'GND', type: 'gnd' },
      { number: '9', name: 'VSS', type: 'power' },
      { number: '10', name: 'INPUT3', type: 'input' },
      { number: '11', name: 'ENABLE B', type: 'input' },
      { number: '12', name: 'INPUT4', type: 'input' },
      { number: '13', name: 'OUTPUT3', type: 'output' },
      { number: '14', name: 'OUTPUT4', type: 'output' },
      { number: '15', name: 'CURRENT SENSING B', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'A4988': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'A4988', footprint: 'Package_SO:MSOP-16_3x4mm_P0.5mm',
    library: 'Driver_Motor', description: '步进电机驱动',
    pins: [
      { number: '1', name: 'RESET', type: 'input' },
      { number: '2', name: 'HOME', type: 'output' },
      { number: '3', name: 'MS1', type: 'input' },
      { number: '4', name: 'MS2', type: 'input' },
      { number: '5', name: 'MS3', type: 'input' },
      { number: '6', name: 'ENABLE', type: 'input' },
      { number: '7', name: 'STEP', type: 'input' },
      { number: '8', name: 'DIR', type: 'input' },
      { number: '9', name: 'GND', type: 'gnd' },
      { number: '10', name: 'LOGIC PWR', type: 'power' },
      { number: '11', name: 'MOTOR PWR', type: 'power' },
      { number: '12', name: 'OUT1A', type: 'output' },
      { number: '13', name: 'OUT1B', type: 'output' },
      { number: '14', name: 'OUT2A', type: 'output' },
      { number: '15', name: 'OUT2B', type: 'output' },
      { number: '16', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'DRV8825': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DRV8825', footprint: 'Package_SO:HTSSOP-28_4.4x9.7mm_P0.65mm',
    library: 'Driver_Motor', description: '高性能步进电机驱动',
    pins: [
      { number: '1', name: 'VMOT', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'FAULT', type: 'output' },
      { number: '4', name: 'M0', type: 'input' },
      { number: '5', name: 'M1', type: 'input' },
      { number: '6', name: 'M2', type: 'input' },
      { number: '7', name: 'RESET', type: 'input' },
      { number: '8', name: 'SLEEP', type: 'input' },
      { number: '9', name: 'STEP', type: 'input' },
      { number: '10', name: 'DIR', type: 'input' },
      { number: '11', name: 'ENABLE', type: 'input' },
      { number: '12', name: 'VCC', type: 'power' },
      { number: '13', name: 'NC', type: 'bidirectional' },
      { number: '14', name: 'NC', type: 'bidirectional' },
      { number: '15', name: 'OUT1A', type: 'output' },
      { number: '16', name: 'OUT1B', type: 'output' },
      { number: '17', name: 'PGND', type: 'gnd' },
      { number: '18', name: 'PGND', type: 'gnd' },
      { number: '19', name: 'OUT2A', type: 'output' },
      { number: '20', name: 'OUT2B', type: 'output' },
      { number: '21', name: 'NC', type: 'bidirectional' },
      { number: '22', name: 'NC', type: 'bidirectional' },
      { number: '23', name: 'DECAY', type: 'input' },
      { number: '24', name: 'GND', type: 'gnd' },
      { number: '25', name: 'VCP', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'ULN2003': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'ULN2003', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Driver_Array', description: '达林顿晶体管阵列',
    pins: [
      { number: '1', name: 'IN1', type: 'input' },
      { number: '2', name: 'IN2', type: 'input' },
      { number: '3', name: 'IN3', type: 'input' },
      { number: '4', name: 'IN4', type: 'input' },
      { number: '5', name: 'IN5', type: 'input' },
      { number: '6', name: 'IN6', type: 'input' },
      { number: '7', name: 'IN7', type: 'input' },
      { number: '8', name: 'GND', type: 'gnd' },
      { number: '9', name: 'COM', type: 'power' },
      { number: '10', name: 'OUT7', type: 'output' },
      { number: '11', name: 'OUT6', type: 'output' },
      { number: '12', name: 'OUT5', type: 'output' },
      { number: '13', name: 'OUT4', type: 'output' },
      { number: '14', name: 'OUT3', type: 'output' },
      { number: '15', name: 'OUT2', type: 'output' },
      { number: '16', name: 'OUT1', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'ULN2803': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'ULN2803', footprint: 'Package_SO:SOIC-18_3.9x11.3mm_P1.27mm',
    library: 'Driver_Array', description: '8路达林顿晶体管阵列',
    pins: [
      { number: '1', name: 'IN1', type: 'input' },
      { number: '2', name: 'IN2', type: 'input' },
      { number: '3', name: 'IN3', type: 'input' },
      { number: '4', name: 'IN4', type: 'input' },
      { number: '5', name: 'IN5', type: 'input' },
      { number: '6', name: 'IN6', type: 'input' },
      { number: '7', name: 'IN7', type: 'input' },
      { number: '8', name: 'IN8', type: 'input' },
      { number: '9', name: 'COM', type: 'power' },
      { number: '10', name: 'OUT8', type: 'output' },
      { number: '11', name: 'OUT7', type: 'output' },
      { number: '12', name: 'OUT6', type: 'output' },
      { number: '13', name: 'OUT5', type: 'output' },
      { number: '14', name: 'OUT4', type: 'output' },
      { number: '15', name: 'OUT3', type: 'output' },
      { number: '16', name: 'OUT2', type: 'output' },
      { number: '17', name: 'OUT1', type: 'output' },
      { number: '18', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'IRF540': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'IRF540N', footprint: 'Package_TO_SOT_SMD:TO-263-3_Horizontal',
    library: 'Transistor_FET', description: 'N沟道MOSFET',
    pins: [
      { number: '1', name: 'G', type: 'input' },
      { number: '2', name: 'D', type: 'output' },
      { number: '3', name: 'S', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'IRF9530': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'IRF9530N', footprint: 'Package_TO_SOT_SMD:TO-263-3_Horizontal',
    library: 'Transistor_FET', description: 'P沟道MOSFET',
    pins: [
      { number: '1', name: 'G', type: 'input' },
      { number: '2', name: 'S', type: 'bidirectional' },
      { number: '3', name: 'D', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'IRF2104': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'IRF2104', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Driver_MOSFET', description: '半桥驱动芯片',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'IN', type: 'input' },
      { number: '3', name: 'SD', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'LO', type: 'output' },
      { number: '6', name: 'VS', type: 'power' },
      { number: '7', name: 'HO', type: 'output' },
      { number: '8', name: 'VB', type: 'power' },
      { number: '9', name: 'HO', type: 'output' },
      { number: '10', name: 'VS', type: 'power' },
      { number: '11', name: 'LO', type: 'output' },
      { number: '12', name: 'GND', type: 'gnd' },
      { number: '13', name: 'IN', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'IR2101': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'IR2101', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Driver_MOSFET', description: '半桥驱动芯片',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'IN', type: 'input' },
      { number: '3', name: 'SD', type: 'input' },
      { number: '4', name: 'LO', type: 'output' },
      { number: '5', name: 'VS', type: 'power' },
      { number: '6', name: 'HO', type: 'output' },
      { number: '7', name: 'VB', type: 'power' },
      { number: '8', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'IR2110': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'IR2110', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Driver_MOSFET', description: '高压半桥驱动',
    pins: [
      { number: '1', name: 'LO', type: 'output' },
      { number: '2', name: 'VCC', type: 'power' },
      { number: '3', name: 'VSS', type: 'gnd' },
      { number: '4', name: 'SD', type: 'input' },
      { number: '5', name: 'IN', type: 'input' },
      { number: '6', name: 'VSS', type: 'gnd' },
      { number: '7', name: 'HO', type: 'output' },
      { number: '8', name: 'VS', type: 'power' },
      { number: '9', name: 'VB', type: 'power' },
      { number: '10', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'AMS1117': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AMS1117', footprint: 'Package_TO_SOT_SMD:SOT-223',
    library: 'Regulator_Linear', description: '低压差稳压器',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VOUT', type: 'output' },
      { number: '3', name: 'VIN', type: 'power' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 传感器芯片 */
  'DHT22': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DHT22', footprint: 'Module:DHT22',
    library: 'Sensor', description: '温湿度传感器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'DATA', type: 'bidirectional' },
      { number: '3', name: 'NC', type: 'bidirectional' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'DHT11': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DHT11', footprint: 'Module:DHT11',
    library: 'Sensor', description: '温湿度传感器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'DATA', type: 'bidirectional' },
      { number: '3', name: 'NC', type: 'bidirectional' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'DS18B20': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DS18B20', footprint: 'Package_TO_SOT_THT:TO-92-3_W2.54mm_P1.27mm',
    library: 'Sensor', description: '单总线数字温度传感器',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'DQ', type: 'bidirectional' },
      { number: '3', name: 'VDD', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'BME280': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'BME280', footprint: 'Package_LGA:BME280_2.5x2.5mm',
    library: 'Sensor', description: '气压温湿度传感器',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VDD', type: 'power' },
      { number: '3', name: 'SDO', type: 'output' },
      { number: '4', name: 'SDI', type: 'input' },
      { number: '5', name: 'SCK', type: 'input' },
      { number: '6', name: 'CSB', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MPU6050': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MPU6050', footprint: 'Package_QFN:QFN-24_4x4mm_P0.5mm',
    library: 'Sensor', description: '六轴加速度计陀螺仪',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SCL', type: 'input' },
      { number: '4', name: 'SDA', type: 'bidirectional' },
      { number: '5', name: 'XDA', type: 'bidirectional' },
      { number: '6', name: 'XCL', type: 'bidirectional' },
      { number: '7', name: 'AD0', type: 'input' },
      { number: '8', name: 'INT', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'HC-SR04': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'HC-SR04', footprint: 'Module:HC-SR04',
    library: 'Sensor', description: '超声波测距模块',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'TRIG', type: 'input' },
      { number: '3', name: 'ECHO', type: 'output' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MQ-2': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MQ-2', footprint: 'Module:MQ-2',
    library: 'Sensor', description: '烟雾气体传感器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'AOUT', type: 'output' },
      { number: '3', name: 'DOUT', type: 'output' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'BH1750': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'BH1750', footprint: 'Package_SO:MSOP-8_3x3mm_P0.65mm',
    library: 'Sensor', description: '光照强度传感器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SDA', type: 'bidirectional' },
      { number: '4', name: 'SCL', type: 'input' },
      { number: '5', name: 'ADDR', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 显示驱动芯片 */
  'SSD1306': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SSD1306', footprint: 'Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm',
    library: 'Display', description: '0.96寸OLED驱动芯片',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SCL', type: 'input' },
      { number: '4', name: 'SDA', type: 'bidirectional' },
      { number: '5', name: 'RES', type: 'input' },
      { number: '6', name: 'DC', type: 'input' },
      { number: '7', name: 'CS', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SSD1327': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SSD1327', footprint: 'Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm',
    library: 'Display', description: '1.5寸OLED驱动芯片',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SCL', type: 'input' },
      { number: '4', name: 'SDA', type: 'bidirectional' },
      { number: '5', name: 'RES', type: 'input' },
      { number: '6', name: 'DC', type: 'input' },
      { number: '7', name: 'CS', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'ST7789': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'ST7789', footprint: 'Package_LGA:LGA-20_2.5x2.5mm',
    library: 'Display', description: 'IPS液晶驱动芯片',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SCL', type: 'input' },
      { number: '4', name: 'SDA', type: 'bidirectional' },
      { number: '5', name: 'RES', type: 'input' },
      { number: '6', name: 'DC', type: 'input' },
      { number: '7', name: 'CS', type: 'input' },
      { number: '8', name: 'BLK', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'ILI9341': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'ILI9341', footprint: 'Package_SO:TSOP-40_10.16x6.5mm_P0.5mm',
    library: 'Display', description: 'TFT液晶驱动芯片',
    pins: [
      { number: '1', name: 'VDD', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'DB0', type: 'bidirectional' },
      { number: '4', name: 'DB1', type: 'bidirectional' },
      { number: '5', name: 'DB2', type: 'bidirectional' },
      { number: '6', name: 'DB3', type: 'bidirectional' },
      { number: '7', name: 'DB4', type: 'bidirectional' },
      { number: '8', name: 'DB5', type: 'bidirectional' },
      { number: '9', name: 'DB6', type: 'bidirectional' },
      { number: '10', name: 'DB7', type: 'bidirectional' },
      { number: '11', name: 'RD', type: 'input' },
      { number: '12', name: 'WR', type: 'input' },
      { number: '13', name: 'RS', type: 'input' },
      { number: '14', name: 'CS', type: 'input' },
      { number: '15', name: 'RST', type: 'input' },
      { number: '16', name: 'LED', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'HX711': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'HX711', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Sensor', description: '24位ADC称重芯片',
    pins: [
      { number: '1', name: 'VSUP', type: 'power' },
      { number: '2', name: 'BASE', type: 'output' },
      { number: '3', name: 'VDD', type: 'power' },
      { number: '4', name: 'VFB', type: 'input' },
      { number: '5', name: 'AVDD', type: 'power' },
      { number: '6', name: 'AGNDS', type: 'gnd' },
      { number: '7', name: 'AGND', type: 'gnd' },
      { number: '8', name: 'AIN-', type: 'input' },
      { number: '9', name: 'AIN+', type: 'input' },
      { number: '10', name: 'DGND', type: 'gnd' },
      { number: '11', name: 'DVDD', type: 'power' },
      { number: '12', name: 'CLK', type: 'input' },
      { number: '13', name: 'DOUT', type: 'output' },
      { number: '14', name: 'PD_SCK', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'PCF8574': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'PCF8574', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Interface', description: 'I/O扩展芯片',
    pins: [
      { number: '1', name: 'A0', type: 'input' },
      { number: '2', name: 'A1', type: 'input' },
      { number: '3', name: 'A2', type: 'input' },
      { number: '4', name: 'P0', type: 'bidirectional' },
      { number: '5', name: 'P1', type: 'bidirectional' },
      { number: '6', name: 'P2', type: 'bidirectional' },
      { number: '7', name: 'P3', type: 'bidirectional' },
      { number: '8', name: 'VSS', type: 'gnd' },
      { number: '9', name: 'P4', type: 'bidirectional' },
      { number: '10', name: 'P5', type: 'bidirectional' },
      { number: '11', name: 'P6', type: 'bidirectional' },
      { number: '12', name: 'P7', type: 'bidirectional' },
      { number: '13', name: 'INT', type: 'output' },
      { number: '14', name: 'SCL', type: 'input' },
      { number: '15', name: 'SDA', type: 'bidirectional' },
      { number: '16', name: 'VDD', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'PCF8591': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'PCF8591', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Converter', description: '4路ADC+1路DAC',
    pins: [
      { number: '1', name: 'A0', type: 'input' },
      { number: '2', name: 'A1', type: 'input' },
      { number: '3', name: 'A2', type: 'input' },
      { number: '4', name: 'A GND', type: 'gnd' },
      { number: '5', name: 'AIN0', type: 'input' },
      { number: '6', name: 'AIN1', type: 'input' },
      { number: '7', name: 'AIN2', type: 'input' },
      { number: '8', name: 'AIN3', type: 'input' },
      { number: '9', name: 'VREF', type: 'input' },
      { number: '10', name: 'EXT', type: 'input' },
      { number: '11', name: 'AGND', type: 'gnd' },
      { number: '12', name: 'VSS', type: 'gnd' },
      { number: '13', name: 'SDA', type: 'bidirectional' },
      { number: '14', name: 'SCL', type: 'input' },
      { number: '15', name: 'OSC', type: 'output' },
      { number: '16', name: 'VDD', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'ADS1115': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'ADS1115', footprint: 'Package_SO:MSOP-10_3x3mm_P0.5mm',
    library: 'Converter', description: '16位4通道ADC',
    pins: [
      { number: '1', name: 'ADDR', type: 'input' },
      { number: '2', name: 'ALERT', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'AIN0', type: 'input' },
      { number: '5', name: 'AIN1', type: 'input' },
      { number: '6', name: 'AIN2', type: 'input' },
      { number: '7', name: 'AIN3', type: 'input' },
      { number: '8', name: 'VDD', type: 'power' },
      { number: '9', name: 'SCL', type: 'input' },
      { number: '10', name: 'SDA', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'W25Qxx': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'W25Q128', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory', description: '128Mbit SPI Flash',
    pins: [
      { number: '1', name: '/CS', type: 'input' },
      { number: '2', name: 'SO', type: 'output' },
      { number: '3', name: '/WP', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SI', type: 'input' },
      { number: '6', name: 'CLK', type: 'input' },
      { number: '7', name: '/HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'AT24C256': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AT24C256', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory', description: '256Kbit I2C EEPROM',
    pins: [
      { number: '1', name: 'A0', type: 'input' },
      { number: '2', name: 'A1', type: 'input' },
      { number: '3', name: 'A2', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SDA', type: 'bidirectional' },
      { number: '6', name: 'SCL', type: 'input' },
      { number: '7', name: 'WP', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'NRF24L01': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'NRF24L01', footprint: 'Module:NRF24L01',
    library: 'RF', description: '2.4G无线模块',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VCC', type: 'power' },
      { number: '3', name: 'CE', type: 'input' },
      { number: '4', name: 'CSN', type: 'input' },
      { number: '5', name: 'SCK', type: 'input' },
      { number: '6', name: 'MOSI', type: 'input' },
      { number: '7', name: 'MISO', type: 'output' },
      { number: '8', name: 'IRQ', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LoRa-Radio': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SX1278', footprint: 'Package_DFN_QFN:DFN-8_2x2mm_P0.5mm',
    library: 'RF', description: 'LoRa无线模块',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'DIO0', type: 'bidirectional' },
      { number: '3', name: 'DIO1', type: 'bidirectional' },
      { number: '4', name: 'DIO2', type: 'bidirectional' },
      { number: '5', name: 'DIO3', type: 'bidirectional' },
      { number: '6', name: '3V3', type: 'power' },
      { number: '7', name: 'NSS', type: 'input' },
      { number: '8', name: 'SCK', type: 'input' },
      { number: '9', name: 'MISO', type: 'output' },
      { number: '10', name: 'MOSI', type: 'input' },
      { number: '11', name: 'NRST', type: 'input' },
      { number: '12', name: 'DIO5', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SIM800L': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SIM800L', footprint: 'Module:SIM800L',
    library: 'RF', description: 'GSM/GPRS模块',
    pins: [
      { number: '1', name: 'NET', type: 'bidirectional' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'RST', type: 'input' },
      { number: '4', name: 'RXD', type: 'input' },
      { number: '5', name: 'TXD', type: 'output' },
      { number: '6', name: 'GND', type: 'gnd' },
      { number: '7', name: 'VCC', type: 'power' },
      { number: '8', name: 'DTR', type: 'input' },
      { number: '9', name: 'RING', type: 'output' },
      { number: '10', name: 'DCD', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'GPS-NEO': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'NEO-6M', footprint: 'Module:GPS-NEO-6M',
    library: 'RF', description: 'GPS定位模块',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'RXD', type: 'input' },
      { number: '3', name: 'TXD', type: 'output' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 音频芯片 */
  'PAM8403': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'PAM8403', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Amplifier_Audio', description: '3W D类功放',
    pins: [
      { number: '1', name: 'OUTL+', type: 'output' },
      { number: '2', name: 'OUTL-', type: 'output' },
      { number: '3', name: 'PGND', type: 'gnd' },
      { number: '4', name: 'OUTR-', type: 'output' },
      { number: '5', name: 'OUTR+', type: 'output' },
      { number: '6', name: 'VDD', type: 'power' },
      { number: '7', name: 'MUTE', type: 'input' },
      { number: '8', name: 'INR', type: 'input' },
      { number: '9', name: 'INL', type: 'input' },
      { number: '10', name: 'GND', type: 'gnd' },
      { number: '11', name: 'NC', type: 'bidirectional' },
      { number: '12', name: 'NC', type: 'bidirectional' },
      { number: '13', name: 'NC', type: 'bidirectional' },
      { number: '14', name: 'NC', type: 'bidirectional' },
      { number: '15', name: 'NC', type: 'bidirectional' },
      { number: '16', name: 'NC', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MAX98357A': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MAX98357A', footprint: 'Package_DFN_QFN:DFN-10_2x2mm_P0.4mm',
    library: 'Amplifier_Audio', description: 'I2S音频功放',
    pins: [
      { number: '1', name: 'OUT+', type: 'output' },
      { number: '2', name: 'OUT-', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'VDD', type: 'power' },
      { number: '5', name: 'GAIN', type: 'input' },
      { number: '6', name: 'SD', type: 'input' },
      { number: '7', name: 'BCLK', type: 'input' },
      { number: '8', name: 'LRC', type: 'input' },
      { number: '9', name: 'DIN', type: 'input' },
      { number: '10', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 马达驱动 */
  'L9110': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'L9110', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Driver_Motor', description: '单路马达驱动',
    pins: [
      { number: '1', name: 'OA', type: 'output' },
      { number: '2', name: 'OB', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'VCC', type: 'power' },
      { number: '5', name: 'VCC', type: 'power' },
      { number: '6', name: 'GND', type: 'gnd' },
      { number: '7', name: 'B-IA', type: 'input' },
      { number: '8', name: 'B-IB', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MX1508': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MX1508', footprint: 'Package_SO:SSOP-10_3.9x4.9mm_P0.5mm',
    library: 'Driver_Motor', description: '双路马达驱动',
    pins: [
      { number: '1', name: 'INA', type: 'input' },
      { number: '2', name: 'INB', type: 'input' },
      { number: '3', name: 'INC', type: 'input' },
      { number: '4', name: 'IND', type: 'input' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'OUTA', type: 'output' },
      { number: '7', name: 'OUTB', type: 'output' },
      { number: '8', name: 'OUTC', type: 'output' },
      { number: '9', name: 'OUTD', type: 'output' },
      { number: '10', name: 'VM', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** USB芯片 */
  'USB2512': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'USB2512', footprint: 'Package_SO:QFN-36_6x6mm_P0.5mm',
    library: 'Interface_USB', description: 'USB Hub控制器',
    pins: [
      { number: '1', name: 'VDD', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'DM1', type: 'bidirectional' },
      { number: '4', name: 'DP1', type: 'bidirectional' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'DM2', type: 'bidirectional' },
      { number: '7', name: 'DP2', type: 'bidirectional' },
      { number: '8', name: 'GND', type: 'gnd' },
      { number: '9', name: 'DM3', type: 'bidirectional' },
      { number: '10', name: 'DP3', type: 'bidirectional' },
      { number: '11', name: 'GND', type: 'gnd' },
      { number: '12', name: 'DM0', type: 'bidirectional' },
      { number: '13', name: 'DP0', type: 'bidirectional' },
      { number: '14', name: 'GND', type: 'gnd' },
      { number: '15', name: 'XTAL1', type: 'input' },
      { number: '16', name: 'XTAL2', type: 'output' },
      { number: '17', name: 'TEST', type: 'input' },
      { number: '18', name: 'RST', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 时钟芯片 */
  'DS3231': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DS3231', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'RTC', description: '高精度RTC时钟芯片',
    pins: [
      { number: '1', name: '32K', type: 'output' },
      { number: '2', name: 'VCC', type: 'power' },
      { number: '3', name: 'BAT', type: 'power' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SDA', type: 'bidirectional' },
      { number: '6', name: 'SCL', type: 'input' },
      { number: '7', name: 'SQW', type: 'output' },
      { number: '8', name: 'RST', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'DS1307': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DS1307', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'RTC', description: 'RTC时钟芯片',
    pins: [
      { number: '1', name: 'VBAT', type: 'power' },
      { number: '2', name: 'X1', type: 'input' },
      { number: '3', name: 'X2', type: 'output' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SDA', type: 'bidirectional' },
      { number: '6', name: 'SCL', type: 'input' },
      { number: '7', name: 'SQW', type: 'output' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 触摸芯片 */
  'FT5206': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'FT5206', footprint: 'Package_FP:FT5206',
    library: 'Sensor', description: '电容触摸控制器',
    pins: [
      { number: '1', name: 'VDD', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SCL', type: 'input' },
      { number: '4', name: 'SDA', type: 'bidirectional' },
      { number: '5', name: 'RST', type: 'input' },
      { number: '6', name: 'INT', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'XPT2046': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'XPT2046', footprint: 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
    library: 'Sensor', description: '电阻触摸控制器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'PEN', type: 'output' },
      { number: '4', name: 'DOUT', type: 'output' },
      { number: '5', name: 'DIN', type: 'input' },
      { number: '6', name: 'DCLK', type: 'input' },
      { number: '7', name: 'CS', type: 'input' },
      { number: '8', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** LED驱动 */
  'WS2812B': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'WS2812B', footprint: 'LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm',
    library: 'LED', description: '可编程RGB LED',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'DOUT', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'DIN', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'APA102': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'APA102', footprint: 'LED_SMD:APA102-2020',
    library: 'LED', description: '可编程RGB LED(带时钟)',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'CI', type: 'input' },
      { number: '3', name: 'DI', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'TM1829': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TM1829', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'LED', description: 'LED驱动芯片',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'DOUT', type: 'output' },
      { number: '3', name: 'DIN', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'VCC', type: 'power' },
      { number: '6', name: 'GND', type: 'gnd' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 电机驱动更多 */
  'TB6600': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TB6600', footprint: 'Module:TB6600',
    library: 'Driver_Motor', description: '步进电机驱动模块',
    pins: [
      { number: '1', name: 'E+', type: 'input' },
      { number: '2', name: 'E-', type: 'input' },
      { number: '3', name: 'M+', type: 'input' },
      { number: '4', name: 'M-', type: 'input' },
      { number: '5', name: 'PUL+', type: 'input' },
      { number: '6', name: 'PUL-', type: 'input' },
      { number: '7', name: 'DIR+', type: 'input' },
      { number: '8', name: 'DIR-', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'PCA9685': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'PCA9685', footprint: 'Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm',
    library: 'Driver_LED', description: '16路PWM控制器',
    pins: [
      { number: '1', name: 'A0', type: 'input' },
      { number: '2', name: 'A1', type: 'input' },
      { number: '3', name: 'A2', type: 'input' },
      { number: '4', name: 'A3', type: 'input' },
      { number: '5', name: 'A4', type: 'input' },
      { number: '6', name: 'OE', type: 'input' },
      { number: '7', name: 'LED0', type: 'output' },
      { number: '8', name: 'LED1', type: 'output' },
      { number: '9', name: 'LED2', type: 'output' },
      { number: '10', name: 'LED3', type: 'output' },
      { number: '11', name: 'LED4', type: 'output' },
      { number: '12', name: 'LED5', type: 'output' },
      { number: '13', name: 'LED6', type: 'output' },
      { number: '14', name: 'LED7', type: 'output' },
      { number: '15', name: 'LED8', type: 'output' },
      { number: '16', name: 'LED9', type: 'output' },
      { number: '17', name: 'LED10', type: 'output' },
      { number: '18', name: 'LED11', type: 'output' },
      { number: '19', name: 'LED12', type: 'output' },
      { number: '20', name: 'LED13', type: 'output' },
      { number: '21', name: 'LED14', type: 'output' },
      { number: '22', name: 'LED15', type: 'output' },
      { number: '23', name: 'VSS', type: 'gnd' },
      { number: '24', name: 'VCC', type: 'power' },
      { number: '25', name: 'SDA', type: 'bidirectional' },
      { number: '26', name: 'SCL', type: 'input' },
      { number: '27', name: 'OSC', type: 'input' },
      { number: '28', name: 'A5', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 光电耦合 */
  'PC817': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'PC817', footprint: 'Package_SO:SOIC-4_3.9x4.6mm_P1.27mm',
    library: 'Optocoupler', description: '光电耦合器',
    pins: [
      { number: '1', name: 'ANODE', type: 'input' },
      { number: '2', name: 'CATHODE', type: 'input' },
      { number: '3', name: 'EMITTER', type: 'output' },
      { number: '4', name: 'COLLECTOR', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'TLP281': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TLP281', footprint: 'Package_SO:SOIC-4_3.9x4.6mm_P1.27mm',
    library: 'Optocoupler', description: '光电耦合器(双路)',
    pins: [
      { number: '1', name: 'ANODE1', type: 'input' },
      { number: '2', name: 'CATHODE1', type: 'input' },
      { number: '3', name: 'EMITTER2', type: 'output' },
      { number: '4', name: 'COLLECTOR2', type: 'output' },
      { number: '5', name: 'ANODE2', type: 'input' },
      { number: '6', name: 'CATHODE2', type: 'input' },
      { number: '7', name: 'EMITTER1', type: 'output' },
      { number: '8', name: 'COLLECTOR1', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** DC-DC升压/降压 */
  'MT2492': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MT2492', footprint: 'Package_SO:ESOP-8',
    library: 'Regulator_Switching', description: '2A同步降压芯片',
    pins: [
      { number: '1', name: 'SW', type: 'output' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'FB', type: 'input' },
      { number: '4', name: 'EN', type: 'input' },
      { number: '5', name: 'VIN', type: 'power' },
      { number: '6', name: 'VIN', type: 'power' },
      { number: '7', name: 'VIN', type: 'power' },
      { number: '8', name: 'SW', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'FP6291': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'FP6291', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Regulator_Switching', description: '升压DC-DC芯片',
    pins: [
      { number: '1', name: 'SW', type: 'output' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'FB', type: 'input' },
      { number: '4', name: 'EN', type: 'input' },
      { number: '5', name: 'VIN', type: 'power' },
      { number: '6', name: 'NC', type: 'bidirectional' },
      { number: '7', name: 'NC', type: 'bidirectional' },
      { number: '8', name: 'SW', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 更多运算放大器 */
  'LM741': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM741', footprint: 'Package_TO_SOT_THT:TO-99-8',
    library: 'Amplifier_Operational', description: '经典运算放大器',
    pins: [
      { number: '1', name: 'NULL', type: 'input' },
      { number: '2', name: '-IN', type: 'input' },
      { number: '3', name: '+IN', type: 'input' },
      { number: '4', name: 'V-', type: 'power' },
      { number: '5', name: 'NULL', type: 'input' },
      { number: '6', name: 'OUT', type: 'output' },
      { number: '7', name: 'V+', type: 'power' },
      { number: '8', name: 'NULL', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LM324': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM324', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Amplifier_Operational', description: '四运算放大器',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: 'VCC+', type: 'power' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: '-IN2', type: 'input' },
      { number: '7', name: 'OUT2', type: 'output' },
      { number: '8', name: 'OUT3', type: 'output' },
      { number: '9', name: '-IN3', type: 'input' },
      { number: '10', name: '+IN3', type: 'input' },
      { number: '11', name: 'VCC-', type: 'power' },
      { number: '12', name: '+IN4', type: 'input' },
      { number: '13', name: '-IN4', type: 'input' },
      { number: '14', name: 'OUT4', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LM339': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM339', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Comparator', description: '四电压比较器',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: '-IN2', type: 'input' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: 'OUT2', type: 'output' },
      { number: '7', name: 'OUT3', type: 'output' },
      { number: '8', name: '-IN3', type: 'input' },
      { number: '9', name: '+IN3', type: 'input' },
      { number: '10', name: '-IN4', type: 'input' },
      { number: '11', name: '+IN4', type: 'input' },
      { number: '12', name: 'OUT4', type: 'output' },
      { number: '13', name: 'GND', type: 'gnd' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LM386': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM386', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Amplifier_Audio', description: '音频功率放大器',
    pins: [
      { number: '1', name: 'GAIN', type: 'input' },
      { number: '2', name: '-IN', type: 'input' },
      { number: '3', name: '+IN', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'OUT', type: 'output' },
      { number: '6', name: 'VCC', type: 'power' },
      { number: '7', name: 'BYPASS', type: 'input' },
      { number: '8', name: 'GAIN', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'TL082': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TL082', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Amplifier_Operational', description: '双JFET运算放大器',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: 'V-', type: 'power' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: '-IN2', type: 'input' },
      { number: '7', name: 'OUT2', type: 'output' },
      { number: '8', name: 'V+', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 接口转换芯片 */
  'MAX3232': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MAX3232', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Interface_UART', description: 'RS232电平转换芯片',
    pins: [
      { number: '1', name: 'C1+', type: 'power' },
      { number: '2', name: 'V+', type: 'power' },
      { number: '3', name: 'C1-', type: 'power' },
      { number: '4', name: 'C2+', type: 'power' },
      { number: '5', name: 'C2-', type: 'power' },
      { number: '6', name: 'V-', type: 'power' },
      { number: '7', name: 'T1OUT', type: 'output' },
      { number: '8', name: 'R1IN', type: 'input' },
      { number: '9', name: 'R1OUT', type: 'output' },
      { number: '10', name: 'T1IN', type: 'input' },
      { number: '11', name: 'T2IN', type: 'input' },
      { number: '12', name: 'R2OUT', type: 'output' },
      { number: '13', name: 'R2IN', type: 'input' },
      { number: '14', name: 'T2OUT', type: 'output' },
      { number: '15', name: 'GND', type: 'gnd' },
      { number: '16', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SN74LVC245': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74LVC245', footprint: 'Package_SO:SOIC-20_3.9x12.5mm_P1.27mm',
    library: 'Logic_Buffer', description: '8路双向电平转换器',
    pins: [
      { number: '1', name: 'DIR', type: 'input' },
      { number: '2', name: 'A1', type: 'bidirectional' },
      { number: '3', name: 'B1', type: 'bidirectional' },
      { number: '4', name: 'A2', type: 'bidirectional' },
      { number: '5', name: 'B2', type: 'bidirectional' },
      { number: '6', name: 'A3', type: 'bidirectional' },
      { number: '7', name: 'B3', type: 'bidirectional' },
      { number: '8', name: 'A4', type: 'bidirectional' },
      { number: '9', name: 'B4', type: 'bidirectional' },
      { number: '10', name: 'GND', type: 'gnd' },
      { number: '11', name: 'B5', type: 'bidirectional' },
      { number: '12', name: 'A5', type: 'bidirectional' },
      { number: '13', name: 'B6', type: 'bidirectional' },
      { number: '14', name: 'A6', type: 'bidirectional' },
      { number: '15', name: 'B7', type: 'bidirectional' },
      { number: '16', name: 'A7', type: 'bidirectional' },
      { number: '17', name: 'B8', type: 'bidirectional' },
      { number: '18', name: 'A8', type: 'bidirectional' },
      { number: '19', name: 'OE', type: 'input' },
      { number: '20', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SN74HC14': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC14', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_Inverter', description: '六路施密特触发器',
    pins: [
      { number: '1', name: 'A1', type: 'input' },
      { number: '2', name: 'Y1', type: 'output' },
      { number: '3', name: 'A2', type: 'input' },
      { number: '4', name: 'Y2', type: 'output' },
      { number: '5', name: 'A3', type: 'input' },
      { number: '6', name: 'Y3', type: 'output' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: 'Y4', type: 'output' },
      { number: '9', name: 'A4', type: 'input' },
      { number: '10', name: 'Y5', type: 'output' },
      { number: '11', name: 'A5', type: 'input' },
      { number: '12', name: 'Y6', type: 'output' },
      { number: '13', name: 'A6', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  '74HC573': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC573', footprint: 'Package_SO:SOIC-20_3.9x12.5mm_P1.27mm',
    library: 'Logic_Latch', description: '八路D锁存器',
    pins: [
      { number: '1', name: 'LE', type: 'input' },
      { number: '2', name: 'D1', type: 'input' },
      { number: '3', name: 'Q1', type: 'bidirectional' },
      { number: '4', name: 'D2', type: 'input' },
      { number: '5', name: 'Q2', type: 'bidirectional' },
      { number: '6', name: 'D3', type: 'input' },
      { number: '7', name: 'Q3', type: 'bidirectional' },
      { number: '8', name: 'D4', type: 'input' },
      { number: '9', name: 'Q4', type: 'bidirectional' },
      { number: '10', name: 'GND', type: 'gnd' },
      { number: '11', name: 'Q5', type: 'bidirectional' },
      { number: '12', name: 'D5', type: 'input' },
      { number: '13', name: 'Q6', type: 'bidirectional' },
      { number: '14', name: 'D6', type: 'input' },
      { number: '15', name: 'Q7', type: 'bidirectional' },
      { number: '16', name: 'D7', type: 'input' },
      { number: '17', name: 'Q8', type: 'bidirectional' },
      { number: '18', name: 'OE', type: 'input' },
      { number: '19', name: 'D8', type: 'input' },
      { number: '20', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 存储器 */
  'W25Q64': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'W25Q64', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory', description: '64Mbit SPI Flash',
    pins: [
      { number: '1', name: '/CS', type: 'input' },
      { number: '2', name: 'SO', type: 'output' },
      { number: '3', name: '/WP', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SI', type: 'input' },
      { number: '6', name: 'CLK', type: 'input' },
      { number: '7', name: '/HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'W25Q256': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'W25Q256', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory', description: '256Mbit SPI Flash',
    pins: [
      { number: '1', name: '/CS', type: 'input' },
      { number: '2', name: 'SO', type: 'output' },
      { number: '3', name: '/WP', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SI', type: 'input' },
      { number: '6', name: 'CLK', type: 'input' },
      { number: '7', name: '/HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'AT25DF041A': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AT25DF041A', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory', description: '4Mbit SPI Flash',
    pins: [
      { number: '1', name: '/CS', type: 'input' },
      { number: '2', name: 'SO', type: 'output' },
      { number: '3', name: '/WP', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'SI', type: 'input' },
      { number: '6', name: 'SCK', type: 'input' },
      { number: '7', name: '/HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'AT93C46': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AT93C46', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Memory', description: '1Kbit EEPROM',
    pins: [
      { number: '1', name: 'CS', type: 'input' },
      { number: '2', name: 'CLK', type: 'input' },
      { number: '3', name: 'DI', type: 'input' },
      { number: '4', name: 'DO', type: 'output' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'ORG', type: 'input' },
      { number: '7', name: 'NC', type: 'bidirectional' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 电源监控 */
  'LM2596-ADJ': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM2596-ADJ', footprint: 'Package_TO_SOT_SMD:TO-263-5_Horizontal',
    library: 'Regulator_Switching', description: '可调降压模块',
    pins: [
      { number: '1', name: 'VIN', type: 'power' },
      { number: '2', name: 'VOUT', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'FB', type: 'input' },
      { number: '5', name: 'ON/OFF', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MP1584': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MP1584', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Regulator_Switching', description: '3A降压芯片',
    pins: [
      { number: '1', name: 'BS', type: 'input' },
      { number: '2', name: 'IN', type: 'power' },
      { number: '3', name: 'SW', type: 'output' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'FB', type: 'input' },
      { number: '6', name: 'EN', type: 'input' },
      { number: '7', name: 'COMP', type: 'input' },
      { number: '8', name: 'IN', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 电池管理 */
  'DW01': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DW01', footprint: 'Package_SO:SSOP-6',
    library: 'Battery_Management', description: '锂电池保护芯片',
    pins: [
      { number: '1', name: 'OD', type: 'output' },
      { number: '2', name: 'CS', type: 'input' },
      { number: '3', name: 'OC', type: 'output' },
      { number: '4', name: 'TD', type: 'input' },
      { number: '5', name: 'VCC', type: 'power' },
      { number: '6', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'DW06': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'DW06', footprint: 'Package_SO:TSSOP-8',
    library: 'Battery_Management', description: '锂电池保护芯片',
    pins: [
      { number: '1', name: 'ODM', type: 'output' },
      { number: '2', name: 'CS', type: 'input' },
      { number: '3', name: 'OD', type: 'output' },
      { number: '4', name: 'CS', type: 'input' },
      { number: '5', name: 'OC', type: 'output' },
      { number: '6', name: 'VCC', type: 'power' },
      { number: '7', name: 'VCC', type: 'power' },
      { number: '8', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SY6970': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SY6970', footprint: 'Package_SO:QFN-16_3x3mm_P0.5mm',
    library: 'Battery_Management', description: '锂电池充电管理',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'SW', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'FB', type: 'input' },
      { number: '5', name: 'ISET', type: 'input' },
      { number: '6', name: 'BAT', type: 'power' },
      { number: '7', name: 'TS', type: 'input' },
      { number: '8', name: 'GND', type: 'gnd' },
      { number: '9', name: 'LED', type: 'output' },
      { number: '10', name: 'STDBY', type: 'output' },
      { number: '11', name: 'CHRG', type: 'output' },
      { number: '12', name: 'CE', type: 'input' },
      { number: '13', name: 'TS', type: 'input' },
      { number: '14', name: 'BAT', type: 'power' },
      { number: '15', name: 'BAT', type: 'power' },
      { number: '16', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 湿度传感器 */
  'HM3301': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'HM3301', footprint: 'Module:HM3301',
    library: 'Sensor', description: 'PM2.5激光传感器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SET', type: 'input' },
      { number: '4', name: 'RX', type: 'input' },
      { number: '5', name: 'TX', type: 'output' },
      { number: '6', name: 'NC', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SGP30': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SGP30', footprint: 'Package_LGA:LGA-6_2.5x2.5mm_P0.8mm',
    library: 'Sensor', description: '空气质量传感器',
    pins: [
      { number: '1', name: 'VCC', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SDA', type: 'bidirectional' },
      { number: '4', name: 'SCL', type: 'input' },
      { number: '5', name: 'SEL', type: 'input' },
      { number: '6', name: 'NC', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'BME680': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'BME680', footprint: 'Package_LGA:LGA-8_3x3mm_P0.8mm',
    library: 'Sensor', description: '环境传感器(温湿度气压VOC)',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VCC', type: 'power' },
      { number: '3', name: 'SDO', type: 'output' },
      { number: '4', name: 'SDI', type: 'bidirectional' },
      { number: '5', name: 'SCK', type: 'input' },
      { number: '6', name: 'CSB', type: 'input' },
      { number: '7', name: 'I2S_AD', type: 'bidirectional' },
      { number: '8', name: 'I2S_WS', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'AS5600': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AS5600', footprint: 'Package_SO:SOC-12_4.9x5.9mm_P1.5mm',
    library: 'Sensor', description: '磁性旋转位置传感器',
    pins: [
      { number: '1', name: 'VDD', type: 'power' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'DIR', type: 'input' },
      { number: '4', name: 'Z', type: 'output' },
      { number: '5', name: 'PWM', type: 'output' },
      { number: '6', name: 'SDA', type: 'bidirectional' },
      { number: '7', name: 'SCL', type: 'input' },
      { number: '8', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MLX90614': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MLX90614', footprint: 'Package_TO_SOT_THT:TO-39-4_W4.0mm',
    library: 'Sensor', description: '红外温度传感器',
    pins: [
      { number: '1', name: 'SCL', type: 'input' },
      { number: '2', name: 'SDA', type: 'bidirectional' },
      { number: '3', name: 'VDD', type: 'power' },
      { number: '4', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MAX6675': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MAX6675', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Sensor', description: 'K型热电偶放大器',
    pins: [
      { number: '1', name: 'T-', type: 'input' },
      { number: '2', name: 'T+', type: 'input' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'VCC', type: 'power' },
      { number: '6', name: 'SO', type: 'output' },
      { number: '7', name: 'CS', type: 'input' },
      { number: '8', name: 'SCK', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 编码器 */
  'EC11': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'EC11', footprint: 'Rotary_Encoder:RotaryEncoder_Alps_EC11E',
    library: 'Switch', description: '旋转编码器',
    pins: [
      { number: '1', name: 'A', type: 'output' },
      { number: '2', name: 'C', type: 'output' },
      { number: '3', name: 'B', type: 'output' },
      { number: '4', name: 'SW', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 无线充电 */
  'BQ500110': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'BQ500110', footprint: 'Package_QFN:QFN-20_3x3mm_P0.5mm',
    library: 'Power_Management', description: '无线充电发送芯片',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VCC', type: 'power' },
      { number: '3', name: 'TX', type: 'output' },
      { number: '4', name: 'ISENSE', type: 'input' },
      { number: '5', name: 'LOOP', type: 'output' },
      { number: '6', name: 'GD', type: 'input' },
      { number: '7', name: 'LED', type: 'output' },
      { number: '8', name: 'FOD', type: 'input' },
      { number: '9', name: 'COMM', type: 'bidirectional' },
      { number: '10', name: 'EN', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 音频CODEC */
  'WM8978': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'WM8978', footprint: 'Package_QFN:QFN-48_7x7mm_P0.5mm',
    library: 'Audio', description: '音频CODEC芯片',
    pins: [
      { number: '1', name: 'VDD', type: 'power' },
      { number: '2', name: 'DCVDD', type: 'power' },
      { number: '3', name: 'AVDD', type: 'power' },
      { number: '4', name: 'AGND', type: 'gnd' },
      { number: '5', name: 'DGND', type: 'gnd' },
      { number: '6', name: 'BCLKDIV', type: 'input' },
      { number: '7', name: 'MCLK', type: 'input' },
      { number: '8', name: 'BCLK', type: 'bidirectional' },
      { number: '9', name: 'DACDAT', type: 'input' },
      { number: '10', name: 'DACLRC', type: 'bidirectional' },
      { number: '11', name: 'ADCDAT', type: 'output' },
      { number: '12', name: 'ADCLRC', type: 'bidirectional' },
      { number: '13', name: 'SCLK', type: 'bidirectional' },
      { number: '14', name: 'SDIN', type: 'bidirectional' },
      { number: '15', name: 'MODE', type: 'input' },
      { number: '16', name: 'CSB', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'ES8388': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'ES8388', footprint: 'Package_QFN:QFN-32_5x5mm_P0.5mm',
    library: 'Audio', description: '低功耗音频CODEC',
    pins: [
      { number: '1', name: 'VDD', type: 'power' },
      { number: '2', name: 'DGND', type: 'gnd' },
      { number: '3', name: 'AVDD', type: 'power' },
      { number: '4', name: 'AGND', type: 'gnd' },
      { number: '5', name: 'MCLK', type: 'input' },
      { number: '6', name: 'SCLK', type: 'bidirectional' },
      { number: '7', name: 'LRCK', type: 'bidirectional' },
      { number: '8', name: 'SDIN', type: 'input' },
      { number: '9', name: 'SDOUT', type: 'output' },
      { number: '10', name: 'I2C_SDA', type: 'bidirectional' },
      { number: '11', name: 'I2C_SCL', type: 'input' },
      { number: '12', name: 'HPOR', type: 'input' },
      { number: '13', name: 'DACS', type: 'input' },
      { number: '14', name: 'ADCS', type: 'input' },
      { number: '15', name: 'HPEN', type: 'input' },
      { number: '16', name: 'SDA', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 运算放大器 */
  'LM358': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM358', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Amplifier_Operational', description: '双运算放大器',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: '-IN2', type: 'input' },
      { number: '7', name: 'OUT2', type: 'output' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LM393': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM393', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Comparator', description: '双电压比较器',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: '-IN2', type: 'input' },
      { number: '7', name: 'OUT2', type: 'output' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'TL072': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TL072', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Amplifier_Operational', description: '低噪声JFET双运放',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: 'VCC-', type: 'power' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: '-IN2', type: 'input' },
      { number: '7', name: 'OUT2', type: 'output' },
      { number: '8', name: 'VCC+', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'TL074': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TL074', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Amplifier_Operational', description: '低噪声JFET四运放',
    pins: [
      { number: '1', name: 'OUT1', type: 'output' },
      { number: '2', name: '-IN1', type: 'input' },
      { number: '3', name: '+IN1', type: 'input' },
      { number: '4', name: 'VCC+', type: 'power' },
      { number: '5', name: '+IN2', type: 'input' },
      { number: '6', name: '-IN2', type: 'input' },
      { number: '7', name: 'OUT2', type: 'output' },
      { number: '8', name: 'OUT3', type: 'output' },
      { number: '9', name: '-IN3', type: 'input' },
      { number: '10', name: '+IN3', type: 'input' },
      { number: '11', name: 'VCC-', type: 'power' },
      { number: '12', name: '+IN4', type: 'input' },
      { number: '13', name: '-IN4', type: 'input' },
      { number: '14', name: 'OUT4', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'LM311': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM311', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Comparator', description: '电压比较器',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: '+IN', type: 'input' },
      { number: '3', name: '-IN', type: 'input' },
      { number: '4', name: 'VCC-', type: 'power' },
      { number: '5', name: 'BAL', type: 'input' },
      { number: '6', name: 'BAL/STR', type: 'input' },
      { number: '7', name: 'OUT', type: 'output' },
      { number: '8', name: 'VCC+', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 逻辑芯片 */
  'SN74HC08': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC08', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_74xx', description: '四2输入与门',
    pins: [
      { number: '1', name: '1A', type: 'input' },
      { number: '2', name: '1B', type: 'input' },
      { number: '3', name: '1Y', type: 'output' },
      { number: '4', name: '2A', type: 'input' },
      { number: '5', name: '2B', type: 'input' },
      { number: '6', name: '2Y', type: 'output' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: '3Y', type: 'output' },
      { number: '9', name: '3B', type: 'input' },
      { number: '10', name: '3A', type: 'input' },
      { number: '11', name: '4Y', type: 'output' },
      { number: '12', name: '4B', type: 'input' },
      { number: '13', name: '4A', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SN74HC32': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC32', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_74xx', description: '四2输入或门',
    pins: [
      { number: '1', name: '1A', type: 'input' },
      { number: '2', name: '1B', type: 'input' },
      { number: '3', name: '1Y', type: 'output' },
      { number: '4', name: '2A', type: 'input' },
      { number: '5', name: '2B', type: 'input' },
      { number: '6', name: '2Y', type: 'output' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: '3Y', type: 'output' },
      { number: '9', name: '3B', type: 'input' },
      { number: '10', name: '3A', type: 'input' },
      { number: '11', name: '4Y', type: 'output' },
      { number: '12', name: '4B', type: 'input' },
      { number: '13', name: '4A', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SN74HC86': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC86', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_74xx', description: '四2输入异或门',
    pins: [
      { number: '1', name: '1A', type: 'input' },
      { number: '2', name: '1B', type: 'input' },
      { number: '3', name: '1Y', type: 'output' },
      { number: '4', name: '2A', type: 'input' },
      { number: '5', name: '2B', type: 'input' },
      { number: '6', name: '2Y', type: 'output' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: '3Y', type: 'output' },
      { number: '9', name: '3B', type: 'input' },
      { number: '10', name: '3A', type: 'input' },
      { number: '11', name: '4Y', type: 'output' },
      { number: '12', name: '4B', type: 'input' },
      { number: '13', name: '4A', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SN74HC00': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC00', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_74xx', description: '四2输入与非门',
    pins: [
      { number: '1', name: '1A', type: 'input' },
      { number: '2', name: '1B', type: 'input' },
      { number: '3', name: '1Y', type: 'output' },
      { number: '4', name: '2A', type: 'input' },
      { number: '5', name: '2B', type: 'input' },
      { number: '6', name: '2Y', type: 'output' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: '3Y', type: 'output' },
      { number: '9', name: '3B', type: 'input' },
      { number: '10', name: '3A', type: 'input' },
      { number: '11', name: '4Y', type: 'output' },
      { number: '12', name: '4B', type: 'input' },
      { number: '13', name: '4A', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SN74HC04': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SN74HC04', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_74xx', description: '六反相器',
    pins: [
      { number: '1', name: '1A', type: 'input' },
      { number: '2', name: '1Y', type: 'output' },
      { number: '3', name: '2A', type: 'input' },
      { number: '4', name: '2Y', type: 'output' },
      { number: '5', name: '3A', type: 'input' },
      { number: '6', name: '3Y', type: 'output' },
      { number: '7', name: 'GND', type: 'gnd' },
      { number: '8', name: '4Y', type: 'output' },
      { number: '9', name: '4A', type: 'input' },
      { number: '10', name: '5Y', type: 'output' },
      { number: '11', name: '5A', type: 'input' },
      { number: '12', name: '6Y', type: 'output' },
      { number: '13', name: '6A', type: 'input' },
      { number: '14', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'CD4051': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'CD4051', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Logic_40xx', description: '8通道模拟多路复用器',
    pins: [
      { number: '1', name: 'Y0', type: 'bidirectional' },
      { number: '2', name: 'Y1', type: 'bidirectional' },
      { number: '3', name: 'Z', type: 'bidirectional' },
      { number: '4', name: 'Y2', type: 'bidirectional' },
      { number: '5', name: 'Y3', type: 'bidirectional' },
      { number: '6', name: 'Y4', type: 'bidirectional' },
      { number: '7', name: 'Y5', type: 'bidirectional' },
      { number: '8', name: 'VEE', type: 'power' },
      { number: '9', name: 'VSS', type: 'gnd' },
      { number: '10', name: 'Y6', type: 'bidirectional' },
      { number: '11', name: 'Y7', type: 'bidirectional' },
      { number: '12', name: 'A', type: 'input' },
      { number: '13', name: 'B', type: 'input' },
      { number: '14', name: 'C', type: 'input' },
      { number: '15', name: 'INH', type: 'input' },
      { number: '16', name: 'VDD', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'CD4011': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'CD4011', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Logic_40xx', description: '四2输入与非门',
    pins: [
      { number: '1', name: '1A', type: 'input' },
      { number: '2', name: '1B', type: 'input' },
      { number: '3', name: '1Y', type: 'output' },
      { number: '4', name: '2A', type: 'input' },
      { number: '5', name: '2B', type: 'input' },
      { number: '6', name: '2Y', type: 'output' },
      { number: '7', name: 'VSS', type: 'gnd' },
      { number: '8', name: '3Y', type: 'output' },
      { number: '9', name: '3B', type: 'input' },
      { number: '10', name: '3A', type: 'input' },
      { number: '11', name: '4Y', type: 'output' },
      { number: '12', name: '4B', type: 'input' },
      { number: '13', name: '4A', type: 'input' },
      { number: '14', name: 'VDD', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 更多电源芯片 */
  'LM2576': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'LM2576', footprint: 'Package_TO_SOT_THT:TO-263-5_Horizontal',
    library: 'Regulator_Switching', description: '3A降压稳压器',
    pins: [
      { number: '1', name: 'VIN', type: 'power' },
      { number: '2', name: 'OUTPUT', type: 'output' },
      { number: '3', name: 'GND', type: 'gnd' },
      { number: '4', name: 'FEEDBACK', type: 'input' },
      { number: '5', name: 'ON/OFF', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MC34063': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MC34063', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Regulator_Switching', description: 'DC-DC升压/降压芯片',
    pins: [
      { number: '1', name: 'SC', type: 'output' },
      { number: '2', name: 'SE', type: 'output' },
      { number: '3', name: 'CT', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'IN-', type: 'input' },
      { number: '6', name: 'VCC', type: 'power' },
      { number: '7', name: 'IS', type: 'input' },
      { number: '8', name: 'DRC', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 更多传感器 */
  'AHT10': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'AHT10', footprint: 'Package_QFN:QFN-4_1.5x1.5mm_P1.0mm',
    library: 'Sensor', description: '高精度温湿度传感器(I2C)',
    pins: [
      { number: '1', name: 'SDA', type: 'bidirectional' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'VCC', type: 'power' },
      { number: '4', name: 'SCL', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'SHT30': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'SHT30', footprint: 'Package_DFN_WSON:DFN-8_2.5x2.5mm_P1.25mm',
    library: 'Sensor', description: '高精度温湿度传感器(I2C)',
    pins: [
      { number: '1', name: 'SDA', type: 'bidirectional' },
      { number: '2', name: 'ADR', type: 'input' },
      { number: '3', name: 'SCL', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'VCC', type: 'power' },
      { number: '7', name: 'ALERT', type: 'output' },
      { number: '8', name: 'RST', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'INA219': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'INA219', footprint: 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    library: 'Sensor', description: '高精度电流/功率监测芯片(I2C)',
    pins: [
      { number: '1', name: 'A0', type: 'input' },
      { number: '2', name: 'A1', type: 'input' },
      { number: '3', name: 'SDA', type: 'bidirectional' },
      { number: '4', name: 'SCL', type: 'input' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'V-', type: 'power' },
      { number: '7', name: 'V+', type: 'power' },
      { number: '8', name: 'VS', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'INA226': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'INA226', footprint: 'Package_SO:MSOP-10_3x3mm_P0.5mm',
    library: 'Sensor', description: '高精度电流/功率监测芯片(I2C)',
    pins: [
      { number: '1', name: 'VBUS', type: 'input' },
      { number: '2', name: 'GND', type: 'gnd' },
      { number: '3', name: 'SDA', type: 'bidirectional' },
      { number: '4', name: 'SCL', type: 'input' },
      { number: '5', name: 'A0', type: 'input' },
      { number: '6', name: 'A1', type: 'input' },
      { number: '7', name: 'ALERT', type: 'output' },
      { number: '8', name: 'VS', type: 'power' },
      { number: '9', name: 'V-', type: 'power' },
      { number: '10', name: 'I-', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'MAX31865': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'MAX31865', footprint: 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    library: 'Sensor', description: 'PT100/PT1000铂电阻接口芯片',
    pins: [
      { number: '1', name: 'RD+', type: 'input' },
      { number: '2', name: 'RD-', type: 'input' },
      { number: '3', name: 'FORCE-', type: 'output' },
      { number: '4', name: 'FORCE+', type: 'power' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'VCC', type: 'power' },
      { number: '7', name: 'SCK', type: 'input' },
      { number: '8', name: 'SDO', type: 'output' },
      { number: '9', name: 'SDI', type: 'input' },
      { number: '10', name: 'CS', type: 'input' },
      { number: '11', name: 'CLK', type: 'input' },
      { number: '12', name: 'DATA', type: 'bidirectional' },
      { number: '13', name: 'DRDY', type: 'output' },
      { number: '14', name: 'GND', type: 'gnd' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 更多存储芯片 */
  'W25Q128': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'W25Q128', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory_Flash', description: '128Mbit串行闪存',
    pins: [
      { number: '1', name: '/CS', type: 'input' },
      { number: '2', name: 'DO', type: 'output' },
      { number: '3', name: '/WP', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'DI', type: 'input' },
      { number: '6', name: 'CLK', type: 'input' },
      { number: '7', name: '/HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'W25Q512': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'W25Q512', footprint: 'Package_SO:SOIC-16_5.23x10.3mm_P1.27mm',
    library: 'Memory_Flash', description: '512Mbit串行闪存',
    pins: [
      { number: '1', name: '/CS', type: 'input' },
      { number: '2', name: 'DO', type: 'output' },
      { number: '3', name: '/WP', type: 'input' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'DI', type: 'input' },
      { number: '6', name: 'CLK', type: 'input' },
      { number: '7', name: '/HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
      { number: '9', name: 'NC', type: 'bidirectional' },
      { number: '10', name: 'NC', type: 'bidirectional' },
      { number: '11', name: 'NC', type: 'bidirectional' },
      { number: '12', name: 'NC', type: 'bidirectional' },
      { number: '13', name: 'NC', type: 'bidirectional' },
      { number: '14', name: 'NC', type: 'bidirectional' },
      { number: '15', name: 'NC', type: 'bidirectional' },
      { number: '16', name: 'NC', type: 'bidirectional' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'M95M01': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'M95M01', footprint: 'Package_SO:SOIC-8_5.23x5.23mm_P1.27mm',
    library: 'Memory_EEPROM', description: '1Mbit串行EEPROM',
    pins: [
      { number: '1', name: 'C', type: 'input' },
      { number: '2', name: 'F', type: 'bidirectional' },
      { number: '3', name: 'W', type: 'input' },
      { number: '4', name: 'VSS', type: 'gnd' },
      { number: '5', name: 'S', type: 'bidirectional' },
      { number: '6', name: 'S', type: 'bidirectional' },
      { number: '7', name: 'HOLD', type: 'input' },
      { number: '8', name: 'VCC', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 步进电机驱动 */
  'TMC2208': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TMC2208', footprint: 'Package_SO:TQFP-32_5x5mm_P0.5mm',
    library: 'Driver_Motor', description: '静音步进电机驱动',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VCC_IO', type: 'power' },
      { number: '3', name: 'MS1', type: 'input' },
      { number: '4', name: 'MS2', type: 'input' },
      { number: '5', name: 'DIR', type: 'input' },
      { number: '6', name: 'STEP', type: 'input' },
      { number: '7', name: 'EN', type: 'input' },
      { number: '8', name: 'INDEX', type: 'output' },
      { number: '9', name: 'PWR_EN', type: 'input' },
      { number: '10', name: 'GND', type: 'gnd' },
      { number: '11', name: 'VVMOT', type: 'power' },
      { number: '12', name: 'VMOT', type: 'power' },
      { number: '13', name: 'A1', type: 'output' },
      { number: '14', name: 'A2', type: 'output' },
      { number: '15', name: 'B2', type: 'output' },
      { number: '16', name: 'B1', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'TMC2225': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'TMC2225', footprint: 'Package_QFN:QFN-32_5x5mm_P0.5mm',
    library: 'Driver_Motor', description: '静音步进电机驱动',
    pins: [
      { number: '1', name: 'GND', type: 'gnd' },
      { number: '2', name: 'VCC_IO', type: 'power' },
      { number: '3', name: 'MS1', type: 'input' },
      { number: '4', name: 'MS2', type: 'input' },
      { number: '5', name: 'DIR', type: 'input' },
      { number: '6', name: 'STEP', type: 'input' },
      { number: '7', name: 'EN', type: 'input' },
      { number: '8', name: 'INDEX', type: 'output' },
      { number: '9', name: 'PDN_UART', type: 'bidirectional' },
      { number: '10', name: 'GND', type: 'gnd' },
      { number: '11', name: 'VBB', type: 'power' },
      { number: '12', name: 'BR1', type: 'output' },
      { number: '13', name: 'OA1', type: 'output' },
      { number: '14', name: 'OA2', type: 'output' },
      { number: '15', name: 'OB2', type: 'output' },
      { number: '16', name: 'OB1', type: 'output' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  'L293D': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'L293D', footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    library: 'Driver_Motor', description: '双H桥电机驱动',
    pins: [
      { number: '1', name: 'ENABLE1', type: 'input' },
      { number: '2', name: 'OUTPUT1', type: 'output' },
      { number: '3', name: 'OUTPUT2', type: 'output' },
      { number: '4', name: 'GND', type: 'gnd' },
      { number: '5', name: 'GND', type: 'gnd' },
      { number: '6', name: 'OUTPUT3', type: 'output' },
      { number: '7', name: 'OUTPUT4', type: 'output' },
      { number: '8', name: 'VCC2', type: 'power' },
      { number: '9', name: 'ENABLE2', type: 'input' },
      { number: '10', name: 'INPUT3', type: 'input' },
      { number: '11', name: 'INPUT4', type: 'input' },
      { number: '12', name: 'GND', type: 'gnd' },
      { number: '13', name: 'GND', type: 'gnd' },
      { number: '14', name: 'INPUT1', type: 'input' },
      { number: '15', name: 'INPUT2', type: 'input' },
      { number: '16', name: 'VCC1', type: 'power' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
  /** 电池保护芯片 */
  'FS8205': [{
    id: 'u1', reference: 'U1', type: 'ic', name: 'FS8205', footprint: 'Package_TSSOP:TSSOP-8_3x4.4mm_P0.65mm',
    library: 'Battery_Management', description: '双N沟道MOSFET',
    pins: [
      { number: '1', name: 'S1', type: 'bidirectional' },
      { number: '2', name: 'S1', type: 'bidirectional' },
      { number: '3', name: 'S2', type: 'bidirectional' },
      { number: '4', name: 'S2', type: 'bidirectional' },
      { number: '5', name: 'D', type: 'bidirectional' },
      { number: '6', name: 'D', type: 'bidirectional' },
      { number: '7', name: 'G1', type: 'input' },
      { number: '8', name: 'G2', type: 'input' },
    ],
    position: { x: 50, y: 30 }, required: true,
  }],
};

/** 常用电源芯片模板 */
export const POWER_REGULATOR_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'lm7805',
    name: 'LM7805 线性稳压器',
    description: '5V 输出线性稳压器，输入 7-35V',
    category: 'power',
    keywords: ['7805', '5V', '线性稳压', '电源'],
    parameters: [
      { name: '输入电压', symbol: 'Vin', defaultValue: '12V', description: '输入电压范围 7-35V' },
      { name: '输出电压', symbol: 'Vout', defaultValue: '5V', description: '固定 5V 输出' },
      { name: '输出电流', symbol: 'Iout', defaultValue: '1A', description: '最大 1.5A' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'LM7805',
        footprint: 'TO-220-3_Horizontal',
        library: ' Regulator_Linear',
        description: '5V 线性稳压器',
        pins: [
          { number: '1', name: 'VIN', type: 'power' },
          { number: '2', name: 'GND', type: 'gnd' },
          { number: '3', name: 'VOUT', type: 'output' },
        ],
        position: { x: 50, y: 30 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '输入电容',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '输入滤波电容 100uF',
        position: { x: 30, y: 30 },
        required: true,
      },
      {
        id: 'c2',
        reference: 'C2',
        type: 'capacitor',
        name: '输出电容',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '输出滤波电容 100uF',
        position: { x: 70, y: 30 },
        required: true,
      },
    ],
    nets: [
      {
        name: 'VIN',
        connections: [
          { componentId: 'c1', pin: '1' },
          { componentId: 'u1', pin: '1' },
        ],
      },
      {
        name: 'GND',
        connections: [
          { componentId: 'c1', pin: '2' },
          { componentId: 'c2', pin: '2' },
          { componentId: 'u1', pin: '2' },
        ],
      },
      {
        name: 'VOUT',
        connections: [
          { componentId: 'c2', pin: '1' },
          { componentId: 'u1', pin: '3' },
        ],
      },
    ],
    layout: {
      boardSize: { width: 60, height: 40 },
      groups: [
        { name: '输入', componentIds: ['c1'], position: { x: 20, y: 30 } },
        { name: '稳压', componentIds: ['u1'], position: { x: 40, y: 30 } },
        { name: '输出', componentIds: ['c2'], position: { x: 60, y: 30 } },
      ],
    },
  },
  {
    id: 'ams1117-3.3',
    name: 'AMS1117-3.3 降压芯片',
    description: '3.3V 输出低压差稳压器，输入 4.7-12V',
    category: 'power',
    keywords: ['AMS1117', '3.3V', 'LDO', '降压'],
    parameters: [
      { name: '输入电压', symbol: 'Vin', defaultValue: '5V', description: '输入电压范围 4.7-12V' },
      { name: '输出电压', symbol: 'Vout', defaultValue: '3.3V', description: '固定 3.3V 输出' },
      { name: '输出电流', symbol: 'Iout', defaultValue: '1A', description: '最大 1A' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'AMS1117-3.3',
        footprint: 'Package_TO_SOT_SMD:SOT-223',
        library: 'Regulator_Linear',
        description: '3.3V LDO 稳压器',
        pins: [
          { number: '1', name: 'GND', type: 'gnd' },
          { number: '2', name: 'VOUT', type: 'output' },
          { number: '3', name: 'VIN', type: 'power' },
          { number: '4', name: 'GND', type: 'gnd' }, // SOT-223 thermal
        ],
        position: { x: 40, y: 30 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '输入电容',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '输入滤波电容 10uF',
        position: { x: 20, y: 30 },
        required: true,
      },
      {
        id: 'c2',
        reference: 'C2',
        type: 'capacitor',
        name: '输出电容',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '输出滤波电容 22uF',
        position: { x: 60, y: 30 },
        required: true,
      },
    ],
    nets: [
      {
        name: 'VIN',
        connections: [
          { componentId: 'c1', pin: '1' },
          { componentId: 'u1', pin: '3' },
        ],
      },
      {
        name: 'GND',
        connections: [
          { componentId: 'c1', pin: '2' },
          { componentId: 'c2', pin: '2' },
          { componentId: 'u1', pin: '1' },
          { componentId: 'u1', pin: '4' },
        ],
      },
      {
        name: 'VOUT',
        connections: [
          { componentId: 'c2', pin: '1' },
          { componentId: 'u1', pin: '2' },
        ],
      },
    ],
    layout: {
      boardSize: { width: 50, height: 30 },
    },
  },
];

/** 单片机最小系统模板 */
export const MCU_MINIMAL_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'stm32-minimal',
    name: 'STM32 最小系统',
    description: 'STM32F103C8T6 最小系统板，包含复位、晶振、调试接口',
    category: 'mcu',
    keywords: ['STM32', '最小系统', '单片机', 'ARM'],
    parameters: [
      { name: '晶振频率', symbol: 'HSE', defaultValue: '8MHz', description: '高速外部晶振' },
      { name: '晶振频率', symbol: 'LSE', defaultValue: '32768Hz', description: '低速外部晶振' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'STM32F103C8T6',
        footprint: 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
        library: 'MCU_ST_STM32F1',
        description: 'STM32F1 系列芯片',
        position: { x: 40, y: 35 },
        required: true,
      },
      {
        id: 'y1',
        reference: 'Y1',
        type: 'crystal',
        name: '8MHz 晶振',
        footprint: 'Crystal_SMD:Crystal_SMD_3225-4Pin',
        library: 'Crystal',
        description: '高速外部晶振',
        position: { x: 25, y: 45 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '晶振负载电容',
        footprint: 'Capacitor_SMD:C_0603',
        library: 'Capacitor_SMD',
        description: '20pF 负载电容',
        position: { x: 20, y: 45 },
        required: true,
      },
      {
        id: 'c2',
        reference: 'C2',
        type: 'capacitor',
        name: '晶振负载电容',
        footprint: 'Capacitor_SMD:C_0603',
        library: 'Capacitor_SMD',
        description: '20pF 负载电容',
        position: { x: 30, y: 45 },
        required: true,
      },
      {
        id: 'sw1',
        reference: 'SW1',
        type: 'ic',
        name: '复位按键',
        footprint: 'Button_Switch_SMD:SW_SPST_B3U-3000',
        library: 'Button_Switch_SMD',
        description: '复位按键',
        position: { x: 20, y: 25 },
        required: true,
      },
      {
        id: 'r1',
        reference: 'R1',
        type: 'resistor',
        name: '上拉电阻',
        footprint: 'Resistor_SMD:R_0603',
        library: 'Resistor_SMD',
        description: '10K 上拉电阻',
        position: { x: 25, y: 25 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: 'SWD 调试接口',
        footprint: 'Connector_PinHeader_2.54mm:PinHeader_2x5_P2.54mm_Horizontal',
        library: 'Connector_PinHeader_2.54mm',
        description: 'SWD 调试接口',
        position: { x: 60, y: 35 },
        required: true,
      },
    ],
    nets: [
      { name: 'VDD', connections: [{ componentId: 'u1', pin: '48' }, { componentId: 'r1', pin: '1' }, { componentId: 'j1', pin: '1' }] },
      { name: 'VSS', connections: [{ componentId: 'u1', pin: '24' }, { componentId: 'sw1', pin: '2' }, { componentId: 'j1', pin: '2' }] },
      { name: 'NRST', connections: [{ componentId: 'u1', pin: '7' }, { componentId: 'sw1', pin: '1' }, { componentId: 'r1', pin: '2' }] },
      { name: 'OSC_IN', connections: [{ componentId: 'u1', pin: '5' }, { componentId: 'y1', pin: '1' }] },
      { name: 'OSC_OUT', connections: [{ componentId: 'u1', pin: '6' }, { componentId: 'y1', pin: '2' }] },
    ],
    layout: {
      boardSize: { width: 80, height: 60 },
    },
  },
];

/** 通信接口模板 */
export const COMMUNICATION_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'ch340-usb-serial',
    name: 'CH340C USB转串口',
    description: 'CH340C USB转TTL串口模块，内置晶振，支持3.3V/5V',
    category: 'communication',
    keywords: ['USB', '串口', 'CH340', 'CH340C', 'TTL', 'UART', 'USB转串口'],
    parameters: [
      { name: '工作电压', symbol: 'VCC', defaultValue: '5V', description: 'USB供电5V' },
      { name: '波特率', symbol: 'Baud', defaultValue: '115200', description: '最大2Mbps' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'CH340C',
        footprint: 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
        library: 'Interface_USB',
        description: 'USB转串口芯片',
        position: { x: 40, y: 30 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: 'USB-C',
        footprint: 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
        library: 'Connector_USB',
        description: 'USB-C 接口',
        position: { x: 15, y: 30 },
        required: true,
      },
      {
        id: 'y1',
        reference: 'Y1',
        type: 'crystal',
        name: '12MHz晶振',
        footprint: 'Crystal_SMD:Crystal_SMD_3225-4Pin_3.2x2.5mm',
        library: 'Crystal',
        description: '外部晶振',
        position: { x: 60, y: 20 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '去耦电容',
        footprint: 'Capacitor_SMD:C_0603',
        library: 'Capacitor_SMD',
        description: '100nF去耦电容',
        position: { x: 55, y: 30 },
        required: true,
      },
      {
        id: 'c2',
        reference: 'C2',
        type: 'capacitor',
        name: '晶振电容',
        footprint: 'Capacitor_SMD:C_0603',
        library: 'Capacitor_SMD',
        description: '22pF负载电容',
        position: { x: 65, y: 20 },
        required: true,
      },
      {
        id: 'c3',
        reference: 'C3',
        type: 'capacitor',
        name: '晶振电容',
        footprint: 'Capacitor_SMD:C_0603',
        library: 'Capacitor_SMD',
        description: '22pF负载电容',
        position: { x: 55, y: 20 },
        required: true,
      },
    ],
    nets: [
      { name: 'VBUS', connections: [{ componentId: 'j1', pin: '1' }, { componentId: 'u1', pin: '16' }] },
      { name: 'GND', connections: [{ componentId: 'j1', pin: 'GND' }, { componentId: 'u1', pin: '8' }] },
      { name: 'D+', connections: [{ componentId: 'j1', pin: 'D+' }, { componentId: 'u1', pin: '5' }] },
      { name: 'D-', connections: [{ componentId: 'j1', pin: 'D-' }, { componentId: 'u1', pin: '6' }] },
    ],
    layout: {
      boardSize: { width: 70, height: 45 },
    },
  },
];

/** 电机驱动模板 */
export const MOTOR_DRIVER_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'l298n-dual-motor',
    name: 'L298N 双路电机驱动',
    description: '双H桥电机驱动模块，支持2路直流电机或1路步进电机',
    category: 'amplifier',
    keywords: ['电机', '驱动', 'L298N', 'H桥', 'PWM'],
    parameters: [
      { name: '驱动电压', symbol: 'VM', defaultValue: '12V', description: '电机驱动电压 5-46V' },
      { name: '单路电流', symbol: 'I', defaultValue: '2A', description: '每路最大2A' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'L298N',
        footprint: 'Package_TO_SOT_THT:TO-220-15',
        library: 'Driver_Motor',
        description: '双H桥电机驱动芯片',
        position: { x: 40, y: 35 },
        required: true,
      },
      {
        id: 'd1',
        reference: 'D1',
        type: 'diode',
        name: '续流二极管',
        footprint: 'Diode_SMD:D_SMA',
        library: 'Diode_SMD',
        description: '1N5822 肖特基二极管',
        position: { x: 25, y: 25 },
        required: true,
      },
      {
        id: 'd2',
        reference: 'D2',
        type: 'diode',
        name: '续流二极管',
        footprint: 'Diode_SMD:D_SMA',
        library: 'Diode_SMD',
        description: '1N5822 肖特基二极管',
        position: { x: 35, y: 25 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '电源滤波',
        footprint: 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
        library: 'Capacitor_THT',
        description: '100uF电解电容',
        position: { x: 55, y: 35 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: '电机接口',
        footprint: 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
        library: 'Connector_PinHeader_2.54mm',
        description: '电机和控制信号接口',
        position: { x: 70, y: 35 },
        required: true,
      },
    ],
    nets: [
      { name: 'VM', connections: [{ componentId: 'c1', pin: '1' }, { componentId: 'u1', pin: '4' }] },
      { name: 'GND', connections: [{ componentId: 'c1', pin: '2' }, { componentId: 'u1', pin: '8' }] },
    ],
    layout: {
      boardSize: { width: 80, height: 50 },
    },
  },
];

/** LED驱动模板 */
export const LED_DRIVER_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'ws2812b-strip',
    name: 'WS2812B LED灯带驱动',
    description: '可编程RGB LED灯带控制电路',
    category: 'amplifier',
    keywords: ['LED', 'RGB', 'WS2812B', '灯带', 'NeoPixel'],
    parameters: [
      { name: 'LED数量', symbol: 'N', defaultValue: '8', description: '级联LED数量' },
      { name: '工作电压', symbol: 'VCC', defaultValue: '5V', description: '5V供电' },
    ],
    components: [
      {
        id: 'led1',
        reference: 'LED1',
        type: 'ic',
        name: 'WS2812B',
        footprint: 'LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm',
        library: 'LED_SMD',
        description: '可编程RGB LED',
        position: { x: 20, y: 30 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '去耦电容',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '100nF去耦电容',
        position: { x: 30, y: 30 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: '数据接口',
        footprint: 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
        library: 'Connector_PinHeader_2.54mm',
        description: 'VCC/GND/DATA接口',
        position: { x: 10, y: 30 },
        required: true,
      },
    ],
    nets: [
      { name: 'VCC', connections: [{ componentId: 'j1', pin: '1' }, { componentId: 'led1', pin: '1' }, { componentId: 'c1', pin: '1' }] },
      { name: 'GND', connections: [{ componentId: 'j1', pin: '3' }, { componentId: 'led1', pin: '3' }, { componentId: 'c1', pin: '2' }] },
      { name: 'DATA', connections: [{ componentId: 'j1', pin: '2' }, { componentId: 'led1', pin: '4' }] },
    ],
    layout: {
      boardSize: { width: 40, height: 30 },
    },
  },
];

/** ESP32最小系统模板 */
export const ESP32_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'esp32-minimal',
    name: 'ESP32 WiFi模块最小系统',
    description: 'ESP32-WROOM WiFi+蓝牙模块最小系统',
    category: 'mcu',
    keywords: ['ESP32', 'WiFi', '蓝牙', 'IoT', '物联网'],
    parameters: [
      { name: '工作电压', symbol: 'VCC', defaultValue: '3.3V', description: '3.3V供电' },
      { name: 'Flash', symbol: 'Flash', defaultValue: '4MB', description: '内置4MB Flash' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'ESP32-WROOM-32',
        footprint: 'RF_Module:ESP32-WROOM-32',
        library: 'RF_Module',
        description: 'ESP32 WiFi+蓝牙模块',
        position: { x: 40, y: 35 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '电源滤波',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '10uF钽电容',
        position: { x: 25, y: 35 },
        required: true,
      },
      {
        id: 'c2',
        reference: 'C2',
        type: 'capacitor',
        name: '去耦电容',
        footprint: 'Capacitor_SMD:C_0603',
        library: 'Capacitor_SMD',
        description: '100nF陶瓷电容',
        position: { x: 55, y: 35 },
        required: true,
      },
      {
        id: 'r1',
        reference: 'R1',
        type: 'resistor',
        name: 'EN上拉',
        footprint: 'Resistor_SMD:R_0603',
        library: 'Resistor_SMD',
        description: '10K上拉电阻',
        position: { x: 25, y: 25 },
        required: true,
      },
      {
        id: 'sw1',
        reference: 'SW1',
        type: 'ic',
        name: '复位按键',
        footprint: 'Button_Switch_SMD:SW_SPST_B3U-3000',
        library: 'Button_Switch_SMD',
        description: '复位按键',
        position: { x: 35, y: 25 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: '编程接口',
        footprint: 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
        library: 'Connector_PinHeader_2.54mm',
        description: 'UART编程接口',
        position: { x: 70, y: 35 },
        required: true,
      },
    ],
    nets: [
      { name: '3V3', connections: [{ componentId: 'c1', pin: '1' }, { componentId: 'c2', pin: '1' }, { componentId: 'u1', pin: '2' }] },
      { name: 'GND', connections: [{ componentId: 'c1', pin: '2' }, { componentId: 'c2', pin: '2' }, { componentId: 'u1', pin: '1' }, { componentId: 'sw1', pin: '2' }] },
      { name: 'EN', connections: [{ componentId: 'r1', pin: '1' }, { componentId: 'u1', pin: '3' }, { componentId: 'sw1', pin: '1' }] },
    ],
    layout: {
      boardSize: { width: 80, height: 50 },
    },
  },
];

/** NE555 振荡器模板 */
export const NE555_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'ne555-oscillator',
    name: 'NE555 方波振荡器',
    description: '基于NE555定时器的方波振荡器电路，产生1kHz方波输出',
    category: 'amplifier',
    keywords: ['NE555', '555', '振荡器', '方波', '定时器', '震荡', 'oscillator'],
    parameters: [
      { name: '频率', symbol: 'f', defaultValue: '1kHz', description: '输出方波频率' },
      { name: '占空比', symbol: 'D', defaultValue: '50%', description: '方波占空比' },
      { name: '工作电压', symbol: 'VCC', defaultValue: '5V', description: '电源电压' },
    ],
    components: [
      {
        id: 'u1',
        reference: 'U1',
        type: 'ic',
        name: 'NE555',
        footprint: 'Package_DIP:DIP-8_W7.62mm',
        library: 'Timer',
        description: 'NE555定时器芯片',
        position: { x: 40, y: 30 },
        required: true,
      },
      {
        id: 'r1',
        reference: 'R1',
        type: 'resistor',
        name: '上拉电阻',
        footprint: 'Resistor_SMD:R_0603',
        library: 'Resistor_SMD',
        description: '10kΩ电阻',
        position: { x: 25, y: 20 },
        required: true,
      },
      {
        id: 'r2',
        reference: 'R2',
        type: 'resistor',
        name: '定时电阻',
        footprint: 'Resistor_SMD:R_0603',
        library: 'Resistor_SMD',
        description: '4.7kΩ电阻',
        position: { x: 40, y: 15 },
        required: true,
      },
      {
        id: 'c1',
        reference: 'C1',
        type: 'capacitor',
        name: '定时电容',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '100nF陶瓷电容',
        position: { x: 55, y: 15 },
        required: true,
      },
      {
        id: 'c2',
        reference: 'C2',
        type: 'capacitor',
        name: '电源滤波',
        footprint: 'Capacitor_SMD:C_0805',
        library: 'Capacitor_SMD',
        description: '100nF去耦电容',
        position: { x: 25, y: 40 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: '电源接口',
        footprint: 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
        library: 'Connector_PinHeader_2.54mm',
        description: 'VCC/GND/OUT接口',
        position: { x: 70, y: 30 },
        required: true,
      },
    ],
    nets: [
      { name: 'VCC', connections: [{ componentId: 'u1', pin: '8' }, { componentId: 'c2', pin: '1' }, { componentId: 'r1', pin: '1' }, { componentId: 'j1', pin: '1' }] },
      { name: 'GND', connections: [{ componentId: 'u1', pin: '1' }, { componentId: 'c2', pin: '2' }, { componentId: 'j1', pin: '2' }] },
      { name: 'OUT', connections: [{ componentId: 'u1', pin: '3' }, { componentId: 'j1', pin: '3' }] },
    ],
    layout: {
      boardSize: { width: 80, height: 50 },
    },
  },
];

/** NPN三极管LED驱动模板 */
export const NPN_LED_DRIVER_TEMPLATES: CircuitTemplate[] = [
  {
    id: 'npn-led-driver',
    name: 'NPN三极管LED驱动',
    description: '基于NPN三极管的LED驱动电路，用于大功率LED或多个LED串',
    category: 'amplifier',
    keywords: ['NPN', '三极管', 'LED', '驱动', '晶体管', 'transistor', 'LED driver'],
    parameters: [
      { name: 'LED数量', symbol: 'N', defaultValue: '3', description: 'LED串联数量' },
      { name: '工作电压', symbol: 'VCC', defaultValue: '12V', description: '电源电压' },
      { name: 'LED电流', symbol: 'I', defaultValue: '20mA', description: 'LED工作电流' },
    ],
    components: [
      {
        id: 'q1',
        reference: 'Q1',
        type: 'ic',
        name: 'S8050',
        footprint: 'Package_TO_SOT_SMD:SOT-23',
        library: 'Transistor_BJT',
        description: 'NPN三极管S8050',
        position: { x: 40, y: 30 },
        required: true,
      },
      {
        id: 'r1',
        reference: 'R1',
        type: 'resistor',
        name: '限流电阻',
        footprint: 'Resistor_SMD:R_0603',
        library: 'Resistor_SMD',
        description: '基极限流电阻330Ω',
        position: { x: 25, y: 20 },
        required: true,
      },
      {
        id: 'led1',
        reference: 'LED1',
        type: 'diode',
        name: 'LED',
        footprint: 'LED_SMD:LED_0805',
        library: 'LED_SMD',
        description: '红色LED 5mm',
        position: { x: 55, y: 30 },
        required: true,
      },
      {
        id: 'r2',
        reference: 'R2',
        type: 'resistor',
        name: 'LED限流电阻',
        footprint: 'Resistor_SMD:R_0603',
        library: 'Resistor_SMD',
        description: 'LED限流电阻470Ω',
        position: { x: 70, y: 30 },
        required: true,
      },
      {
        id: 'j1',
        reference: 'J1',
        type: 'connector',
        name: '控制接口',
        footprint: 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
        library: 'Connector_PinHeader_2.54mm',
        description: 'IN/GND接口',
        position: { x: 10, y: 30 },
        required: true,
      },
    ],
    nets: [
      { name: 'VCC', connections: [{ componentId: 'r2', pin: '1' }, { componentId: 'j1', pin: '1' }] },
      { name: 'GND', connections: [{ componentId: 'led1', pin: '2' }, { componentId: 'j1', pin: '2' }, { componentId: 'q1', pin: '1' }] },
      { name: 'IN', connections: [{ componentId: 'r1', pin: '1' }, { componentId: 'j1', pin: '3' }] },
      { name: 'OUT', connections: [{ componentId: 'r1', pin: '2' }, { componentId: 'q1', pin: '2' }, { componentId: 'led1', pin: '1' }, { componentId: 'r2', pin: '2' }] },
    ],
    layout: {
      boardSize: { width: 80, height: 40 },
    },
  },
];

/** 所有模板 */
export const ALL_TEMPLATES: CircuitTemplate[] = [
  ...POWER_REGULATOR_TEMPLATES,
  ...MCU_MINIMAL_TEMPLATES,
  ...COMMUNICATION_TEMPLATES,
  ...MOTOR_DRIVER_TEMPLATES,
  ...LED_DRIVER_TEMPLATES,
  ...ESP32_TEMPLATES,
  ...NE555_TEMPLATES,
  ...NPN_LED_DRIVER_TEMPLATES,
];

/**
 * 获取芯片引脚定义
 * @param chipName 芯片名称 (如 'STM32F103C8T6', 'CH340G', 'LM7805')
 * @returns 芯片引脚定义数组，如果没有找到则返回空数组
 */
export function getChipPins(chipName: string): TemplateComponent[] {
  // 精确匹配
  if (CHIP_PIN_DEFINITIONS[chipName]) {
    return CHIP_PIN_DEFINITIONS[chipName];
  }
  
  // 模糊匹配 (忽略大小写和空格)
  const searchName = chipName.toUpperCase().replace(/\s+/g, '');
  for (const [key, value] of Object.entries(CHIP_PIN_DEFINITIONS)) {
    if (key.toUpperCase().replace(/\s+/g, '').includes(searchName) || 
        searchName.includes(key.toUpperCase().replace(/\s+/g, ''))) {
      return value;
    }
  }
  
  return [];
}

/**
 * 检查芯片是否有引脚定义
 * @param chipName 芯片名称
 * @returns 是否有引脚定义
 */
export function hasChipPins(chipName: string): boolean {
  return getChipPins(chipName).length > 0;
}

/**
 * 获取所有支持的芯片列表
 * @returns 芯片名称数组
 */
export function getSupportedChips(): string[] {
  return Object.keys(CHIP_PIN_DEFINITIONS);
}

/**
 * 按类别获取芯片列表
 * @param category 芯片类别
 * @return 芯片名称数组
 */
export function getChipsByCategory(category: 'power' | 'mcu' | 'communication' | 'amplifier' | 'driver' | 'logic'): string[] {
  const categoryPatterns: Record<string, string[]> = {
    'power': ['LM', 'AMS', 'TP40', 'FS82', 'XL60', 'MT36'],
    'mcu': ['STM32', 'ATmega', 'ATtiny', 'ESP32', 'RP2040'],
    'communication': ['CH340', 'CP210', 'FT232', 'MAX232', 'MAX485'],
    'amplifier': ['LM358', 'LM393', 'TL072', 'TL074', 'LM311'],
    'driver': ['L298', 'A4988', 'DRV88', 'ULN20', 'IRF21', 'IR210'],
    'logic': ['SN74HC', 'CD4017', 'NE55'],
  };
  
  const patterns = categoryPatterns[category] || [];
  return Object.keys(CHIP_PIN_DEFINITIONS).filter(chip => 
    patterns.some(p => chip.toUpperCase().includes(p.toUpperCase()))
  );
}

/** 根据关键词搜索模板 */
export function searchTemplates(keywords: string[]): CircuitTemplate[] {
  const lowerKeywords = keywords.map(k => k.toLowerCase());
  return ALL_TEMPLATES.filter(template =>
    template.keywords.some(keyword =>
      lowerKeywords.some(k => keyword.toLowerCase().includes(k))
    )
  );
}

/** 根据ID获取模板 */
export function getTemplateById(id: string): CircuitTemplate | undefined {
  return ALL_TEMPLATES.find(t => t.id === id);
}

/** 根据类别获取模板 */
export function getTemplatesByCategory(category: CircuitTemplate['category']): CircuitTemplate[] {
  return ALL_TEMPLATES.filter(t => t.category === category);
}

/**
 * 从模板生成 PCB 数据
 */
export function generatePCBFromTemplate(template: CircuitTemplate): Partial<PCBData> {
  // 生成唯一ID前缀
  const idPrefix = `template-${Date.now()}`;

  // 1. 生成 footprints
  const footprints: Footprint[] = template.components.map((comp, index) => ({
    id: `${idPrefix}-fp-${index}`,
    type: 'footprint' as const,
    libraryName: comp.library,
    footprintName: comp.footprint,
    fullFootprintName: `${comp.library}:${comp.footprint}`,
    reference: comp.reference,
    value: comp.name,
    position: comp.position || { x: 40 + index * 10, y: 30 },
    rotation: 0,
    layer: 'F.Cu',
    pads: generatePadsFromPins(comp.pins || []),
    attributes: { description: comp.description },
  }));

  // 2. 生成网络
  const nets: Net[] = template.nets.map((net, index) => ({
    id: `${idPrefix}-net-${index}`,
    name: net.name,
    color: net.color,
  }));

  // 3. 根据网络生成走线
  const tracks: Track[] = generateTracksFromNets(template, footprints, idPrefix);

  // 4. 生成板框
  const boardWidth = template.layout?.boardSize?.width || 80;
  const boardHeight = template.layout?.boardSize?.height || 60;
  const boardOutline: Point2D[] = [
    { x: 5, y: 5 },
    { x: 5 + boardWidth, y: 5 },
    { x: 5 + boardWidth, y: 5 + boardHeight },
    { x: 5, y: 5 + boardHeight },
  ];

  return {
    id: `${idPrefix}-pcb`,
    boardOutline,
    boardWidth,
    boardHeight,
    boardThickness: 1.6,
    footprints,
    tracks,
    nets,
  };
}

/** 根据引脚生成焊盘 */
function generatePadsFromPins(pins: ComponentPin[]): Footprint['pads'] {
  return pins.map((pin, index) => ({
    id: `pad-${index}`,
    number: pin.number,
    type: 'smd' as const,
    shape: 'rect' as const,
    position: { x: index * 2, y: 0 },
    size: { x: 0.6, y: 0.3 },
    layers: ['F.Cu', 'F.Paste'],
    netId: '',
  }));
}

/** 根据网络生成走线 */
function generateTracksFromNets(template: CircuitTemplate, footprints: Footprint[], idPrefix: string): Track[] {
  const tracks: Track[] = [];

  template.nets.forEach((net, netIndex) => {
    const connections = net.connections;
    for (let i = 0; i < connections.length - 1; i++) {
      const from = connections[i];
      const to = connections[i + 1];

      const fromComp = footprints.find(f => f.reference === template.components.find(c => c.id === from.componentId)?.reference);
      const toComp = footprints.find(f => f.reference === template.components.find(c => c.id === to.componentId)?.reference);

      if (fromComp && toComp) {
        tracks.push({
          id: `${idPrefix}-track-${netIndex}-${i}`,
          type: 'track',
          layer: 'F.Cu',
          width: 0.254,
          points: [fromComp.position, toComp.position],
          netId: net.name,
        });
      }
    }
  });

  return tracks;
}
