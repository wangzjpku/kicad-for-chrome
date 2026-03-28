/**
 * 封装渲染器 (Task 2.2, 2.5)
 * 支持选择和拖拽
 */

import React, { useCallback, useRef } from 'react';
import { Group, Rect, Text, Line, Circle } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import { Footprint, FootprintGraphic, Pad } from '../types';
import { MM_TO_PX } from '../data/samplePCB';
import { usePCBStore } from '../stores/pcbStore';

interface FootprintRendererProps {
  footprint: Footprint;
}

const FootprintRenderer: React.FC<FootprintRendererProps> = ({ footprint }) => {
  const { id, position, rotation, layer, reference, pads, pad, silkscreen } = footprint;
  // 兼容后端返回的 pad 和 pads 两种字段名
  const padList: Pad[] = pads || pad || [];

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
    if (e.evt) {
      e.evt.stopPropagation(); // 阻止DOM事件冒泡到 Stage
    }
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

  // 渲染silkscreen图形
  const renderSilkscreen = () => {
    if (!silkscreen || silkscreen.length === 0) {
      // 没有silkscreen数据时，生成一个简单的边框
      if (padList.length > 0) {
        // 根据焊盘位置生成一个简单的边框
        const minX = Math.min(...padList.map((p) => (p.position?.x ?? 0) - ((p.size?.x ?? 1) / 2)));
        const maxX = Math.max(...padList.map((p) => (p.position?.x ?? 0) + ((p.size?.x ?? 1) / 2)));
        const minY = Math.min(...padList.map((p) => (p.position?.y ?? 0) - ((p.size?.y ?? 1) / 2)));
        const maxY = Math.max(...padList.map((p) => (p.position?.y ?? 0) + ((p.size?.y ?? 1) / 2)));
        const margin = 0.8;
        return (
          <Rect
            key="silk-default"
            x={(minX - margin) * MM_TO_PX}
            y={(minY - margin) * MM_TO_PX}
            width={(maxX - minX + margin * 2) * MM_TO_PX}
            height={(maxY - minY + margin * 2) * MM_TO_PX}
            stroke="#888888"
            strokeWidth={2}
            listening={false}
          />
        );
      }
      return null;
    }

    return silkscreen.map((item: FootprintGraphic, index: number) => {
      if (item.type === 'line') {
        return (
          <Line
            key={`silk-${index}`}
            points={[
              (item.x1 || 0) * MM_TO_PX,
              (item.y1 || 0) * MM_TO_PX,
              (item.x2 || 0) * MM_TO_PX,
              (item.y2 || 0) * MM_TO_PX
            ]}
            stroke="#888888"
            strokeWidth={2}
            listening={false}
          />
        );
      } else if (item.type === 'rect') {
        const x = Math.min(item.x1 || 0, item.x2 || 0);
        const y = Math.min(item.y1 || 0, item.y2 || 0);
        const width = Math.abs((item.x2 || 0) - (item.x1 || 0));
        const height = Math.abs((item.y2 || 0) - (item.y1 || 0));
        return (
          <Rect
            key={`silk-${index}`}
            x={x * MM_TO_PX}
            y={y * MM_TO_PX}
            width={width * MM_TO_PX}
            height={height * MM_TO_PX}
            stroke="#888888"
            strokeWidth={2}
            listening={false}
          />
        );
      } else if (item.type === 'circle') {
        return (
          <Circle
            key={`silk-${index}`}
            x={(item.cx || 0) * MM_TO_PX}
            y={(item.cy || 0) * MM_TO_PX}
            radius={Math.sqrt(Math.pow(((item.x1 || 0) - (item.cx || 0)) * MM_TO_PX, 2) + Math.pow(((item.y1 || 0) - (item.cy || 0)) * MM_TO_PX, 2))}
            stroke="#888888"
            strokeWidth={2}
            listening={false}
          />
        );
      }
      return null;
    });
  };

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

      {/* 绘制丝印图形 */}
      {renderSilkscreen()}

      {/* 绘制焊盘 */}
      {padList.length > 0 ? (
        padList.map((pad) => {
          // 确保焊盘有最小可见尺寸（放大显示以便用户容易点击）
          const minSize = 30; // 最小12像素，更容易点击
          // 兼容没有size属性的情况，使用默认值
          const padWidth = Math.max((pad.size?.x ?? 1) * MM_TO_PX, minSize);
          const padHeight = Math.max((pad.size?.y ?? 1) * MM_TO_PX, minSize);
          // 兼容没有position的情况
          const padX = pad.position?.x ?? 0;
          const padY = pad.position?.y ?? 0;
          return (
            <Rect
              key={pad.id}
              x={padX * MM_TO_PX - padWidth / 2}
              y={padY * MM_TO_PX - padHeight / 2}
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
