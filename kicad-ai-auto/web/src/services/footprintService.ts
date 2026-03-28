/**
 * 封装服务
 * 从KiCad封装库读取真实封装数据
 */

import { Footprint } from '../types';

export interface FootprintGraphic {
  type: 'pad' | 'line' | 'circle' | 'arc' | 'text' | 'polygon';
  layer: string;
  // pad properties
  padNumber?: string;
  padType?: 'smd' | 'thru_hole' | 'np_thru_hole';
  shape?: 'circle' | 'rect' | 'oval' | 'trapezoid';
  size?: { x: number; y: number };
  position?: { x: number; y: number };
  // line properties
  start?: { x: number; y: number };
  end?: { x: number; y: number };
  width?: number;
  // circle properties
  center?: { x: number; y: number };
  radius?: number;
  // text properties
  text?: string;
  // polygon
  points?: { x: number; y: number }[];
}

export interface FootprintData {
  name: string;
  description: string;
  tags: string[];
  graphics: FootprintGraphic[];
  pads: Array<{
    number: string;
    type: string;
    shape: string;
    position: { x: number; y: number };
    size: { x: number; y: number };
    layers: string[];
  }>;
}

// 封装缓存
const footprintCache: Map<string, FootprintData> = new Map();

/**
 * 获取封装数据（带缓存）
 */
export async function getFootprintData(
  library: string,
  name: string
): Promise<FootprintData | null> {
  const cacheKey = `${library}:${name}`;
  if (footprintCache.has(cacheKey)) {
    return footprintCache.get(cacheKey)!;
  }

  try {
    const response = await fetch(
      `/api/v1/footprints/${library}/${name}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch footprint: ${response.status}`);
    }
    const data = await response.json();
    if (data.success) {
      footprintCache.set(cacheKey, data.footprint);
      return data.footprint;
    }
  } catch (error) {
    console.warn(`[FootprintService] Failed to load footprint ${cacheKey}:`, error);
  }

  return null;
}

/**
 * 根据封装名称查找
 */
export async function findFootprint(name: string): Promise<FootprintData | null> {
  if (footprintCache.has(`find:${name}`)) {
    return footprintCache.get(`find:${name}`)!;
  }

  try {
    const response = await fetch(
      `/api/v1/footprints/find?name=${encodeURIComponent(name)}`
    );
    if (!response.ok) {
      throw new Error(`Failed to find footprint: ${response.status}`);
    }
    const data = await response.json();
    if (data.success && data.footprint) {
      footprintCache.set(`find:${name}`, data.footprint);
      return data.footprint;
    }
  } catch (error) {
    console.warn(`[FootprintService] Failed to find footprint ${name}:`, error);
  }

  return null;
}

/**
 * 获取默认封装轮廓（当真实封装不可用时）
 */
export function getDefaultFootprintOutline(footprintName: string): FootprintGraphic[] {
  // 根据封装名推断形状
  const graphics: FootprintGraphic[] = [];

  // 解析封装尺寸
  const sizeMatch = footprintName.match(/(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)/);
  const width = sizeMatch ? parseFloat(sizeMatch[1]) : 3;
  const height = sizeMatch ? parseFloat(sizeMatch[2]) : 3;

  // 外框
  graphics.push({
    type: 'line',
    layer: 'F.SilkS',
    start: { x: -width / 2, y: -height / 2 },
    end: { x: width / 2, y: -height / 2 },
    width: 0.15,
  });
  graphics.push({
    type: 'line',
    layer: 'F.SilkS',
    start: { x: width / 2, y: -height / 2 },
    end: { x: width / 2, y: height / 2 },
    width: 0.15,
  });
  graphics.push({
    type: 'line',
    layer: 'F.SilkS',
    start: { x: width / 2, y: height / 2 },
    end: { x: -width / 2, y: height / 2 },
    width: 0.15,
  });
  graphics.push({
    type: 'line',
    layer: 'F.SilkS',
    start: { x: -width / 2, y: height / 2 },
    end: { x: -width / 2, y: -height / 2 },
    width: 0.15,
  });

  // 引脚1标记
  graphics.push({
    type: 'circle',
    layer: 'F.SilkS',
    center: { x: -width / 2 - 0.5, y: -height / 2 - 0.5 },
    radius: 0.2,
  });

  return graphics;
}

/**
 * 清除缓存
 */
export function clearFootprintCache(): void {
  footprintCache.clear();
}

/**
 * 获取缓存大小
 */
export function getFootprintCacheSize(): number {
  return footprintCache.size;
}
