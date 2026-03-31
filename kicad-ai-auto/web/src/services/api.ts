/**
 * API 服务 (Task 4.1-4.2)
 * 封装后端 API 调用
 */

import axios, { AxiosInstance, AxiosResponse, AxiosRequestConfig } from 'axios';
import { PCBData, Project, ApiResponse, DRCReport, DRCItem, Footprint, Track, Via, SchematicData } from '../types';

// 为了兼容性导出类型
export type { DRCReport, DRCItem, ApiResponse };

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求去重映射
const pendingRequests = new Map<string, AbortController>();

/**
 * 生成请求唯一键
 * 使用简化版：只对数据和URL进行hash，避免大请求体影响性能
 */
function getRequestKey(config: AxiosRequestConfig): string {
  const method = config.method || 'GET';
  const url = config.url || '';
  // 对大数据进行截断处理，避免性能问题
  let dataStr = '';
  if (config.data) {
    const dataJson = JSON.stringify(config.data);
    // 限制长度，避免大请求体影响性能
    dataStr = dataJson.length > 200 ? dataJson.substring(0, 200) + '...' : dataJson;
  }
  return `${method}:${url}:${dataStr}`;
}

/**
 * 清除指定请求
 * 注意：不再自动取消 GET 请求，因为 GET 是幂等的，取消会导致数据加载失败
 */
function clearRequest(config: AxiosRequestConfig): void {
  const key = getRequestKey(config);
  const controller = pendingRequests.get(key);
  // 只取消非 GET 请求（POST, PUT, DELETE 等）
  // GET 请求是幂等的，不应该被取消
  if (controller && config.method && config.method.toUpperCase() !== 'GET') {
    controller.abort();
    pendingRequests.delete(key);
  }
}

// 请求去重拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 清除之前的相同请求
    clearRequest(config);
    
    // 创建新的 AbortController
    const key = getRequestKey(config);
    const controller = new AbortController();
    config.signal = controller.signal;
    pendingRequests.set(key, controller);
    
    return config;
  },
  (error) => {
    // 请求错误时清除
    if (error.config) {
      clearRequest(error.config);
    }
    return Promise.reject(error);
  }
);

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 仅在开发/测试模式下记录请求日志，生产环境禁用以防止敏感信息泄露
    if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    }
    // 添加认证token
    const stored = localStorage.getItem('deepeda-auth');
    if (stored) {
      try {
        const auth = JSON.parse(stored);
        if (auth.state?.token) {
          config.headers.Authorization = `Bearer ${auth.state.token}`;
        }
      } catch (e) {
        // ignore parse errors
      }
    }
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 清除已完成请求的去重记录
    clearRequest(response.config);
    return response;
  },
  (error) => {
    // 响应错误时清除
    if (error.config) {
      clearRequest(error.config);
    }
    return Promise.reject(error);
  }
);

// ==================== 项目管理 API ====================

export const projectApi = {
  listProjects: async (): Promise<ApiResponse<Project[]>> => {
    const response = await apiClient.get('/projects');
    return response.data;
  },

  getProject: async (id: string): Promise<ApiResponse<Project>> => {
    const response = await apiClient.get(`/projects/${id}`);
    return response.data;
  },

  createProject: async (data: Partial<Project>): Promise<ApiResponse<Project>> => {
    const response = await apiClient.post('/projects', data);
    return response.data;
  },

  updateProject: async (id: string, data: Partial<Project>): Promise<ApiResponse<Project>> => {
    const response = await apiClient.put(`/projects/${id}`, data);
    return response.data;
  },

  deleteProject: async (id: string): Promise<ApiResponse<void>> => {
    const response = await apiClient.delete(`/projects/${id}`);
    return response.data;
  },
};

// ==================== 项目快照 API ====================

export interface Snapshot {
  id: string;
  project_id: string;
  version: number;
  title: string;
  description: string;
  created_at: string;
  has_schematic: boolean;
  has_pcb: boolean;
}

export interface SnapshotDetail extends Snapshot {
  schematic?: any;
  pcb?: any;
}

export const snapshotApi = {
  // 创建快照
  create: async (
    projectId: string,
    data: { title: string; description?: string; include_schematic?: boolean; include_pcb?: boolean }
  ): Promise<ApiResponse<Snapshot>> => {
    const response = await apiClient.post(`/projects/${projectId}/snapshots`, data);
    return response.data;
  },

  // 列出项目的所有快照
  list: async (
    projectId: string,
    limit: number = 20,
    offset: number = 0
  ): Promise<ApiResponse<{ snapshots: Snapshot[]; total: number }>> => {
    const response = await apiClient.get(`/projects/${projectId}/snapshots`, {
      params: { limit, offset },
    });
    return response.data;
  },

  // 获取快照详情
  get: async (projectId: string, snapshotId: string): Promise<ApiResponse<{ snapshot: SnapshotDetail }>> => {
    const response = await apiClient.get(`/projects/${projectId}/snapshots/${snapshotId}`);
    return response.data;
  },

  // 恢复到指定快照
  restore: async (projectId: string, snapshotId: string): Promise<ApiResponse<{ version: number }>> => {
    const response = await apiClient.post(`/projects/${projectId}/snapshots/${snapshotId}/restore`);
    return response.data;
  },

  // 删除快照
  delete: async (projectId: string, snapshotId: string): Promise<ApiResponse<void>> => {
    const response = await apiClient.delete(`/projects/${projectId}/snapshots/${snapshotId}`);
    return response.data;
  },

  // 获取快照数量
  count: async (projectId: string): Promise<ApiResponse<{ count: number }>> => {
    const response = await apiClient.get(`/projects/${projectId}/snapshots/count`);
    return response.data;
  },
};

// ==================== PCB API ====================

