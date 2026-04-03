/**
 * 走线渲染器 (Task 2.3 + Phase 10B-2: Diff pair highlighting)
 * 支持选择、差分对特殊颜色
 */

import React, { useCallback, useMemo } from 'react';
import { Line, Circle } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import { Track } from '../types';
import { MM_TO_PX } from '../data/samplePCB';
import { usePCBStore } from '../stores/pcbStore';

// Diff pair net name patterns
const DIFF_POS_PATTERNS = [
  /DIFF_P/i, /D\+/, /TX\+/, /RX\+/, /DIN\+/, /DOUT\+/,
  /DP\d/i, /DATA_P/i, /USB_DP/i, /HS_P/i, /_P$/i,
];
const DIFF_NEG_PATTERNS = [
  /DIFF_N/i, /D\-/, /TX\-/, /RX\-/, /DIN\-/, /DOUT\-/,
  /DN\d/i, /DATA_N/i, /USB_DM/i, /HS_N/i, /_N$/i,
];

function isDiffPairPos(netName: string): boolean {
  return DIFF_POS_PATTERNS.some(p => p.test(netName));
}
function isDiffPairNeg(netName: string): boolean {
  return DIFF_NEG_PATTERNS.some(p => p.test(netName));
}
function isDiffPair(netName: string): boolean {
  return isDiffPairPos(netName) || isDiffPairNeg(netName);
}

// Layer colors
const LAYER_COLORS: Record<string, string> = {
  'F.Cu': '#FF0000',   // Red for top copper
  'B.Cu': '#00FF00',   // Green for bottom copper
  'In1.Cu': '#FF8C00', // Orange for inner 1
  'In2.Cu': '#8A2BE2', // Purple for inner 2
};

// Diff pair colors
const DIFF_POS_COLOR = '#00BFFF';  // Deep sky blue for positive
const DIFF_NEG_COLOR = '#FF69B4';  // Hot pink for negative

interface TrackRendererProps {
  track: Track;
}

const TrackRenderer: React.FC<TrackRendererProps> = ({ track }) => {
  const { id, points, width, layer, net, netId } = track;
  const netName = net || netId || '';

  // 从 store 获取状态
  const { selectedIds, toggleSelection, currentTool, updateTrackPoints } = usePCBStore();
  const selected = selectedIds.includes(id);

  // 使用 useMemo 缓存像素坐标计算结果
  const pixelPoints = useMemo(() =>
    points.flatMap((p) => [p.x * MM_TO_PX, p.y * MM_TO_PX]),
    [points]
  );

  // Phase 10B-2: Color logic with diff pair highlighting
  const color = useMemo(() => {
    if (selected) return '#FFFF00';

    // Diff pair highlighting takes priority
    if (netName && isDiffPairPos(netName)) return DIFF_POS_COLOR;
    if (netName && isDiffPairNeg(netName)) return DIFF_NEG_COLOR;

    // Standard layer color
    return LAYER_COLORS[layer] || '#00FF00';
  }, [selected, layer, netName]);

  // Diff pair tracks get a slightly different stroke style
  const isDiff = netName && isDiffPair(netName);

  // 点击处理
  const handleClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.cancelBubble = true; // 防止冒泡到 Stage
    toggleSelection(id);
  }, [id, toggleSelection]);

  // 处理端点拖拽
  const handlePointDrag = useCallback((pointIndex: number, newX: number, newY: number) => {
    if (!updateTrackPoints) return;

    const newPoints = [...points];
    newPoints[pointIndex] = { x: newX / MM_TO_PX, y: newY / MM_TO_PX };
    updateTrackPoints(id, newPoints);
  }, [id, points, updateTrackPoints]);

  // 使用 useMemo 缓存每个端点的拖拽回调
  const handlePointDragMemo = useCallback((pointIndex: number) =>
    (e: KonvaEventObject<DragEvent>) => {
      handlePointDrag(pointIndex, e.target.x(), e.target.y());
    },
    [handlePointDrag]
  );

  // 点击事件回调
  const handleCircleClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.cancelBubble = true;
  }, []);

  // 确保走线有最小宽度（放大显示以便调试）
  const minTrackWidth = 10; // 最小2像素
  const trackWidth = Math.max((width || 0.25) * MM_TO_PX, minTrackWidth);

  return (
    <>
      <Line
        points={pixelPoints}
        stroke={color}
        strokeWidth={trackWidth}
        hitStrokeWidth={Math.max(trackWidth, 10)} // 增加点击区域
        onClick={handleClick}
        onTap={handleClick}
        // Diff pair: slightly dashed outer glow effect via opacity
        opacity={isDiff && !selected ? 0.9 : 1}
      />
      {/* Diff pair: render a thin dashed centerline for visual distinction */}
      {isDiff && !selected && (
        <Line
          points={pixelPoints}
          stroke={isDiffPairPos(netName) ? '#FFFFFF' : '#FFFFFF'}
          strokeWidth={1}
          dash={[4, 4]}
          opacity={0.4}
          listening={false}
        />
      )}
      {/* 选中时显示端点手柄 */}
      {selected && currentTool === 'select' && points.map((point, index) => (
        <Circle
          key={`${id}-endpoint-${index}`}
          x={point.x * MM_TO_PX}
          y={point.y * MM_TO_PX}
          radius={6}
          fill={isDiff ? (isDiffPairPos(netName) ? DIFF_POS_COLOR : DIFF_NEG_COLOR) : '#FFFF00'}
          stroke="#000000"
          strokeWidth={1}
          draggable
          onDragMove={handlePointDragMemo(index)}
          onClick={handleCircleClick}
        />
      ))}
    </>
  );
};

// Export the diff pair detection utilities for reuse
export { isDiffPair, isDiffPairPos, isDiffPairNeg, DIFF_POS_COLOR, DIFF_NEG_COLOR };

export default TrackRenderer;
