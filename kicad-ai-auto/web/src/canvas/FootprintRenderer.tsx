/**
 * 封装渲染器 (Task 2.2, 2.5)
 * 支持选择和拖拽
 */

import React, { useCallback, useRef } from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import { Footprint } from '../types';
import { MM_TO_PX } from '../data/samplePCB';
import { usePCBStore } from '../stores/pcbStore';

interface FootprintRendererProps {
  footprint: Footprint;
}

const FootprintRenderer: React.FC<FootprintRendererProps> = ({ footprint }) => {
  const { id, position, rotation, layer, reference, pads, pad } = footprint;
  // 兼容后端返回的 pad 和 pads 两种字段名
  const padList = pads || pad || [];

  // 从 store 获取状态和操作
  const { selectedIds, toggleSelection, currentTool, updateFootprintPosition, pushHistory, gridSize, snapToGrid } = usePCBStore();
  const selected = selectedIds.includes(id);
  
  // 用于保存拖拽开始时的位置
  const dragStartPos = useRef({ x: 0, y: 0 });
  
  // 转换位置到像素
  const x = position.x * MM_TO_PX;
  const y = position.y * MM_TO_PX;
  
  // 根据层设置颜色
  const color = layer === 'F.Cu' ? '#FF0000' : '#00FF00';
  const highlightColor = selected ? '#FFFF00' : color;

  // 点击处理
  const handleClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.cancelBubble = true; // 防止冒泡到 Stage
    toggleSelection(id);
  }, [id, toggleSelection]);

  // 拖拽开始 - 保存历史记录
  const handleDragStart = useCallback((e: KonvaEventObject<DragEvent>) => {
    dragStartPos.current = { x: e.target.x(), y: e.target.y() };
    pushHistory(); // 保存历史，支持撤销
  }, [pushHistory]);

  // 拖拽中 - 网格吸附
  const handleDragMove = useCallback((e: KonvaEventObject<DragEvent>) => {
    if (!snapToGrid) return;
    
    const node = e.target;
    // 转换回毫米
    let newX = node.x() / MM_TO_PX;
    let newY = node.y() / MM_TO_PX;
    
    // 网格吸附
    newX = Math.round(newX / gridSize) * gridSize;
    newY = Math.round(newY / gridSize) * gridSize;
    
    // 转换回像素并设置位置
    node.x(newX * MM_TO_PX);
    node.y(newY * MM_TO_PX);
  }, [snapToGrid, gridSize]);

  // 拖拽结束
  const handleDragEnd = useCallback((e: KonvaEventObject<DragEvent>) => {
    const node = e.target;
    // 转换回毫米坐标
    const newX = node.x() / MM_TO_PX;
    const newY = node.y() / MM_TO_PX;
    updateFootprintPosition(id, { x: newX, y: newY });
  }, [id, updateFootprintPosition]);

  // 只有选择工具或移动工具时可以拖拽
  const draggable = selected && (currentTool === 'select' || currentTool === 'move');

  return (
    <Group
      x={x}
      y={y}
      rotation={(rotation || 0)}
      onClick={handleClick}
      onTap={handleClick}
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragMove={handleDragMove}
      onDragEnd={handleDragEnd}
    >
      {/* 绘制焊盘 */}
      {padList.map((pad) => (
        <Rect
          key={pad.id}
          x={pad.position.x * MM_TO_PX - (pad.size.x * MM_TO_PX) / 2}
          y={pad.position.y * MM_TO_PX - (pad.size.y * MM_TO_PX) / 2}
          width={pad.size.x * MM_TO_PX}
          height={pad.size.y * MM_TO_PX}
          fill={highlightColor}
          stroke={selected ? '#FFFF00' : '#FFFFFF'}
          strokeWidth={selected ? 2 : 1}
        />
      ))}
      
      {/* 位号文字 */}
      <Text
        text={reference}
        x={-15}
        y={-25}
        fontSize={12}
        fill="#FFFFFF"
        align="center"
      />
      
      {/* 选中高亮框 */}
      {selected && (
        <Rect
          x={-20}
          y={-20}
          width={40}
          height={40}
          stroke="#FFFF00"
          strokeWidth={2}
          dash={[5, 5]}
        />
      )}
    </Group>
  );
};

export default FootprintRenderer;
