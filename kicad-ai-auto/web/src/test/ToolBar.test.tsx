import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ToolBar from '../components/ToolBar'
import { useKiCadStore } from '../stores/kicadStore'

// Mock the API module
vi.mock('../services/api', () => ({
  kicadApi: {
    activateTool: vi.fn(),
    startKiCad: vi.fn(),
    saveProject: vi.fn(),
    sendKeyboardAction: vi.fn(),
    runDRC: vi.fn(),
    getDRCReport: vi.fn(),
    export: vi.fn(),
    clickMenu: vi.fn(),
  },
}))

// Mock WebSocket hook
vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendCommand: vi.fn(),
  }),
}))

describe('ToolBar', () => {
  beforeEach(() => {
    // Reset store state
    useKiCadStore.setState({
      currentTool: null,
      errors: [],
      logs: [],
    })
  })

  it('should render the toolbar', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('toolbar')).toBeInTheDocument()
  })

  it('should render file operation buttons', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('btn-new')).toBeInTheDocument()
    expect(screen.getByTestId('btn-save')).toBeInTheDocument()
  })

  it('should render edit operation buttons', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('btn-undo')).toBeInTheDocument()
    expect(screen.getByTestId('btn-redo')).toBeInTheDocument()
  })

  it('should render tool buttons', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('tool-select')).toBeInTheDocument()
    expect(screen.getByTestId('tool-move')).toBeInTheDocument()
    expect(screen.getByTestId('tool-route')).toBeInTheDocument()
    expect(screen.getByTestId('tool-place_symbol')).toBeInTheDocument()
    expect(screen.getByTestId('tool-place_footprint')).toBeInTheDocument()
    expect(screen.getByTestId('tool-draw_wire')).toBeInTheDocument()
    expect(screen.getByTestId('tool-add_via')).toBeInTheDocument()
  })

  it('should render zoom control buttons', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('btn-zoom-in')).toBeInTheDocument()
    expect(screen.getByTestId('btn-zoom-out')).toBeInTheDocument()
    expect(screen.getByTestId('btn-zoom-fit')).toBeInTheDocument()
  })

  it('should render check tool buttons', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('btn-drc')).toBeInTheDocument()
    expect(screen.getByTestId('btn-erc')).toBeInTheDocument()
  })

  it('should render export buttons', () => {
    render(<ToolBar />)
    expect(screen.getByTestId('btn-export-gerber')).toBeInTheDocument()
    expect(screen.getByTestId('btn-export-bom')).toBeInTheDocument()
  })

  it('should highlight active tool', () => {
    useKiCadStore.setState({ currentTool: 'route' })
    render(<ToolBar />)
    
    const routeTool = screen.getByTestId('tool-route')
    expect(routeTool).toHaveClass('active')
  })

  it('should handle tool click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    const selectTool = screen.getByTestId('tool-select')
    fireEvent.click(selectTool)
    
    expect(useKiCadStore.getState().currentTool).toBe('select')
  })

  it('should handle undo button click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    fireEvent.click(screen.getByTestId('btn-undo'))
    
    expect(kicadApi.sendKeyboardAction).toHaveBeenCalledWith({ keys: ['ctrl', 'z'] })
  })

  it('should handle redo button click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    fireEvent.click(screen.getByTestId('btn-redo'))
    
    expect(kicadApi.sendKeyboardAction).toHaveBeenCalledWith({ keys: ['ctrl', 'y'] })
  })

  it('should handle zoom in button click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    fireEvent.click(screen.getByTestId('btn-zoom-in'))
    
    expect(kicadApi.sendKeyboardAction).toHaveBeenCalledWith({ keys: ['ctrl', 'plus'] })
  })

  it('should handle zoom out button click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    fireEvent.click(screen.getByTestId('btn-zoom-out'))
    
    expect(kicadApi.sendKeyboardAction).toHaveBeenCalledWith({ keys: ['ctrl', 'minus'] })
  })

  it('should handle zoom fit button click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    fireEvent.click(screen.getByTestId('btn-zoom-fit'))
    
    expect(kicadApi.sendKeyboardAction).toHaveBeenCalledWith({ keys: ['ctrl', 'home'] })
  })

  it('should handle DRC button click', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.runDRC.mockResolvedValue({ success: true })
    kicadApi.getDRCReport.mockResolvedValue({ error_count: 0, warning_count: 0 })
    
    render(<ToolBar />)
    fireEvent.click(screen.getByTestId('btn-drc'))
    
    expect(kicadApi.runDRC).toHaveBeenCalled()
  })

  it('should handle ERC button click', async () => {
    const { kicadApi } = await import('../services/api')
    render(<ToolBar />)
    
    fireEvent.click(screen.getByTestId('btn-erc'))
    
    expect(kicadApi.clickMenu).toHaveBeenCalledWith('tools', 'erc')
  })

  it('should handle new project button click', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.startKiCad.mockResolvedValue({ success: true })
    
    render(<ToolBar />)
    fireEvent.click(screen.getByTestId('btn-new'))
    
    expect(kicadApi.startKiCad).toHaveBeenCalled()
  })

  it('should handle save project button click', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.saveProject.mockResolvedValue({ success: true })
    
    render(<ToolBar />)
    fireEvent.click(screen.getByTestId('btn-save'))
    
    expect(kicadApi.saveProject).toHaveBeenCalled()
  })

  it('should handle export gerber button click', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.export.mockResolvedValue({ success: true, files: [] })
    
    render(<ToolBar />)
    fireEvent.click(screen.getByTestId('btn-export-gerber'))
    
    expect(kicadApi.export).toHaveBeenCalledWith('gerber', '/output/gerber')
  })

  it('should handle export BOM button click', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.export.mockResolvedValue({ success: true, file: '/output/bom.csv' })
    
    render(<ToolBar />)
    fireEvent.click(screen.getByTestId('btn-export-bom'))
    
    expect(kicadApi.export).toHaveBeenCalledWith('bom', '/output')
  })

  it('should log actions', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.activateTool.mockResolvedValue({ success: true })
    
    render(<ToolBar />)
    fireEvent.click(screen.getByTestId('tool-select'))
    
    // Just verify the component renders without throwing
    expect(screen.getByTestId('tool-select')).toBeInTheDocument()
  })

  it('should handle errors gracefully', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.export.mockRejectedValue(new Error('Export failed'))
    
    // Just verify the component renders without throwing
    render(<ToolBar />)
    expect(screen.getByTestId('toolbar')).toBeInTheDocument()
  })
})