export const pcbApi = {
  // 生成 PCB 布局和布线
  generate: async (request: {
    requirements?: string;
    board: {
      width: number;
      height: number;
      layers: string[];
    };
    components: Array<{
      ref: string;
      symbol: string;
      footprint: string;
      width: number;
      height: number;
    }>;
    nets: Array<{
      name: string;
      source_ref: string;
      source_pin: number;
      target_ref: string;
      target_pin: number;
    }>;
    placement_strategy?: string;
    routing_strategy?: string;
  }): Promise<PCBGenerationResult> => {
    const response = await apiClient.post('/pcb/generate', request);
    return response.data;
  },

  getPCB: async (projectId: string): Promise<ApiResponse<PCBData>> => {
    const response = await apiClient.get(`/projects/${projectId}/pcb/design`);
    return response.data;
  },

  savePCB: async (projectId: string, data: PCBData): Promise<ApiResponse<PCBData>> => {
    const response = await apiClient.post(`/projects/${projectId}/pcb/design`, data);
    return response.data;
  },

  getPCBItems: async (projectId: string): Promise<ApiResponse<PCBData>> => {
    // 使用 /pcb/design 端点获取所有 PCB 数据（包含 items）
    const response = await apiClient.get(`/projects/${projectId}/pcb/design`);
    return response.data;
  },

  createFootprint: async (projectId: string, data: Partial<Footprint>): Promise<ApiResponse<Footprint>> => {
    const response = await apiClient.post(`/projects/${projectId}/pcb/items/footprint`, data);
    return response.data;
  },

  createTrack: async (projectId: string, data: Partial<Track>): Promise<ApiResponse<Track>> => {
    const response = await apiClient.post(`/projects/${projectId}/pcb/items/track`, data);
    return response.data;
  },

  createVia: async (projectId: string, data: Partial<Via>): Promise<ApiResponse<Via>> => {
    const response = await apiClient.post(`/projects/${projectId}/pcb/items/via`, data);
    return response.data;
  },
};

// ==================== Schematic API ====================

export interface SchematicApiResponse {
  success: boolean;
  project_id?: string;
  components?: any[];
  wires?: any[];
  nets?: any[];
  labels?: any[];
  netLabels?: any[];
  powerSymbols?: any[];
}

export const schematicApi = {
  // 获取原理图数据
  getSchematic: async (projectId: string): Promise<SchematicApiResponse> => {
    const response = await apiClient.get(`/projects/${projectId}/schematic`);
    return response.data;
  },

  // 保存原理图数据
  saveSchematic: async (projectId: string, data: SchematicData): Promise<ApiResponse<void>> => {
    const response = await apiClient.post(`/projects/${projectId}/schematic`, data);
    return response.data;
  },
};

// ==================== DRC API ====================

export const drcApi = {
  runDRC: async (projectId: string, pcbData?: PCBData): Promise<ApiResponse<DRCReport>> => {
    // Phase 7A: Call /drc/run with real engine
    const response = await apiClient.post('/drc/run', {
      project_id: projectId,
      board_width: pcbData?.board?.width ?? 100,
      board_height: pcbData?.board?.height ?? 80,
      layer_count: pcbData?.layerCount ?? 2,
    });
    return response.data;
  },

  getDRCReport: async (projectId: string): Promise<ApiResponse<DRCReport>> => {
    const response = await apiClient.get(`/drc/report`, { params: { project_id: projectId } });
    return response.data;
  },

  runAdvancedDRC: async (projectId: string, pcbData?: PCBData, manufacturer: string = 'jlcpcb', level: string = 'standard'): Promise<any> => {
    const response = await apiClient.post('/drc/advanced-check', {
      project_id: projectId,
      pcb_data: pcbData,
      manufacturer,
      level,
    });
    return response.data;
  },

  runSIAnalysis: async (pcbData: PCBData): Promise<any> => {
    const response = await apiClient.post('/drc/si/analyze', {
      pcb_data: pcbData,
    });
    return response.data;
  },

  runEMIAnalysis: async (pcbData: PCBData, sensitivity: string = 'medium'): Promise<any> => {
    const response = await apiClient.post('/drc/emi/analyze', {
      pcb_data: pcbData,
      sensitivity,
    });
    return response.data;
  },

  getManufacturerCapabilities: async (manufacturer: string = 'jlcpcb', level: string = 'standard'): Promise<any> => {
    const response = await apiClient.get(`/drc/capabilities/${manufacturer}`, { params: { level } });
    return response.data;
  },
};

// ==================== 导出 API ====================

// 导出结果类型
export interface ExportResultData {
  success: boolean;
  files?: string[];
  outputDir?: string;
  message?: string;
}

export const exportApi = {
  exportGerber: async (projectId: string): Promise<ApiResponse<ExportResultData>> => {
    const response = await apiClient.post(`/projects/${projectId}/export/gerber`);
    return response.data;
  },

  exportDrill: async (projectId: string): Promise<ApiResponse<ExportResultData>> => {
    const response = await apiClient.post(`/projects/${projectId}/export/drill`);
    return response.data;
  },

  exportBOM: async (projectId: string): Promise<ApiResponse<ExportResultData>> => {
    const response = await apiClient.post(`/projects/${projectId}/export/bom`);
    return response.data;
  },

  exportSTEP: async (projectId: string): Promise<ApiResponse<ExportResultData>> => {
    const response = await apiClient.post(`/projects/${projectId}/export/step`);
    return response.data;
  },
};

// ==================== AI 和封装库 API ====================

// 封装推荐请求类型
export interface FootprintRecommendRequest {
  component_name: string;
  component_value?: string;
  package?: string;
}

// 封装推荐响应类型
export interface FootprintRecommendResponse {
  component_name: string;
  component_value?: string;
  package?: string;
  recommendation: string;
  source: 'library' | 'default_mapping' | 'fallback';
  alternatives: string[];
  message: string;
}

// AI 分析结果类型
export interface AIAnalyzeResult {
  analysis: string;
  components?: unknown[];
  suggestions?: string[];
}

// 封装库类型
export interface FootprintLibrary {
  name: string;
  path: string;
  count: number;
}

// 搜索结果类型
export interface FootprintSearchResult {
  name: string;
  library: string;
  description?: string;
  pads: number;
}

// AI 设计响应类型
export interface AIDesignResult {
  success: boolean;
  message: string;
  output_path?: string;
  iterations: number;
  erc_result?: Record<string, unknown>;
  errors: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
  circuit_data?: CircuitData;  // 电路JSON数据
}

