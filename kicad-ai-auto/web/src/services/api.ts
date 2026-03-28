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
    const response = await apiClient.get(`/projects/${projectId}/pcb/items`);
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
    const response = await apiClient.post(`/projects/${projectId}/drc/run`, pcbData || {});
    return response.data;
  },

  getDRCReport: async (projectId: string): Promise<ApiResponse<DRCReport>> => {
    const response = await apiClient.get(`/projects/${projectId}/drc/report`);
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
  getFullPCB: async (): Promise<FullPCBData> => {
    const response = await apiClient.get('/kicad-ipc/full-pcb');
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
