/**
 * 原理图编辑器 Zustand Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  SchematicData,
  SchematicComponent,
  Wire,
  Label,
  Point2D,
  SchematicSheet,
  Project
} from '../types';
import apiClient from '../services/api';

interface HistoryState {
  components: SchematicComponent[];
  wires: Wire[];
  labels: Label[];
  selectedIds: string[];
}

interface SchematicStoreState {
  // 项目状态
  currentProject: Project | null;
  projectId: string | null;
  setCurrentProject: (project: Project | null) => void;

  // 原理图数据
  schematicData: SchematicData | null;
  setSchematicData: (data: SchematicData) => void;
  loadSchematicData: (projectId: string) => Promise<void>;
  
  // 当前工作表
  currentSheetId: string | null;
  setCurrentSheet: (sheetId: string) => void;
  
  // 选择状态
  selectedIds: string[];
  setSelectedIds: (ids: string[]) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  
  // 工具状态
  currentTool: 'select' | 'place_symbol' | 'place_wire' | 'place_label' | 'place_power';
  setCurrentTool: (tool: 'select' | 'place_symbol' | 'place_wire' | 'place_label' | 'place_power') => void;
  
  // 画布状态
  zoom: number;
  setZoom: (zoom: number) => void;
  pan: Point2D;
  setPan: (pan: Point2D) => void;
  
  // 元素操作
  addComponent: (component: SchematicComponent) => void;
  removeComponent: (id: string) => void;
  updateComponent: (id: string, updates: Partial<SchematicComponent>) => void;
  updateComponentPosition: (id: string, position: Point2D) => void;
  updateComponentRotation: (id: string, rotation: number) => void;

  addWire: (wire: Wire) => void;
  removeWire: (id: string) => void;
  updateWire: (id: string, updates: Partial<Wire>) => void;
  updateWirePoints: (id: string, points: Point2D[]) => void;

  addLabel: (label: Label) => void;
  removeLabel: (id: string) => void;
  updateLabel: (id: string, updates: Partial<Label>) => void;
  
  removeSelectedElements: () => void;
  
  // 历史记录
  history: HistoryState[];
  historyIndex: number;
  canUndo: boolean;
  canRedo: boolean;
  pushHistory: () => void;
  undo: () => void;
  redo: () => void;
}

export const useSchematicStore = create<SchematicStoreState>()(
  devtools(
    (set, get) => ({
      // 项目状态
      currentProject: null,
      projectId: null,
      setCurrentProject: (project) => {
        set({ currentProject: project, projectId: project?.id || null });
        // Load schematic data when project changes
        if (project?.id) {
          get().loadSchematicData(project.id);
        }
      },

      // 初始状态
      schematicData: null,
      currentSheetId: null,
      selectedIds: [],
      currentTool: 'select',
      zoom: 1,
      pan: { x: 0, y: 0 },
      history: [],
      historyIndex: -1,
      canUndo: false,
      canRedo: false,

      // 加载原理图数据
      loadSchematicData: async (projectId: string) => {
        try {
          const axiosResponse = await apiClient.get(`/projects/${projectId}/schematic`);
          // axios 返回的响应在 data 属性中
          const data = axiosResponse.data;
          console.log('[SchematicStore] Load schematic response:', data);
          if (data && typeof data === 'object') {
            // 后端直接返回数据，没有 success 包装器
            // 转换元件数据格式：后端返回 name, model -> 前端需要 reference, value
            const components = (data.components || []).map((comp: any, idx: number) => ({
              id: comp.id || `comp-${idx}`,
              libraryName: 'AI_Lib',
              symbolName: comp.name,
              fullSymbolName: comp.name,
              reference: `${(comp.name || 'U')[0]}${idx + 1}`,
              value: comp.model || '',
              position: comp.position || { x: 0, y: 0 },
              rotation: comp.rotation || 0,
              mirror: comp.mirror || false,
              unit: comp.unit || 1,
              fields: {},
              footprint: comp.footprint,
              pins: (comp.pins || []).map((pin: any, pinIdx: number) => ({
                id: `pin-${pinIdx}`,
                number: pin.number || String(pinIdx + 1),
                name: pin.name || ''
              }))
            }));

            const schematicData: SchematicData = {
              id: data.id || `schematic-${projectId}`,
              projectId: projectId,
              components,
              wires: data.wires || [],
              nets: data.nets || [],
              labels: data.labels || [],
              powerSymbols: data.powerSymbols || [],
              sheets: data.sheets || [{ id: 'sheet1', name: 'Sheet1', components: [], wires: [] }]
            };
            console.log('[SchematicStore] Schematic loaded, components:', schematicData.components.length);
            set({ schematicData });
          }
        } catch (error) {
          console.error('Failed to load schematic data:', error);
        }
      },

      // 设置原理图数据
      setSchematicData: (data) => {
        set({ schematicData: data });
        if (data && data.sheets && data.sheets.length > 0) {
          set({ currentSheetId: data.sheets[0].id });
        }
        if (data) {
          get().pushHistory();
        }
      },
      
      // 设置当前工作表
      setCurrentSheet: (sheetId) => set({ currentSheetId: sheetId }),
      
      // 选择状态
      setSelectedIds: (ids) => set({ selectedIds: ids }),
      
      toggleSelection: (id) => {
        const { selectedIds } = get();
        if (selectedIds.includes(id)) {
          set({ selectedIds: selectedIds.filter(item => item !== id) });
        } else {
          set({ selectedIds: [...selectedIds, id] });
        }
      },
      
      clearSelection: () => set({ selectedIds: [] }),
      
      // 工具状态
      setCurrentTool: (tool) => set({ currentTool: tool }),
      
      // 画布状态
      setZoom: (zoom) => set({ zoom: Math.max(0.1, Math.min(zoom, 10)) }),
      setPan: (pan) => set({ pan }),
      
      // 元件操作
      addComponent: (component) => {
        const { schematicData } = get();
        if (!schematicData) return;
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            components: [...schematicData.components, component]
          }
        });
      },
      
      removeComponent: (id) => {
        const { schematicData } = get();
        if (!schematicData) return;
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            components: schematicData.components.filter(c => c.id !== id)
          },
          selectedIds: get().selectedIds.filter(sid => sid !== id)
        });
      },
      
      updateComponentPosition: (id, position) => {
        const { schematicData } = get();
        if (!schematicData) return;
        
        const newComponents = schematicData.components.map(c =>
          c.id === id ? { ...c, position } : c
        );
        
        set({
          schematicData: { ...schematicData, components: newComponents }
        });
      },
      
      updateComponentRotation: (id, rotation) => {
        const { schematicData } = get();
        if (!schematicData) return;

        const newComponents = schematicData.components.map(c =>
          c.id === id ? { ...c, rotation } : c
        );

        set({
          schematicData: { ...schematicData, components: newComponents }
        });
      },

      updateComponent: (id, updates) => {
        const { schematicData } = get();
        if (!schematicData) return;

        const newComponents = schematicData.components.map(c =>
          c.id === id ? { ...c, ...updates } : c
        );

        set({
          schematicData: { ...schematicData, components: newComponents }
        });
      },
      
      // 导线操作
      addWire: (wire) => {
        const { schematicData } = get();
        if (!schematicData) return;
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            wires: [...schematicData.wires, wire]
          }
        });
      },
      
      removeWire: (id) => {
        const { schematicData } = get();
        if (!schematicData) return;
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            wires: schematicData.wires.filter(w => w.id !== id)
          },
          selectedIds: get().selectedIds.filter(sid => sid !== id)
        });
      },
      
      updateWirePoints: (id, points) => {
        const { schematicData } = get();
        if (!schematicData) return;

        const newWires = schematicData.wires.map(w =>
          w.id === id ? { ...w, points } : w
        );

        set({
          schematicData: { ...schematicData, wires: newWires }
        });
      },

      updateWire: (id, updates) => {
        const { schematicData } = get();
        if (!schematicData) return;

        const newWires = schematicData.wires.map(w =>
          w.id === id ? { ...w, ...updates } : w
        );

        set({
          schematicData: { ...schematicData, wires: newWires }
        });
      },
      
      // 标签操作
      addLabel: (label) => {
        const { schematicData } = get();
        if (!schematicData) return;
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            labels: [...schematicData.labels, label]
          }
        });
      },
      
      removeLabel: (id) => {
        const { schematicData } = get();
        if (!schematicData) return;
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            labels: schematicData.labels.filter(l => l.id !== id)
          },
          selectedIds: get().selectedIds.filter(sid => sid !== id)
        });
      },

      updateLabel: (id, updates) => {
        const { schematicData } = get();
        if (!schematicData) return;

        const newLabels = schematicData.labels.map(l =>
          l.id === id ? { ...l, ...updates } : l
        );

        set({
          schematicData: { ...schematicData, labels: newLabels }
        });
      },

      // 删除选中元素
      removeSelectedElements: () => {
        const { schematicData, selectedIds } = get();
        if (!schematicData || selectedIds.length === 0) return;
        
        get().pushHistory();
        set({
          schematicData: {
            ...schematicData,
            components: schematicData.components.filter(c => !selectedIds.includes(c.id)),
            wires: schematicData.wires.filter(w => !selectedIds.includes(w.id)),
            labels: schematicData.labels.filter(l => !selectedIds.includes(l.id))
          },
          selectedIds: []
        });
      },
      
      // 历史记录
      pushHistory: () => {
        const { schematicData, selectedIds, history, historyIndex } = get();
        if (!schematicData) return;
        
        const newState: HistoryState = {
          components: [...schematicData.components],
          wires: [...schematicData.wires],
          labels: [...schematicData.labels],
          selectedIds: [...selectedIds]
        };
        
        const newHistory = history.slice(0, historyIndex + 1);
        newHistory.push(newState);
        
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
        const { history, historyIndex, schematicData } = get();
        if (historyIndex <= 0 || !schematicData) return;
        
        const newIndex = historyIndex - 1;
        const state = history[newIndex];
        
        set({
          schematicData: {
            ...schematicData,
            components: state.components,
            wires: state.wires,
            labels: state.labels
          },
          selectedIds: state.selectedIds,
          historyIndex: newIndex,
          canUndo: newIndex > 0,
          canRedo: true
        });
      },
      
      redo: () => {
        const { history, historyIndex, schematicData } = get();
        if (historyIndex >= history.length - 1 || !schematicData) return;
        
        const newIndex = historyIndex + 1;
        const state = history[newIndex];
        
        set({
          schematicData: {
            ...schematicData,
            components: state.components,
            wires: state.wires,
            labels: state.labels
          },
          selectedIds: state.selectedIds,
          historyIndex: newIndex,
          canUndo: true,
          canRedo: newIndex < history.length - 1
        });
      },
    }),
    { name: 'SchematicStore' }
  )
);

export default useSchematicStore;