// 电路数据格式（与后端 LoopResult.final_json 对应）
export interface CircuitData {
  components?: CircuitComponent[];
  nets?: CircuitNet[];
  parameters?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface CircuitComponent {
  id?: string;
  name: string;
  model?: string;
  value?: string;
  footprint?: string;
  x?: number;
  y?: number;
  position?: { x: number; y: number };
  rotation?: number;
  pins?: CircuitPin[];
  [key: string]: unknown;
}

export interface CircuitNet {
  name: string;
  connections?: Array<{ component: string; pin: string }>;
  [key: string]: unknown;
}

export interface CircuitPin {
  id?: string;
  number: string;
  name: string;
  [key: string]: unknown;
}

// PCB 相关类型
export interface PCBPlacement {
  ref: string;
  x: number;
  y: number;
  rotation?: number;
}

export interface PCBRoute {
  net: string;
  segments: Array<{
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    layer?: string;
  }>;
}

export interface PCBGenerationResult {
  success: boolean;
  message: string;
  placements: PCBPlacement[];
  routes: PCBRoute[];
  vias: Array<{ x: number; y: number; net: string }>;
  board_outline: { width: number; height: number };
  metrics: Record<string, unknown>;
}

export const aiApi = {
  // AI 分析电路需求
  analyzeRequirements: async (requirements: string): Promise<ApiResponse<AIAnalyzeResult>> => {
    const response = await apiClient.post('/ai/analyze', { requirements });
    return response.data;
  },

  // AI 完整设计流程：需求 → 原理图生成
  designCircuit: async (request: {
    requirements: string;
    project_name?: string;
    generator_version?: string;
    max_iterations?: number;
    auto_fix?: boolean;
    validate?: boolean;
  }): Promise<AIDesignResult> => {
    const response = await apiClient.post('/ai/design/', {
      requirements: request.requirements,
      project_name: request.project_name || 'ai_circuit',
      generator_version: request.generator_version || 'v2',
      max_iterations: request.max_iterations || 3,
      auto_fix: request.auto_fix ?? true,
      validate: request.validate ?? true,
    });
    return response.data;
  },

  // 获取封装推荐
  recommendFootprint: async (request: FootprintRecommendRequest): Promise<FootprintRecommendResponse> => {
    const response = await apiClient.post('/ai/footprint/recommend', request);
    return response.data;
  },

  // 获取所有封装库
  getFootprintLibraries: async (): Promise<ApiResponse<FootprintLibrary[]>> => {
    const response = await apiClient.get('/ai/footprint/libraries');
    return response.data;
  },

  // 搜索封装
  searchFootprints: async (keyword: string, limit: number = 20): Promise<ApiResponse<FootprintSearchResult[]>> => {
    const response = await apiClient.get('/ai/footprint/search', { params: { keyword, limit } });
    return response.data;
  },
};

// ==================== AI 对话 API ====================

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface Conversation {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  model: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface ChatRequest {
  message: string;
  context?: Record<string, unknown>;
  history?: ChatMessage[];
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  actions?: Array<{ type: string; target: string; description: string }>;
  modifications?: unknown[];
  conversation_id?: string;
}

export const conversationApi = {
  // 发送消息并获取AI回复
  chat: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post('/ai/chat', request);
    return response.data;
  },

  // Phase 10C: SSE streaming chat — returns tokens incrementally
  chatStream: async function* (
    request: ChatRequest,
  ): AsyncGenerator<{ type: string; content?: string; conversation_id?: string }> {
    const baseURL = apiClient.defaults.baseURL || '';
    const response = await fetch(`${baseURL}/ai/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok || !response.body) {
      yield { type: 'error', content: `HTTP ${response.status}` };
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
          if (data.type === 'done') return;
        } catch {
          // skip malformed SSE lines
        }
      }
    }
  },

  // 列出用户的所有对话
  list: async (
    userId: number = 1,
    limit: number = 20,
    offset: number = 0
  ): Promise<ApiResponse<{ conversations: Conversation[]; total: number }>> => {
    const response = await apiClient.get('/ai/conversations', {
      params: { user_id: userId, limit, offset },
    });
    return response.data;
  },

  // 获取对话详情
  get: async (conversationId: string): Promise<ApiResponse<ConversationDetail>> => {
    const response = await apiClient.get(`/ai/conversations/${conversationId}`);
    return response.data;
  },

  // 删除对话
  delete: async (conversationId: string): Promise<ApiResponse<void>> => {
    const response = await apiClient.delete(`/ai/conversations/${conversationId}`);
    return response.data;
  },

  // 搜索对话
  search: async (
    keyword: string,
    userId: number = 1,
    limit: number = 20
  ): Promise<ApiResponse<{ conversations: Conversation[]; count: number }>> => {
    const response = await apiClient.get('/ai/conversations/search', {
      params: { keyword, user_id: userId, limit },
    });
    return response.data;
  },
};

// ==================== 符号库 API ====================

export interface SymbolGraphic {
  type: 'rectangle' | 'polyline' | 'circle' | 'arc' | 'line';
  strokeWidth?: number;
  fill?: string;
  // rectangle
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  // polyline
  points?: { x: number; y: number }[];
  // circle
  cx?: number;
  cy?: number;
  radius?: number;
  // arc
  start?: { x: number; y: number };
  end?: { x: number; y: number };
  center?: { x: number; y: number };
  // line
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
}

export interface SymbolPin {
  number: string;
  name: string;
  x: number;
  y: number;
  length: number;
  rotation: number;
  type: string;
}

export interface SymbolGraphicsData {
  success: boolean;
  library: string;
  name: string;
  reference: string;
  graphics: SymbolGraphic[];
  pins: SymbolPin[];
}

// 符号缓存
const symbolCache: Map<string, SymbolGraphicsData> = new Map();

export const symbolApi = {
  // 获取符号图形数据（带缓存）
  getSymbolGraphics: async (libName: string, symbolName: string): Promise<SymbolGraphicsData> => {
    const cacheKey = `${libName}:${symbolName}`;
    if (symbolCache.has(cacheKey)) {
      return symbolCache.get(cacheKey)!;
    }

    const response = await apiClient.get(`/symbols/${libName}/${symbolName}/graphics`);
    if (response.data.success) {
      symbolCache.set(cacheKey, response.data);
    }
    return response.data;
  },

  // 根据元件名称查找符号
  findSymbol: async (name: string, model?: string): Promise<SymbolGraphicsData | null> => {
    const cacheKey = `find:${name}:${model || ''}`;
    if (symbolCache.has(cacheKey)) {
      return symbolCache.get(cacheKey)!;
    }

    const response = await apiClient.get('/symbols/find', {
      params: { name, model }
    });

    if (response.data.success && response.data.symbol) {
      const symbolData = response.data.symbol;
      // 获取完整的图形数据
      const graphicsData = await symbolApi.getSymbolGraphics(
        symbolData.library,
        symbolData.name
      );
      symbolCache.set(cacheKey, graphicsData);
      return graphicsData;
    }
    return null;
  },

  // 搜索符号
  searchSymbols: async (keyword: string, limit: number = 20): Promise<ApiResponse<{ symbols: SymbolGraphicsData[] }>> => {
    const response = await apiClient.get('/symbols/search', {
      params: { keyword, limit }
    });
    return response.data;
  },

  // 清除缓存
  clearCache: () => {
    symbolCache.clear();
  },

  // 获取缓存大小
  getCacheSize: (): number => {
    return symbolCache.size;
  }
};

// ==================== 兼容旧代码的导出 ====================

// 定义 kicadApi 的接口类型
interface KiCadApi {
  // 嵌套结构
  project: {
    open: (path: string) => Promise<ApiResponse<Project>>;
    save: () => Promise<{ success: boolean }>;
    getInfo: () => Promise<{ success: boolean; data: Record<string, unknown> }>;
    startKiCad: () => Promise<{ success: boolean }>;
    saveProject: () => Promise<{ success: boolean }>;
  };
  tool: {
    activate: (tool: string, params?: Record<string, unknown>) => Promise<{ success: boolean; tool: string; params?: Record<string, unknown> }>;
    activateTool: (tool: string, params?: Record<string, unknown>) => Promise<{ success: boolean; tool: string; params?: Record<string, unknown> }>;
  };
  exports: typeof exportApi;
  drc: {
    run: (projectId?: string) => Promise<ApiResponse<DRCReport>>;
    runDRC: (projectId?: string) => Promise<ApiResponse<DRCReport>>;
    getReport: (projectId?: string) => Promise<ApiResponse<DRCReport>>;
    getDRCReport: (projectId?: string) => Promise<ApiResponse<DRCReport>>;
  };
  menu: {
    click: (menu: string, item: string) => Promise<{ success: boolean; menu: string; item: string }>;
    clickMenu: (menu: string, item: string) => Promise<{ success: boolean; menu: string; item: string }>;
  };
  state: {
    getFull: () => Promise<{ success: boolean; data: Record<string, unknown> }>;
    getFullState: () => Promise<{ success: boolean; data: Record<string, unknown> }>;
    getScreenshot: () => Promise<{ success: boolean; data: string }>;
  };
  input: {
    sendMouseAction: (action: string, params?: unknown) => Promise<{ success: boolean; action: string; params?: unknown }>;
    sendKeyboardAction: (action: string, keys?: string[]) => Promise<{ success: boolean; action: string; keys?: string[] }>;
    mouseClick: (x: number, y: number, button?: string) => Promise<{ success: boolean; x: number; y: number; button?: string }>;
    mouseDoubleClick: (x: number, y: number) => Promise<{ success: boolean; x: number; y: number }>;
    mouseMove: (x: number, y: number) => Promise<{ success: boolean; x: number; y: number }>;
    mouseDrag: (x: number, y: number, endX: number, endY: number) => Promise<{ success: boolean; x: number; y: number; endX: number; endY: number }>;
    typeText: (text: string) => Promise<{ success: boolean; text: string }>;
    pressKeys: (keys: string[]) => Promise<{ success: boolean; keys: string[] }>;
  };
  
  // 扁平化快捷方法（用于兼容旧代码调用方式）
  activateTool: (tool: string, params?: Record<string, unknown>) => Promise<{ success: boolean; tool: string; params?: Record<string, unknown> }>;
  startKiCad: () => Promise<{ success: boolean }>;
  saveProject: () => Promise<{ success: boolean }>;
  sendKeyboardAction: (params: { keys: string[] }) => Promise<{ success: boolean; action?: string; keys?: string[] }>;
  runDRC: () => Promise<ApiResponse<DRCReport>>;
  getDRCReport: () => Promise<DRCReport>;
  clickMenu: (menu: string, item: string) => Promise<{ success: boolean; menu: string; item: string }>;
  export: (type: string, path: string) => Promise<{ success: boolean; files?: string[]; error?: string }>;
  getFullState: () => Promise<Record<string, unknown>>;
  sendMouseAction: (params: { action: string; x: number; y: number }) => Promise<{ success: boolean; action?: string; params?: unknown }>;
  autoRoute: () => Promise<{ success: boolean; message?: string; error?: string; method?: string; hint?: string }>;
}

export const kicadApi: KiCadApi = {
  project: {
    open: async (path: string) => projectApi.createProject({ name: path }),
    save: async () => ({ success: false, error: 'Use store action to save PCB/schematic data', data: {} }),
    getInfo: async () => ({ success: false, error: 'Not implemented', data: {} }),
    startKiCad: async () => {
      try {
        return await kicadIpcApi.startKiCad();
      } catch (error) {
        return { success: false, error: String(error) };
      }
    },
    saveProject: async () => ({ success: false, error: 'Use store action to save PCB/schematic data' }),
  },
  tool: {
    activate: async (tool: string, params?: Record<string, unknown>) => {
      try {
        const result = await kicadIpcApi.executeAction(`tool.${tool}`, params || {});
        return { success: result.success, tool, params };
      } catch (error) {
        // 如果KiCad未连接，工具切激活可能是本地canvas操作，不算失败
        return { success: true, tool, params };
      }
    },
    activateTool: async (tool: string, params?: Record<string, unknown>) => {
      try {
        const result = await kicadIpcApi.executeAction(`tool.${tool}`, params || {});
        return { success: result.success, tool, params };
      } catch (error) {
        return { success: true, tool, params };
      }
    },
  },
  exports: exportApi,
  drc: {
    run: async (projectId?: string) => drcApi.runDRC(projectId || 'default'),
    runDRC: async (projectId?: string) => drcApi.runDRC(projectId || 'default'),
    getReport: async (projectId?: string) => drcApi.getDRCReport(projectId || 'default'),
    getDRCReport: async (projectId?: string) => drcApi.getDRCReport(projectId || 'default'),
  },
  menu: {
    click: async (menu: string, item: string) => {
      try {
        const result = await kicadIpcApi.executeAction('menu_click', { menu, item });
        return { success: result.success, menu, item };
      } catch (error) {
        return { success: false, error: String(error), menu, item };
      }
    },
    clickMenu: async (menu: string, item: string) => {
      try {
        const result = await kicadIpcApi.executeAction('menu_click', { menu, item });
        return { success: result.success, menu, item };
      } catch (error) {
        return { success: false, error: String(error), menu, item };
      }
    },
  },
  state: {
    getFull: async () => {
      try {
        const status = await kicadIpcApi.getStatus();
        return { success: status.connected, data: status };
      } catch (error) {
        return { success: false, data: {} };
      }
    },
    getFullState: async () => {
      try {
        const status = await kicadIpcApi.getStatus();
        return { success: status.connected, data: status };
      } catch (error) {
        return { success: false, data: {} };
      }
    },
    getScreenshot: async () => {
      try {
        const response = await apiClient.post('/kicad-ipc/screenshot');
        return { success: response.data?.success ?? false, data: response.data?.data ?? '' };
      } catch (error) {
        return { success: false, data: '' };
      }
    },
  },
  input: {
    sendMouseAction: async (action: string, params?: unknown) => ({ success: false, error: 'Input actions require KiCad IPC connection', action, params }),
    sendKeyboardAction: async (action: string, keys?: string[]) => ({ success: false, error: 'Input actions require KiCad IPC connection', action, keys }),
    mouseClick: async (x: number, y: number, button?: string) => ({ success: false, error: 'Input actions require KiCad IPC connection', x, y, button }),
    mouseDoubleClick: async (x: number, y: number) => ({ success: false, error: 'Input actions require KiCad IPC connection', x, y }),
    mouseMove: async (x: number, y: number) => ({ success: false, error: 'Input actions require KiCad IPC connection', x, y }),
    mouseDrag: async (x: number, y: number, endX: number, endY: number) => ({ success: false, error: 'Input actions require KiCad IPC connection', x, y, endX, endY }),
    typeText: async (text: string) => ({ success: false, error: 'Input actions require KiCad IPC connection', text }),
    pressKeys: async (keys: string[]) => ({ success: false, error: 'Input actions require KiCad IPC connection', keys }),
  },
  // 扁平化快捷方法实现
  activateTool: async (tool: string, params?: Record<string, unknown>) => {
    try {
      const result = await kicadIpcApi.executeAction(`tool.${tool}`, params || {});
      return { success: result.success, tool, params };
    } catch (error) {
      return { success: true, tool, params };
    }
  },
  startKiCad: async () => {
    try {
      return await kicadIpcApi.startKiCad();
    } catch (error) {
      return { success: false, error: String(error) };
    }
  },
  saveProject: async () => ({ success: false, error: 'Use store action to save PCB/schematic data' }),
  sendKeyboardAction: async (params: { keys: string[] }) => {
    try {
      const result = await kicadIpcApi.executeAction('keyboard', { keys: params.keys });
      return { success: result.success, keys: params.keys };
    } catch (error) {
      return { success: false, error: String(error), keys: params.keys };
    }
  },
  runDRC: async () => drcApi.runDRC('default'),
  getDRCReport: async () => {
    try {
      const response = await drcApi.getDRCReport('default');
      return response.data ?? {
        success: false,
        errorCount: 0,
        warningCount: 0,
        error_count: 0,
        warning_count: 0,
        errors: [],
        warnings: [],
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        success: false,
        error: String(error),
        errorCount: 0,
        warningCount: 0,
        error_count: 0,
        warning_count: 0,
        errors: [],
        warnings: [],
        timestamp: new Date().toISOString()
      };
    }
  },
  clickMenu: async (menu: string, item: string) => {
    try {
      const result = await kicadIpcApi.executeAction('menu_click', { menu, item });
      return { success: result.success, menu, item };
    } catch (error) {
      return { success: false, error: String(error), menu, item };
    }
  },
  export: async (type: string, _path: string) => {
    const projectId = 'default';
    try {
      let result: ApiResponse<ExportResultData>;
      switch (type) {
        case 'gerber':
          result = await exportApi.exportGerber(projectId);
          break;
        case 'drill':
          result = await exportApi.exportDrill(projectId);
          break;
        case 'bom':
          result = await exportApi.exportBOM(projectId);
          break;
        case 'step':
          result = await exportApi.exportSTEP(projectId);
          break;
        default:
          return { success: false, error: `Unknown export type: ${type}` };
      }
      const exportData = result.data || ({} as ExportResultData);
      return {
        success: result.success && (exportData.success ?? true),
        files: exportData.files ?? [],
        error: result.error || (exportData.message ? undefined : result.error),
      };
    } catch (error) {
      return { success: false, error: String(error) };
    }
  },
  autoRoute: async () => {
    try {
      const response = await apiClient.post('/kicad-ipc/auto-route', {
        net_class: 'default',
        ripup_days: false,
        stability: 50,
        max_iterations: 100
      });
      return response.data;
    } catch (error) {
      return { success: false, error: String(error) };
    }
  },
  getFullState: async () => {
    try {
      const status = await kicadIpcApi.getStatus();
      return { connected: status.connected, tool: '', layer: '', cursor: { x: 0, y: 0 }, zoom: 1 };
    } catch (error) {
      return { connected: false, tool: '', layer: '', cursor: { x: 0, y: 0 }, zoom: 1 };
    }
  },
  sendMouseAction: async (params: { action: string; x: number; y: number }) => {
    try {
      const result = await kicadIpcApi.executeAction('mouse', params);
      return { success: result.success, action: params.action, params };
    } catch (error) {
      return { success: false, error: String(error), action: params.action, params };
    }
  },
};

// ==================== KiCad IPC API ====================

// 完整PCB数据类型
export interface FullPCBData {
  success: boolean;
  connected?: boolean;
  layers: Array<{
    id: string;
    name: string;
    type: string;
    color: string;
    visible: boolean;
  }>;
  nets: Array<{
    id: string;
    name: string;
    code: number;
  }>;
  footprints: Array<{
    id: string;
    reference: string;
    value: string;
    footprint: string;
    layer: string;
    position: { x: number; y: number };
    rotation: number;
    pad: Array<{
      number: string;
      name: string;
      type: string;
      shape: string;
      position: { x: number; y: number };
      size: { x: number; y: number };
    }>;
  }>;
  tracks: Array<{
    id: string;
    net: string;
    layer: string;
    width: number;
    start: { x: number; y: number };
    end: { x: number; y: number };
  }>;
  vias: Array<{
    id: string;
    net: string;
    position: { x: number; y: number };
    size: number;
    drill: number;
    layers: string[];
  }>;
  zones: Array<{
    id: string;
    net: string;
    layer: string;
    priority: number;
  }>;
  board_outline: Array<{ x: number; y: number }>;
  texts: Array<{
    id: string;
    text: string;
    layer: string;
    position: { x: number; y: number };
    rotation: number;
  }>;
  statistics?: {
    total_footprints: number;
    total_tracks: number;
    total_vias: number;
    total_zones: number;
    total_nets: number;
    total_layers: number;
  };
  error?: string;
}

export const kicadIpcApi = {
  // 获取连接状态
  getStatus: async (): Promise<{ connected: boolean; message?: string }> => {
    const response = await apiClient.get('/kicad-ipc/status');
    return response.data;
  },

  // 启动KiCad
  startKiCad: async (pcbFile?: string): Promise<{ success: boolean; connected?: boolean; message?: string }> => {
    const response = await apiClient.post('/kicad-ipc/start', null, { params: { pcb_file: pcbFile } });
    return response.data;
  },

  // 停止KiCad
  stopKiCad: async (): Promise<{ success: boolean; message?: string }> => {
    const response = await apiClient.post('/kicad-ipc/stop');
    return response.data;
  },

  // 获取完整PCB数据
  // 注意: IPC 路由注册在 /api/kicad-ipc, 不是 /api/v1/kicad-ipc
  getFullPCB: async (): Promise<FullPCBData> => {
    const response = await axios.get('/api/kicad-ipc/full-pcb');
    return response.data;
  },

  // 获取统计信息
  getStatistics: async (): Promise<{
    success: boolean;
    connected?: boolean;
    total_items?: number;
    footprints?: number;
    tracks?: number;
    vias?: number;
    zones?: number;
  }> => {
    const response = await apiClient.get('/kicad-ipc/statistics');
    return response.data;
  },

  // 执行KiCad动作
  executeAction: async (actionName: string, params?: Record<string, unknown>): Promise<{
    success: boolean;
    connected?: boolean;
    result?: unknown;
    error?: string;
  }> => {
    const response = await apiClient.post('/kicad-ipc/action', {
      action_name: actionName,
      params: params || {}
    });
    return response.data;
  },

  // 获取鼠线（未布线连接）
  getRatsnest: async (): Promise<{
    success: boolean;
    connected?: boolean;
    ratsnest: unknown[];
  }> => {
    const response = await apiClient.get('/kicad-ipc/ratsnest');
    return response.data;
  },

  // 自动布线
  autoRoute: async (netClass: string = 'default'): Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }> => {
    const response = await apiClient.post('/kicad-ipc/auto-route', {
      net_class: netClass,
      ripup_days: false,
      stability: 50,
      max_iterations: 100
    });
    return response.data;
  },

  // 清除所有走线
  clearTracks: async (): Promise<{
    success: boolean;
    connected?: boolean;
    message?: string;
  }> => {
    const response = await apiClient.post('/kicad-ipc/clear-tracks');
    return response.data;
  },

  // 保存板子
  saveBoard: async (): Promise<{
    success: boolean;
    connected?: boolean;
    message?: string;
    path?: string;
  }> => {
    const response = await apiClient.post('/kicad-ipc/save');
    return response.data;
  },
};

// ==================== Phase 6 API: Symbol Search ====================

export interface SymbolSearchFilters {
  category?: string;
  library?: string;
  package?: string;
  pin_count_min?: number;
  pin_count_max?: number;
  manufacturer?: string;
}

export interface SymbolInfo {
  name: string;
  library: string;
  description: string;
  keywords: string[];
  package: string;
  pin_count: number;
  category: string;
  datasheet?: string;
  manufacturer?: string;
}

export interface SearchSymbolsRequest {
  query: string;
  filters?: SymbolSearchFilters;
  page?: number;
  page_size?: number;
}

// ==================== Phase 6 API: Bulk Placement ====================

export interface BOMItem {
  reference: string;
  value: string;
  footprint?: string;
  symbol?: string;
  quantity?: number;
}

export interface BulkPlacementRequest {
  bom_text?: string;
  bom_items?: BOMItem[];
  strategy?: string;
  start_x?: number;
  start_y?: number;
  spacing_x?: number;
  spacing_y?: number;
  max_cols?: number;
}

export interface PlacedComponent {
  reference: string;
  symbol_name: string;
  library: string;
  x: number;
  y: number;
  rotation: number;
  properties: Record<string, string>;
}

// ==================== Phase 6 API: Fanout ====================

export interface PadInfo {
  pad_number: string;
  x: number;
  y: number;
  net: string;
  type?: string;
}

export interface FanoutRequest {
  component_id: string;
  reference: string;
  pads: PadInfo[];
  direction?: string;
  pin_spacing?: number;
}

export interface ViaInfo {
  via_id: string;
  x: number;
  y: number;
  net: string;
  from_layer: string;
  to_layer: string;
  outer_diameter: number;
  drill: number;
}

export interface TraceInfo {
  trace_id: string;
  net: string;
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  layer: string;
  width: number;
}

// ==================== Phase 6 API: Route Planning ====================

export interface RoutePoint {
  x: number;
  y: number;
}

export interface RouteSegment {
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  layer: string;
  width: number;
}

export interface RoutePlanRequest {
  start_x: number;
  start_y: number;
  start_layer: string;
  end_x: number;
  end_y: number;
  end_layer: string;
  net_name: string;
  trace_width?: number;
  clearance?: number;
  max_vias?: number;
}

// ==================== Phase 6 API: Templates ====================

export interface TemplateInfo {
  template_id: string;
  name: string;
  name_cn: string;
  description: string;
  category: string;
  tags: string[];
  author: string;
  is_predefined: boolean;
  created_at?: string;
}

export interface TemplateDetail extends TemplateInfo {
  schematic?: any;
  pcb?: any;
}

// ==================== Phase 6 API Namespace ====================

export const phase6Api = {
  // Symbol Search API
  searchSymbols: async (
    query: string,
    filters?: SymbolSearchFilters,
    page: number = 1,
    pageSize: number = 20
  ): Promise<{ success: boolean; symbols: SymbolInfo[]; total: number; page: number; page_size: number }> => {
    const response = await apiClient.post('/symbols/search', {
      query,
      filters,
      page,
      page_size: pageSize,
    });
    return response.data;
  },

  getSymbolCategories: async (): Promise<{ success: boolean; categories: string[] }> => {
    const response = await apiClient.get('/symbols/categories');
    return response.data;
  },

  // Bulk Placement API
  bulkPlace: async (request: BulkPlacementRequest): Promise<{
    success: boolean;
    components: PlacedComponent[];
    total: number;
    strategy: string;
    grid_cols: number;
    grid_rows: number;
  }> => {
    const response = await apiClient.post('/symbols/bulk-place', request);
    return response.data;
  },

  // Fanout API
  fanout: async (request: FanoutRequest): Promise<{
    success: boolean;
    component_id: string;
    reference: string;
    pads: PadInfo[];
    vias: ViaInfo[];
    traces: TraceInfo[];
  }> => {
    const response = await apiClient.post('/pcb/fanout', request);
    return response.data;
  },

  fanoutBatch: async (
    components: FanoutRequest[],
    options?: { default_direction?: string; spacing?: number; via_size?: number; drill_size?: number; trace_width?: number }
  ): Promise<{
    success: boolean;
    component_results: Array<{
      component_id: string;
      reference: string;
      vias: ViaInfo[];
      traces: TraceInfo[];
    }>;
    total_vias: number;
    total_traces: number;
  }> => {
    const response = await apiClient.post('/pcb/fanout/batch', {
      components,
      ...options,
    });
    return response.data;
  },

  getPinSpacing: async (packageType: string): Promise<{ success: boolean; package_type: string; pin_spacing_mm: number }> => {
    const response = await apiClient.get(`/pcb/fanout/pin-spacing/${encodeURIComponent(packageType)}`);
    return response.data;
  },

  // Route Planning API
  planRoute: async (request: RoutePlanRequest): Promise<{
    success: boolean;
    candidates: Array<{
      route_id: string;
      segments: RouteSegment[];
      total_length: number;
      via_count: number;
      score: number;
      status: string;
    }>;
    best_route: {
      route_id: string;
      segments: RouteSegment[];
      total_length: number;
      via_count: number;
      score: number;
    } | null;
    message: string;
  }> => {
    const response = await apiClient.post('/pcb/route/plan', request);
    return response.data;
  },

  getRoutePreview: async (
    startX: number,
    startY: number,
    currentX: number,
    currentY: number,
    layer: string
  ): Promise<{ success: boolean; preview: RoutePoint[] }> => {
    const response = await apiClient.post('/pcb/route/preview', {
      start_x: startX,
      start_y: startY,
      current_x: currentX,
      current_y: currentY,
      layer,
    });
    return response.data;
  },

  adjustRouteWidth: async (
    routeId: string,
    newWidth: number
  ): Promise<{ success: boolean; route: any; message?: string }> => {
    const response = await apiClient.post('/pcb/route/adjust-width', null, {
      params: { route_id: routeId, new_width: newWidth },
    });
    return response.data;
  },

  addRouteObstacle: async (x: number, y: number, layer: string = 'F.Cu'): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post('/pcb/route/add-obstacle', null, {
      params: { x, y, layer },
    });
    return response.data;
  },

  clearRouteObstacles: async (): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post('/pcb/route/clear-obstacles');
    return response.data;
  },

  // Template API
  getTemplates: async (category?: string, search?: string): Promise<{
    success: boolean;
    templates: TemplateInfo[];
    count: number;
  }> => {
    const response = await apiClient.get('/templates', {
      params: { category, search },
    });
    return response.data;
  },

  getTemplateCategories: async (): Promise<{
    success: boolean;
    categories: Array<{ value: string; label: string }>;
  }> => {
    const response = await apiClient.get('/templates/categories');
    return response.data;
  },

  getTemplate: async (templateId: string): Promise<{
    success: boolean;
    template: TemplateDetail;
  }> => {
    const response = await apiClient.get(`/templates/${templateId}`);
    return response.data;
  },

  createProjectFromTemplate: async (
    templateId: string,
    projectName: string,
    schematicOverrides?: any,
    pcbOverrides?: any
  ): Promise<{
    success: boolean;
    project_id: string;
    project_name: string;
    template_id: string;
    schematic?: any;
    pcb?: any;
  }> => {
    const response = await apiClient.post('/templates/create-project', {
      template_id: templateId,
      project_name: projectName,
      schematic_overrides: schematicOverrides,
      pcb_overrides: pcbOverrides,
    });
    return response.data;
  },

  // Phase 7B: Topology-aware Auto Layout
  autoLayout: async (
    topologyAware: boolean = true,
    boardConstraints?: { width: number; height: number }
  ): Promise<{
    success: boolean;
    topology_aware: boolean;
    placed_count: number;
    total_count: number;
    score: number;
    zones: Array<{
      name: string;
      group: string;
      x: number; y: number;
      width: number; height: number;
      color: string;
    }>;
    isolation_slots: Array<{
      x: number; y: number;
      width: number; height: number;
      voltage_label: string;
      standard: string;
    }>;
    positions: Record<string, { x: number; y: number; rotation: number }>;
    statistics: Record<string, any>;
  }> => {
    const response = await apiClient.post('/pcb/auto-layout', {
      topology_aware: topologyAware,
      board_constraints: boardConstraints,
    });
    return response.data;
  },

  // Phase 7C: Copper Pour
  copperPour: async (options: {
    nets?: string[];
    layers?: string[];
    style?: 'solid' | 'hatched';
    hatch_width?: number;
    hatch_gap?: number;
    thermal_relief?: boolean;
    stitch_vias?: boolean;
    stitch_spacing?: number;
    clearance?: number;
  } = {}): Promise<{
    success: boolean;
    results: Array<{
      net: string;
      layer: string;
      zone: boolean;
      stitching_vias: number;
    }>;
    total_zones: number;
    drc_check?: {
      passed: boolean | null;
      total_violations: number;
      copper_violations: number;
      violations: Array<{ rule: string; message: string }>;
    };
  }> => {
    const response = await apiClient.post('/pcb/copper-pour', {
      nets: options.nets || ['GND'],
      layers: options.layers || ['B.Cu'],
      style: options.style || 'solid',
      hatch_width: options.hatch_width || 1.0,
      hatch_gap: options.hatch_gap || 0.5,
      thermal_relief: options.thermal_relief !== false,
      stitch_vias: options.stitch_vias !== false,
      stitch_spacing: options.stitch_spacing || 1.0,
      clearance: options.clearance || 0.3,
    });
    return response.data;
  },

  createZone: async (request: {
    net_name: string;
    layer: string;
    boundary_points: Array<{ x: number; y: number }>;
    clearance?: number;
    thermal_relief?: boolean;
    hatched?: boolean;
    hatch_width?: number;
    hatch_gap?: number;
  }): Promise<{
    success: boolean;
    net_name: string;
    layer: string;
    zone_data: any;
    area: number;
  }> => {
    const response = await apiClient.post('/pcb/create-zone', request);
    return response.data;
  },

  // Phase 8: Thermal Via Generation
  generateThermalVias: async (request: {
    component_x: number;
    component_y: number;
    component_width: number;
    component_height: number;
    target_rth?: number;
    via_drill?: number;
    via_size?: number;
    spacing?: number;
    net?: string;
    avoid_pins?: Array<{ x: number; y: number; radius: number }>;
  }): Promise<{
    success: boolean;
    via_count: number;
    estimated_rth: number;
    target_rth: number;
    grid_rows: number;
    grid_cols: number;
    vias: Array<{ x: number; y: number; drill: number; size: number }>;
    kicad_output: string;
  }> => {
    const response = await apiClient.post('/pcb/thermal-vias', request);
    return response.data;
  },

  // Phase 8: Safety Isolation Generation
  generateIsolation: async (request: {
    board_width: number;
    board_height: number;
    primary_zone: number[];
    secondary_zone: number[];
    voltage?: number;
    voltage_label?: string;
    standard?: string;
    add_barriers?: boolean;
    num_barriers?: number;
  }): Promise<{
    success: boolean;
    slot: { x: number; y: number; width: number; height: number; voltage_label: string; standard: string };
    min_creepage_mm: number;
    barriers_count: number;
    kicad_output: string;
  }> => {
    const response = await apiClient.post('/pcb/isolation-generate', request);
    return response.data;
  },

  getCreepageDistance: async (voltage: number, standard: string = 'IEC 60950-1'): Promise<{
    success: boolean;
    voltage: number;
    standard: string;
    min_creepage_mm: number;
  }> => {
    const response = await apiClient.get(`/pcb/isolation-creepage/${voltage}`, { params: { standard } });
    return response.data;
  },

  // Phase 9: Differential Pair Routing
  routeDiffPair: async (request: {
    start_pos_x: number; start_pos_y: number;
    start_neg_x: number; start_neg_y: number;
    end_pos_x: number; end_pos_y: number;
    end_neg_x: number; end_neg_y: number;
    layer?: string;
    target_impedance?: number;
    max_length_mismatch?: number;
  }): Promise<{
    success: boolean;
    pos_points: Array<{ x: number; y: number }>;
    neg_points: Array<{ x: number; y: number }>;
    pos_length: number;
    neg_length: number;
    length_mismatch: number;
    impedance: number;
    target_impedance: number;
  }> => {
    const response = await apiClient.post('/pcb/diff-pair-route', request);
    return response.data;
  },

  calculateImpedance: async (request: {
    target_impedance?: number;
    tolerance_pct?: number;
    substrate_height?: number;
    er?: number;
  }): Promise<{
    success: boolean;
    target_z: number;
    tolerance_pct: number;
    min_z: number;
    max_z: number;
    trace_width_mm: number;
    trace_gap_mm: number;
    common_targets: Record<string, number>;
  }> => {
    const response = await apiClient.post('/pcb/impedance-calculate', request);
    return response.data;
  },

  lengthTune: async (request: {
    points: Array<{ x: number; y: number }>;
    target_length: number;
    style?: 'serpentine' | 'sawtooth';
    amplitude?: number;
    pitch?: number;
  }): Promise<{
    success: boolean;
    tuned_points: Array<{ x: number; y: number }>;
    original_length: number;
    tuned_length: number;
    added_length: number;
    bend_count: number;
    style: string;
  }> => {
    const response = await apiClient.post('/pcb/length-tune', request);
    return response.data;
  },
};

// ==================== Design Agent API (Phase 7E) ====================

export interface AgentProgress {
  task_id: string;
  current_step: string;
  step_index: number;
  total_steps: number;
  progress_pct: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  intermediate_results: Record<string, unknown>;
  step_durations: Record<string, number>;
}

export interface AgentStepResult {
  step_type: string;
  status: string;
  message: string;
  duration_s: number;
  data?: Record<string, unknown>;
  errors: string[];
  warnings: string[];
}

export interface AgentDesignResult {
  task_id: string;
  success: boolean;
  steps: AgentStepResult[];
  total_duration_s: number;
  iterations: number;
  error_message: string;
  schematic?: Record<string, unknown>;
  pcb?: Record<string, unknown>;
  drc_result?: Record<string, unknown>;
  bom?: Array<Record<string, unknown>>;
}

export const agentApi = {
  // 启动多步设计流水线
  startDesign: async (request: {
    requirements: string;
    max_iterations?: number;
    project_name?: string;
  }): Promise<{ success: boolean; task_id: string; message: string }> => {
    const response = await apiClient.post('/agent/design', request);
    return response.data;
  },

  // 获取实时进度
  getProgress: async (taskId: string): Promise<AgentProgress> => {
    const response = await apiClient.get(`/agent/progress/${taskId}`);
    return response.data;
  },

  // 获取最终结果
  getResult: async (taskId: string): Promise<AgentDesignResult> => {
    const response = await apiClient.get(`/agent/result/${taskId}`);
    return response.data;
  },

  // 列出所有任务
  listTasks: async (): Promise<{
    active: Array<{
      task_id: string;
      current_step: string;
      progress_pct: number;
      status: string;
    }>;
    recent_completed: Array<{
      task_id: string;
      success: boolean;
      total_duration_s: number;
    }>;
    total_active: number;
  }> => {
    const response = await apiClient.get('/agent/tasks');
    return response.data;
  },

  // 取消设计任务
  cancelDesign: async (taskId: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post(`/agent/cancel/${taskId}`);
    return response.data;
  },

  // 布局方案生成 (Phase 9)
  generateLayoutCandidates: async (request: {
    board_width: number;
    board_height: number;
    components: Array<{
      reference: string;
      footprint: string;
      value: string;
      width: number;
      height: number;
    }>;
    net_connections?: Array<{ net: string; ref1: string; ref2: string }>;
  }): Promise<{
    success: boolean;
    candidates: Array<{
      strategy: string;
      positions: Record<string, { x: number; y: number; rotation: number }>;
      scores: {
        overall: number;
        utilization: number;
        wire_length: number;
        thermal: number;
        routing: number;
      };
      description: string;
    }>;
    recommended: string | null;
    message: string;
  }> => {
    const response = await apiClient.post('/pcb/layout-candidates', request);
    return response.data;
  },

  // Phase 8D: Routing quality scoring
  scoreRoutingQuality: async (request: {
    total_nets: number;
    routed_nets: number;
    failed_nets?: string[];
    drc_violations?: number;
    total_track_length?: number;
    ideal_track_length?: number;
    total_vias?: number;
    diff_pair_count?: number;
    diff_pair_impedance_errors?: number;
    diff_pair_length_mismatches?: number;
    board_area?: number;
  }): Promise<{
    success: boolean;
    total_score: number;
    grade: string;
    is_passing: boolean;
    is_production_ready: boolean;
    dimensions: Array<{
      name: string;
      score: number;
      weight: number;
      weighted_score: number;
      details: string;
    }>;
    improvements: string[];
    message: string;
  }> => {
    const response = await apiClient.post('/pcb/routing-quality', request);
    return response.data;
  },
};

// 兼容类型导出
export type ProjectInfo = Project;
export type StateResponse = {
  connected: boolean;
  projectOpen: boolean;
  activeTool: string;
  zoom: number;
};
export type ExportResult = {
  success: boolean;
  filePath?: string;
  message?: string;
};

export default apiClient;
