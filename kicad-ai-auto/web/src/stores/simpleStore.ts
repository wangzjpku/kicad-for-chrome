/**
 * 简化版 Zustand Store (Task 2.1)
 * 只包含最基本的选择功能
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export type ToolType = 'select' | 'move' | 'route' | 'place_footprint';

interface SimpleStoreState {
  // 选择状态
  selectedIds: string[];
  setSelectedIds: (ids: string[]) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  
  // 工具状态
  currentTool: ToolType;
  setCurrentTool: (tool: ToolType) => void;
  
  // 画布状态
  zoom: number;
  setZoom: (zoom: number) => void;
  pan: { x: number; y: number };
  setPan: (pan: { x: number; y: number }) => void;
  
  // 元素位置 (用于拖拽)
  elementPositions: Record<string, { x: number; y: number }>;
  updateElementPosition: (id: string, position: { x: number; y: number }) => void;
}

export const useSimpleStore = create<SimpleStoreState>()(
  devtools(
    (set, get) => ({
      // 选择
      selectedIds: [],
      setSelectedIds: (ids) => set({ selectedIds: ids }, false, 'setSelectedIds'),
      toggleSelection: (id) => {
        const { selectedIds } = get();
        if (selectedIds.includes(id)) {
          set(
            { selectedIds: selectedIds.filter((item) => item !== id) },
            false,
            'toggleSelection/remove'
          );
        } else {
          set(
            { selectedIds: [...selectedIds, id] },
            false,
            'toggleSelection/add'
          );
        }
      },
      clearSelection: () => set({ selectedIds: [] }, false, 'clearSelection'),
      
      // 工具
      currentTool: 'select',
      setCurrentTool: (tool) => set({ currentTool: tool }, false, 'setCurrentTool'),
      
      // 画布
      zoom: 1,
      setZoom: (zoom) => set({ zoom }, false, 'setZoom'),
      pan: { x: 0, y: 0 },
      setPan: (pan) => set({ pan }, false, 'setPan'),
      
      // 元素位置
      elementPositions: {},
      updateElementPosition: (id, position) =>
        set(
          (state) => ({
            elementPositions: {
              ...state.elementPositions,
              [id]: position,
            },
          }),
          false,
          'updateElementPosition'
        ),
    }),
    { name: 'SimplePCBStore' }
  )
);

export default useSimpleStore;
