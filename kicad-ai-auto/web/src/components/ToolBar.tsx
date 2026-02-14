import { useKiCadStore } from '../stores/kicadStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { kicadApi } from '../services/api'

interface ToolButton {
  id: string
  label: string
  icon: string
  hotkey?: string
}

interface ToolBarProps {
  dataTestId?: string
}

export default function ToolBar({ dataTestId }: ToolBarProps) {
  const { currentTool, setTool, addLog, addError, clearErrors } = useKiCadStore()
  const { sendCommand } = useWebSocket()

  const tools: ToolButton[] = [
    { id: 'select', label: '选择', icon: '↖', hotkey: 'Esc' },
    { id: 'move', label: '移动', icon: '✥', hotkey: 'M' },
    { id: 'route', label: '布线', icon: '∿', hotkey: 'X' },
    { id: 'place_symbol', label: '放置符号', icon: '□', hotkey: 'A' },
    { id: 'place_footprint', label: '放置封装', icon: '◈', hotkey: 'P' },
    { id: 'draw_wire', label: '绘制导线', icon: '/', hotkey: 'W' },
    { id: 'add_via', label: '添加过孔', icon: '⊕', hotkey: 'V' },
  ]

  const handleToolClick = async (toolId: string) => {
    setTool(toolId)
    sendCommand({ type: 'tool', tool: toolId })
    
    try {
      await kicadApi.activateTool(toolId)
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'info',
        message: `激活工具: ${toolId}`,
      })
    } catch (error) {
      console.error('激活工具失败:', error)
    }
  }

  // 文件操作
  const handleNew = async () => {
    try {
      await kicadApi.startKiCad()
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'success',
        message: 'KiCad 已启动',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '启动失败'
      addError(message)
    }
  }

  const handleSave = async () => {
    try {
      await kicadApi.saveProject()
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'success',
        message: '项目已保存',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '保存失败'
      addError(message)
    }
  }

  // 编辑操作
  const handleUndo = async () => {
    try {
      await kicadApi.sendKeyboardAction({ keys: ['ctrl', 'z'] })
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'info',
        message: '撤销',
      })
    } catch (error) {
      console.error('撤销失败:', error)
    }
  }

  const handleRedo = async () => {
    try {
      await kicadApi.sendKeyboardAction({ keys: ['ctrl', 'y'] })
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'info',
        message: '重做',
      })
    } catch (error) {
      console.error('重做失败:', error)
    }
  }

  // 视图操作
  const handleZoomIn = async () => {
    try {
      await kicadApi.sendKeyboardAction({ keys: ['ctrl', 'plus'] })
    } catch (error) {
      console.error('缩放失败:', error)
    }
  }

  const handleZoomOut = async () => {
    try {
      await kicadApi.sendKeyboardAction({ keys: ['ctrl', 'minus'] })
    } catch (error) {
      console.error('缩放失败:', error)
    }
  }

  const handleZoomFit = async () => {
    try {
      await kicadApi.sendKeyboardAction({ keys: ['ctrl', 'home'] })
    } catch (error) {
      console.error('缩放失败:', error)
    }
  }

  // DRC/ERC
  const handleDRC = async () => {
    clearErrors()
    try {
      await kicadApi.runDRC()
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'success',
        message: 'DRC 检查完成',
      })
      
      const report = await kicadApi.getDRCReport()
      if (report.error_count > 0) {
        addError(`DRC 发现 ${report.error_count} 个错误`)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'DRC 检查失败'
      addError(message)
    }
  }

  const handleERC = async () => {
    clearErrors()
    try {
      // ERC 通过菜单调用
      await kicadApi.clickMenu('tools', 'erc')
      addLog({
        id: Date.now().toString(),
        timestamp: new Date(),
        level: 'success',
        message: 'ERC 检查已启动',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'ERC 检查失败'
      addError(message)
    }
  }

  // 导出
  const handleExportGerber = async () => {
    try {
      const result = await kicadApi.export('gerber', '/output/gerber')
      if (result.success) {
        addLog({
          id: Date.now().toString(),
          timestamp: new Date(),
          level: 'success',
          message: `Gerber 导出成功: ${result.files?.length || 0} 个文件`,
        })
      } else {
        throw new Error(result.error || '导出失败')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '导出 Gerber 失败'
      addError(message)
    }
  }

  const handleExportBOM = async () => {
    try {
      const result = await kicadApi.export('bom', '/output')
      if (result.success) {
        addLog({
          id: Date.now().toString(),
          timestamp: new Date(),
          level: 'success',
          message: 'BOM 导出成功',
        })
      } else {
        throw new Error(result.error || '导出失败')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '导出 BOM 失败'
      addError(message)
    }
  }

  return (
    <div className="toolbar" data-testid={dataTestId || 'toolbar'}>
      {/* 文件操作 */}
      <div className="flex items-center gap-1 pr-2 border-r border-gray-700">
        <button
          className="toolbar-button"
          title="新建"
          onClick={handleNew}
          data-testid="btn-new"
        >
          📄
        </button>
        <button
          className="toolbar-button"
          title="保存 (Ctrl+S)"
          onClick={handleSave}
          data-testid="btn-save"
        >
          💾
        </button>
      </div>

      {/* 编辑操作 */}
      <div className="flex items-center gap-1 px-2 border-r border-gray-700">
        <button
          className="toolbar-button"
          title="撤销 (Ctrl+Z)"
          onClick={handleUndo}
          data-testid="btn-undo"
        >
          ↩
        </button>
        <button
          className="toolbar-button"
          title="重做 (Ctrl+Y)"
          onClick={handleRedo}
          data-testid="btn-redo"
        >
          ↪
        </button>
      </div>

      {/* 工具选择 */}
      <div className="flex items-center gap-1 px-2 border-r border-gray-700">
        {tools.map((tool) => (
          <button
            key={tool.id}
            className={`toolbar-button ${currentTool === tool.id ? 'active' : ''}`}
            title={`${tool.label} (${tool.hotkey})`}
            onClick={() => handleToolClick(tool.id)}
            data-testid={`tool-${tool.id}`}
            data-action="activate-tool"
            data-target={tool.id}
          >
            {tool.icon}
          </button>
        ))}
      </div>

      {/* 视图控制 */}
      <div className="flex items-center gap-1 px-2 border-r border-gray-700">
        <button
          className="toolbar-button"
          title="放大"
          onClick={handleZoomIn}
          data-testid="btn-zoom-in"
        >
          🔍+
        </button>
        <button
          className="toolbar-button"
          title="缩小"
          onClick={handleZoomOut}
          data-testid="btn-zoom-out"
        >
          🔍-
        </button>
        <button
          className="toolbar-button"
          title="适应窗口"
          onClick={handleZoomFit}
          data-testid="btn-zoom-fit"
        >
          ⊞
        </button>
      </div>

      {/* 检查工具 */}
      <div className="flex items-center gap-1 px-2 border-r border-gray-700">
        <button
          className="toolbar-button"
          title="运行 DRC (Ctrl+D)"
          onClick={handleDRC}
          data-testid="btn-drc"
        >
          ✓ DRC
        </button>
        <button
          className="toolbar-button"
          title="运行 ERC"
          onClick={handleERC}
          data-testid="btn-erc"
        >
          ✓ ERC
        </button>
      </div>

      {/* 右侧操作 */}
      <div className="flex-1" />

      <div className="flex items-center gap-1 px-2">
        <button
          className="toolbar-button"
          title="导出 Gerber"
          onClick={handleExportGerber}
          data-testid="btn-export-gerber"
        >
          📤 Gerber
        </button>
        <button
          className="toolbar-button"
          title="导出 BOM"
          onClick={handleExportBOM}
          data-testid="btn-export-bom"
        >
          📤 BOM
        </button>
      </div>
    </div>
  )
}
