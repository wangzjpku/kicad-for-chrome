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
  const { selectedIds, toggleSelection, setSelectedIds, currentTool, updateFootprintPosition, pushHistory, gridSize, snapToGrid } = usePCBStore();
  const selected = selectedIds.includes(id);
  
  // 用于保存拖拽开始时的位置
  const dragStartPos = useRef({ x: 0, y: 0 });
  
  // 转换位置到像素（添加安全检查，防止NaN）
  const safeX = (position?.x ?? 0);
  const safeY = (position?.y ?? 0);
  const x = safeX * MM_TO_PX;
  const y = safeY * MM_TO_PX;
  
  // 根据层设置颜色
  const color = layer === 'F.Cu' ? '#FF0000' : '#00FF00';
  const highlightColor = selected ? '#FFFF00' : color;

  // 点击处理
  const handleClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.evt.stopPropagation(); // 阻止DOM事件冒泡到 Stage
    e.cancelBubble = true; // 阻止Konva事件冒泡
    console.log('[FootprintRenderer] Clicked:', id, reference);
    toggleSelection(id);
  }, [id, toggleSelection, reference]);

  // 拖拽开始 - 保存历史记录并自动选中
  const handleDragStart = useCallback((e: KonvaEventObject<DragEvent>) => {
    dragStartPos.current = { x: e.target.x(), y: e.target.y() };
    // 选择工具下拖动时自动选中该footprint
    if (currentTool === 'select' && !selected) {
      setSelectedIds([id]);
    }
    pushHistory(); // 保存历史，支持撤销
  }, [pushHistory, currentTool, selected, id, setSelectedIds]);

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

  // 选择工具或移动工具时可以拖拽
  // 选择工具下：可以直接拖动任何footprint（无需预先选中）
  // 移动工具下：可以拖动已选中的footprint
  const draggable = (currentTool === 'select') || (selected && currentTool === 'move');

  // 如果没有焊盘，渲染一个默认的封装形状（放大以便可见和点击）
  const renderDefaultFootprint = () => {
    return (
      <Rect
        x={-20}
        y={-20}
        width={40}
        height={40}
        fill={highlightColor}
        stroke={selected ? '#FFFF00' : color}
        strokeWidth={selected ? 2 : 1}
        listening={false}
      />
    );
  };

  // 点击目标区域大小（确保有足够大的可点击区域）
  const HIT_AREA_SIZE = 40;

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
      {/* 透明点击区域 - 增大可点击范围 */}
      <Rect
        x={-HIT_AREA_SIZE / 2}
        y={-HIT_AREA_SIZE / 2}
        width={HIT_AREA_SIZE}
        height={HIT_AREA_SIZE}
        fill="rgba(0,0,0,0.001)"
        listening={true}
      />

      {/* 绘制焊盘 */}
      {padList.length > 0 ? (
        padList.map((pad) => {
          // 确保焊盘有最小可见尺寸（放大显示以便用户容易点击）
          const minSize = 12; // 最小12像素，更容易点击
          const padWidth = Math.max(pad.size.x * MM_TO_PX, minSize);
          const padHeight = Math.max(pad.size.y * MM_TO_PX, minSize);
          return (
            <Rect
              key={pad.id}
              x={pad.position.x * MM_TO_PX - padWidth / 2}
              y={pad.position.y * MM_TO_PX - padHeight / 2}
              width={padWidth}
              height={padHeight}
              fill={highlightColor}
              stroke={selected ? '#FFFF00' : '#FFFFFF'}
              strokeWidth={selected ? 2 : 1}
              listening={false}
            />
          );
        })
      ) : (
        // 没有焊盘时渲染默认形状
        renderDefaultFootprint()
      )}

      {/* 位号文字 */}
      <Text
        text={reference}
        x={-15}
        y={-25}
        fontSize={12}
        fill="#FFFFFF"
        align="center"
        listening={false}
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
          listening={false}
        />
      )}
    </Group>
  );
};

export default FootprintRenderer;
