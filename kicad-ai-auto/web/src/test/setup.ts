import '@testing-library/jest-dom'
import { vi, afterEach } from 'vitest'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.OPEN
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor(_url: string) {
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 0)
  }

  send(_data: string) {
    // Mock send
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  }
}

// @ts-expect-error - Mocking WebSocket for tests
global.WebSocket = MockWebSocket

// Mock import.meta.env
vi.mock('import.meta', () => ({
  env: {
    VITE_API_URL: 'http://localhost:8000',
    VITE_WS_URL: 'ws://localhost:8000/ws/control',
  },
}))

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks()
})
