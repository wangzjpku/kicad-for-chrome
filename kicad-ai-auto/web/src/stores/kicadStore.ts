import { create } from 'zustand'

export interface KiCadState {
  // 连接状态
  connected: boolean

  // 项目信息
  projectPath: string | null
  projectName: string | null

  // 编辑器状态
  currentTool: string | null
  currentLayer: string
  cursorX: number
  cursorY: number
  zoom: number

  // 截图
  screenshotUrl: string | null
  screenshotEmpty: boolean  // 截图是否为空白（白色）

  // 错误和日志
  errors: string[]
  logs: LogEntry[]

  // UI 状态
  theme: 'light' | 'dark'
  activeOutputTab: string

  // 操作
  setConnected: (connected: boolean) => void
  setProject: (path: string, name: string) => void
  setTool: (tool: string) => void
  setLayer: (layer: string) => void
  setCursor: (x: number, y: number) => void
  setZoom: (zoom: number) => void
  setScreenshot: (url: string) => void
  addError: (error: string) => void
  clearErrors: () => void
  addLog: (entry: LogEntry) => void
  setTheme: (theme: 'light' | 'dark') => void
  setActiveOutputTab: (tab: string) => void
}

export interface LogEntry {
  id: string
  timestamp: Date
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
}

export const useKiCadStore = create<KiCadState>((set) => ({
  // 初始状态
  connected: false,
  projectPath: null,
  projectName: null,
  currentTool: null,
  currentLayer: 'F.Cu',
  cursorX: 0,
  cursorY: 0,
  zoom: 100,
  screenshotUrl: null,
  screenshotEmpty: false,
  errors: [],
  logs: [],
  theme: 'dark',
  activeOutputTab: 'logs',

  // 操作方法
  setConnected: (connected) => set({ connected }),

  setProject: (path, name) =>
    set({
      projectPath: path,
      projectName: name,
    }),

  setTool: (tool) => set({ currentTool: tool }),

  setLayer: (layer) => set({ currentLayer: layer }),

  setCursor: (x, y) =>
    set({
      cursorX: x,
      cursorY: y,
    }),

  setZoom: (zoom) => set({ zoom }),

  setScreenshot: (url) => {
    // 检测截图是否为空白（白色）
    // 简单检测：如果URL包含大量连续的白色像素模式
    const isEmpty = url && (
      url.includes('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==') || // 1x1透明像素
      url.length < 5000 // 截图数据太小，可能是空白
    )
    set({ screenshotUrl: url, screenshotEmpty: isEmpty })
  },

  addError: (error) =>
    set((state) => ({
      errors: [...state.errors, error],
    })),

  clearErrors: () => set({ errors: [] }),

  addLog: (entry) =>
    set((state) => ({
      logs: [...state.logs.slice(-999), entry], // 保留最近 1000 条
    })),

  setTheme: (theme) => set({ theme }),

  setActiveOutputTab: (tab) => set({ activeOutputTab: tab }),
}))
