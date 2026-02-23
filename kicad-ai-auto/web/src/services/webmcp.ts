/**
 * WebMCP 客户端 - 用于 AI 代理与网页的结构化交互
 * 
 * WebMCP (Web Model Context Protocol) 是 Google Chrome 推出的新协议
 * 允许网站暴露结构化工具给 AI 代理，无需截图和 DOM 解析
 * 
 * 需要 Chrome 146+ 并启用 --enable-features=WebMCP
 */

interface WebMCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
}

interface WebMCPState {
  tools: WebMCPTool[];
  context: Record<string, unknown>;
  version: string;
}

interface WebMCPToolResult {
  success: boolean;
  result?: unknown;
  error?: string;
}

// 定义回调函数类型
type StateChangeCallback = (state: WebMCPState) => void;
type ToolCallCallback = (tool: string, params: unknown) => void;

// Chrome WebMCP API 类型定义
interface ChromeWebMCP {
  getState: () => Promise<WebMCPState>;
  callTool: (toolName: string, params: Record<string, unknown>) => Promise<unknown>;
  onStateChange: (callback: StateChangeCallback) => void;
  onToolCall: (callback: ToolCallCallback) => void;
}

// 扩展 Window 接口
declare global {
  interface Window {
    chrome?: {
      webmcp?: ChromeWebMCP;
    };
  }
}

class WebMCPClient {
  private baseUrl: string;
  private state: WebMCPState | null = null;
  private listeners: Map<string, StateChangeCallback[] | ToolCallCallback[]> = new Map();

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  /**
   * 检查浏览器是否支持 WebMCP
   */
  static isSupported(): boolean {
    return 'webmcp' in navigator || 
           window.chrome?.webmcp !== undefined;
  }

  /**
   * 获取 WebMCP 状态
   */
  async getState(): Promise<WebMCPState | null> {
    try {
      // 尝试通过 chrome.webmcp API 获取
      if (window.chrome?.webmcp) {
        const state = await window.chrome.webmcp.getState();
        this.state = state;
        return state;
      }
      
      // 如果不支持，返回 null
      console.warn('WebMCP not supported in this browser');
      return null;
    } catch (error) {
      console.error('Failed to get WebMCP state:', error);
      return null;
    }
  }

  /**
   * 获取可用工具列表
   */
  async getTools(): Promise<WebMCPTool[]> {
    const state = await this.getState();
    return state?.tools || [];
  }

  /**
   * 调用工具
   */
  async callTool(toolName: string, params: Record<string, unknown>): Promise<WebMCPToolResult> {
    try {
      if (window.chrome?.webmcp) {
        const result = await window.chrome.webmcp.callTool(toolName, params);
        return {
          success: true,
          result
        };
      }
      
      // 如果不支持，返回错误
      return {
        success: false,
        error: 'WebMCP not supported in this browser'
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Tool call failed';
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 监听状态变化
   */
  onStateChange(callback: StateChangeCallback): () => void {
    if (!window.chrome?.webmcp?.onStateChange) {
      return () => {};
    }
    
    window.chrome.webmcp.onStateChange(callback);
    
    return () => {
      // 取消监听
    };
  }

  /**
   * 监听工具调用
   */
  onToolCall(callback: ToolCallCallback): () => void {
    if (!window.chrome?.webmcp?.onToolCall) {
      return () => {};
    }
    
    window.chrome.webmcp.onToolCall(callback);
    
    return () => {
      // 取消监听
    };
  }
}

/**
 * 示例：在网页中声明 WebMCP 工具
 * 
 * 网站需要实现以下 JavaScript 来暴露工具：
 */

// 示例 1: Declarative API (HTML 表单方式)
/*
<!DOCTYPE html>
<html>
<head>
  <script type="application/webmcp+json" id="webmcp-tools">
  {
    "tools": [
      {
        "name": "search_products",
        "description": "Search for products in the catalog",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": { "type": "string", "description": "Search query" },
            "category": { "type": "string", "description": "Product category" },
            "maxResults": { "type": "number", "description": "Maximum results", "default": 10 }
          },
          "required": ["query"]
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "results": { "type": "array", "items": { "type": "object" } },
            "total": { "type": "number" }
          }
        }
      },
      {
        "name": "add_to_cart",
        "description": "Add a product to shopping cart",
        "inputSchema": {
          "type": "object",
          "properties": {
            "productId": { "type": "string" },
            "quantity": { "type": "number", "default": 1 }
          },
          "required": ["productId"]
        }
      }
    ]
  }
  </script>
</head>
<body>
  ...
</body>
</html>
*/

// 示例 2: Imperative API (JavaScript 方式)
/*
// 在网页中注册工具
if (window.chrome?.webmcp) {
  window.chrome.webmcp.registerTool({
    name: 'checkout',
    description: 'Complete the checkout process',
    inputSchema: {
      type: 'object',
      properties: {
        shippingAddress: { type: 'object' },
        paymentMethod: { type: 'string' }
      },
      required: ['shippingAddress']
    },
    outputSchema: {
      type: 'object',
      properties: {
        orderId: { type: 'string' },
        success: { type: 'boolean' }
      }
    },
    handler: async (params) => {
      const result = await processCheckout(params);
      return result;
    }
  });
}
*/

export { WebMCPClient };
export type { WebMCPTool, WebMCPState, WebMCPToolResult };
export default WebMCPClient;
