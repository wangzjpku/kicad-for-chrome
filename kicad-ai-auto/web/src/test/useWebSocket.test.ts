import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'

// Mock the store before importing the hook
const mockStoreActions = {
  setScreenshot: vi.fn(),
  setTool: vi.fn(),
  setLayer: vi.fn(),
  setCursor: vi.fn(),
  setZoom: vi.fn(),
  setConnected: vi.fn(),
  addError: vi.fn(),
  addLog: vi.fn(),
}

vi.mock('../stores/kicadStore', () => ({
  useKiCadStore: () => mockStoreActions,
}))

// Import after mocking
import { useWebSocket } from '../hooks/useWebSocket'

describe('useWebSocket Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(result.current.connected).toBe(false)
  })

  it('should have all required methods', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(typeof result.current.connect).toBe('function')
    expect(typeof result.current.send).toBe('function')
    expect(typeof result.current.sendMouse).toBe('function')
    expect(typeof result.current.sendKeyboard).toBe('function')
    expect(typeof result.current.sendCommand).toBe('function')
  })

  it('should have send method that does not throw', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(() => {
      result.current.send({ type: 'test' })
    }).not.toThrow()
  })

  it('should have sendMouse method that does not throw', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(() => {
      result.current.sendMouse('click', 100, 200)
    }).not.toThrow()
  })

  it('should have sendKeyboard method that does not throw', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(() => {
      result.current.sendKeyboard(['Ctrl', 'S'])
    }).not.toThrow()
  })

  it('should have sendCommand method that does not throw', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(() => {
      result.current.sendCommand({ type: 'screenshot' })
    }).not.toThrow()
  })

  it('should return an object with correct structure', () => {
    const { result } = renderHook(() => useWebSocket())

    const hookResult = result.current
    expect(hookResult).toHaveProperty('connected')
    expect(hookResult).toHaveProperty('connect')
    expect(hookResult).toHaveProperty('send')
    expect(hookResult).toHaveProperty('sendMouse')
    expect(hookResult).toHaveProperty('sendKeyboard')
    expect(hookResult).toHaveProperty('sendCommand')
  })
})
