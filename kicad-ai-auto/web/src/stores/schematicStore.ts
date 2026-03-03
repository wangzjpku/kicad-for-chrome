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
  // SchematicSheet, // 未使用
  Project,
  Point2D
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
  currentTool: 'select' | 'place_symbol' | 'place_wire' | 'place_label' | 'place_power' | 'place_footprint' | 'route' | 'place_via' | 'rotate' | 'mirror';
  setCurrentTool: (tool: 'select' | 'place_symbol' | 'place_wire' | 'place_label' | 'place_power' | 'place_footprint' | 'route' | 'place_via' | 'rotate' | 'mirror') => void;
  
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
  rotateSelectedComponents: (angle: number) => void;
  mirrorSelectedComponents: () => void;

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
      zoom: 1,  // 初始zoom为1，确保内容可见
      pan: { x: 100, y: 50 },  // 默认偏移，配合 MM_TO_PX=0.5 让元件显示在视野内
      history: [],
      historyIndex: -1,
      canUndo: false,
      canRedo: false,

      // 加载原理图数据
      loadSchematicData: async (projectId: string) => {
        console.log('[SchematicStore] loadSchematicData called with projectId:', projectId);
        try {
          const axiosResponse = await apiClient.get(`/projects/${projectId}/schematic`);
          // axios 返回的响应在 data 属性中
          const data = axiosResponse.data;
          console.log('[SchematicStore] Load schematic response:', data);
          if (data && typeof data === 'object') {
            // 后端直接返回数据，没有 success 包装器
            // 转换元件数据格式：后端返回 name, model -> 前端需要 reference, value
            interface BackendComponent {
              id?: string;
              name?: string;
              model?: string;
              reference?: string;
              position?: Point2D;
              rotation?: number;
              mirror?: boolean;
              unit?: number;
              footprint?: string;
              category?: string;
              symbol_library?: string;
              pins?: Array<{number?: string; name?: string; position?: Point2D}>;
            }
            
            interface BackendPin {
              number?: string;
              name?: string;
              position?: Point2D;
            }
            
            // 网格布局参数
            const GRID_COLS = 2;  // 每行2个元器件（更宽松的布局）
            const GRID_SPACING_X = 300;  // 水平间距增加到300mm，留出足够连线空间
            const GRID_SPACING_Y = 250;  // 垂直间距增加到250mm，确保连线有足够空间
            const START_X = 100;  // 起始X位置
            const START_Y = 80;  // 起始Y位置
            const MIN_DISTANCE = 30; // 元器件之间的最小允许距离

            // 自动布局：检查是否需要自动排列元器件
            const hasInvalidPosition = data.components?.some((comp: BackendComponent) =>
              !comp.position ||
              typeof comp.position.x !== 'number' ||
              typeof comp.position.y !== 'number' ||
              (comp.position.x === 0 && comp.position.y === 0)
            );

            // 检查元器件是否过于密集（彼此距离小于阈值）
            const isTooDense = (() => {
              const positions = (data.components || [])
                .filter((comp: BackendComponent) => comp.position && typeof comp.position.x === 'number' && typeof comp.position.y === 'number')
                .map((comp: BackendComponent) => ({ x: comp.position!.x, y: comp.position!.y }));

              for (let i = 0; i < positions.length; i++) {
                for (let j = i + 1; j < positions.length; j++) {
                  const dx = positions[i].x - positions[j].x;
                  const dy = positions[i].y - positions[j].y;
                  const distance = Math.sqrt(dx * dx + dy * dy);
                  if (distance < MIN_DISTANCE) {
                    console.log(`[SchematicStore] Components too close: ${distance.toFixed(1)}mm, need auto-layout`);
                    return true;
                  }
                }
              }
              return false;
            })();

            const needsAutoLayout = hasInvalidPosition || isTooDense;

            const components = (data.components || []).map((comp: BackendComponent, idx: number) => {
              // 安全获取 position 值，确保不是 null/undefined
              let posX = (comp.position && typeof comp.position.x === 'number') ? comp.position.x : 0;
              let posY = (comp.position && typeof comp.position.y === 'number') ? comp.position.y : 0;

              // 如果需要自动布局，或者位置为(0,0)，则计算网格位置
              if (needsAutoLayout || (posX === 0 && posY === 0)) {
                const col = idx % GRID_COLS;
                const row = Math.floor(idx / GRID_COLS);
                posX = START_X + col * GRID_SPACING_X;
                posY = START_Y + row * GRID_SPACING_Y;
                console.log(`[SchematicStore] Auto-layout for ${comp.name || comp.id}: row=${row}, col=${col}, pos=(${posX}, ${posY})`);
              }

              return {
                id: comp.id || `comp-${idx}`,
                libraryName: comp.category || 'AI_Lib',
                symbolName: comp.name || '',
                fullSymbolName: comp.symbol_library || comp.name || '',
                // 优先使用后端返回的 reference，否则生成一个
                reference: comp.reference || `${(comp.name || 'U')[0]}${idx + 1}`,
                value: comp.model || '',
                position: { x: posX, y: posY },
                rotation: comp.rotation || 0,
                mirror: comp.mirror || false,
                unit: comp.unit || 1,
                fields: {},
                footprint: comp.footprint,
                symbol_library: comp.symbol_library || '',  // 传递符号库信息
                category: comp.category || '',  // 传递类别信息
                pins: (comp.pins || []).map((pin: BackendPin, pinIdx: number) => ({
                  id: `pin-${pinIdx}`,
                  number: pin.number || String(pinIdx + 1),
                  name: pin.name || '',
                  position: (pin.position && typeof pin.position.x === 'number')
                    ? { x: pin.position.x, y: pin.position.y || 0 }
                    : { x: 0, y: 0 },
                  electricalType: 'passive' as const
                }))
              };
            });

            const rawPositions = data.components?.map((c, i) => ({ id: c.id || `comp-${i}`, name: c.name, pos: c.position, ref: c.reference }));
            console.log('[SchematicStore] Component positions (raw from backend):', rawPositions);
            console.log('[SchematicStore] Needs auto-layout:', needsAutoLayout);
            console.log('[SchematicStore] Component positions (after transform/auto-layout):', components.map(c => ({ id: c.id, ref: c.reference, pos: c.position })));

            // 暴露到 window 用于调试
            if (typeof window !== 'undefined') {
              (window as any).__schematicDebug = { raw: rawPositions, transformed: components };
            }

            const schematicData: SchematicData = {
              id: data.id || `schematic-${projectId}`,
              projectId: projectId,
              components,
              wires: data.wires || [],
              nets: data.nets || [],
              // 兼容后端返回的 netLabels 和 labels 两种字段名
              labels: data.labels || data.netLabels || [],
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

      rotateSelectedComponents: (angle: number) => {
        const { schematicData, selectedIds } = get();
        if (!schematicData || selectedIds.length === 0) return;

        get().pushHistory();
        const newComponents = schematicData.components.map(c => {
          if (selectedIds.includes(c.id)) {
            return { ...c, rotation: (c.rotation || 0) + angle };
          }
          return c;
        });

        set({
          schematicData: { ...schematicData, components: newComponents }
        });
      },

      mirrorSelectedComponents: () => {
        const { schematicData, selectedIds } = get();
        if (!schematicData || selectedIds.length === 0) return;

        get().pushHistory();
        const newComponents = schematicData.components.map(c => {
          if (selectedIds.includes(c.id)) {
            return { ...c, mirror: !c.mirror };
          }
          return c;
        });

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
