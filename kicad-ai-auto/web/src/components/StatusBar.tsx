import { useKiCadStore } from '../stores/kicadStore'

interface StatusBarProps {
  dataTestId?: string
}

export default function StatusBar({ dataTestId }: StatusBarProps) {
  const { cursorX, cursorY, currentLayer, zoom, connected, errors } = useKiCadStore()

  const formatCoord = (value: number): string => {
    return value.toFixed(3)
  }

  return (
    <div className="status-bar" data-testid={dataTestId || 'statusbar'}>
      {/* 左侧信息 */}
      <div className="flex items-center gap-4">
        {/* 光标坐标 */}
        <div className="status-item" data-testid="status-coords">
          <span className="text-gray-400">X:</span>{' '}
          <span className="font-mono">{formatCoord(cursorX)}</span>
          <span className="text-gray-400 ml-2">Y:</span>{' '}
          <span className="font-mono">{formatCoord(cursorY)}</span>
        </div>

        {/* 当前层 */}
        <div className="status-item" data-testid="status-layer">
          <span className="text-gray-400">层:</span>{' '}
          <span>{currentLayer}</span>
        </div>

        {/* 缩放 */}
        <div className="status-item" data-testid="status-zoom">
          <span className="text-gray-400">缩放:</span>{' '}
          <span className="font-mono">{zoom}%</span>
        </div>
      </div>

      {/* 右侧信息 */}
      <div className="flex items-center gap-4">
        {/* 错误计数 */}
        {errors.length > 0 && (
          <div
            className="status-item text-red-400"
            data-testid="status-errors"
          >
            ⚠ {errors.length} 个错误
          </div>
        )}

        {/* 连接状态 */}
        <div
          className={`status-item ${connected ? 'text-green-400' : 'text-red-400'}`}
          data-testid="status-connection"
        >
          {connected ? '● 已连接' : '○ 未连接'}
        </div>

        {/* 版本信息 */}
        <div className="status-item text-gray-500" data-testid="status-version">
          KiCad AI Auto v1.0.0
        </div>
      </div>
    </div>
  )
}
