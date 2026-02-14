import { describe, it, expect, beforeEach } from 'vitest'
import { act } from '@testing-library/react'
import { useKiCadStore } from '../stores/kicadStore'

describe('KiCad Store', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    act(() => {
      useKiCadStore.setState({
        connected: false,
        projectPath: null,
        projectName: null,
        currentTool: null,
        currentLayer: 'F.Cu',
        cursorX: 0,
        cursorY: 0,
        zoom: 100,
        screenshotUrl: null,
        errors: [],
        logs: [],
        theme: 'dark',
        activeOutputTab: 'logs',
      })
    })
  })

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useKiCadStore.getState()

      expect(state.connected).toBe(false)
      expect(state.projectPath).toBeNull()
      expect(state.projectName).toBeNull()
      expect(state.currentTool).toBeNull()
      expect(state.currentLayer).toBe('F.Cu')
      expect(state.cursorX).toBe(0)
      expect(state.cursorY).toBe(0)
      expect(state.zoom).toBe(100)
      expect(state.screenshotUrl).toBeNull()
      expect(state.errors).toEqual([])
      expect(state.logs).toEqual([])
      expect(state.theme).toBe('dark')
      expect(state.activeOutputTab).toBe('logs')
    })
  })

  describe('Connection Actions', () => {
    it('should set connected to true', () => {
      act(() => {
        useKiCadStore.getState().setConnected(true)
      })

      expect(useKiCadStore.getState().connected).toBe(true)
    })

    it('should set connected to false', () => {
      act(() => {
        useKiCadStore.getState().setConnected(true)
        useKiCadStore.getState().setConnected(false)
      })

      expect(useKiCadStore.getState().connected).toBe(false)
    })
  })

  describe('Project Actions', () => {
    it('should set project path and name', () => {
      act(() => {
        useKiCadStore.getState().setProject('/projects/test.kicad_pro', 'test')
      })

      const state = useKiCadStore.getState()
      expect(state.projectPath).toBe('/projects/test.kicad_pro')
      expect(state.projectName).toBe('test')
    })
  })

  describe('Tool Actions', () => {
    it('should set current tool', () => {
      act(() => {
        useKiCadStore.getState().setTool('route')
      })

      expect(useKiCadStore.getState().currentTool).toBe('route')
    })

    it('should set layer', () => {
      act(() => {
        useKiCadStore.getState().setLayer('B.Cu')
      })

      expect(useKiCadStore.getState().currentLayer).toBe('B.Cu')
    })
  })

  describe('Cursor Actions', () => {
    it('should set cursor position', () => {
      act(() => {
        useKiCadStore.getState().setCursor(100, 200)
      })

      const state = useKiCadStore.getState()
      expect(state.cursorX).toBe(100)
      expect(state.cursorY).toBe(200)
    })

    it('should update cursor position independently', () => {
      act(() => {
        useKiCadStore.getState().setCursor(50, 75)
        useKiCadStore.getState().setCursor(150, 250)
      })

      const state = useKiCadStore.getState()
      expect(state.cursorX).toBe(150)
      expect(state.cursorY).toBe(250)
    })
  })

  describe('Zoom Actions', () => {
    it('should set zoom level', () => {
      act(() => {
        useKiCadStore.getState().setZoom(200)
      })

      expect(useKiCadStore.getState().zoom).toBe(200)
    })
  })

  describe('Screenshot Actions', () => {
    it('should set screenshot URL', () => {
      const testUrl = 'data:image/png;base64,testdata'

      act(() => {
        useKiCadStore.getState().setScreenshot(testUrl)
      })

      expect(useKiCadStore.getState().screenshotUrl).toBe(testUrl)
    })
  })

  describe('Error Actions', () => {
    it('should add error', () => {
      act(() => {
        useKiCadStore.getState().addError('Test error 1')
      })

      expect(useKiCadStore.getState().errors).toContain('Test error 1')
    })

    it('should accumulate multiple errors', () => {
      act(() => {
        useKiCadStore.getState().addError('Error 1')
        useKiCadStore.getState().addError('Error 2')
        useKiCadStore.getState().addError('Error 3')
      })

      const errors = useKiCadStore.getState().errors
      expect(errors).toHaveLength(3)
      expect(errors).toContain('Error 1')
      expect(errors).toContain('Error 2')
      expect(errors).toContain('Error 3')
    })

    it('should clear all errors', () => {
      act(() => {
        useKiCadStore.getState().addError('Error 1')
        useKiCadStore.getState().addError('Error 2')
        useKiCadStore.getState().clearErrors()
      })

      expect(useKiCadStore.getState().errors).toEqual([])
    })
  })

  describe('Log Actions', () => {
    it('should add log entry', () => {
      const logEntry = {
        id: '1',
        timestamp: new Date(),
        level: 'info' as const,
        message: 'Test log message',
      }

      act(() => {
        useKiCadStore.getState().addLog(logEntry)
      })

      const logs = useKiCadStore.getState().logs
      expect(logs).toHaveLength(1)
      expect(logs[0]).toEqual(logEntry)
    })

    it('should add multiple log entries in order', () => {
      act(() => {
        useKiCadStore.getState().addLog({
          id: '1',
          timestamp: new Date('2024-01-01T10:00:00'),
          level: 'info',
          message: 'First log',
        })
        useKiCadStore.getState().addLog({
          id: '2',
          timestamp: new Date('2024-01-01T10:00:01'),
          level: 'success',
          message: 'Second log',
        })
      })

      const logs = useKiCadStore.getState().logs
      expect(logs).toHaveLength(2)
      expect(logs[0].message).toBe('First log')
      expect(logs[1].message).toBe('Second log')
    })

    it('should limit logs to 1000 entries', () => {
      act(() => {
        // Add 1005 log entries
        for (let i = 0; i < 1005; i++) {
          useKiCadStore.getState().addLog({
            id: `log-${i}`,
            timestamp: new Date(),
            level: 'info',
            message: `Log message ${i}`,
          })
        }
      })

      const logs = useKiCadStore.getState().logs
      expect(logs.length).toBe(1000)
      // Should keep the most recent ones
      expect(logs[0].message).toBe('Log message 5')
      expect(logs[999].message).toBe('Log message 1004')
    })
  })

  describe('UI Actions', () => {
    it('should set theme to light', () => {
      act(() => {
        useKiCadStore.getState().setTheme('light')
      })

      expect(useKiCadStore.getState().theme).toBe('light')
    })

    it('should set theme to dark', () => {
      act(() => {
        useKiCadStore.getState().setTheme('dark')
      })

      expect(useKiCadStore.getState().theme).toBe('dark')
    })

    it('should set active output tab', () => {
      act(() => {
        useKiCadStore.getState().setActiveOutputTab('errors')
      })

      expect(useKiCadStore.getState().activeOutputTab).toBe('errors')
    })
  })

  describe('Complex Scenarios', () => {
    it('should handle full workflow state changes', () => {
      act(() => {
        const store = useKiCadStore.getState()

        // Connect
        store.setConnected(true)

        // Open project
        store.setProject('/projects/myproject.kicad_pro', 'myproject')

        // Change tool and layer
        store.setTool('route')
        store.setLayer('F.Cu')

        // Move cursor
        store.setCursor(500, 300)

        // Zoom
        store.setZoom(150)

        // Add some logs
        store.addLog({
          id: '1',
          timestamp: new Date(),
          level: 'info',
          message: 'Project opened',
        })
      })

      const state = useKiCadStore.getState()
      expect(state.connected).toBe(true)
      expect(state.projectName).toBe('myproject')
      expect(state.currentTool).toBe('route')
      expect(state.currentLayer).toBe('F.Cu')
      expect(state.cursorX).toBe(500)
      expect(state.cursorY).toBe(300)
      expect(state.zoom).toBe(150)
      expect(state.logs).toHaveLength(1)
    })
  })
})
