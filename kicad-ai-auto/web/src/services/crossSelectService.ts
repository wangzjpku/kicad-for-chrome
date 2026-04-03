/**
 * 交叉选择服务
 * 同步原理图和PCB之间的选中状态
 */

import { useEffect } from 'react';
import { useSchematicStore } from '../stores/schematicStore';
import { usePCBStore } from '../stores/pcbStore';

// 全局事件发射器
class CrossSelectEventEmitter {
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  off(event: string, callback: (data: any) => void) {
    this.listeners.get(event)?.delete(callback);
  }

  emit(event: string, data: any) {
    this.listeners.get(event)?.forEach(callback => callback(data));
  }
}

export const crossSelectEmitter = new CrossSelectEventEmitter();

/**
 * 同步原理图选中到PCB
 */
export function syncSchematicToPCB(schematicComponentId: string, reference: string) {
  crossSelectEmitter.emit('schematic:select', { id: schematicComponentId, reference });
}

/**
 * 同步PCB选中到原理图
 */
export function syncPCBToSchematic(footprintId: string, reference: string) {
  crossSelectEmitter.emit('pcb:select', { id: footprintId, reference });
}

/**
 * 使用交叉选择钩子（在App组件中使用）
 */
export function useCrossSelection() {
  // 注意：直接在hook中使用store的set方法
  const setSchematicSelectedIds = useSchematicStore(state => state.setSelectedIds);
  const setPCBSelectedIds = usePCBStore(state => state.setSelectedIds);

  useEffect(() => {
    // 监听原理图选择事件
    const handleSchematicSelect = (data: { id: string; reference: string }) => {
      // 在PCB中查找对应封装的ID
      const { pcbData } = usePCBStore.getState();
      if (pcbData) {
        const matchingFootprint = pcbData.footprints.find(
          f => f.reference === data.reference
        );
        if (matchingFootprint) {
          setPCBSelectedIds([matchingFootprint.id]);
        }
      }
    };

    // 监听PCB选择事件
    const handlePCBSelect = (data: { id: string; reference: string }) => {
      // 在原理图中查找对应元件的ID
      const { schematicData } = useSchematicStore.getState();
      if (schematicData) {
        const matchingComponent = schematicData.components.find(
          c => c.reference === data.reference
        );
        if (matchingComponent) {
          setSchematicSelectedIds([matchingComponent.id]);
        }
      }
    };

    crossSelectEmitter.on('schematic:select', handleSchematicSelect);
    crossSelectEmitter.on('pcb:select', handlePCBSelect);

    return () => {
      crossSelectEmitter.off('schematic:select', handleSchematicSelect);
      crossSelectEmitter.off('pcb:select', handlePCBSelect);
    };
  }, [setSchematicSelectedIds, setPCBSelectedIds]);

  // 这个hook不返回数据，只设置副作用
  return null;
}

/**
 * 根据位号查找对应ID
 */
export function findPCBFootprintIdByReference(reference: string): string | null {
  const { pcbData } = usePCBStore.getState();
  if (!pcbData) return null;

  const footprint = pcbData.footprints.find(f => f.reference === reference);
  return footprint?.id || null;
}

export function findSchematicComponentIdByReference(reference: string): string | null {
  const { schematicData } = useSchematicStore.getState();
  if (!schematicData) return null;

  const component = schematicData.components.find(c => c.reference === reference);
  return component?.id || null;
}
