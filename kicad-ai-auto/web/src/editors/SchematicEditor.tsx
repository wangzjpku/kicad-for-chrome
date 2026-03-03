/**
 * 原理图编辑器 (SchematicEditor)
 * 基于 Konva 的原理图编辑画布
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Stage, Layer, Line, Text, Group, Rect, Circle } from 'react-konva';
import type { Stage as StageType } from 'konva/lib/Stage';
import type { KonvaEventObject } from 'konva/lib/Node';
import Konva from 'konva';

// Note: Konva.useStrictMode is not available in Konva 9.3.33
// React 18 compatibility is handled through proper ref management below

import { useSchematicStore } from '../stores/schematicStore';
import { SchematicComponent, Wire, Label } from '../types';
import { v4 as uuidv4 } from 'uuid';
import SchematicSymbol from '../components/SchematicSymbol';
import SchematicDebugOverlay, { calculateRecommendedPan } from '../components/SchematicDebugOverlay';

// 原理图坐标转换 - 后端返回的是mm坐标，需要转换为像素
// 元件坐标范围约 0-800mm，画布约 800x500px，所以用 0.5 缩放让元件合适显示
const MM_TO_PX = 0.5;

// 网格配置
const GRID_SIZE = 10;
const GRID_COLOR = '#333333';  // 网格颜色

interface SchematicEditorProps {
  width?: number;
  height?: number;
}

// 示例原理图数据
const createEmptySchematic = () => ({
  id: 'schematic-001',
  projectId: 'project-001',
  sheets: [
    { id: 'sheet-1', name: 'Root', pageNumber: 1, width: 297, height: 210 }
  ],
  components: [],
  wires: [],
  labels: [],
  powerSymbols: [],
  nets: [
    { id: 'net-gnd', name: 'GND' },
    { id: 'net-vcc', name: 'VCC' },
    { id: 'net-5v', name: '+5V' }
  ]
});

const SchematicEditor: React.FC<SchematicEditorProps> = ({
  width: propWidth = 800,
  height: propHeight = 500
}) => {
  // Fix: Use function-based ref with state to track Layer instance
  const [stageRef, setStageRef] = useState<StageType | null>(null);
  const [contentLayer, setContentLayer] = useState<Konva.Layer | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debug: Log when contentLayer changes
  useEffect(() => {
    if (contentLayer) {
      console.log('[SchematicEditor] Content Layer ref set, _id:', (contentLayer as any)._id, 'children count:', contentLayer.getChildren().length);
    }
  }, [contentLayer]);
  const [showDebug, setShowDebug] = useState(false); // 调试模式
  const [containerSize, setContainerSize] = useState({
    width: 800,
    height: 500
  });

  // 自动调整画布尺寸 - 使用 ResizeObserver 监听整个容器树
  useEffect(() => {
    const DEFAULT_WIDTH = 800;
    const DEFAULT_HEIGHT = 500;

    const updateSize = () => {
      if (containerRef.current) {
        // 使用 getBoundingClientRect 获取更可靠的尺寸
        const rect = containerRef.current.getBoundingClientRect();
        let newWidth = Math.round(rect.width);
        let newHeight = Math.round(rect.height);

        // 如果容器尺寸为0或太小，尝试从父元素获取
        if (newWidth < 100 || newHeight < 100) {
          const parent = containerRef.current.parentElement;
          if (parent) {
            const parentRect = parent.getBoundingClientRect();
            newWidth = Math.round(parentRect.width);
            newHeight = Math.round(parentRect.height);
          }
        }

        // 如果还是太小，使用默认值（确保不会渲染0尺寸的Stage）
        if (newWidth < 100) newWidth = DEFAULT_WIDTH;
        if (newHeight < 100) newHeight = DEFAULT_HEIGHT;

        // 只有尺寸真正变化时才更新（避免无限循环）
        if (newWidth !== containerSize.width || newHeight !== containerSize.height) {
          console.log('[SchematicEditor] Size update:', { newWidth, newHeight, prev: containerSize });
          setContainerSize({ width: newWidth, height: newHeight });
        }
      }
    };

    // 初始更新 - 使用 requestAnimationFrame 确保 DOM 完全渲染
    const rafId = requestAnimationFrame(updateSize);

    // 延迟更新确保 DOM 完全渲染
    const timers = [
      setTimeout(updateSize, 50),
      setTimeout(updateSize, 200),
      setTimeout(updateSize, 500),
    ];

    // 监听窗口大小变化
    window.addEventListener('resize', updateSize);

    // 使用 ResizeObserver 监听容器
    const resizeObserver = new ResizeObserver(() => {
      // 使用 requestAnimationFrame 确保在下一帧更新，避免布局抖动
      requestAnimationFrame(updateSize);
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
      // 同时监听父元素
      if (containerRef.current.parentElement) {
        resizeObserver.observe(containerRef.current.parentElement);
      }
    }

    return () => {
      cancelAnimationFrame(rafId);
      timers.forEach(clearTimeout);
      window.removeEventListener('resize', updateSize);
      resizeObserver.disconnect();
    };
  }, []);

  // 强制刷新：当容器尺寸变化时重新渲染
  const [, forceUpdate] = useState(0);
  const width = containerSize.width;
  const height = containerSize.height;

  // 监听容器尺寸强制更新
  useEffect(() => {
    const checkSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const newWidth = Math.floor(rect.width);
        const newHeight = Math.floor(rect.height);

        // 只有尺寸有效且真正变化时才更新
        if (newWidth > 100 && newHeight > 100 &&
            (newWidth !== containerSize.width || newHeight !== containerSize.height)) {
          setContainerSize({ width: newWidth, height: newHeight });
        }
      }
    };

    // 频繁检查 - 使用 requestAnimationFrame 减少不必要的更新
    let rafId: number;
    const interval = setInterval(() => {
      rafId = requestAnimationFrame(checkSize);
    }, 500);

    window.addEventListener('resize', checkSize);

    return () => {
      cancelAnimationFrame(rafId);
      clearInterval(interval);
      window.removeEventListener('resize', checkSize);
    };
  }, [containerSize.width, containerSize.height]);

  const {
    schematicData,
    setSchematicData,
    loadSchematicData,
    projectId,
    selectedIds,
    // setSelectedIds, // 未使用
    toggleSelection,
    clearSelection,
    currentTool,
    setCurrentTool,
    zoom,
    setZoom,
    pan,
    setPan,
    addComponent,
    // addWire, // 未使用 - 未来功能
    // addLabel, // 未使用 - 未来功能
    removeSelectedElements,
    // canUndo, // 未使用 - 未来功能
    // canRedo, // 未使用 - 未来功能
    // undo, // 未使用 - 未来功能
    // redo, // 未使用 - 未来功能
    updateComponent,
    updateWire,
    updateLabel
  } = useSchematicStore();

  // 调试：检查 Stage 尺寸
  console.log('[SchematicEditor] Stage dimensions:', { width, height, zoom, pan, componentsCount: schematicData?.components?.length || 0 });

  // 获取当前选中的元素（在 useSchematicStore 调用之后）
  const selectedComponent = schematicData?.components.find(c => selectedIds.includes(c.id));
  const selectedWire = schematicData?.wires.find(w => selectedIds.includes(w.id));
  const selectedLabel = schematicData?.labels.find(l => selectedIds.includes(l.id));
  const selectedElement = selectedComponent || selectedWire || selectedLabel;
  
  // 初始化数据 - 加载项目数据或使用示例数据
  useEffect(() => {
    if (projectId) {
      loadSchematicData(projectId).catch(() => {
        // 如果加载失败，使用空原理图
        console.warn('[SchematicEditor] Failed to load schematic, using empty data');
        setSchematicData(createEmptySchematic());
      });
    } else if (!schematicData) {
      setSchematicData(createEmptySchematic());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // 当原理图数据加载后，自动调整视图以显示所有元件
  useEffect(() => {
    console.log('[SchematicEditor] AutoView useEffect triggered:', {
      hasData: !!schematicData,
      components: schematicData?.components?.length,
      width,
      height
    });
    if (!schematicData || schematicData.components.length === 0) return;
    if (!width || !height) return;
    // 延迟一点执行，确保 width/height 已经初始化
    const timer = setTimeout(() => {
      // 直接在这里计算，不用 handleAutoView 避免循环依赖
      // 注意：元件坐标是mm，需要乘以 MM_TO_PX 转换为像素
      const positions = schematicData.components.map(c => c.position || { x: 0, y: 0 });
      const minX = Math.min(...positions.map(p => p.x * MM_TO_PX));
      const maxX = Math.max(...positions.map(p => p.x * MM_TO_PX));
      const minY = Math.min(...positions.map(p => p.y * MM_TO_PX));
      const maxY = Math.max(...positions.map(p => p.y * MM_TO_PX));
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const newPan = {
        x: width / 2 - centerX,
        y: height / 2 - centerY
      };
      console.log('[SchematicEditor] Auto view calculated:', { centerX, centerY, pan: newPan });
      setPan(newPan);
      setZoom(1);
    }, 100);
    return () => clearTimeout(timer);
  }, [schematicData?.components?.length, width, height]);

  // 简化重绘逻辑 - 直接使用 contentLayer ref
  useEffect(() => {
    if (schematicData && stageRef) {
      console.log('[SchematicEditor] Triggering redraw, contentLayer:', !!contentLayer);

      const timers = [
        setTimeout(() => {
          stageRef?.batchDraw();
          if (contentLayer) {
            contentLayer.draw();
          }
          console.log('[SchematicEditor] batchDraw executed');
        }, 100),
        setTimeout(() => {
          stageRef?.batchDraw();
        }, 500),
      ];
      return () => timers.forEach(clearTimeout);
    }
  }, [schematicData, width, height, stageRef, contentLayer]);

  // 自动调整视图以显示所有元件
  const handleAutoView = useCallback(() => {
    if (!schematicData || schematicData.components.length === 0) return;

    // 计算所有元件的中心位置（转换为像素坐标）
    const positions = schematicData.components.map(c => c.position || { x: 0, y: 0 });
    const minX = Math.min(...positions.map(p => p.x * MM_TO_PX));
    const maxX = Math.max(...positions.map(p => p.x * MM_TO_PX));
    const minY = Math.min(...positions.map(p => p.y * MM_TO_PX));
    const maxY = Math.max(...positions.map(p => p.y * MM_TO_PX));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    // 将元件中心对齐到画布中心
    const newPan = {
      x: width / 2 - centerX,
      y: height / 2 - centerY
    };

    setPan(newPan);
    setZoom(1);
    console.log('[SchematicEditor] Auto view applied:', { centerX, centerY, pan: newPan });
  }, [schematicData, width, height, setPan, setZoom]);

  // 滚轮缩放
  const handleWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const newScale = e.evt.deltaY > 0 ? zoom / scaleBy : zoom * scaleBy;
    setZoom(Math.max(0.1, Math.min(newScale, 10)));
  };
  
  // 点击空白处取消选择
  const handleStageClick = (e: KonvaEventObject<MouseEvent>) => {
    if (e.target === e.target.getStage()) {
      clearSelection();
    }
  };

  // 拖拽平移状态
  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef({ x: 0, y: 0 });
  const panStart = useRef({ x: 0, y: 0 });

  // 处理鼠标按下 - 开始拖拽
  const handleMouseDown = (e: KonvaEventObject<MouseEvent>) => {
    // 只有在选择工具模式下且点击 Stage 本身时才启动拖拽
    if (currentTool === 'select' && e.target === e.target.getStage()) {
      setIsDragging(true);
      dragStartPos.current = { x: e.evt.clientX, y: e.evt.clientY };
      panStart.current = { ...pan };
    }
  };

  // 处理鼠标移动 - 拖拽中
  const handleMouseMove = (e: KonvaEventObject<MouseEvent>) => {
    if (!isDragging) return;
    const dx = e.evt.clientX - dragStartPos.current.x;
    const dy = e.evt.clientY - dragStartPos.current.y;
    setPan({
      x: panStart.current.x + dx,
      y: panStart.current.y + dy
    });
  };

  // 处理鼠标释放 - 结束拖拽
  const handleMouseUp = () => {
    setIsDragging(false);
  };
  
  // 处理放置元件
  const handlePlaceSymbol = (e: KonvaEventObject<MouseEvent>) => {
    if (currentTool !== 'place_symbol') return;
    
    const stage = e.target.getStage();
    if (!stage) return;
    
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
    
    const transform = stage.getAbsoluteTransform().copy();
    transform.invert();
    const pos = transform.point(pointer);
    
    // 转换为毫米坐标
    const mmPos = {
      x: pos.x / MM_TO_PX,
      y: pos.y / MM_TO_PX
    };
    
    // 创建新元件
    const newComponent: SchematicComponent = {
      id: `comp-${uuidv4()}`,
      libraryName: 'Device',
      symbolName: 'R',
      fullSymbolName: 'Device:R',
      reference: `R${(schematicData?.components.length || 0) + 1}`,
      value: '10k',
      position: mmPos,
      rotation: 0,
      mirror: false,
      unit: 1,
      fields: {},
      pins: [
        { id: 'pin-1', number: '1', name: '1', position: { x: -3, y: 0 }, electricalType: 'passive' },
        { id: 'pin-2', number: '2', name: '2', position: { x: 3, y: 0 }, electricalType: 'passive' }
      ]
    };
    
    addComponent(newComponent);
    setCurrentTool('select');
  };
  
  // 键盘事件
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 撤销: Ctrl+Z / Cmd+Z
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        useSchematicStore.getState().undo();
      }
      // 重做: Ctrl+Y / Cmd+Y / Ctrl+Shift+Z
      else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        useSchematicStore.getState().redo();
      }
      else if (e.key === 'Delete' || e.key === 'Backspace') {
        removeSelectedElements();
      } else if (e.key === 'Escape') {
        setCurrentTool('select');
        clearSelection();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [removeSelectedElements, setCurrentTool, clearSelection]);
  
  // 生成网格 - 相对于 Stage 坐标（Stage 已经应用了 pan）
  const generateGridLines = () => {
    const lines = [];
    const gridPixelSize = GRID_SIZE * zoom;
    // 计算网格偏移，创造"无限画布"效果
    // 使用 pan 值确保网格看起来是连续的
    const offsetX = (-pan.x) % gridPixelSize;
    const offsetY = (-pan.y) % gridPixelSize;

    for (let x = offsetX; x <= width; x += gridPixelSize) {
      lines.push(
        <Line key={`v-${x}`} points={[x, 0, x, height]} stroke={GRID_COLOR} strokeWidth={1} />
      );
    }
    for (let y = offsetY; y <= height; y += gridPixelSize) {
      lines.push(
        <Line key={`h-${y}`} points={[0, y, width, y]} stroke={GRID_COLOR} strokeWidth={1} />
      );
    }
    return lines;
  };
  
  // 渲染元件 - 使用新的符号渲染器
  const renderComponent = (comp: SchematicComponent) => {
    // 安全检查：确保 position 存在
    const selected = selectedIds.includes(comp.id);

    // 注意：Layer已经应用了pan和zoom变换，所以这里只需要传递原始毫米坐标
    // SchematicSymbol内部会进行MM_TO_PX转换
    const mmX = comp.position?.x ?? 0;
    const mmY = comp.position?.y ?? 0;

    // 调试日志
    console.log(`[SchematicEditor] Rendering component ${comp.id}:`, {
      mmPosition: { x: mmX, y: mmY },
      pxPosition: { x: mmX * MM_TO_PX, y: mmY * MM_TO_PX },
      pan, zoom,
      symbol_library: comp.symbol_library,
      category: comp.category,
      value: comp.value,
      stageWidth: width,
      stageHeight: height,
    });

    // 拖拽结束处理
    const handleDragEnd = (e: KonvaEventObject<DragEvent>) => {
      const node = e.target;
      // 从像素坐标转换回毫米坐标
      updateComponent(comp.id, {
        position: {
          x: node.x() / MM_TO_PX,
          y: node.y() / MM_TO_PX
        }
      });
    };

    return (
      <SchematicSymbol
        key={comp.id}
        component={{
          id: comp.id,
          name: comp.value || comp.symbolName || '',
          model: comp.value || '',
          reference: comp.reference,
          value: comp.value,
          // 传递原始毫米坐标，SchematicSymbol内部会进行转换
          position: { x: mmX, y: mmY },
          rotation: comp.rotation,
          pins: comp.pins?.map(p => ({
            id: p.id,
            number: p.number,
            name: p.name,
            // 引脚位置也是毫米坐标
            position: p.position || { x: 0, y: 0 },
            electricalType: p.electricalType
          })),
          footprint: comp.footprint,
          category: comp.category || comp.libraryName,
          symbolName: comp.symbolName,
          symbol_library: comp.symbol_library || '',
        }}
        selected={selected}
        onClick={() => toggleSelection(comp.id)}
        onDragEnd={handleDragEnd}
        draggable={currentTool === 'select'}
      />
    );
  };
  
  // 渲染导线
  const renderWire = (wire: Wire) => {
    const selected = selectedIds.includes(wire.id);
    // 只需要 MM_TO_PX 转换，pan 和 zoom 已经在 Layer 上应用
    const points = wire.points.flatMap(p => [
      p.x * MM_TO_PX,
      p.y * MM_TO_PX
    ]);

    return (
      <Line
        key={wire.id}
        points={points}
        stroke={selected ? '#ffff00' : '#00ff00'}
        strokeWidth={selected ? 2 : 1}
        onClick={() => toggleSelection(wire.id)}
      />
    );
  };

  // 渲染标签
  const renderLabel = (label: Label) => {
    // 只需要 MM_TO_PX 转换，pan 和 zoom 已经在 Layer 上应用
    const x = label.position.x * MM_TO_PX;
    const y = label.position.y * MM_TO_PX;

    return (
      <Group
        key={label.id}
        x={x}
        y={y}
        rotation={label.rotation}
        onClick={() => toggleSelection(label.id)}
      >
        <Text
          text={label.text}
          fontSize={12}
          fill={label.labelType === 'power' ? '#ff6600' : '#00aaff'}
        />
      </Group>
    );
  };
  
  if (!schematicData) {
    return <div style={{ color: '#fff', padding: 40 }}>Loading...</div>;
  }

  // 调试日志：检查数据
  console.log('[SchematicEditor] Rendering with data:', {
    componentsCount: schematicData.components.length,
    wiresCount: schematicData.wires.length,
    zoom,
    pan,
    canvasSize: { width, height },
  });

  // 额外调试：检查每个元件的渲染参数
  if (schematicData.components.length > 0) {
    schematicData.components.forEach((comp, idx) => {
      const renderX = (comp.position?.x ?? 0) * MM_TO_PX;
      const renderY = (comp.position?.y ?? 0) * MM_TO_PX;
      // 考虑 Stage 的 pan 偏移
      const stageOffsetX = renderX + pan.x;
      const stageOffsetY = renderY + pan.y;
      console.log(`[SchematicEditor] Component ${idx}:`, {
        id: comp.id,
        originalPos: comp.position,
        renderPos: { x: renderX, y: renderY },
        withPan: { x: stageOffsetX, y: stageOffsetY },
        inViewport: stageOffsetX >= 0 && stageOffsetX <= width && stageOffsetY >= 0 && stageOffsetY <= height,
        symbol_library: comp.symbol_library,
      });
    });
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1a1a1a', position: 'relative' }}>
      {/* 画布区域 */}
      <div style={{ flex: 1, position: 'relative', display: 'flex', minWidth: 0 }}>
        <div ref={containerRef} style={{ flex: 1, position: 'relative', minWidth: 0, minHeight: 400 }}>
          {/* 使用 ResizeSensor 强制更新 Stage 尺寸 */}
          <div
            id="stage-resize-sensor"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              overflow: 'hidden',
              pointerEvents: 'none',
            }}
          />
          {width > 0 && height > 0 ? (
          <Stage
            width={width}
            height={height}
            onWheel={handleWheel}
            onClick={currentTool === 'place_symbol' ? handlePlaceSymbol : handleStageClick}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            draggable={false}
            ref={(ref) => {
                if (ref !== stageRef) {
                  console.log('[SchematicEditor] Stage ref callback called, _id:', (ref as any)?._id);
                  setStageRef(ref);
                }
              }}
            style={{ cursor: isDragging ? 'grabbing' : 'default', background: '#1a1a1a' }}
          >
            {/* 背景层 - 固定不变 */}
            <Layer>
              <Rect x={0} y={0} width={width} height={height} fill="#1a1a1a" />
              {generateGridLines()}
            </Layer>

            {/* 内容层 - 应用平移和缩放变换 */}
            {/* Fix: Apply pan and zoom on Layer for proper coordinate transformation */}
            <Layer
              x={pan.x}
              y={pan.y}
              scaleX={zoom}
              scaleY={zoom}
              ref={(node) => {
                if (node !== contentLayer) {
                  console.log('[SchematicEditor] Layer ref callback called, _id:', (node as any)?._id);
                  setContentLayer(node);
                }
              }}
            >
              {/* 导线 */}
              {schematicData.wires.map(renderWire)}

              {/* 元件 */}
              {schematicData.components.map(renderComponent)}

              {/* 标签 */}
              {schematicData.labels.map(renderLabel)}
            </Layer>
          </Stage>
          ) : (
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#666',
              backgroundColor: '#1a1a1a'
            }}>
              Initializing canvas...
            </div>
          )}

          {/* 调试覆盖层 */}
          {showDebug && (
            <SchematicDebugOverlay
              stageWidth={width}
              stageHeight={height}
              zoom={zoom}
              pan={pan}
              components={schematicData.components.map(c => ({
                id: c.id,
                position: c.position,
                reference: c.reference,
                value: c.value,
              }))}
            />
          )}

          {/* 顶部工具栏 - 整合状态信息和操作按钮 */}
          <div style={{
            position: 'absolute',
            top: 10,
            right: 10,
            background: 'rgba(30,30,30,0.95)',
            color: '#fff',
            padding: '8px 14px',
            borderRadius: 8,
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            border: '1px solid #444',
            boxShadow: '0 2px 10px rgba(0,0,0,0.4)',
          }}>
            {/* 缩放显示 */}
            <span style={{ color: '#4a9eff', fontWeight: 600 }}>{(zoom * 100).toFixed(0)}%</span>
            <span style={{ color: '#555' }}>|</span>
            <span>{schematicData.components.length} 元件</span>
            <span style={{ color: '#555' }}>|</span>
            <span>{schematicData.wires.length} 导线</span>

            {/* 分隔 */}
            <span style={{ color: '#555' }}>|</span>

            {/* 撤销/重做按钮组 */}
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                onClick={() => useSchematicStore.getState().undo()}
                disabled={!useSchematicStore.getState().canUndo}
                style={{
                  background: useSchematicStore.getState().canUndo ? '#3a3a3a' : '#252525',
                  border: 'none',
                  borderRadius: '4px',
                  color: useSchematicStore.getState().canUndo ? '#fff' : '#555',
                  padding: '4px 10px',
                  cursor: useSchematicStore.getState().canUndo ? 'pointer' : 'not-allowed',
                  fontSize: 12,
                }}
                title="撤销 (Ctrl+Z)"
              >
                ↶
              </button>
              <button
                onClick={() => useSchematicStore.getState().redo()}
                disabled={!useSchematicStore.getState().canRedo}
                style={{
                  background: useSchematicStore.getState().canRedo ? '#3a3a3a' : '#252525',
                  border: 'none',
                  borderRadius: '4px',
                  color: useSchematicStore.getState().canRedo ? '#fff' : '#555',
                  padding: '4px 10px',
                  cursor: useSchematicStore.getState().canRedo ? 'pointer' : 'not-allowed',
                  fontSize: 12,
                }}
                title="重做 (Ctrl+Y)"
              >
                ↷
              </button>
            </div>

            {/* 自动视图按钮 */}
            <button
              onClick={handleAutoView}
              style={{
                background: '#4a9eff',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                padding: '5px 12px',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 500,
              }}
              title="自动调整视图显示所有元件"
            >
              🔍 适应
            </button>

            {/* 调试按钮 */}
            <button
              onClick={() => setShowDebug(!showDebug)}
              style={{
                background: showDebug ? '#ff6600' : '#3a3a3a',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                padding: '5px 10px',
                cursor: 'pointer',
                fontSize: 11,
              }}
            >
              {showDebug ? '关闭调试' : '调试'}
            </button>
          </div>
        </div>

        {/* 属性编辑面板 */}
        {selectedIds.length > 0 && selectedElement && (
          <div style={{
            width: 280,
            backgroundColor: '#2d2d2d',
            borderLeft: '1px solid #4d4d4d',
            padding: 16,
            overflow: 'auto',
            color: '#ffffff'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: 16, fontSize: 14, color: '#4a9eff' }}>
              属性编辑
            </h3>

            {/* 删除按钮 */}
            <button
              onClick={() => removeSelectedElements()}
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: '#ff4444',
                color: '#ffffff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                marginBottom: 16
              }}
            >
              删除选中元素
            </button>

            {/* 元件属性 */}
            {selectedComponent && (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>位号 (Reference)</label>
                  <input
                    type="text"
                    value={selectedComponent.reference || ''}
                    onChange={(e) => {
                      const newRef = e.target.value;
                      if (updateComponent) {
                        updateComponent(selectedComponent.id, { reference: newRef });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>值 (Value)</label>
                  <input
                    type="text"
                    value={selectedComponent.value || ''}
                    onChange={(e) => {
                      const newValue = e.target.value;
                      if (updateComponent) {
                        updateComponent(selectedComponent.id, { value: newValue });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>封装 (Footprint)</label>
                  <input
                    type="text"
                    value={selectedComponent.footprint || ''}
                    onChange={(e) => {
                      const newFootprint = e.target.value;
                      if (updateComponent) {
                        updateComponent(selectedComponent.id, { footprint: newFootprint });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
              </div>
            )}

            {/* 导线属性 */}
            {selectedWire && (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>导线颜色</label>
                  <input
                    type="color"
                    value={selectedWire.color || '#00ff00'}
                    onChange={(e) => {
                      const newColor = e.target.value;
                      if (updateWire) {
                        updateWire(selectedWire.id, { color: newColor });
                      }
                    }}
                    style={{ width: '100%', height: 40, cursor: 'pointer' }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>线宽</label>
                  <input
                    type="number"
                    value={selectedWire.strokeWidth || 1}
                    onChange={(e) => {
                      const newWidth = parseFloat(e.target.value) || 1;
                      if (updateWire) {
                        updateWire(selectedWire.id, { strokeWidth: newWidth });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
              </div>
            )}

            {/* 标签属性 */}
            {selectedLabel && (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>标签文本</label>
                  <input
                    type="text"
                    value={selectedLabel.text || ''}
                    onChange={(e) => {
                      const newText = e.target.value;
                      if (updateLabel) {
                        updateLabel(selectedLabel.id, { text: newText });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>X 坐标</label>
                  <input
                    type="number"
                    value={selectedLabel.position.x || 0}
                    onChange={(e) => {
                      const newX = parseFloat(e.target.value) || 0;
                      if (updateLabel) {
                        updateLabel(selectedLabel.id, { position: { ...selectedLabel.position, x: newX } });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>Y 坐标</label>
                  <input
                    type="number"
                    value={selectedLabel.position.y || 0}
                    onChange={(e) => {
                      const newY = parseFloat(e.target.value) || 0;
                      if (updateLabel) {
                        updateLabel(selectedLabel.id, { position: { ...selectedLabel.position, y: newY } });
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      backgroundColor: '#3d3d3d',
                      border: '1px solid #4d4d4d',
                      borderRadius: 4,
                      color: '#ffffff'
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// 添加 defaultProps 确保默认值生效
SchematicEditor.defaultProps = {
  width: 800,
  height: 500
};

export default SchematicEditor;
