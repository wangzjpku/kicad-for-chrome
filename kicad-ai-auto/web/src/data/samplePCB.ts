/**
 * 示例 PCB 数据
 * 用于 Phase 1 MVP 测试
 */

import { PCBData, Footprint, Track, Via, Layer, Net } from '../types';

// 毫米到像素的转换比例
export const MM_TO_PX = 10;

// 示例层定义
export const sampleLayers: Layer[] = [
  {
    id: 'F.Cu',
    name: 'F.Cu',
    type: 'signal',
    color: '#FF0000',
    visible: true,
    active: true,
    layerNumber: 0,
    thickness: 0.035,
  },
  {
    id: 'B.Cu',
    name: 'B.Cu',
    type: 'signal',
    color: '#00FF00',
    visible: true,
    active: false,
    layerNumber: 31,
    thickness: 0.035,
  },
];

// 示例网络定义
export const sampleNets: Net[] = [
  { id: 'net1', name: 'GND' },
  { id: 'net2', name: 'VCC' },
  { id: 'net3', name: 'SIGNAL1' },
];

// 示例封装 1: R1 (电阻)
export const sampleFootprint1: Footprint = {
  id: 'fp1',
  type: 'footprint',
  libraryName: 'Resistor_SMD',
  footprintName: 'R_0805',
  fullFootprintName: 'Resistor_SMD:R_0805',
  reference: 'R1',
  value: '10k',
  position: { x: 50, y: 40 }, // mm
  rotation: 0,
  layer: 'F.Cu',
  pads: [
    {
      id: 'fp1-pad1',
      number: '1',
      type: 'smd',
      shape: 'rect',
      position: { x: -1, y: 0 },
      size: { x: 1, y: 1.2 },
      layers: ['F.Cu', 'F.Mask', 'F.Paste'],
      netId: 'net3',
    },
    {
      id: 'fp1-pad2',
      number: '2',
      type: 'smd',
      shape: 'rect',
      position: { x: 1, y: 0 },
      size: { x: 1, y: 1.2 },
      layers: ['F.Cu', 'F.Mask', 'F.Paste'],
      netId: 'net1',
    },
  ],
  attributes: {},
};

// 示例封装 2: C1 (电容)
export const sampleFootprint2: Footprint = {
  id: 'fp2',
  type: 'footprint',
  libraryName: 'Capacitor_SMD',
  footprintName: 'C_0805',
  fullFootprintName: 'Capacitor_SMD:C_0805',
  reference: 'C1',
  value: '100nF',
  position: { x: 70, y: 40 }, // mm
  rotation: 90,
  layer: 'F.Cu',
  pads: [
    {
      id: 'fp2-pad1',
      number: '1',
      type: 'smd',
      shape: 'rect',
      position: { x: 0, y: -1 },
      size: { x: 1.2, y: 1 },
      layers: ['F.Cu', 'F.Mask', 'F.Paste'],
      netId: 'net2',
    },
    {
      id: 'fp2-pad2',
      number: '2',
      type: 'smd',
      shape: 'rect',
      position: { x: 0, y: 1 },
      size: { x: 1.2, y: 1 },
      layers: ['F.Cu', 'F.Mask', 'F.Paste'],
      netId: 'net1',
    },
  ],
  attributes: {},
};

// 示例走线 1: 从 R1 到 C1
export const sampleTrack1: Track = {
  id: 'track1',
  type: 'track',
  layer: 'F.Cu',
  width: 0.2, // mm
  points: [
    { x: 51, y: 40 }, // R1 pad2
    { x: 60, y: 40 },
    { x: 60, y: 42 },
    { x: 70, y: 42 }, // C1 pad2
  ],
  netId: 'net1',
};

// 示例走线 2: 从 R1 到左侧
export const sampleTrack2: Track = {
  id: 'track2',
  type: 'track',
  layer: 'F.Cu',
  width: 0.2,
  points: [
    { x: 49, y: 40 }, // R1 pad1
    { x: 45, y: 40 },
    { x: 45, y: 35 },
  ],
  netId: 'net3',
};

// 示例走线 3: B.Cu 层走线
export const sampleTrack3: Track = {
  id: 'track3',
  type: 'track',
  layer: 'B.Cu',
  width: 0.25,
  points: [
    { x: 20, y: 20 },
    { x: 80, y: 20 },
    { x: 80, y: 60 },
  ],
  netId: 'net2',
};

// 示例过孔
export const sampleVia1: Via = {
  id: 'via1',
  type: 'via',
  position: { x: 60, y: 42 },
  size: 0.8, // mm (外径)
  drill: 0.4, // mm (内径)
  startLayer: 'F.Cu',
  endLayer: 'B.Cu',
  viaType: 'through',
  netId: 'net1',
};

// 完整的示例 PCB 数据
export const samplePCB: PCBData = {
  id: 'pcb-001',
  projectId: 'project-001',
  boardOutline: [
    { x: 10, y: 10 },
    { x: 90, y: 10 },
    { x: 90, y: 70 },
    { x: 10, y: 70 },
  ],
  boardWidth: 80, // mm
  boardHeight: 60, // mm
  boardThickness: 1.6, // mm
  layerStack: sampleLayers,
  footprints: [sampleFootprint1, sampleFootprint2],
  tracks: [sampleTrack1, sampleTrack2, sampleTrack3],
  vias: [sampleVia1],
  zones: [],
  texts: [],
  nets: sampleNets,
  netclasses: [],
  designRules: {
    minTrackWidth: 0.1,
    minViaSize: 0.4,
    minViaDrill: 0.2,
    minClearance: 0.1,
    minHoleClearance: 0.2,
    layerRules: {},
    netclassRules: [],
  },
};

export default samplePCB;
