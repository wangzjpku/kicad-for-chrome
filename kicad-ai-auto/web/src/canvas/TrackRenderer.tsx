/**
 * 走线渲染器 (Task 2.3)
 * 支持选择
 */

import React, { useCallback } from 'react';
import { Line } from 'react-konva';
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
  const { selectedIds, toggleSelection } = usePCBStore();
  const selected = selectedIds.includes(id);
  
  // 将点数组转换为像素坐标
  const pixelPoints = points.flatMap((p) => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
  
  // 根据层设置颜色
  const layerColor = layer === 'F.Cu' ? '#FF0000' : '#00FF00';
  const color = selected ? '#FFFF00' : layerColor;

  // 点击处理
  const handleClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.cancelBubble = true; // 防止冒泡到 Stage
    toggleSelection(id);
  }, [id, toggleSelection]);

  // 确保走线有最小宽度（放大显示以便调试）
  const minTrackWidth = 2; // 最小2像素
  const trackWidth = Math.max((width || 0.25) * MM_TO_PX, minTrackWidth);

  return (
    <Line
      points={pixelPoints}
      stroke={color}
      strokeWidth={trackWidth}
      hitStrokeWidth={Math.max(trackWidth, 10)} // 增加点击区域
      onClick={handleClick}
      onTap={handleClick}
    />
  );
};

export default TrackRenderer;
