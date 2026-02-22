/**
 * 电路模板系统
 * 提供常见电路的完整定义，包括元件、网络连接和封装信息
 */

import { PCBData, Footprint, Track, Via, Net, Point2D } from '../types';

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

/** 所有模板 */
export const ALL_TEMPLATES: CircuitTemplate[] = [
  ...POWER_REGULATOR_TEMPLATES,
  ...MCU_MINIMAL_TEMPLATES,
];

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
