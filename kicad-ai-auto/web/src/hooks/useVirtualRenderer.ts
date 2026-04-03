/**
 * Virtual Renderer for large PCB canvases.
 *
 * Only renders items within the current viewport (frustum culling),
 * with Level-of-Detail (LOD) support for zoom-dependent simplification.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// ---- Types ----

export interface VirtualItem {
  id: string;
  type: 'component' | 'track' | 'via' | 'pad' | 'zone' | 'text';
  bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
  layer: string;
  data?: Record<string, unknown>;
}

export interface Viewport {
  x: number;      // center x in PCB coordinates (mm)
  y: number;      // center y in PCB coordinates (mm)
  width: number;  // visible width in mm
  height: number; // visible height in mm
  zoom: number;   // pixels per mm
}

export type LODLevel = 'full' | 'simplified' | 'bbox_only' | 'hidden';

export interface RenderItem extends VirtualItem {
  lod: LODLevel;
  screenArea: number; // approximate screen pixels
}

// ---- BBox helpers ----

function bboxIntersects(
  a: { x1: number; y1: number; x2: number; y2: number },
  b: { x1: number; y1: number; x2: number; y2: number },
): boolean {
  return !(a.x2 < b.x1 || a.x1 > b.x2 || a.y2 < b.y1 || a.y1 > b.y2);
}

function bboxArea(bbox: { x1: number; y1: number; x2: number; y2: number }): number {
  return (bbox.x2 - bbox.x1) * (bbox.y2 - bbox.y1);
}

function viewportBBox(vp: Viewport) {
  return {
    x1: vp.x - vp.width / 2,
    y1: vp.y - vp.height / 2,
    x2: vp.x + vp.width / 2,
    y2: vp.y + vp.height / 2,
  };
}

// ---- LOD determination ----

function computeLOD(item: VirtualItem, vp: Viewport): LODLevel {
  const vpBBox = viewportBBox(vp);

  // Not in viewport at all
  if (!bboxIntersects(item.bbox, vpBBox)) {
    return 'hidden';
  }

  // Estimate screen area in pixels
  const widthPx = (item.bbox.x2 - item.bbox.x1) * vp.zoom;
  const heightPx = (item.bbox.y2 - item.bbox.y1) * vp.zoom;
  const screenArea = widthPx * heightPx;

  // Too small to see
  if (screenArea < 1) {
    return 'hidden';
  }

  // Very small — just show bbox outline
  if (screenArea < 16) {
    return 'bbox_only';
  }

  // Medium — simplified rendering (no fine details)
  if (screenArea < 400) {
    return 'simplified';
  }

  return 'full';
}

// ---- Grid-based spatial index for fast viewport queries ----

class ItemGrid {
  private cellSize: number;
  private cells: Map<string, VirtualItem[]>;

  constructor(cellSize = 10) {
    this.cellSize = cellSize;
    this.cells = new Map();
  }

  clear() {
    this.cells.clear();
  }

  insert(item: VirtualItem) {
    const minCx = Math.floor(item.bbox.x1 / this.cellSize);
    const minCy = Math.floor(item.bbox.y1 / this.cellSize);
    const maxCx = Math.floor(item.bbox.x2 / this.cellSize);
    const maxCy = Math.floor(item.bbox.y2 / this.cellSize);

    for (let cx = minCx; cx <= maxCx; cx++) {
      for (let cy = minCy; cy <= maxCy; cy++) {
        const key = `${cx},${cy}`;
        let cell = this.cells.get(key);
        if (!cell) {
          cell = [];
          this.cells.set(key, cell);
        }
        cell.push(item);
      }
    }
  }

  query(bbox: { x1: number; y1: number; x2: number; y2: number }): VirtualItem[] {
    const minCx = Math.floor(bbox.x1 / this.cellSize);
    const minCy = Math.floor(bbox.y1 / this.cellSize);
    const maxCx = Math.floor(bbox.x2 / this.cellSize);
    const maxCy = Math.floor(bbox.y2 / this.cellSize);

    const seen = new Set<string>();
    const results: VirtualItem[] = [];

    for (let cx = minCx; cx <= maxCx; cx++) {
      for (let cy = minCy; cy <= maxCy; cy++) {
        const cell = this.cells.get(`${cx},${cy}`);
        if (!cell) continue;
        for (const item of cell) {
          if (!seen.has(item.id) && bboxIntersects(item.bbox, bbox)) {
            seen.add(item.id);
            results.push(item);
          }
        }
      }
    }
    return results;
  }
}

// ---- Hook ----

export interface VirtualRendererOptions {
  /** Pre-add margin around viewport for smooth scrolling (0.0-0.5, default 0.1) */
  viewportMargin?: number;
  /** Grid cell size in mm (default 10) */
  gridCellSize?: number;
  /** Maximum items to render (default 5000) */
  maxRenderItems?: number;
  /** Layer filter (null = all layers) */
  visibleLayers?: string[] | null;
}

