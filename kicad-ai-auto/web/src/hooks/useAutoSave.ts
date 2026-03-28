/**
 * 自动保存 Hook (Task 4.5)
 */

import { useEffect, useRef, useCallback } from 'react';
import { PCBData } from '../types';

interface UseAutoSaveOptions {
  pcbData: PCBData | null;
  projectId?: string; // 可选，保留用于未来项目关联功能
  enabled?: boolean;
  interval?: number;
  onSave?: (pcbData: PCBData) => Promise<void>;
}

export const useAutoSave = ({
  pcbData,
  projectId: _projectId, // 保留用于未来项目关联功能
  enabled = true,
  interval = 5000, // 5秒
  onSave,
}: UseAutoSaveOptions) => {
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedDataRef = useRef<string>('');
  const isSavingRef = useRef(false);
  // 使用 ref 存储最新的 pcbData，避免 setTimeout 闭包捕获旧值
  const pcbDataRef = useRef(pcbData);
  pcbDataRef.current = pcbData;

  // 执行保存 - 始终读取 ref 中的最新数据
  const performSave = useCallback(async () => {
    if (isSavingRef.current || !onSave) return;

    const currentPcbData = pcbDataRef.current;
    const currentData = JSON.stringify(currentPcbData);
    if (currentData === lastSavedDataRef.current) {
      console.log('[AutoSave] No changes to save');
      return;
    }

    isSavingRef.current = true;
    console.log('[AutoSave] Saving...', new Date().toLocaleTimeString());

    try {
      await onSave(currentPcbData);
      lastSavedDataRef.current = currentData;
      console.log('[AutoSave] Save successful');
    } catch (error) {
      console.error('[AutoSave] Save failed:', error);
    } finally {
      isSavingRef.current = false;
    }
  }, [onSave]);

  // 防抖保存
  const debouncedSave = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(() => {
      performSave();
    }, interval);
  }, [performSave, interval]);

  // 监听数据变化
  useEffect(() => {
    if (!enabled) return;

    debouncedSave();

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [pcbData, enabled, debouncedSave]);

  // 组件卸载时立即保存
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
        performSave();
      }
    };
  }, [performSave]);

  return {
    save: performSave,
    isSaving: () => isSavingRef.current,
  };
};

export default useAutoSave;
