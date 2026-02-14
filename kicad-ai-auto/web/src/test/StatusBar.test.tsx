import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StatusBar from '../components/StatusBar'
import { useKiCadStore } from '../stores/kicadStore'

describe('StatusBar', () => {
  beforeEach(() => {
    // Reset store state
    useKiCadStore.setState({
      cursorX: 0,
      cursorY: 0,
      currentLayer: 'F.Cu',
      zoom: 100,
      connected: false,
      errors: [],
    })
  })

  it('should render the status bar', () => {
    render(<StatusBar />)
    expect(screen.getByTestId('statusbar')).toBeInTheDocument()
  })

  it('should display cursor coordinates', () => {
    useKiCadStore.setState({ cursorX: 123.456, cursorY: 789.012 })
    render(<StatusBar />)
    
    const coords = screen.getByTestId('status-coords')
    expect(coords).toHaveTextContent('X:')
    expect(coords).toHaveTextContent('123.456')
    expect(coords).toHaveTextContent('Y:')
    expect(coords).toHaveTextContent('789.012')
  })

  it('should display current layer', () => {
    useKiCadStore.setState({ currentLayer: 'B.Cu' })
    render(<StatusBar />)
    
    const layer = screen.getByTestId('status-layer')
    expect(layer).toHaveTextContent('B.Cu')
  })

  it('should display zoom level', () => {
    useKiCadStore.setState({ zoom: 150 })
    render(<StatusBar />)
    
    const zoom = screen.getByTestId('status-zoom')
    expect(zoom).toHaveTextContent('150%')
  })

  it('should show disconnected status', () => {
    useKiCadStore.setState({ connected: false })
    render(<StatusBar />)
    
    const connection = screen.getByTestId('status-connection')
    expect(connection).toHaveTextContent('未连接')
    expect(connection).toHaveClass('text-red-400')
  })

  it('should show connected status', () => {
    useKiCadStore.setState({ connected: true })
    render(<StatusBar />)
    
    const connection = screen.getByTestId('status-connection')
    expect(connection).toHaveTextContent('已连接')
    expect(connection).toHaveClass('text-green-400')
  })

  it('should display error count when errors exist', () => {
    useKiCadStore.setState({ errors: ['Error 1', 'Error 2'] })
    render(<StatusBar />)
    
    const errors = screen.getByTestId('status-errors')
    expect(errors).toHaveTextContent('2 个错误')
    expect(errors).toHaveClass('text-red-400')
  })

  it('should not display errors when no errors exist', () => {
    useKiCadStore.setState({ errors: [] })
    render(<StatusBar />)
    
    expect(screen.queryByTestId('status-errors')).not.toBeInTheDocument()
  })

  it('should display version information', () => {
    render(<StatusBar />)
    
    const version = screen.getByTestId('status-version')
    expect(version).toHaveTextContent('KiCad AI Auto v1.0.0')
  })

  it('should format coordinates with 3 decimal places', () => {
    useKiCadStore.setState({ cursorX: 100, cursorY: 200 })
    render(<StatusBar />)
    
    const coords = screen.getByTestId('status-coords')
    expect(coords).toHaveTextContent('100.000')
    expect(coords).toHaveTextContent('200.000')
  })

  it('should handle zero coordinates', () => {
    useKiCadStore.setState({ cursorX: 0, cursorY: 0 })
    render(<StatusBar />)
    
    const coords = screen.getByTestId('status-coords')
    expect(coords).toHaveTextContent('0.000')
  })

  it('should handle negative coordinates', () => {
    useKiCadStore.setState({ cursorX: -50.5, cursorY: -100.25 })
    render(<StatusBar />)
    
    const coords = screen.getByTestId('status-coords')
    expect(coords).toHaveTextContent('-50.500')
    expect(coords).toHaveTextContent('-100.250')
  })

  it('should update when store state changes', () => {
    const { rerender } = render(<StatusBar />)
    
    useKiCadStore.setState({ cursorX: 100, cursorY: 200 })
    rerender(<StatusBar />)
    
    const coords = screen.getByTestId('status-coords')
    expect(coords).toHaveTextContent('100.000')
  })

  it('should show multiple errors correctly', () => {
    useKiCadStore.setState({ 
      errors: ['Error 1', 'Error 2', 'Error 3', 'Error 4', 'Error 5']
    })
    render(<StatusBar />)
    
    const errors = screen.getByTestId('status-errors')
    expect(errors).toHaveTextContent('5 个错误')
  })

  it('should render all status items with correct structure', () => {
    useKiCadStore.setState({
      cursorX: 100,
      cursorY: 200,
      currentLayer: 'F.SilkS',
      zoom: 200,
      connected: true,
      errors: ['Test error'],
    })
    
    render(<StatusBar />)
    
    expect(screen.getByTestId('status-coords')).toBeInTheDocument()
    expect(screen.getByTestId('status-layer')).toBeInTheDocument()
    expect(screen.getByTestId('status-zoom')).toBeInTheDocument()
    expect(screen.getByTestId('status-connection')).toBeInTheDocument()
    expect(screen.getByTestId('status-errors')).toBeInTheDocument()
    expect(screen.getByTestId('status-version')).toBeInTheDocument()
  })
})
