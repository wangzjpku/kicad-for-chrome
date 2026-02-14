import { useEffect, useRef, useCallback, useState } from 'react'
import { useKiCadStore } from '../stores/kicadStore'
import { kicadApi } from '../services/api'

const POLLING_INTERVAL = 1000 // 1秒轮询一次

interface PollingMessage {
  type: string
  data?: string
  tool?: string
  layer?: string
  cursor?: { x: number; y: number }
  zoom?: number
  message?: string
}

interface SendMessage {
  type: string
  event?: string
  x?: number
  y?: number
  keys?: string[]
  command?: { type: string; [key: string]: unknown }
}

/**
 * HTTP 轮询 Hook - 作为 WebSocket 的替代方案
 * 在 WebSocket 不可用时使用
 */
export function useHttpPolling() {
  const [connected, setConnected] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  const { 
    setConnected: setStoreConnected, 
    setTool, 
    setLayer, 
    setCursor, 
    setZoom,
    setScreenshot,
    addLog,
    addError 
  } = useKiCadStore()

  // 获取状态并更新 store
  const pollState = useCallback(async () => {
    try {
      const state = await kicadApi.getFullState() as {
        tool?: string;
        layer?: string;
        cursor?: { x: number; y: number };
        zoom?: number;
      }
      
      if (state.tool) setTool(state.tool)
      if (state.layer) setLayer(state.layer)
      if (state.cursor) {
        setCursor(state.cursor.x, state.cursor.y)
      }
      if (state.zoom) setZoom(state.zoom)
      
      setConnected(true)
      setStoreConnected(true)
    } catch (error) {
      console.error('Polling error:', error)
      setConnected(false)
      setStoreConnected(false)
    }
  }, [setTool, setLayer, setCursor, setZoom, setStoreConnected])

  // 启动轮询
  const startPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    // 立即执行一次
    pollState()
    
    // 设置定时轮询
    pollingRef.current = setInterval(pollState, POLLING_INTERVAL)
    
    addLog({
      id: Date.now().toString(),
      timestamp: new Date(),
      level: 'info',
      message: 'HTTP 轮询模式已启动',
    })
  }, [pollState, addLog])

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setConnected(false)
    setStoreConnected(false)
  }, [setStoreConnected])

  // 发送消息（通过 HTTP API）
  const send = useCallback(async (message: SendMessage) => {
    try {
      switch (message.type) {
        case 'mouse':
          if (message.event === 'click' && message.x !== undefined && message.y !== undefined) {
            await kicadApi.sendMouseAction({ action: 'click', x: message.x, y: message.y })
          }
          break
        case 'keyboard':
          if (message.keys) {
            await kicadApi.sendKeyboardAction({ keys: message.keys })
          }
          break
        case 'command':
          // 命令通过其他 API 处理
          console.log('Command:', message.command)
          break
      }
    } catch (error) {
      console.error('Send error:', error)
    }
  }, [])

  // 启动连接
  const connect = useCallback(() => {
    startPolling()
  }, [startPolling])

  // 断开连接
  const disconnect = useCallback(() => {
    stopPolling()
  }, [stopPolling])

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      stopPolling()
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [stopPolling])

  return {
    connected,
    connect,
    disconnect,
    send,
  }
}

export default useHttpPolling
