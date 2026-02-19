/**
 * 完整 PCB 画布组件 (Task 2.4)
 * 集成所有渲染器 + 使用 simpleStore
 */

import React, { useRef, useCallback } from 'react';
import { Stage, Layer, Line, Text } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import type { Stage as StageType } from 'konva/lib/Stage';

import { PCBData } from '../types';
import BoardOutlineRenderer from './BoardOutlineRenderer';
import FootprintRenderer from './FootprintRenderer';
import TrackRenderer from './TrackRenderer';
import ViaRenderer from './ViaRenderer';
import { usePCBStore } from '../stores/pcbStore';

interface PCBCanvasProps {
  pcbData: PCBData;
  width?: number;
  height?: number;
}

// 网格配置
const GRID_SIZE = 10; // 像素
const GRID_COLOR = '#333333';

const PCBCanvas: React.FC<PCBCanvasProps> = ({
  pcbData,
  width = 1000,
  height = 800,
}) => {
  const stageRef = useRef<StageType>(null);
  
  // 从 store 获取状态
  const {
    zoom,
    setZoom,
    pan,
    setPan,
    clearSelection,
  } = usePCBStore();

  // 滚轮缩放
  const handleWheel = useCallback((e: KonvaEventObject<WheelEvent>) => {
    if (!e.evt) return;
    e.evt.preventDefault();
    
    const stage = stageRef.current;
    if (!stage) return;

    const oldScale = zoom;
    const pointer = stage.getPointerPosition();
    if (!pointer) return;

    const scaleBy = 1.1;
    const newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;
    const clampedScale = Math.max(0.1, Math.min(newScale, 10));
    
    const mousePointTo = {
      x: (pointer.x - pan.x) / oldScale,
      y: (pointer.y - pan.y) / oldScale,
    };
    
    const newPos = {
      x: pointer.x - mousePointTo.x * clampedScale,
      y: pointer.y - mousePointTo.y * clampedScale,
    };
    
    setZoom(clampedScale);
    setPan(newPos);
  }, [zoom, pan, setZoom, setPan]);

  // 点击空白处取消选择 (Task 2.4)
  const handleStageClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    // 如果点击的是 Stage 本身 (不是子元素)
    const stage = e.target.getStage?.();
    if (stage && e.target === stage) {
      clearSelection();
    }
  }, [clearSelection]);

  // 拖拽平移
  const handleDragMove = useCallback((e: KonvaEventObject<DragEvent>) => {
    setPan({
      x: e.target.x(),
      y: e.target.y(),
    });
  }, [setPan]);

  // 拖拽结束 - 更新最终的平移位置
  const handleDragEnd = useCallback((e: KonvaEventObject<DragEvent>) => {
    setPan({
      x: e.target.x(),
      y: e.target.y(),
    });
  }, [setPan]);

  // 生成网格线
  const generateGridLines = () => {
    const lines = [];
    const gridSize = GRID_SIZE * zoom;
    const offsetX = pan.x % gridSize;
    const offsetY = pan.y % gridSize;
    
    for (let x = offsetX; x <= width; x += gridSize) {
      lines.push(
        <Line
          key={`v-${x}`}
          points={[x, 0, x, height]}
          stroke={GRID_COLOR}
          strokeWidth={1 / zoom}
        />
      );
    }
    
    for (let y = offsetY; y <= height; y += gridSize) {
      lines.push(
        <Line
          key={`h-${y}`}
          points={[0, y, width, y]}
          stroke={GRID_COLOR}
          strokeWidth={1 / zoom}
        />
      );
    }
    
    return lines;
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#000000',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* 缩放比例显示 */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          color: '#FFFFFF',
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          padding: '5px 10px',
          borderRadius: 4,
          fontFamily: 'monospace',
          fontSize: 12,
          zIndex: 10,
        }}
      >
        Zoom: {(zoom * 100).toFixed(0)}%
      </div>

      <Stage
        ref={stageRef}
        width={width}
        height={height}
        onWheel={handleWheel}
        onClick={handleStageClick}
        draggable={true}
        onDragMove={handleDragMove}
        onDragEnd={handleDragEnd}
        x={pan.x}
        y={pan.y}
        style={{
          cursor: 'grab',
        }}
      >
        {/* 背景网格层 */}
        <Layer>{generateGridLines()}</Layer>

        {/* PCB 元素层 (应用缩放) */}
        <Layer scaleX={zoom} scaleY={zoom}>
          {/* 板框 */}
          <BoardOutlineRenderer outline={pcbData.boardOutline} />

          {/* 走线 */}
          {pcbData.tracks.map((track) => (
            <TrackRenderer key={track.id} track={track} />
          ))}

          {/* 过孔 */}
          {pcbData.vias.map((via) => (
            <ViaRenderer key={via.id} via={via} />
          ))}

          {/* 封装 */}
          {pcbData.footprints.map((footprint) => (
            <FootprintRenderer key={footprint.id} footprint={footprint} />
          ))}
        </Layer>

        {/* UI 层 */}
        <Layer>
          <Text
            text="X"
            x={width - 30}
            y={height / 2}
            fill="#666666"
            fontSize={12}
          />
          <Text
            text="Y"
            x={width / 2}
            y={10}
            fill="#666666"
            fontSize={12}
          />
        </Layer>
      </Stage>
    </div>
  );
};

export default PCBCanvas;
