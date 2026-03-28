/**
 * 完整版 Zustand Store
 * 支持完整 PCB 数据管理、历史记录、API 集成
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { PCBData, Footprint, Track, Via, Project } from '../types';
// projectApi 未使用，暂时移除
import { pcbApi, kicadIpcApi, FullPCBData } from '../services/api';

export type ToolType = 'select' | 'move' | 'route' | 'place_footprint' | 'place_via' | 'rotate' | 'mirror' | 'place_zone' | 'place_text';

interface HistoryState {
  pcbData: PCBData;
  selectedIds: string[];
}

interface PCBStoreState {
  // ========== 项目状态 ==========
  currentProject: Project | null;
  projectId: string | null;
  setCurrentProject: (project: Project | null) => void;
  
  // ========== PCB 数据 ==========
  pcbData: PCBData | null;
  setPCBData: (data: PCBData) => void;
  loadPCBData: (projectId: string) => Promise<void>;
  savePCBData: () => Promise<void>;

  // ========== KiCad IPC 完整数据 ==========
  fullPCBData: FullPCBData | null;
  loadFullPCBData: () => Promise<void>;
  isIPCConnected: boolean;
  
  // ========== 选择状态 ==========
  selectedIds: string[];
  setSelectedIds: (ids: string[]) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  
  // ========== 工具状态 ==========
  currentTool: ToolType;
  setCurrentTool: (tool: ToolType) => void;
  
  // ========== 画布状态 ==========
  zoom: number;
  setZoom: (zoom: number) => void;
  pan: { x: number; y: number };
  setPan: (pan: { x: number; y: number }) => void;
  gridSize: number;
  setGridSize: (size: number) => void;
  snapToGrid: boolean;
  setSnapToGrid: (snap: boolean) => void;

  // ========== 层状态 ==========
  activeLayer: string;
  visibleLayers: string[];
  setActiveLayer: (layer: string) => void;
  toggleLayerVisibility: (layer: string) => void;
  showAllLayers: () => void;
  hideAllLayers: () => void;

  // ========== 网络高亮状态 ==========
  highlightedNet: string | null;
  setHighlightedNet: (net: string | null) => void;

  // ========== 元素操作 ==========
  updateFootprintPosition: (id: string, position: { x: number; y: number }) => void;
  updateFootprintRotation: (id: string, rotation: number) => void;
  rotateSelectedFootprints: (angle: number) => void;
  mirrorSelectedFootprints: (axis: 'x' | 'y') => void;
  addFootprint: (footprint: Footprint) => void;
  removeFootprint: (id: string) => void;
  addTrack: (track: Track) => void;
  removeTrack: (id: string) => void;
  updateTrackPoints: (id: string, points: { x: number; y: number }[]) => void;
  addVia: (via: Via) => void;
  removeVia: (id: string) => void;
  removeSelectedElements: () => void;
  
  // ========== 历史记录 (撤销/重做) ==========
  history: HistoryState[];
  historyIndex: number;
  canUndo: boolean;
  canRedo: boolean;
  pushHistory: () => void;
  undo: () => void;
  redo: () => void;
  
  // ========== 加载状态 ==========
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  error: string | null;
  setError: (error: string | null) => void;
}

export const usePCBStore = create<PCBStoreState>()(
  devtools(
    (set, get) => ({
      // ========== 项目状态 ==========
      currentProject: null,
      projectId: null,
      setCurrentProject: async (project) => {
        set({ currentProject: project, projectId: project?.id || null });
        // Load PCB data when project changes
        if (project?.id) {
          await get().loadPCBData(project.id);
        }
      },
      
      // ========== PCB 数据 ==========
      pcbData: null,
      setPCBData: (data) => {
        set({ pcbData: data });
        get().pushHistory();
      },
      
      loadPCBData: async (projectId: string) => {
        console.log('[PCBStore] loadPCBData called with projectId:', projectId);
        set({ isLoading: true, error: null });
        try {
          // pcbApi.getPCB 返回后端数据
          // pcbApi.getPCB 返回 ApiResponse<PCBData>，需要从 response 获取 data
          const response = await pcbApi.getPCB(projectId);
          console.log('[PCBStore] Load PCB response:', response);
          let pcbData = (response as any).data || response;
          console.log('[PCBStore] pcbData type:', typeof pcbData, 'has tracks:', pcbData?.tracks?.length);

          // 转换 tracks 格式：从 {start, end} 转换为 {points}
          if (pcbData && Array.isArray(pcbData.tracks)) {
            pcbData = {
              ...pcbData,
              tracks: pcbData.tracks.map((track: any) => {
                // 如果已经有 points 数组，直接返回
                if (track.points && track.points.length > 0) {
                  return track;
                }
                // 从 start/end 转换为 points
                if (track.start && track.end) {
                  return {
                    ...track,
                    points: [track.start, track.end]
                  };
                }
                return track;
              })
            };
          }

          if (pcbData && typeof pcbData === 'object' && 'id' in pcbData) {
            set({
              pcbData: pcbData,
              projectId,
              isLoading: false,
              history: [{ pcbData: pcbData, selectedIds: [] }],
              historyIndex: 0,
            });
            console.log('[PCBStore] PCB data loaded, footprints:', pcbData.footprints?.length, 'tracks:', pcbData.tracks?.length);
          } else {
            console.error('[PCBStore] Invalid PCB data:', response);
            set({ error: 'Failed to load PCB data', isLoading: false });
          }
        } catch (error: any) {
          // 忽略请求被取消的错误（快速切换页面时发生）
          console.log('[PCBStore] ===== Catch error =====:', JSON.stringify(error?.message || error));
          if (error instanceof Error && error.name === 'CanceledError') {
            console.log('[PCBStore] PCB load cancelled (page navigation)');
          } else if (error?.name === 'CanceledError' || (error?.message && error.message.includes('cancel'))) {
            console.log('[PCBStore] PCB load cancelled');
          } else {
            console.error('[PCBStore] Load PCB error:', error);
          }
          set({ error: null, isLoading: false });
        }
      },
      
      savePCBData: async () => {
        const { pcbData, projectId } = get();
        if (!pcbData || !projectId) return;

        // 防止空数据覆盖后端生成的数据
        if (!pcbData.footprints || pcbData.footprints.length === 0) {
          console.warn('[PCBStore] No footprints to save, skipping');
          return;
        }

        set({ isSaving: true });
        try {
          // 调用真实API保存PCB数据
          const response = await pcbApi.savePCB(projectId, pcbData);
          if (response.success) {
            set({ isSaving: false, lastSaved: new Date() });
          } else {
            set({ error: response.error || 'Failed to save', isSaving: false });
          }
        } catch {
          set({ error: 'Failed to save', isSaving: false });
        }
      },

      // ========== KiCad IPC 完整数据 ==========
      fullPCBData: null,
      isIPCConnected: false,

      loadFullPCBData: async () => {
        console.log("[PCBStore] loadFullPCBData called");
        try {
          const response = await kicadIpcApi.getFullPCB();
          console.log("[PCBStore] Full PCB response:", response);
          if (response.success && response.connected) {
            set({
              fullPCBData: response,
              isIPCConnected: true
            });
            console.log("[PCBStore] Full PCB data loaded:", {
              layers: response.layers?.length,
              nets: response.nets?.length,
              footprints: response.footprints?.length,
              tracks: response.tracks?.length,
              zones: response.zones?.length
            });
          } else {
            console.log("[PCBStore] KiCad not connected or error:", (response as any).message || response.error);
            set({ isIPCConnected: false });
          }
        } catch (error: any) {
          console.error("[PCBStore] Failed to load full PCB data:", error);
          set({ isIPCConnected: false });
        }
      },
      
      // ========== 选择状态 ==========
      selectedIds: [],
      setSelectedIds: (ids) => set({ selectedIds: ids }),
      toggleSelection: (id) => {
        const { selectedIds } = get();
        if (selectedIds.includes(id)) {
          set({ selectedIds: selectedIds.filter((item) => item !== id) });
        } else {
          set({ selectedIds: [...selectedIds, id] });
        }
      },
      clearSelection: () => set({ selectedIds: [] }),
      
      // ========== 工具状态 ==========
      currentTool: 'select',
      setCurrentTool: (tool) => set({ currentTool: tool }),
      
      // ========== 画布状态 ==========
      zoom: 1,  // 初始缩放 1:1
      setZoom: (zoom) => set({ zoom: Math.max(0.1, Math.min(zoom, 10)) }),
      pan: { x: 0, y: 0 },  // 初始偏移为0
      setPan: (pan) => set({ pan }),
      gridSize: 1, // 1mm
      setGridSize: (size) => set({ gridSize: size }),
      snapToGrid: true,
      setSnapToGrid: (snap) => set({ snapToGrid: snap }),

      // ========== 层状态 ==========
      activeLayer: 'F.Cu',
      visibleLayers: ['F.Cu', 'B.Cu', 'F.SilkS', 'B.SilkS', 'F.Mask', 'B.Mask', 'Edge.Cuts'],
      setActiveLayer: (layer) => set({ activeLayer: layer }),
      toggleLayerVisibility: (layer) => {
        const { visibleLayers } = get();
        if (visibleLayers.includes(layer)) {
          set({ visibleLayers: visibleLayers.filter(l => l !== layer) });
        } else {
          set({ visibleLayers: [...visibleLayers, layer] });
        }
      },
      showAllLayers: () => set({ visibleLayers: ['F.Cu', 'B.Cu', 'F.SilkS', 'B.SilkS', 'F.Mask', 'B.Mask', 'Edge.Cuts', 'F.Paste', 'B.Paste'] }),
      hideAllLayers: () => set({ visibleLayers: [] }),

      // ========== 网络高亮状态 ==========
      highlightedNet: null,
      setHighlightedNet: (net) => set({ highlightedNet: net }),

      // ========== 元素操作 ==========
      updateFootprintPosition: (id, position) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        const newFootprints = pcbData.footprints.map(fp =>
          fp.id === id ? { ...fp, position } : fp
        );
        
        set({
          pcbData: { ...pcbData, footprints: newFootprints }
        });
      },
      
      updateFootprintRotation: (id, rotation) => {
        const { pcbData } = get();
        if (!pcbData) return;

        const newFootprints = pcbData.footprints.map(fp =>
          fp.id === id ? { ...fp, rotation } : fp
        );

        set({
          pcbData: { ...pcbData, footprints: newFootprints }
        });
      },

      rotateSelectedFootprints: (angle: number) => {
        const { pcbData, selectedIds } = get();
        if (!pcbData || selectedIds.length === 0) return;

        get().pushHistory();
        const newFootprints = pcbData.footprints.map(fp => {
          if (selectedIds.includes(fp.id)) {
            return { ...fp, rotation: (fp.rotation || 0) + angle };
          }
          return fp;
        });

        set({
          pcbData: { ...pcbData, footprints: newFootprints }
        });
      },

      mirrorSelectedFootprints: (axis: 'x' | 'y') => {
        const { pcbData, selectedIds } = get();
        if (!pcbData || selectedIds.length === 0) return;

        get().pushHistory();
        const newFootprints = pcbData.footprints.map(fp => {
          if (selectedIds.includes(fp.id)) {
            const newFp = { ...fp };
            if (axis === 'x') {
              newFp.position = { x: fp.position.x, y: -fp.position.y };
            } else {
              newFp.position = { x: -fp.position.x, y: fp.position.y };
            }
            // Toggle mirror flag
            newFp.mirror = !fp.mirror;
            return newFp;
          }
          return fp;
        });

        set({
          pcbData: { ...pcbData, footprints: newFootprints }
        });
      },
      
      addFootprint: (footprint) => {
        const { pcbData } = get();
        if (!pcbData) {
          console.warn('[PCBStore] addFootprint failed: pcbData is null');
          return;
        }

        console.log('[PCBStore] addFootprint called, current footprints:', pcbData.footprints.length);
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            footprints: [...pcbData.footprints, footprint]
          }
        });
        console.log('[PCBStore] addFootprint completed, new footprints:', pcbData.footprints.length + 1);
      },
      
      removeFootprint: (id) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            footprints: pcbData.footprints.filter(fp => fp.id !== id)
          },
          selectedIds: get().selectedIds.filter(sid => sid !== id)
        });
      },
      
      addTrack: (track) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            tracks: [...pcbData.tracks, track]
          }
        });
      },
      
      removeTrack: (id) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            tracks: pcbData.tracks.filter(t => t.id !== id)
          },
          selectedIds: get().selectedIds.filter(sid => sid !== id)
        });
      },
      
      updateTrackPoints: (id, points) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        const newTracks = pcbData.tracks.map(track =>
          track.id === id ? { ...track, points } : track
        );
        
        set({
          pcbData: { ...pcbData, tracks: newTracks }
        });
      },
      
      addVia: (via) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            vias: [...pcbData.vias, via]
          }
        });
      },
      
      removeVia: (id) => {
        const { pcbData } = get();
        if (!pcbData) return;
        
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            vias: pcbData.vias.filter(v => v.id !== id)
          },
          selectedIds: get().selectedIds.filter(sid => sid !== id)
        });
      },
      
      removeSelectedElements: () => {
        const { pcbData, selectedIds } = get();
        if (!pcbData || selectedIds.length === 0) return;
        
        get().pushHistory();
        set({
          pcbData: {
            ...pcbData,
            footprints: pcbData.footprints.filter(fp => !selectedIds.includes(fp.id)),
            tracks: pcbData.tracks.filter(t => !selectedIds.includes(t.id)),
            vias: pcbData.vias.filter(v => !selectedIds.includes(v.id))
          },
          selectedIds: []
        });
      },
      
      // ========== 历史记录 ==========
      history: [],
      historyIndex: -1,
      canUndo: false,
      canRedo: false,
      
      pushHistory: () => {
        const { pcbData, selectedIds, history, historyIndex } = get();
        if (!pcbData) return;
        
        const newState: HistoryState = {
          pcbData: JSON.parse(JSON.stringify(pcbData)),
          selectedIds: [...selectedIds]
        };
        
        // 删除当前位置之后的历史
        const newHistory = history.slice(0, historyIndex + 1);
        newHistory.push(newState);
        
        // 限制历史记录数量
        if (newHistory.length > 50) {
          newHistory.shift();
        }
        
        set({
          history: newHistory,
          historyIndex: newHistory.length - 1,
          canUndo: newHistory.length > 1,
          canRedo: false
        });
      },
      
      undo: () => {
        const { history, historyIndex } = get();
        if (historyIndex <= 0) return;
        
        const newIndex = historyIndex - 1;
        const state = history[newIndex];
        
        set({
          pcbData: JSON.parse(JSON.stringify(state.pcbData)),
          selectedIds: [...state.selectedIds],
          historyIndex: newIndex,
          canUndo: newIndex > 0,
          canRedo: true
        });
      },
      
      redo: () => {
        const { history, historyIndex } = get();
        if (historyIndex >= history.length - 1) return;
        
        const newIndex = historyIndex + 1;
        const state = history[newIndex];
        
        set({
          pcbData: JSON.parse(JSON.stringify(state.pcbData)),
          selectedIds: [...state.selectedIds],
          historyIndex: newIndex,
          canUndo: true,
          canRedo: newIndex < history.length - 1
        });
      },
      
      // ========== 状态 ==========
      isLoading: false,
      isSaving: false,
      lastSaved: null,
      error: null,
      setError: (error) => set({ error }),
    }),
    { name: 'PCBStore' }
  )
);

export default usePCBStore;
