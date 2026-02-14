/**
 * 布线工具组件 (Phase 5.1)
 * 支持交互式绘制走线
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Layer, Line, Circle } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import { usePCBStore } from '../stores/pcbStore';
import { Track } from '../types';
import { MM_TO_PX } from '../data/samplePCB';
import { v4 as uuidv4 } from 'uuid';

interface RoutingToolProps {
  active: boolean;
}

const RoutingTool: React.FC<RoutingToolProps> = ({ active }) => {
  const { 
    addTrack, 
    setCurrentTool,
    snapToGrid, 
    gridSize,
    pcbData 
  } = usePCBStore();
  
  // 当前正在绘制的走线状态
  const [isRouting, setIsRouting] = useState(false);
  const [points, setPoints] = useState<{ x: number; y: number }[]>([]);
  const [currentMousePos, setCurrentMousePos] = useState<{ x: number; y: number } | null>(null);
  const [layer, setLayer] = useState('F.Cu');
  const [width, setWidth] = useState(0.2);

  // 吸附到网格
  const snapToGridFn = useCallback((pos: { x: number; y: number }) => {
    if (!snapToGrid) return pos;
    return {
      x: Math.round(pos.x / gridSize) * gridSize,
      y: Math.round(pos.y / gridSize) * gridSize
    };
  }, [snapToGrid, gridSize]);

  // 开始布线
  const startRouting = useCallback((e: KonvaEventObject<MouseEvent>) => {
    if (!active) return;
    
    const stage = e.target.getStage();
    if (!stage) return;
    
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
    
    // 考虑画布缩放和平移
    const transform = stage.getAbsoluteTransform().copy();
    transform.invert();
    const pos = transform.point(pointer);
    
    // 转换为毫米坐标
    const mmPos = {
      x: pos.x / MM_TO_PX,
      y: pos.y / MM_TO_PX
    };
    
    const snappedPos = snapToGridFn(mmPos);
    
    if (!isRouting) {
      // 开始新的走线
      setIsRouting(true);
      setPoints([snappedPos]);
    } else {
      // 添加新的点
      setPoints(prev => [...prev, snappedPos]);
    }
  }, [active, isRouting, snapToGridFn]);

  // 鼠标移动更新预览
  const handleMouseMove = useCallback((e: KonvaEventObject<MouseEvent>) => {
    if (!active || !isRouting) return;
    
    const stage = e.target.getStage();
    if (!stage) return;
    
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
    
    const transform = stage.getAbsoluteTransform().copy();
    transform.invert();
    const pos = transform.point(pointer);
    
    const mmPos = {
      x: pos.x / MM_TO_PX,
      y: pos.y / MM_TO_PX
    };
    
    setCurrentMousePos(snapToGridFn(mmPos));
  }, [active, isRouting, snapToGridFn]);

  // 完成布线
  const finishRouting = useCallback(() => {
    if (!isRouting || points.length < 2) {
      setIsRouting(false);
      setPoints([]);
      setCurrentMousePos(null);
      return;
    }
    
    // 创建新走线
    const newTrack: Track = {
      id: `track-${uuidv4()}`,
      type: 'track',
      layer,
      width,
      points,
      netId: undefined
    };
    
    addTrack(newTrack);
    
    // 重置状态
    setIsRouting(false);
    setPoints([]);
    setCurrentMousePos(null);
    
    // 切换到选择工具
    setCurrentTool('select');
  }, [isRouting, points, layer, width, addTrack, setCurrentTool]);

  // 取消布线
  const cancelRouting = useCallback(() => {
    setIsRouting(false);
    setPoints([]);
    setCurrentMousePos(null);
  }, []);

  // 键盘事件
  useEffect(() => {
    if (!active) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        cancelRouting();
      } else if (e.key === 'Enter' && isRouting) {
        finishRouting();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [active, isRouting, cancelRouting, finishRouting]);

  // 渲染预览线
  const renderPreview = () => {
    if (!isRouting || points.length === 0 || !currentMousePos) return null;
    
    const previewPoints = [
      ...points,
      currentMousePos
    ].flatMap(p => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
    
    return (
      <Line
        points={previewPoints}
        stroke="#FFFF00"
        strokeWidth={width * MM_TO_PX}
        dash={[5, 5]}
        opacity={0.7}
      />
    );
  };

  // 渲染已放置的点
  const renderPoints = () => {
    return points.map((point, index) => (
      <Circle
        key={index}
        x={point.x * MM_TO_PX}
        y={point.y * MM_TO_PX}
        radius={3}
        fill="#4a9eff"
        stroke="#ffffff"
        strokeWidth={1}
      />
    ));
  };

  if (!active) return null;

  return (
    <>
      {/* 点击层捕获事件 */}
      <Layer
        onClick={startRouting}
        onMouseMove={handleMouseMove}
        onDblClick={finishRouting}
      >
        {renderPoints()}
        {renderPreview()}
      </Layer>
      
      {/* 布线状态提示 */}
      {isRouting && (
        <div
          style={{
            position: 'absolute',
            top: 60,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(74, 158, 255, 0.9)',
            color: '#ffffff',
            padding: '8px 16px',
            borderRadius: 4,
            fontSize: 12,
            zIndex: 100,
            pointerEvents: 'none'
          }}
        >
          布线中... 点击添加点，双击完成，ESC取消
        </div>
      )}
    </>
  );
};

export default RoutingTool;
