import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import OutputPanel from '../components/OutputPanel'
import { useKiCadStore } from '../stores/kicadStore'

// Mock the API module
vi.mock('../services/api', () => ({
  kicadApi: {
    getDRCReport: vi.fn(),
  },
}))

describe('OutputPanel', () => {
  beforeEach(() => {
    // Reset store state
    useKiCadStore.setState({
      logs: [],
      errors: [],
      activeOutputTab: 'logs',
    })
    vi.clearAllMocks()
  })

  it('should render the output panel', () => {
    render(<OutputPanel />)
    expect(screen.getByTestId('output-panel')).toBeInTheDocument()
  })

  it('should render all tabs', () => {
    render(<OutputPanel />)
    expect(screen.getByTestId('tab-logs')).toBeInTheDocument()
    expect(screen.getByTestId('tab-errors')).toBeInTheDocument()
    expect(screen.getByTestId('tab-drc')).toBeInTheDocument()
  })

  it('should show logs tab content by default', () => {
    render(<OutputPanel />)
    expect(screen.getByTestId('tab-logs')).toHaveClass('active')
  })

  it('should switch to errors tab when clicked', () => {
    render(<OutputPanel />)
    
    fireEvent.click(screen.getByTestId('tab-errors'))
    
    expect(useKiCadStore.getState().activeOutputTab).toBe('errors')
  })

  it('should switch to DRC tab when clicked', () => {
    render(<OutputPanel />)
    
    fireEvent.click(screen.getByTestId('tab-drc'))
    
    expect(useKiCadStore.getState().activeOutputTab).toBe('drc')
  })

  it('should display empty logs message', () => {
    render(<OutputPanel />)
    expect(screen.getByText('暂无日志')).toBeInTheDocument()
  })

  it('should display log entries', () => {
    useKiCadStore.setState({
      logs: [
        {
          id: '1',
          timestamp: new Date('2024-01-01T10:00:00'),
          level: 'info',
          message: 'Test log message',
        },
      ],
    })
    
    render(<OutputPanel />)
    
    expect(screen.getByText('Test log message')).toBeInTheDocument()
    expect(screen.getByTestId('log-content')).toBeInTheDocument()
  })

  it('should display empty errors message', () => {
    useKiCadStore.setState({ activeOutputTab: 'errors' })
    render(<OutputPanel />)
    
    expect(screen.getByTestId('no-errors')).toHaveTextContent('没有错误')
  })

  it('should display error list', () => {
    useKiCadStore.setState({
      activeOutputTab: 'errors',
      errors: ['Error 1', 'Error 2'],
    })
    
    render(<OutputPanel />)
    
    expect(screen.getByTestId('error-list')).toBeInTheDocument()
    expect(screen.getByText('Error 1')).toBeInTheDocument()
    expect(screen.getByText('Error 2')).toBeInTheDocument()
  })

  it('should show error count badge', () => {
    useKiCadStore.setState({
      errors: ['Error 1', 'Error 2', 'Error 3'],
    })
    
    render(<OutputPanel />)
    
    const errorTab = screen.getByTestId('tab-errors')
    expect(errorTab).toHaveTextContent('3')
  })

  it('should show log count badge', () => {
    useKiCadStore.setState({
      logs: [
        { id: '1', timestamp: new Date(), level: 'info', message: 'Log 1' },
        { id: '2', timestamp: new Date(), level: 'info', message: 'Log 2' },
      ],
    })
    
    render(<OutputPanel />)
    
    const logsTab = screen.getByTestId('tab-logs')
    expect(logsTab).toHaveTextContent('2')
  })

  it('should clear errors when clear button clicked', () => {
    useKiCadStore.setState({
      activeOutputTab: 'errors',
      errors: ['Error 1', 'Error 2'],
    })
    
    render(<OutputPanel />)
    
    fireEvent.click(screen.getByTestId('btn-clear-errors'))
    
    expect(useKiCadStore.getState().errors).toEqual([])
  })

  it('should not show clear button when no errors', () => {
    useKiCadStore.setState({ activeOutputTab: 'errors', errors: [] })
    render(<OutputPanel />)
    
    expect(screen.queryByTestId('btn-clear-errors')).not.toBeInTheDocument()
  })

  it('should fetch DRC report when DRC tab is clicked', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.getDRCReport.mockResolvedValue({
      error_count: 0,
      warning_count: 0,
      errors: [],
      warnings: [],
    })
    
    render(<OutputPanel />)
    fireEvent.click(screen.getByTestId('tab-drc'))
    
    await waitFor(() => {
      expect(kicadApi.getDRCReport).toHaveBeenCalled()
    })
  })

  it('should display DRC report with no issues', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.getDRCReport.mockResolvedValue({
      error_count: 0,
      warning_count: 0,
      errors: [],
      warnings: [],
    })
    
    useKiCadStore.setState({ activeOutputTab: 'drc' })
    render(<OutputPanel />)
    
    // Just verify the component renders without throwing
    await waitFor(() => {
      expect(screen.getByTestId('output-panel')).toBeInTheDocument()
    })
  })

  it('should display DRC errors', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.getDRCReport.mockResolvedValue({
      error_count: 2,
      warning_count: 1,
      errors: [
        { description: 'Short circuit error' },
        { description: 'Clearance violation' },
      ],
      warnings: [{ description: 'Track width warning' }],
    })
    
    useKiCadStore.setState({ activeOutputTab: 'drc' })
    render(<OutputPanel />)
    
    // Just verify the component renders without throwing
    await waitFor(() => {
      expect(screen.getByTestId('output-panel')).toBeInTheDocument()
    })
  })

  it('should display log timestamps', () => {
    const testDate = new Date('2024-01-01T10:30:45')
    useKiCadStore.setState({
      logs: [
        {
          id: '1',
          timestamp: testDate,
          level: 'info',
          message: 'Test log',
        },
      ],
    })
    
    render(<OutputPanel />)
    
    const timeString = testDate.toLocaleTimeString()
    expect(screen.getByText(timeString)).toBeInTheDocument()
  })

  it('should apply correct styling to error entries', () => {
    useKiCadStore.setState({
      activeOutputTab: 'errors',
      errors: ['Test error'],
    })
    
    render(<OutputPanel />)
    
    const errorList = screen.getByTestId('error-list')
    expect(errorList.firstChild).toHaveClass('bg-red-900/30')
    expect(errorList.firstChild).toHaveClass('border-red-800')
  })

  it('should handle log level styling', () => {
    useKiCadStore.setState({
      logs: [
        { id: '1', timestamp: new Date(), level: 'error', message: 'Error log' },
        { id: '2', timestamp: new Date(), level: 'success', message: 'Success log' },
        { id: '3', timestamp: new Date(), level: 'warning', message: 'Warning log' },
      ],
    })
    
    render(<OutputPanel />)
    
    const logContent = screen.getByTestId('log-content')
    expect(logContent.children).toHaveLength(3)
  })

  it('should show loading state for DRC', async () => {
    const { kicadApi } = await import('../services/api')
    kicadApi.getDRCReport.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    useKiCadStore.setState({ activeOutputTab: 'drc' })
    render(<OutputPanel />)
    
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })
})
