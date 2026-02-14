/**
 * 过孔渲染器
 * 支持选择
 */

import React, { useCallback } from 'react';
import { Group, Circle } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import { Via } from '../types';
import { MM_TO_PX } from '../data/samplePCB';
import { usePCBStore } from '../stores/pcbStore';

interface ViaRendererProps {
  via: Via;
}

const ViaRenderer: React.FC<ViaRendererProps> = ({ via }) => {
  const { id, position, size, drill } = via;
  
  // 从 store 获取状态
  const { selectedIds, toggleSelection } = usePCBStore();
  const selected = selectedIds.includes(id);
  
  // 转换到像素坐标
  const x = position.x * MM_TO_PX;
  const y = position.y * MM_TO_PX;
  const outerRadius = (size / 2) * MM_TO_PX;
  const innerRadius = (drill / 2) * MM_TO_PX;

  // 点击处理
  const handleClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.cancelBubble = true; // 防止冒泡到 Stage
    toggleSelection(id);
  }, [id, toggleSelection]);

  return (
    <Group onClick={handleClick} onTap={handleClick}>
      {/* 外圈 (铜) */}
      <Circle
        x={x}
        y={y}
        radius={outerRadius}
        fill="#8B4513" // 棕色铜色
        stroke={selected ? '#FFFF00' : '#FFFFFF'}
        strokeWidth={selected ? 2 : 1}
      />
      
      {/* 内圈 (孔) */}
      <Circle
        x={x}
        y={y}
        radius={innerRadius}
        fill="#000000" // 黑色孔
      />
    </Group>
  );
};

export default ViaRenderer;
