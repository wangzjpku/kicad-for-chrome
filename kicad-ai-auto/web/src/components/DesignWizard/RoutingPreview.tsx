/**
 * RoutingPreview.tsx - Routing result visualization
 *
 * Shows routed traces on the PCB with color-coded layers,
 * via positions, and unrouted net guides as dashed lines.
 */

import React, { useMemo, useCallback, useRef, useState } from 'react';

interface RoutedTrack {
  net: string;
  points: Array<{ x: number; y: number }>;
  layer: string;
  width?: number;
}

interface Via {
  x: number;
  y: number;
  net?: string;
}

interface UnroutedNet {
  name: string;
  start: { x: number; y: number };
  end: { x: number; y: number };
}

interface RoutingPreviewProps {
  tracks: RoutedTrack[];
  vias: Via[];
  unroutedNets?: UnroutedNet[];
  boardWidth?: number;
  boardHeight?: number;
  canvasWidth?: number;
  canvasHeight?: number;
}

const TRACK_COLORS: Record<string, string> = {
  'F.Cu': '#ef5350',
  'B.Cu': '#42a5f5',
  'In1.Cu': '#66bb6a',
  'In2.Cu': '#ffca28',
};

function getNetColor(net: string): string {
  const n = net.toLowerCase();
  if (n.includes('gnd') || n.includes('vss')) return '#4caf50';
  if (n.includes('vcc') || n.includes('vdd') || n.includes('3v') || n.includes('5v') || n.includes('power')) return '#ff5722';
  if (n.includes('diff') || n.includes('_p') || n.includes('_n')) return '#e040fb';
  return '#64b5f6';
}

export const RoutingPreview: React.FC<RoutingPreviewProps> = ({
  tracks,
  vias,
  unroutedNets = [],
  boardWidth = 100,
  boardHeight = 80,
  canvasWidth = 480,
  canvasHeight = 300,
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  const margin = 20;
  const scale = useMemo(() => {
    const sx = (canvasWidth - 2 * margin) / boardWidth;
    const sy = (canvasHeight - 2 * margin) / boardHeight;
    return Math.min(sx, sy);
  }, [boardWidth, boardHeight, canvasWidth, canvasHeight]);

  const toC = useCallback(
    (x: number, y: number) => ({ x: margin + x * scale, y: margin + y * scale }),
    [scale, margin],
  );

  const trackPaths = useMemo(() =>
    tracks.map((t, i) => ({
      key: `track-${i}`,
      points: t.points.map(p => toC(p.x, p.y)),
      layer: t.layer,
      net: t.net,
      width: Math.max(1, (t.width || 0.25) * scale),
    })),
    [tracks, toC, scale],
  );

  const viaDots = useMemo(() =>
    vias.map((v, i) => ({ key: `via-${i}`, ...toC(v.x, v.y) })),
    [vias, toC],
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

  const totalLength = useMemo(() => {
    let len = 0;
    for (const t of tracks) {
      for (let i = 1; i < t.points.length; i++) {
        const dx = t.points[i].x - t.points[i - 1].x;
        const dy = t.points[i].y - t.points[i - 1].y;
        len += Math.sqrt(dx * dx + dy * dy);
      }
    }
    return len;
  }, [tracks]);

  return (
    <div style={{ position: 'relative' }}>
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
          {/* Board */}
          <rect
            x={margin} y={margin}
            width={boardWidth * scale} height={boardHeight * scale}
            rx={2}
            fill="#263238"
            stroke="#546e7a"
            strokeWidth={1.5}
          />

          {/* Unrouted nets (dashed guide lines) */}
          {unroutedNets.map((net, i) => {
            const s = toC(net.start.x, net.start.y);
            const e = toC(net.end.x, net.end.y);
            return (
              <line
                key={`unrouted-${i}`}
                x1={s.x} y1={s.y} x2={e.x} y2={e.y}
                stroke="#ff572266"
                strokeWidth={1}
                strokeDasharray="4 4"
              />
            );
          })}

          {/* Routed tracks */}
          {trackPaths.map(t =>
            t.points.length >= 2 ? (
              <polyline
                key={t.key}
                points={t.points.map(p => `${p.x},${p.y}`).join(' ')}
                fill="none"
                stroke={TRACK_COLORS[t.layer] || '#64b5f6'}
                strokeWidth={t.width}
                opacity={0.85}
                strokeLinejoin="round"
              />
            ) : null,
          )}

          {/* Vias */}
          {viaDots.map(v => (
            <g key={v.key}>
              <circle cx={v.x} cy={v.y} r={3} fill="#263238" stroke="#ffd54f" strokeWidth={1.5} />
              <circle cx={v.x} cy={v.y} r={1} fill="#ffd54f" />
            </g>
          ))}
        </g>

        {/* Stats overlay */}
        <g transform={`translate(8, 12)`}>
          <text fill="#a0a0a0" fontSize={9} fontFamily="monospace">
            Tracks: {tracks.length} | Vias: {vias.length} | Total: {totalLength.toFixed(1)}mm
          </text>
        </g>
      </svg>
    </div>
  );
};

export default RoutingPreview;
