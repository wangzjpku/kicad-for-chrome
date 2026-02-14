/**
 * 自动保存 Hook (Task 4.5)
 */

import { useEffect, useRef, useCallback } from 'react';
import { PCBData } from '../types';

interface UseAutoSaveOptions {
  pcbData: PCBData;
  projectId: string;
  enabled?: boolean;
  interval?: number; // 毫秒
  onSave?: (data: PCBData) => Promise<void>;
}

export const useAutoSave = ({
  pcbData,
  projectId,
  enabled = true,
  interval = 5000, // 5秒
  onSave,
}: UseAutoSaveOptions) => {
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedDataRef = useRef<string>('');
  const isSavingRef = useRef(false);

  // 执行保存
  const performSave = useCallback(async () => {
    if (isSavingRef.current || !onSave) return;

    const currentData = JSON.stringify(pcbData);
    if (currentData === lastSavedDataRef.current) {
      console.log('[AutoSave] No changes to save');
      return;
    }

    isSavingRef.current = true;
    console.log('[AutoSave] Saving...', new Date().toLocaleTimeString());

    try {
      await onSave(pcbData);
      lastSavedDataRef.current = currentData;
      console.log('[AutoSave] Save successful');
    } catch (error) {
      console.error('[AutoSave] Save failed:', error);
    } finally {
      isSavingRef.current = false;
    }
  }, [pcbData, onSave]);

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
