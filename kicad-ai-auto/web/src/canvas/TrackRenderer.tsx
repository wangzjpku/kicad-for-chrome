/**
 * 走线渲染器 (Task 2.3)
 * 支持选择
 */

import React, { useCallback, useMemo } from 'react';
import { Line, Circle } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import { Track } from '../types';
import { MM_TO_PX } from '../data/samplePCB';
import { usePCBStore } from '../stores/pcbStore';

interface TrackRendererProps {
  track: Track;
}

const TrackRenderer: React.FC<TrackRendererProps> = ({ track }) => {
  const { id, points, width, layer } = track;

  // 从 store 获取状态
  const { selectedIds, toggleSelection, currentTool, updateTrackPoints } = usePCBStore();
  const selected = selectedIds.includes(id);
  
  // 使用 useMemo 缓存像素坐标计算结果
  const pixelPoints = useMemo(() => 
    points.flatMap((p) => [p.x * MM_TO_PX, p.y * MM_TO_PX]),
    [points]
  );
  
  // 使用 useMemo 缓存颜色
  const layerColor = useMemo(() => layer === 'F.Cu' ? '#FF0000' : '#00FF00', [layer]);
  const color = selected ? '#FFFF00' : layerColor;

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
      />
      {/* 选中时显示端点手柄 */}
      {selected && currentTool === 'select' && points.map((point, index) => (
        <Circle
          key={`${id}-endpoint-${index}`}
          x={point.x * MM_TO_PX}
          y={point.y * MM_TO_PX}
          radius={6}
          fill="#FFFF00"
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

export default TrackRenderer;
