/**
 * SchematicPreview.tsx - Mini schematic canvas preview
 *
 * Renders a lightweight visual representation of the generated schematic
 * using SVG. Shows components as labeled boxes, nets as colored lines.
 * Supports zoom and pan via mouse wheel + drag.
 */

import React, { useMemo, useCallback, useRef, useState } from 'react';

interface Component {
  reference?: string;
  name?: string;
  value?: string;
  model?: string;
  footprint?: string;
  category?: string;
  x?: number;
  y?: number;
}

interface Net {
  name: string;
  connections?: Array<{ component?: string; pin?: string | number }>;
}

interface SchematicPreviewProps {
  components: Component[];
  nets: Net[];
  width?: number;
  height?: number;
}

const COLORS = {
  bg: '#1a1a1a',
  grid: '#2a2a2a',
  component: {
    ic: '#4a9eff',
    passive: '#8bc34a',
    power: '#ff9800',
    connector: '#ab47bc',
    default: '#78909c',
  },
  net: {
    power: '#ff5252',
    ground: '#4caf50',
    signal: '#64b5f6',
    default: '#90a4ae',
  },
  text: {
    primary: '#e0e0e0',
    secondary: '#a0a0a0',
    muted: '#606060',
  },
};

function getComponentColor(comp: Component): string {
  const cat = (comp.category || '').toLowerCase();
  const name = (comp.name || comp.reference || '').toLowerCase();
  if (cat.includes('ic') || cat.includes('mcu') || name.includes('u') || name.includes('ic')) return COLORS.component.ic;
  if (cat.includes('power') || name.includes('ldo') || name.includes('reg')) return COLORS.component.power;
  if (cat.includes('connector') || name.includes('j') || name.includes('conn')) return COLORS.component.connector;
  if (cat.includes('resistor') || cat.includes('capacitor') || name.includes('r') || name.includes('c')) return COLORS.component.passive;
  return COLORS.component.default;
}

function getNetColor(netName: string): string {
  const n = netName.toLowerCase();
  if (n.includes('vcc') || n.includes('vdd') || n.includes('3v') || n.includes('5v') || n.includes('vin') || n.includes('power')) return COLORS.net.power;
  if (n.includes('gnd') || n.includes('vss') || n.includes('ground')) return COLORS.net.ground;
  return COLORS.net.signal;
}

function layoutComponents(components: Component[], canvasW: number, canvasH: number) {
  const margin = 20;
  const usableW = canvasW - 2 * margin;
  const usableH = canvasH - 2 * margin;
  const cols = Math.ceil(Math.sqrt(components.length * (usableW / usableH)));
  const rows = Math.ceil(components.length / cols);
  const cellW = usableW / cols;
  const cellH = usableH / rows;

  return components.map((comp, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const compW = Math.min(cellW * 0.8, 60);
    const compH = Math.min(cellH * 0.5, 30);
    return {
      ...comp,
      x: margin + col * cellW + (cellW - compW) / 2,
      y: margin + row * cellH + (cellH - compH) / 2,
      w: compW,
      h: compH,
    };
  });
}

export const SchematicPreview: React.FC<SchematicPreviewProps> = ({
  components,
  nets,
  width = 480,
  height = 300,
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  const laidOut = useMemo(() => layoutComponents(components, width, height), [components, width, height]);

  const refMap = useMemo(() => {
    const m = new Map<string, { x: number; y: number; w: number; h: number }>();
    laidOut.forEach(c => {
      const ref = c.reference || c.name || '';
      if (ref) m.set(ref, { x: c.x + c.w / 2, y: c.y + c.h / 2, w: c.w, h: c.h });
    });
    return m;
  }, [laidOut]);

  // Build net lines from connections
  const netLines = useMemo(() => {
    const lines: Array<{ x1: number; y1: number; x2: number; y2: number; color: string; name: string }> = [];
    for (const net of nets) {
      const conns = net.connections || [];
      if (conns.length < 2) continue;
      const color = getNetColor(net.name);
      for (let i = 0; i < conns.length - 1; i++) {
        const a = refMap.get(conns[i].component || '');
        const b = refMap.get(conns[i + 1].component || '');
        if (a && b) {
          lines.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, color, name: net.name });
        }
      }
    }
    return lines;
  }, [nets, refMap]);

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
    setPan(p => ({
      x: p.x + (e.clientX - lastPos.current.x),
      y: p.y + (e.clientY - lastPos.current.y),
    }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseUp = useCallback(() => { dragging.current = false; }, []);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ backgroundColor: COLORS.bg, borderRadius: 6, cursor: 'grab' }}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <defs>
        <pattern id="sch-grid" width={20} height={20} patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke={COLORS.grid} strokeWidth={0.5} />
        </pattern>
      </defs>

      <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
        {/* Grid */}
        <rect x={0} y={0} width={width} height={height} fill="url(#sch-grid)" />

        {/* Net lines */}
        {netLines.map((line, i) => (
          <line
            key={`net-${i}`}
            x1={line.x1} y1={line.y1}
            x2={line.x2} y2={line.y2}
            stroke={line.color}
            strokeWidth={1.5}
            opacity={0.6}
          />
        ))}

        {/* Components */}
        {laidOut.map((comp, i) => {
          const color = getComponentColor(comp);
          const label = comp.reference || comp.name || `C${i + 1}`;
          const value = comp.value || comp.model || '';
          return (
            <g key={`comp-${i}`}>
              <rect
                x={comp.x} y={comp.y}
                width={comp.w} height={comp.h}
                rx={4}
                fill={`${color}22`}
                stroke={color}
                strokeWidth={1.5}
              />
              <text
                x={comp.x + comp.w / 2}
                y={comp.y + comp.h / 2 - (value ? 4 : 0)}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={COLORS.text.primary}
                fontSize={9}
                fontWeight={600}
                fontFamily="monospace"
              >
                {label}
              </text>
              {value && (
                <text
                  x={comp.x + comp.w / 2}
                  y={comp.y + comp.h / 2 + 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={COLORS.text.muted}
                  fontSize={7}
                  fontFamily="monospace"
                >
                  {value.length > 10 ? value.slice(0, 10) + '…' : value}
                </text>
              )}
            </g>
          );
        })}
      </g>

      {/* Zoom indicator */}
      <text x={width - 8} y={height - 8} textAnchor="end" fill={COLORS.text.muted} fontSize={9} fontFamily="monospace">
        {Math.round(zoom * 100)}%
      </text>
    </svg>
  );
};

export default SchematicPreview;
