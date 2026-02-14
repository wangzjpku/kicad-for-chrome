import { useCallback, useEffect, useRef, useState } from 'react'
import { useKiCadStore } from '../stores/kicadStore'
import { kicadApi } from '../services/api'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/control'
const RECONNECT_INTERVAL = 3000
const MAX_RECONNECT_ATTEMPTS = 3
const POLLING_INTERVAL = 1000

interface WebSocketMessage {
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

export function useWebSocket() {
  const [connected, setConnected] = useState(false)
  const [usePolling, setUsePolling] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const {
    setScreenshot,
    setTool,
    setLayer,
    setCursor,
    setZoom,
    setConnected: setStoreConnected,
    addError,
    addLog,
  } = useKiCadStore()

  // 轮询获取状态
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
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }
    
    pollState()
    pollingIntervalRef.current = setInterval(pollState, POLLING_INTERVAL)
    
    addLog({
      id: Date.now().toString(),
      timestamp: new Date(),
      level: 'info',
      message: 'HTTP 轮询模式已启动（WebSocket 不可用）',
    })
  }, [pollState, addLog])

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
    setConnected(false)
    setStoreConnected(false)
  }, [setStoreConnected])

  // 处理消息 - 定义在 connect 之前
  const handleMessage = useCallback(
    (data: WebSocketMessage) => {
      switch (data.type) {
        case 'screenshot':
          if (data.data) {
            setScreenshot(`data:image/png;base64,${data.data}`)
          }
          break

        case 'state':
          if (data.tool) setTool(data.tool)
          if (data.layer) setLayer(data.layer)
          if (data.cursor) setCursor(data.cursor.x, data.cursor.y)
          if (data.zoom) setZoom(data.zoom)
          break

        case 'error':
          addError(data.message ?? 'Unknown error')
          addLog({
            id: Date.now().toString(),
            timestamp: new Date(),
            level: 'error',
            message: data.message ?? 'Unknown error',
          })
          break

        case 'pong':
          // 心跳响应
          break

        default:
          console.log('Unknown message type:', data.type)
      }
    },
    [setScreenshot, setTool, setLayer, setCursor, setZoom, addError, addLog]
  )

  // 发送消息
  const send = useCallback((message: SendMessage) => {
    if (usePolling) {
      // 轮询模式下通过 HTTP 发送
      return
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [usePolling])

  const connect = useCallback(() => {
    // 如果使用轮询模式，直接启动轮询
    if (usePolling) {
      startPolling()
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setStoreConnected(true)
        reconnectAttemptsRef.current = 0
        addLog({
          id: Date.now().toString(),
          timestamp: new Date(),
          level: 'success',
          message: '已连接到 KiCad 控制服务 (WebSocket)',
        })

        // 发送心跳
        ws.send(JSON.stringify({ type: 'ping' }))
      }

      ws.onclose = () => {
        setConnected(false)
        setStoreConnected(false)
        
        // 如果尝试次数超过限制，切换到轮询模式
        if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          setUsePolling(true)
          startPolling()
          addLog({
            id: Date.now().toString(),
            timestamp: new Date(),
            level: 'warning',
            message: 'WebSocket 连接失败，已切换到 HTTP 轮询模式',
          })
          return
        }

        reconnectAttemptsRef.current++
        addLog({
          id: Date.now().toString(),
          timestamp: new Date(),
          level: 'warning',
          message: `与 KiCad 控制服务断开连接，尝试重连 (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`,
        })

        // 自动重连
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, RECONNECT_INTERVAL)
      }

      ws.onerror = () => {
        addLog({
          id: Date.now().toString(),
          timestamp: new Date(),
          level: 'error',
          message: 'WebSocket 连接错误',
        })
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage
          handleMessage(data)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      // 如果 WebSocket 初始化失败，切换到轮询
      setUsePolling(true)
      startPolling()
    }
  }, [addLog, handleMessage, startPolling, usePolling])

  const disconnect = useCallback(() => {
    if (usePolling) {
      stopPolling()
      return
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
    setStoreConnected(false)
  }, [stopPolling, usePolling, setStoreConnected])

  const sendMouse = useCallback(
    async (event: string, x: number, y: number) => {
      if (usePolling) {
        // 轮询模式下通过 HTTP API 发送
        try {
          await kicadApi.sendMouseAction({ action: event as 'click' | 'move' | 'drag', x, y })
        } catch (error) {
          console.error('Failed to send mouse action:', error)
        }
        return
      }
      send({ type: 'mouse', event, x, y })
    },
    [send, usePolling]
  )

  const sendKeyboard = useCallback(
    async (keys: string[]) => {
      if (usePolling) {
        // 轮询模式下通过 HTTP API 发送
        try {
          await kicadApi.sendKeyboardAction({ keys })
        } catch (error) {
          console.error('Failed to send keyboard action:', error)
        }
        return
      }
      send({ type: 'keyboard', keys })
    },
    [send, usePolling]
  )

  const sendCommand = useCallback(
    (command: { type: string; [key: string]: unknown }) => {
      send({ type: 'command', command })
    },
    [send]
  )

  // 组件挂载时自动连接
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    connected,
    connect,
    disconnect,
    send,
    sendMouse,
    sendKeyboard,
    sendCommand,
    usePolling,
  }
}

export default useWebSocket
