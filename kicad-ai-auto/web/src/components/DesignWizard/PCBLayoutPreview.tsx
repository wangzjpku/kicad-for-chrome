/**
 * PCBLayoutPreview.tsx - Mini PCB layout canvas preview
 *
 * Renders a visual PCB layout showing component footprints as colored
 * rectangles on a board outline, with routing guides showing net connections.
 * Supports zoom and pan.
 */

import React, { useMemo, useCallback, useRef, useState } from 'react';

interface Placement {
  reference: string;
  footprint?: string;
  x: number;
  y: number;
  rotation?: number;
  width?: number;
  height?: number;
}

interface Route {
  net: string;
  points?: Array<{ x: number; y: number }>;
  layer?: string;
  width?: number;
}

interface BoardOutline {
  width: number;
  height: number;
}

interface PCBLayoutPreviewProps {
  placements: Placement[];
  routes: Route[];
  vias?: Array<{ x: number; y: number }>;
  boardOutline: BoardOutline;
  canvasWidth?: number;
  canvasHeight?: number;
}

const LAYER_COLORS: Record<string, string> = {
  'F.Cu': '#ff6b6b',
  'B.Cu': '#4dabf7',
  'In1.Cu': '#69db7c',
  'In2.Cu': '#ffd43b',
};

const COMP_COLORS: Record<string, string> = {
  ic: '#4a9eff',
  passive: '#8bc34a',
  power: '#ff9800',
  connector: '#ab47bc',
  default: '#78909c',
};

function classifyComponent(ref: string): string {
  const r = ref.toUpperCase();
  if (/^U\d|^IC\d/.test(r)) return 'ic';
  if (/^R\d|^C\d|^L\d/.test(r)) return 'passive';
  if (/^Q\d|^D\d|^LED\d/.test(r)) return 'power';
  if (/^J\d|^CN\d|^CONN\d/.test(r)) return 'connector';
  return 'default';
}

export const PCBLayoutPreview: React.FC<PCBLayoutPreviewProps> = ({
  placements,
  routes,
  vias = [],
  boardOutline,
  canvasWidth = 480,
  canvasHeight = 320,
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  const margin = 20;

  // Scale PCB coords to canvas
  const scale = useMemo(() => {
    const sx = (canvasWidth - 2 * margin) / (boardOutline.width || 100);
    const sy = (canvasHeight - 2 * margin) / (boardOutline.height || 80);
    return Math.min(sx, sy);
  }, [boardOutline, canvasWidth, canvasHeight]);

  const toCanvas = useCallback(
    (x: number, y: number) => ({
      cx: margin + x * scale,
      cy: margin + y * scale,
    }),
    [scale, margin],
  );

  const boardRect = useMemo(() => ({
    x: margin,
    y: margin,
    w: (boardOutline.width || 100) * scale,
    h: (boardOutline.height || 80) * scale,
  }), [boardOutline, scale, margin]);

  const compShapes = useMemo(() =>
    placements.map(p => {
      const { cx, cy } = toCanvas(p.x, p.y);
      const w = (p.width || 5) * scale;
      const h = (p.height || 3) * scale;
      const color = COMP_COLORS[classifyComponent(p.reference)];
      return { reference: p.reference, cx, cy, w, h, color, rotation: p.rotation || 0 };
    }),
    [placements, toCanvas, scale],
  );

  const routeLines = useMemo(() =>
    routes.map(r => ({
      net: r.net,
      layer: r.layer || 'F.Cu',
      color: LAYER_COLORS[r.layer || 'F.Cu'] || '#90a4ae',
      points: (r.points || []).map(pt => toCanvas(pt.x, pt.y)),
    })),
    [routes, toCanvas],
  );

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom(z => Math.max(0.5, Math.min(3, z - e.deltaY * 0.001)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current) return;
    setPan(p => ({ x: p.x + (e.clientX - lastPos.current.x), y: p.y + (e.clientY - lastPos.current.y) }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseUp = useCallback(() => { dragging.current = false; }, []);

  return (
    <svg
      width={canvasWidth}
      height={canvasHeight}
      viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
      style={{ backgroundColor: '#1a1a1a', borderRadius: 6, cursor: 'grab' }}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
        {/* Board outline */}
        <rect
          x={boardRect.x} y={boardRect.y}
          width={boardRect.w} height={boardRect.h}
          rx={2}
          fill="#2d4a2d"
          stroke="#4caf50"
          strokeWidth={2}
        />

        {/* Grid */}
        <defs>
          <pattern id="pcb-grid" width={10 * scale} height={10 * scale} patternUnits="userSpaceOnUse">
            <circle cx={0.5} cy={0.5} r={0.5} fill="#3a5a3a" />
          </pattern>
        </defs>
        <rect x={boardRect.x} y={boardRect.y} width={boardRect.w} height={boardRect.h} fill="url(#pcb-grid)" />

        {/* Routes */}
        {routeLines.map((route, ri) =>
          route.points.length >= 2 ? (
            <polyline
              key={`route-${ri}`}
              points={route.points.map(p => `${p.cx},${p.cy}`).join(' ')}
              fill="none"
              stroke={route.color}
              strokeWidth={1.5}
              opacity={0.7}
            />
          ) : null
        )}

        {/* Components */}
        {compShapes.map((comp, ci) => (
          <g key={`comp-${ci}`} transform={`translate(${comp.cx},${comp.cy}) rotate(${comp.rotation})`}>
            <rect
              x={-comp.w / 2} y={-comp.h / 2}
              width={comp.w} height={comp.h}
              rx={2}
              fill={`${comp.color}33`}
              stroke={comp.color}
              strokeWidth={1}
            />
            {/* Pin 1 indicator */}
            <circle cx={-comp.w / 2 + 2} cy={-comp.h / 2 + 2} r={1.5} fill={comp.color} />
            <text
              x={0} y={0}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#e0e0e0"
              fontSize={Math.max(6, Math.min(10, comp.w * 0.2))}
              fontWeight={600}
              fontFamily="monospace"
            >
              {comp.reference}
            </text>
          </g>
        ))}

        {/* Vias */}
        {vias.map((v, vi) => {
          const { cx, cy } = toCanvas(v.x, v.y);
          return (
            <circle key={`via-${vi}`} cx={cx} cy={cy} r={2} fill="#ffd43b" stroke="#333" strokeWidth={0.5} />
          );
        })}
      </g>

      {/* Legend */}
      <g transform={`translate(8, ${canvasHeight - 50})`}>
        {Object.entries(LAYER_COLORS).slice(0, 2).map(([layer, color], i) => (
          <g key={layer} transform={`translate(${i * 70}, 0)`}>
            <line x1={0} y1={8} x2={16} y2={8} stroke={color} strokeWidth={2} />
            <text x={20} y={11} fill="#a0a0a0" fontSize={8} fontFamily="monospace">{layer}</text>
          </g>
        ))}
      </g>

      <text x={canvasWidth - 8} y={canvasHeight - 8} textAnchor="end" fill="#606060" fontSize={9} fontFamily="monospace">
        {Math.round(zoom * 100)}%
      </text>
    </svg>
  );
};

export default PCBLayoutPreview;