export function useVirtualRenderer(
  items: VirtualItem[],
  viewport: Viewport,
  options: VirtualRendererOptions = {},
) {
  const {
    viewportMargin = 0.1,
    gridCellSize = 10,
    maxRenderItems = 5000,
    visibleLayers = null,
  } = options;

  const gridRef = useRef<ItemGrid>(new ItemGrid(gridCellSize));
  const [itemsVersion, setItemsVersion] = useState(0);

  // Rebuild grid when items change
  useEffect(() => {
    const grid = new ItemGrid(gridCellSize);
    for (const item of items) {
      grid.insert(item);
    }
    gridRef.current = grid;
    setItemsVersion((v) => v + 1);
  }, [items, gridCellSize]);

  // Query viewport with margin
  const renderItems = useMemo(() => {
    const expandedVp: Viewport = {
      ...viewport,
      width: viewport.width * (1 + viewportMargin * 2),
      height: viewport.height * (1 + viewportMargin * 2),
    };

    const vpBBox = viewportBBox(expandedVp);
    const grid = gridRef.current;

    let candidates = grid.query(vpBBox);

    // Layer filter
    if (visibleLayers) {
      const layerSet = new Set(visibleLayers);
      candidates = candidates.filter((item) => layerSet.has(item.layer));
    }

    // Compute LOD and filter hidden items
    const withLod: RenderItem[] = [];
    for (const item of candidates) {
      const lod = computeLOD(item, viewport);
      if (lod === 'hidden') continue;

      const widthPx = (item.bbox.x2 - item.bbox.x1) * viewport.zoom;
      const heightPx = (item.bbox.y2 - item.bbox.y1) * viewport.zoom;
      withLod.push({
        ...item,
        lod,
        screenArea: widthPx * heightPx,
      });
    }

    // Sort by screen area (larger items rendered first / higher priority)
    withLod.sort((a, b) => b.screenArea - a.screenArea);

    // Cap at max items
    if (withLod.length > maxRenderItems) {
      withLod.length = maxRenderItems;
    }

    return withLod;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    itemsVersion,
    viewport.x,
    viewport.y,
    viewport.width,
    viewport.height,
    viewport.zoom,
    viewportMargin,
    maxRenderItems,
    visibleLayers,
  ]);

  // Statistics
  const stats = useMemo(() => {
    const byLod = { full: 0, simplified: 0, bbox_only: 0, hidden: 0 };
    const byType: Record<string, number> = {};
    for (const item of renderItems) {
      byLod[item.lod]++;
      byType[item.type] = (byType[item.type] || 0) + 1;
    }
    return {
      totalItems: items.length,
      visibleItems: renderItems.length,
      culledItems: items.length - renderItems.length,
      byLod,
      byType,
    };
  }, [items.length, renderItems]);

  return {
    renderItems,
    stats,
  };
}
