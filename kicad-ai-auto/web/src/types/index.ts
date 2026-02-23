/**
 * KiCad Web Editor - 类型定义
 */

// ==================== 基础类型 ====================

export interface Point2D {
  x: number;
  y: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface Transform {
  x: number;
  y: number;
  rotation: number;
  scale: number;
}

// ==================== 项目类型 ====================

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived' | 'deleted';
  projectFile?: string;
  schematicFile?: string;
  pcbFile?: string;
  createdAt: string;
  updatedAt: string;
  ownerId: string;
}

// ==================== PCB 元素类型 ====================

export type PCBElementType = 'footprint' | 'track' | 'via' | 'zone' | 'text' | 'dimension';

export interface PCBElement {
  id: string;
  type: PCBElementType;
  selected?: boolean;
  locked?: boolean;
  visible?: boolean;
}

export interface Footprint extends PCBElement {
  type: 'footprint';
  libraryName: string;
  footprintName: string;
  fullFootprintName: string;
  reference: string;
  value: string;
  position: Point2D;
  rotation: number;
  layer: string;
  pads: Pad[];
  pad?: Pad[]; // 兼容后端返回的字段名（单数形式）
  attributes: Record<string, unknown>;
  model3d?: {
    path: string;
    position: Point3D;
    rotation: Point3D;
    scale: Point3D;
  };
}

export interface Pad {
  id: string;
  number: string;
  type: 'smd' | 'thru_hole' | 'np_thru_hole';
  shape: 'rect' | 'circle' | 'oval';
  position: Point2D;
  size: Point2D;
  layers: string[];
  netId?: string;
}

export interface Track extends PCBElement {
  type: 'track';
  layer: string;
  width: number;
  points: Point2D[];
  netId?: string;
}

export interface Via extends PCBElement {
  type: 'via';
  position: Point2D;
  size: number;
  drill: number;
  startLayer: string;
  endLayer: string;
  viaType: 'through' | 'blind' | 'buried' | 'micro';
  netId?: string;
}

export interface Zone extends PCBElement {
  type: 'zone';
  layer: string;
  netId?: string;
  priority: number;
  outline: Point2D[];
  islands?: Point2D[][];
  keepouts?: Keepout[];
  fillStyle: 'solid' | 'hatched';
  thermalRelief: boolean;
}

export interface Keepout {
  type: 'tracks' | 'vias' | 'copper';
  outline: Point2D[];
}

export interface BoardText extends PCBElement {
  type: 'text';
  text: string;
  layer: string;
  position: Point2D;
  rotation: number;
  fontSize: number;
  fontWidth: number;
}

// ==================== 层类型 ====================

export interface Layer {
  id: string;
  name: string;
  type: 'signal' | 'power' | 'dielectric';
  color: string;
  visible: boolean;
  active: boolean;
  layerNumber: number;
  thickness: number;
}

// ==================== 网络类型 ====================

export interface Net {
  id: string;
  name: string;
  netclassId?: string;
  defaultWidth?: number;
  defaultViaSize?: number;
}

export interface NetClass {
  id: string;
  name: string;
  description?: string;
  defaultWidth: number;
  defaultClearance: number;
  defaultViaSize: number;
  defaultViaDrill: number;
}

// ==================== 设计规则 ====================

export interface DesignRules {
  minTrackWidth: number;
  minViaSize: number;
  minViaDrill: number;
  minClearance: number;
  minHoleClearance: number;
  layerRules: Record<string, LayerRule>;
  netclassRules: NetClassRule[];
}

export interface LayerRule {
  minWidth: number;
  maxWidth: number;
  minClearance: number;
}

export interface NetClassRule {
  netclassId: string;
  minWidth: number;
  clearance: number;
}

// ==================== DRC 类型 ====================

export interface DRCItem {
  id: string;
  type: string;
  severity: 'error' | 'warning';
  message: string;
  description?: string; // 兼容性字段
  position?: Point2D;
  objectIds: string[];
}

export interface DRCReport {
  errorCount: number;
  warningCount: number;
  errors: DRCItem[];
  warnings: DRCItem[];
  timestamp: string;
  // 兼容性字段 (snake_case)
  error_count?: number;
  warning_count?: number;
}

