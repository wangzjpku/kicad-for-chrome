import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import { projectApi, pcbApi, drcApi, exportApi } from '../services/api'

// Mock axios
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn(),
      },
    },
  }
  return {
    default: mockAxios,
  }
})

// Import axios after mocking
const axios = (await import('axios')).default as unknown as {
  get: Mock
  post: Mock
  put: Mock
  delete: Mock
}
const mockAxios = axios

describe('API Service Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Project API', () => {
    it('should list projects', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: {
            total: 2,
            items: [
              { id: '1', name: 'Project 1', description: 'Test project 1' },
              { id: '2', name: 'Project 2', description: 'Test project 2' },
            ]
          }
        } 
      }
      mockAxios.get.mockResolvedValueOnce(mockResponse)

      const result = await projectApi.listProjects()

      expect(mockAxios.get).toHaveBeenCalledWith('/projects')
      expect(result.success).toBe(true)
      expect(result.data?.items).toHaveLength(2)
    })

    it('should create project', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { id: 'new-id', name: 'New Project', description: 'Description' }
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await projectApi.createProject({ name: 'New Project', description: 'Description' })

      expect(mockAxios.post).toHaveBeenCalledWith('/projects', { name: 'New Project', description: 'Description' })
      expect(result.success).toBe(true)
      expect(result.data?.name).toBe('New Project')
    })

    it('should get project', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { id: '1', name: 'Project 1', description: 'Test' }
        } 
      }
      mockAxios.get.mockResolvedValueOnce(mockResponse)

      const result = await projectApi.getProject('1')

      expect(mockAxios.get).toHaveBeenCalledWith('/projects/1')
      expect(result.success).toBe(true)
    })

    it('should update project', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { id: '1', name: 'Updated Project', description: 'Updated' }
        } 
      }
      mockAxios.put.mockResolvedValueOnce(mockResponse)

      const result = await projectApi.updateProject('1', { name: 'Updated Project' })

      expect(mockAxios.put).toHaveBeenCalledWith('/projects/1', { name: 'Updated Project' })
      expect(result.success).toBe(true)
    })

    it('should delete project', async () => {
      const mockResponse = { data: { success: true } }
      mockAxios.delete.mockResolvedValueOnce(mockResponse)

      const result = await projectApi.deleteProject('1')

      expect(mockAxios.delete).toHaveBeenCalledWith('/projects/1')
      expect(result.success).toBe(true)
    })
  })

  describe('PCB API', () => {
    it('should get PCB data', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { 
            id: 'pcb-1', 
            footprints: [], 
            tracks: [], 
            vias: [] 
          }
        } 
      }
      mockAxios.get.mockResolvedValueOnce(mockResponse)

      const result = await pcbApi.getPCB('project-1')

      expect(mockAxios.get).toHaveBeenCalledWith('/projects/project-1/pcb/design')
      expect(result.success).toBe(true)
    })

    it('should save PCB data', async () => {
      const pcbData = { 
        id: 'pcb-1', 
        footprints: [], 
        tracks: [], 
        vias: [] 
      }
      const mockResponse = { 
        data: { 
          success: true, 
          message: 'PCB saved'
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await pcbApi.savePCB('project-1', pcbData)

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/pcb/design', pcbData)
      expect(result.success).toBe(true)
    })

    it('should get PCB items', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: []
        } 
      }
      mockAxios.get.mockResolvedValueOnce(mockResponse)

      const result = await pcbApi.getPCBItems('project-1')

      expect(mockAxios.get).toHaveBeenCalledWith('/projects/project-1/pcb/items')
      expect(result.success).toBe(true)
    })

    it('should create footprint', async () => {
      const footprint = { id: 'fp-1', type: 'footprint', reference: 'R1' }
      const mockResponse = { 
        data: { 
          success: true, 
          data: footprint
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await pcbApi.createFootprint('project-1', footprint)

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/pcb/items/footprint', footprint)
      expect(result.success).toBe(true)
    })
  })

  describe('DRC API', () => {
    it('should run DRC', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: {
            errorCount: 0,
            warningCount: 0,
            errors: [],
            warnings: []
          }
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await drcApi.runDRC('project-1')

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/drc/run', {})
      expect(result.success).toBe(true)
    })

    it('should get DRC report', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: {
            errorCount: 0,
            warningCount: 0,
            errors: [],
            warnings: []
          }
        } 
      }
      mockAxios.get.mockResolvedValueOnce(mockResponse)

      const result = await drcApi.getDRCReport('project-1')

      expect(mockAxios.get).toHaveBeenCalledWith('/projects/project-1/drc/report')
      expect(result.success).toBe(true)
    })
  })

  describe('Export API', () => {
    it('should export Gerber', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { exportPath: '/output/gerber', files: [] }
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await exportApi.exportGerber('project-1')

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/export/gerber')
      expect(result.success).toBe(true)
    })

    it('should export Drill', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { exportPath: '/output/drill.drl' }
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await exportApi.exportDrill('project-1')

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/export/drill')
      expect(result.success).toBe(true)
    })

    it('should export BOM', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { exportPath: '/output/bom.csv' }
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await exportApi.exportBOM('project-1')

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/export/bom')
      expect(result.success).toBe(true)
    })

    it('should export STEP', async () => {
      const mockResponse = { 
        data: { 
          success: true, 
          data: { exportPath: '/output/pcb.step' }
        } 
      }
      mockAxios.post.mockResolvedValueOnce(mockResponse)

      const result = await exportApi.exportSTEP('project-1')

      expect(mockAxios.post).toHaveBeenCalledWith('/projects/project-1/export/step')
      expect(result.success).toBe(true)
    })
  })
})
