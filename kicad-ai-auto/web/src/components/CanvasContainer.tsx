import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useKiCadStore } from '../stores/kicadStore'
import { useWebSocket } from '../hooks/useWebSocket'

interface CanvasContainerProps {
  dataTestId?: string
}

// 配置常量
const CONFIG = {
  FPS: 5, // 降低到 5 FPS
  INTERVAL: 200, // 200ms 间隔
  KICAD_WIDTH: 1920,
  KICAD_HEIGHT: 1080,
  THROTTLE_DELAY: 50, // 鼠标事件节流延迟
}

export default function CanvasContainer({ dataTestId = 'canvas-container' }: CanvasContainerProps) {
  const { screenshotUrl, screenshotEmpty, connected } = useKiCadStore()
  const { sendMouse, sendKeyboard, sendCommand } = useWebSocket()
  const containerRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [localMousePos, setLocalMousePos] = useState({ x: 0, y: 0 })
  const [isPaused, setIsPaused] = useState(false)
  
  // 使用 ref 来存储节流状态
  const lastMouseMoveTime = useRef(0)
  const mouseMoveTimeout = useRef<NodeJS.Timeout | null>(null)

  // 定期请求截图 - 带节流和暂停功能
  useEffect(() => {
    // 页面可见性改变时的处理
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setIsPaused(true)
      } else {
        setIsPaused(false)
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // 截图请求循环
    const interval = setInterval(() => {
      if (!isPaused && document.visibilityState === 'visible') {
        sendCommand({ type: 'screenshot' })
      }
    }, CONFIG.INTERVAL)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [sendCommand, isPaused])

  // 坐标转换：浏览器坐标 -> KiCad 坐标
  const convertCoords = useCallback(
    (clientX: number, clientY: number) => {
      if (!containerRef.current) return { x: 0, y: 0 }

      const rect = containerRef.current.getBoundingClientRect()
      const x = clientX - rect.left
      const y = clientY - rect.top

      // 根据缩放比例转换
      const kicadX = (x / rect.width) * CONFIG.KICAD_WIDTH
      const kicadY = (y / rect.height) * CONFIG.KICAD_HEIGHT

      return { x: Math.round(kicadX), y: Math.round(kicadY) }
    },
    []
  )
  
  // 节流的鼠标移动处理
  const throttledMouseMove = useCallback(
    (coords: { x: number; y: number }) => {
      const now = Date.now()
      
      // 清除之前的定时器
      if (mouseMoveTimeout.current) {
        clearTimeout(mouseMoveTimeout.current)
      }
      
      // 如果距离上次发送已经超过节流延迟，立即发送
      if (now - lastMouseMoveTime.current >= CONFIG.THROTTLE_DELAY) {
        sendMouse('move', coords.x, coords.y)
        lastMouseMoveTime.current = now
      } else {
        // 否则延迟发送
        mouseMoveTimeout.current = setTimeout(() => {
          sendMouse('move', coords.x, coords.y)
          lastMouseMoveTime.current = Date.now()
        }, CONFIG.THROTTLE_DELAY)
      }
    },
    [sendMouse]
  )

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      const coords = convertCoords(e.clientX, e.clientY)
      setLocalMousePos(coords)

      if (e.button === 0) {
        // 左键
        setIsDragging(true)
        sendMouse('down', coords.x, coords.y)
      }
    },
    [convertCoords, sendMouse]
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const coords = convertCoords(e.clientX, e.clientY)
      setLocalMousePos(coords)

      if (isDragging) {
        throttledMouseMove(coords)
      }
    },
    [convertCoords, isDragging, throttledMouseMove]
  )

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      const coords = convertCoords(e.clientX, e.clientY)

      if (e.button === 0) {
        setIsDragging(false)
        sendMouse('up', coords.x, coords.y)
        
        // 清除任何待处理的鼠标移动
        if (mouseMoveTimeout.current) {
          clearTimeout(mouseMoveTimeout.current)
        }
      }
    },
    [convertCoords, sendMouse]
  )

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      const coords = convertCoords(e.clientX, e.clientY)
      sendMouse('click', coords.x, coords.y)
    },
    [convertCoords, sendMouse]
  )

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      const coords = convertCoords(e.clientX, e.clientY)
      // 发送双击事件（两次点击）
      sendMouse('click', coords.x, coords.y)
      setTimeout(() => {
        sendMouse('click', coords.x, coords.y)
      }, 50)
    },
    [convertCoords, sendMouse]
  )

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      // 可以显示右键菜单
    },
    []
  )

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault()
      // 缩放控制 - 添加节流
      if (e.deltaY < 0) {
        sendKeyboard(['ctrl', '+'])
      } else {
        sendKeyboard(['ctrl', '-'])
      }
    },
    [sendKeyboard]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const keys: string[] = []

      if (e.ctrlKey) keys.push('ctrl')
      if (e.shiftKey) keys.push('shift')
      if (e.altKey) keys.push('alt')

      if (e.key.length === 1) {
        keys.push(e.key.toLowerCase())
      } else {
        keys.push(e.key.toLowerCase())
      }

      if (keys.length > 0) {
        sendKeyboard(keys)
      }
    },
    [sendKeyboard]
  )
  
  // 切换暂停状态
  const togglePause = useCallback(() => {
    setIsPaused(prev => !prev)
  }, [])

  // 计算显示的位置百分比
  const cursorStyle = useMemo(() => ({
    left: `${(localMousePos.x / CONFIG.KICAD_WIDTH) * 100}%`,
    top: `${(localMousePos.y / CONFIG.KICAD_HEIGHT) * 100}%`,
    transform: 'translate(-50%, -50%)',
  }), [localMousePos])

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 bg-black overflow-hidden cursor-crosshair"
      data-testid={dataTestId}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onContextMenu={handleContextMenu}
      onWheel={handleWheel}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* KiCad 截图显示 */}
      {screenshotUrl ? (
        <img
          src={screenshotUrl}
          alt="KiCad Canvas"
          className="w-full h-full object-contain kicad-canvas"
          data-testid="canvas-image"
          draggable={false}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-gray-500">
          <div className="text-center">
            <div className="text-4xl mb-4">🔌</div>
            <div>等待连接...</div>
            <div className="text-sm mt-2 text-gray-600">
              使用 KiCad 9.0+ 需要启用 IPC Server:
              <br />
              Tools → External Plugin → Start Server
            </div>
          </div>
        </div>
      )}

      {/* 光标位置指示器 */}
      <div
        className="absolute pointer-events-none"
        style={cursorStyle}
      >
        <div className="w-4 h-4 border border-green-500 rounded-full opacity-50" />
      </div>

      {/* 坐标显示 */}
      <div
        className="absolute bottom-2 left-2 bg-black/70 px-2 py-1 rounded text-xs font-mono text-green-400"
        data-testid="canvas-coords"
      >
        {localMousePos.x}, {localMousePos.y}
      </div>
      
      {/* 暂停/恢复按钮 */}
      <button
        onClick={togglePause}
        className={`absolute top-2 left-2 px-2 py-1 rounded text-xs transition-colors ${
          isPaused 
            ? 'bg-yellow-600 hover:bg-yellow-700 text-white' 
            : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
        }`}
        title={isPaused ? '点击恢复截图更新' : '点击暂停截图更新'}
      >
        {isPaused ? '▶ 已暂停' : '⏸ 暂停'}
      </button>
      
      {/* FPS 指示器 */}
      <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-1 rounded text-xs font-mono text-gray-400">
        {CONFIG.FPS} FPS
      </div>
      
      {/* 截图状态提示 - 截图空白时显示 */}
      {connected && screenshotEmpty && (
        <div className="absolute top-2 right-2 bg-yellow-600/90 px-3 py-2 rounded text-xs text-white max-w-xs">
          <div className="font-bold mb-1">⚠️ 截图显示异常</div>
          <div>请将 KiCad 窗口置顶显示</div>
          <div className="text-yellow-200 mt-1">Windows 限制：窗口在前端才能正常截图</div>
        </div>
      )}
    </div>
  )
}
