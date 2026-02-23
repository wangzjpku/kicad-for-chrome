/**
 * KiCad IPC API React Hook
 * 用于浏览器与 KiCad 的实时通信
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// KiCad 状态类型
export interface KiCadState {
  connected: boolean;
  board_path?: string;
  item_count?: number;
  items?: Array<{
    id: string;
    type: string;
    layer?: string;
  }>;
  selection?: string[];
  layers?: string[];
  error?: string;
}

// WebSocket 消息类型
interface WSMessage {
  type: string;
  data?: KiCadState | Record<string, unknown>;
  message?: string;
  timestamp?: number;
}

export function useKiCadIPC() {
  const [connected, setConnected] = useState(false);
  const [kicadState, setKicadState] = useState<KiCadState | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  // 连接 WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${wsUrl}/api/kicad-ipc/ws`);

    ws.onopen = () => {
      console.log('KiCad WebSocket connected');
      setWsConnected(true);
      setError(null);

      // 请求初始状态
      ws.send(JSON.stringify({ type: 'get_status' }));
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'status':
          case 'status_update':
            if (message.data && 'connected' in message.data) {
              setKicadState(message.data as KiCadState);
              setConnected((message.data as KiCadState).connected || false);
            }
            break;

          case 'action_result':
          case 'creation_result':
            console.log('Action result:', message.data);
            break;

          case 'error':
            console.error('KiCad error:', message.message);
            setError(message.message || 'Unknown error');
            break;

          case 'pong':
            // 心跳响应
            break;
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      console.log('KiCad WebSocket disconnected');
      setWsConnected(false);

      // 自动重连
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Attempting to reconnect...');
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection error');
    };

    wsRef.current = ws;
  }, []);

  // 断开连接
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  // 发送消息
  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // 启动 KiCad
  const startKiCad = useCallback(async (pcbFile?: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/start${pcbFile ? `?pcb_file=${encodeURIComponent(pcbFile)}` : ''}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to start KiCad: ${response.statusText}`);
      }

      const result = await response.json();
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start KiCad');
      throw e;
    }
  }, []);

  // 停止 KiCad
  const stopKiCad = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/stop`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to stop KiCad: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to stop KiCad');
      throw e;
    }
  }, []);

  // 执行动作
  const executeAction = useCallback((actionName: string, params?: Record<string, unknown>) => {
    return sendMessage({
      type: 'execute_action',
      action: actionName,
      params,
    });
  }, [sendMessage]);

  // 创建封装
  const createFootprint = useCallback((
    footprintName: string,
    position: { x: number; y: number },
    layer: string = 'F.Cu'
  ) => {
    return sendMessage({
      type: 'create_footprint',
      footprint_name: footprintName,
      position,
      layer,
    });
  }, [sendMessage]);

  // 获取状态
  const refreshStatus = useCallback(() => {
    return sendMessage({ type: 'get_status' });
  }, [sendMessage]);

  // 删除项目
  const deleteItem = useCallback(async (itemId: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/item/${itemId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete item: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete item');
      throw e;
    }
  }, []);

  // 移动项目
  const moveItem = useCallback(async (itemId: string, position: { x: number; y: number }) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/item/${itemId}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(position),
      });

      if (!response.ok) {
        throw new Error(`Failed to move item: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to move item');
      throw e;
    }
  }, []);

  // 创建走线
  const createTrack = useCallback(async (
    start: { x: number; y: number },
    end: { x: number; y: number },
    layer: string = 'F.Cu',
    width: number = 0.25
  ) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start, end, layer, width }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create track: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create track');
      throw e;
    }
  }, []);

  // 创建过孔
  const createVia = useCallback(async (
    position: { x: number; y: number },
    size: number = 0.8,
    drill: number = 0.4
  ) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/via`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...position, size, drill }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create via: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create via');
      throw e;
    }
  }, []);

  // 保存板子
  const saveBoard = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/save`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to save board: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save board');
      throw e;
    }
  }, []);

  // 获取统计信息
  const getStatistics = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/statistics`);

      if (!response.ok) {
        throw new Error(`Failed to get statistics: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get statistics');
      throw e;
    }
  }, []);

  // 选择项目
  const selectItems = useCallback(async (itemIds: string[]) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(itemIds),
      });

      if (!response.ok) {
        throw new Error(`Failed to select items: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to select items');
      throw e;
    }
  }, []);

  // 清除选择
  const clearSelection = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/kicad-ipc/clear-selection`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to clear selection: ${response.statusText}`);
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to clear selection');
      throw e;
    }
  }, []);

  // 自动连接 WebSocket
  useEffect(() => {
    connectWebSocket();

    // 心跳
    const heartbeat = setInterval(() => {
      sendMessage({ type: 'ping' });
    }, 30000);

    return () => {
      clearInterval(heartbeat);
      disconnectWebSocket();
    };
  }, [connectWebSocket, disconnectWebSocket, sendMessage]);

  return {
    // 状态
    connected,
    wsConnected,
    kicadState,
    error,

    // 方法
    startKiCad,
    stopKiCad,
    executeAction,
    createFootprint,
    refreshStatus,
    deleteItem,
    moveItem,
    createTrack,
    createVia,
    saveBoard,
    getStatistics,
    selectItems,
    clearSelection,
  };
}

export default useKiCadIPC;