// ==================== 工具类型 ====================

export type ToolType = 
  | 'select'
  | 'move'
  | 'route'
  | 'place_footprint'
  | 'place_via'
  | 'place_zone'
  | 'place_text'
  | 'draw_line'
  | 'measure'
  | 'zoom'
  | 'pan';

export interface Tool {
  type: ToolType;
  name: string;
  icon: string;
  shortcut?: string;
  cursor?: string;
}

// ==================== 编辑器状态 ====================

export interface EditorState {
  // 当前项目
  currentProject?: Project;
  
  // 当前工具
  currentTool: ToolType;
  
  // 画布状态
  zoom: number;
  pan: Point2D;
  
  // 层状态
  activeLayer: string;
  layers: Layer[];
  
  // 选择状态
  selectedIds: string[];
  hoveredId?: string;
  
  // 网格设置
  gridVisible: boolean;
  gridSize: number;
  gridSnap: boolean;
  
  // 视图设置
  showRatsnest: boolean;
  showDrcErrors: boolean;
  showPads: boolean;
  showTracks: boolean;
  showVias: boolean;
  showZones: boolean;
}

// ==================== PCB 数据 ====================

export interface PCBData {
  id: string;
  projectId: string;
  boardOutline: Point2D[];
  boardWidth: number;
  boardHeight: number;
  boardThickness: number;
  layerStack: Layer[];
  footprints: Footprint[];
  tracks: Track[];
  vias: Via[];
  zones: Zone[];
  texts: BoardText[];
  nets: Net[];
  netclasses: NetClass[];
  designRules: DesignRules;
}

// ==================== 库类型 ====================

export interface SymbolInfo {
  name: string;
  library: string;
  description?: string;
  keywords: string[];
  pinCount: number;
}

export interface FootprintInfo {
  name: string;
  library: string;
  description?: string;
  keywords: string[];
  padCount: number;
  has3dModel: boolean;
  preview?: string;
}

// ==================== API 响应 ====================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
  page: number;
  pageSize: number;
}

// ==================== WebSocket 消息 ====================

export interface WSMessage {
  type: string;
  timestamp: number;
}

export interface WSCursorMove extends WSMessage {
  type: 'cursor_move';
  userId: string;
  x: number;
  y: number;
  editor: 'schematic' | 'pcb';
}

export interface WSElementUpdate extends WSMessage {
  type: 'element_update';
  elementType: PCBElementType;
  elementId: string;
  changes: Partial<PCBElement>;
  userId: string;
}

export interface WSProjectState extends WSMessage {
  type: 'project_state';
  projectId: string;
  lastModified: string;
  activeUsers: string[];
}

export interface WSDRCResult extends WSMessage {
  type: 'drc_result';
  report: DRCReport;
}

// ==================== 原理图类型 ====================

export interface SchematicSheet {
  id: string;
  name: string;
  pageNumber: number;
  width: number;
  height: number;
}

export interface SchematicComponent {
  id: string;
  libraryName: string;
  symbolName: string;
  fullSymbolName: string;
  reference: string;
  value: string;
  position: Point2D;
  rotation: number;
  mirror: boolean;
  unit: number;
  fields: Record<string, string>;
  footprint?: string;
  pins: SchematicPin[];
}

export interface SchematicPin {
  id: string;
  number: string;
  name: string;
  position: Point2D;
  electricalType: 'input' | 'output' | 'bidirectional' | 'power' | 'passive';
}

export interface Wire {
  id: string;
  points: Point2D[];
  netId?: string;
  color?: string;
  strokeWidth?: number;
}

export interface Label {
  id: string;
  text: string;
  position: Point2D;
  rotation: number;
  labelType: 'local' | 'global' | 'hierarchy' | 'power';
}

export interface PowerSymbol {
  id: string;
  name: string;
  position: Point2D;
  rotation: number;
}

export interface SchematicData {
  id: string;
  projectId: string;
  sheets: SchematicSheet[];
  components: SchematicComponent[];
  wires: Wire[];
  labels: Label[];
  powerSymbols: PowerSymbol[];
  nets: Net[];
}
