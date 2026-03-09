/**
 * 应用配置
 * 可根据需要开启/关闭某些特性
 */

export const appConfig = {
  // 开发模式配置
  development: {
    // 显示详细日志（生产环境建议关闭）
    verboseLogging: true,
    // 显示性能调试信息
    showPerformanceMetrics: true,
    // 启用 Redux DevTools
    enableReduxDevTools: true,
  },

  // 功能开关
  features: {
    // 启用 AI 聊天助手
    enableAIAssistant: true,
    // 启用 3D 预览
    enable3DPreview: true,
    // 启用自动保存
    enableAutoSave: true,
    // 自动保存间隔（毫秒）
    autoSaveInterval: 30000,
  },

  // UI 配置
  ui: {
    // 主题: 'dark' | 'light'
    theme: 'dark',
    // 默认编辑器视图: '2d' | '3d'
    defaultView: '2d',
    // 显示网格
    showGrid: true,
    // 显示鼠线
    showRats: true,
    // 网格大小
    gridSize: 10,
  },

  // API 配置
  api: {
    // 请求超时（毫秒）
    timeout: 30000,
    // 重试次数
    retryCount: 3,
    // 请求去重
    enableDeduplication: true,
  },

  // 渲染配置
  rendering: {
    // 最大同时渲染的元件数量
    maxRenderItems: 1000,
    // 启用虚拟滚动
    enableVirtualScroll: true,
    // 缩放限制
    zoomLimits: {
      min: 0.1,
      max: 10,
    },
  },
};

// 导出类型
export type AppConfig = typeof appConfig;

// 开发环境变量覆盖
if (import.meta.env.DEV) {
  // 开发环境默认启用详细日志
  appConfig.development.verboseLogging = true;
}

if (import.meta.env.PROD || import.meta.env.MODE === 'production') {
  // 生产环境关闭详细日志
  appConfig.development.verboseLogging = false;
  appConfig.development.showPerformanceMetrics = false;
}

export default appConfig;
