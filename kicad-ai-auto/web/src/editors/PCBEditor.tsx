/**
 * 完整版 PCBEditor (整合所有功能)
 */

import React, { useState, useEffect, useRef, useCallback, useLayoutEffect } from 'react';
import { Stage, Layer, Line, Group, Circle, Rect, Text as KonvaText } from 'react-konva';
import type { Stage as StageType } from 'konva/lib/Stage';
import Konva from 'konva';

// Note: Konva.useStrictMode is not available in Konva 9.3.3
// React 18 compatibility is handled through proper ref management below

import { usePCBStore } from '../stores/pcbStore';
import { samplePCB } from '../data/samplePCB';

import SimpleToolbar from '../components/SimpleToolbar';
import PropertyPanel from '../panels/PropertyPanel';
import LayerPanel from '../panels/LayerPanel';
import DRCPanel from '../panels/DRCPanel';
import ExportPanel from '../panels/ExportPanel';
import RoutingTool from '../canvas/RoutingTool';
import PCBViewer3D from '../components/PCBViewer3D';
import AIChatAssistant from '../components/AIChatAssistant';

import BoardOutlineRenderer from '../canvas/BoardOutlineRenderer';
import FootprintRenderer from '../canvas/FootprintRenderer';
import TrackRenderer from '../canvas/TrackRenderer';
import ViaRenderer from '../canvas/ViaRenderer';

import { useAutoSave } from '../hooks/useAutoSave';
import { DRCReport } from '../types';
import { MM_TO_PX } from '../data/samplePCB';

const GRID_SIZE = 10;
const GRID_COLOR = '#333333';

const PCBEditor: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  // 使用 ref 跟踪最后一个有效的容器尺寸
  const lastValidSizeRef = useRef({ width: 800, height: 600 });

  const [containerSize, setContainerSize] = useState({ width: 800, height: 600 });
  const [activeTab, setActiveTab] = useState<'properties' | 'layers' | 'drc' | 'export'>('properties');
  const [activeLayer, setActiveLayer] = useState('F.Cu');
  const [drcReport, setDrcReport] = useState<DRCReport | null>(null);
  const [viewMode, setViewMode] = useState<'2d' | '3d'>('2d');
  const [showAIChat, setShowAIChat] = useState(false);

  // 自动调整画布尺寸 - 严格跟随实际容器尺寸
  useEffect(() => {
    const DEFAULT_WIDTH = 800;
    const DEFAULT_HEIGHT = 600;
    const MIN_WIDTH = 300; // 最小宽度限制，小于此值使用上一次有效尺寸
    const MIN_HEIGHT = 300; // 最小高度限制
    let updateTimer: ReturnType<typeof setTimeout> | null = null;

    const updateSize = () => {
      if (!containerRef.current) return;

      // 使用 getBoundingClientRect 获取实际渲染尺寸（包含小数，更精确）
      const rect = containerRef.current.getBoundingClientRect();
      const newWidth = Math.floor(rect.width) || 0;
      const newHeight = Math.floor(rect.height) || 0;

      // 关键修复：如果容器被压缩到小于最小可用尺寸，使用上一次有效尺寸
      // 这样可以防止 flexbox 塌缩导致 canvas 变得太小无法显示内容
      let useWidth = newWidth;
      let useHeight = newHeight;

      if (newWidth < MIN_WIDTH || newHeight < MIN_HEIGHT) {
        if (import.meta.env.DEV) {
          console.log(`[PCBEditor] Container too small (${newWidth}x${newHeight}), using last valid size`);
        }
        useWidth = lastValidSizeRef.current.width;
        useHeight = lastValidSizeRef.current.height;
      }

      // 只有当尺寸真正变化时才更新
      if (useWidth !== containerSize.width || useHeight !== containerSize.height) {
        setContainerSize({
          width: useWidth,
          height: useHeight
        });
        // 同步更新 lastValidSizeRef（只记录大于最小尺寸的有效尺寸）
        if (newWidth >= MIN_WIDTH && newHeight >= MIN_HEIGHT) {
          lastValidSizeRef.current = { width: newWidth, height: newHeight };
        }

        // 注意：不再强制重新创建 Stage，让 React Konva 通过 props 更新处理 resize
        // 强制重新创建会导致 Konva 内部状态混乱，内容消失
      }
    };

    // 初始更新
    requestAnimationFrame(updateSize);

    // 延迟更新确保 DOM 完全渲染
    const timers = [
      setTimeout(updateSize, 50),
      setTimeout(updateSize, 200),
      setTimeout(updateSize, 500),
    ];

    // 使用 ResizeObserver 直接监听内容矩形变化
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;

        // 取消之前的计时器
        if (updateTimer) clearTimeout(updateTimer);
        // 防抖 50ms
        updateTimer = setTimeout(() => {
          const newWidth = Math.floor(width) || 0;
          const newHeight = Math.floor(height) || 0;

          // 关键修复：如果容器被压缩到小于最小可用尺寸，使用上一次有效尺寸
          let useWidth = newWidth;
          let useHeight = newHeight;

          if (newWidth < MIN_WIDTH || newHeight < MIN_HEIGHT) {
            if (import.meta.env.DEV) {
              console.log(`[PCBEditor] Observer: Container too small (${newWidth}x${newHeight}), using last valid size`);
            }
            useWidth = lastValidSizeRef.current.width;
            useHeight = lastValidSizeRef.current.height;
          }

          if (useWidth !== containerSize.width || useHeight !== containerSize.height) {
            setContainerSize({ width: useWidth, height: useHeight });
            // 只记录大于最小尺寸的有效尺寸
            if (newWidth >= MIN_WIDTH && newHeight >= MIN_HEIGHT) {
              lastValidSizeRef.current = { width: newWidth, height: newHeight };
            }
          }
        }, 50);
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      timers.forEach(clearTimeout);
      if (updateTimer) clearTimeout(updateTimer);
      resizeObserver.disconnect();
    };
  }, []);
  
  const {
    pcbData,
    setPCBData,
    loadPCBData,
    savePCBData,
    // selectedIds, // 未使用
    clearSelection,
    currentTool,
    zoom,
    pan,
    setZoom,
    setPan,
    gridSize,
    snapToGrid,
    // undo, // 未使用 - 未来可用于撤销功能
    // redo, // 未使用 - 未来可用于重做功能
    // canUndo, // 未使用
    // canRedo, // 未使用
    // removeSelectedElements, // 未使用 - 未来可用于删除功能
    // isSaving, // 未使用
    // lastSaved, // 未使用
    projectId
  } = usePCBStore();

  // 初始化加载数据
  useEffect(() => {
    if (projectId) {
      loadPCBData(projectId).catch(() => {
        // 如果加载失败，使用示例数据
        console.warn('[PCBEditor] Failed to load PCB, using sample data');
        setPCBData(samplePCB);
      });
    } else {
      // 使用示例数据
      setPCBData(samplePCB);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // 调试：仅在开发模式下记录渲染状态（减少日志输出）
  useEffect(() => {
    if (import.meta.env.DEV && containerSize.width < 100) {
      console.warn('[PCBEditor] Container size unusually small:', containerSize);
    }
  }, [containerSize]);

  // 使用 ref 直接访问 Stage 和 Layer，避免状态延迟问题
  const stageRefDirect = useRef<StageType | null>(null);
  const layerRefDirect = useRef<Konva.Layer | null>(null);


  // 自适应缩放和平移值 - 让PCB内容填满画布
  useEffect(() => {
    console.log('[PCBEditor] Auto-fit PCB effect:', { containerSize, hasPcbData: !!pcbData });

    if (pcbData && viewMode === '2d' && containerSize.width > 0 && containerSize.height > 0) {
      // 计算PCB板的外接矩形
      const boardOutline = pcbData.boardOutline;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

      if (boardOutline && boardOutline.length > 0) {
        boardOutline.forEach(point => {
          minX = Math.min(minX, point.x);
          minY = Math.min(minY, point.y);
          maxX = Math.max(maxX, point.x);
          maxY = Math.max(maxY, point.y);
        });
      } else {
        // 如果没有板轮廓，使用元件的边界
        pcbData.footprints.forEach(fp => {
          minX = Math.min(minX, fp.position.x - 10);
          minY = Math.min(minY, fp.position.y - 10);
          maxX = Math.max(maxX, fp.position.x + 10);
          maxY = Math.max(maxY, fp.position.y + 10);
        });
      }

      // 转换为像素并添加边距
      const margin = 50; // 像素边距
      const boardWidthPx = (maxX - minX) * MM_TO_PX;
      const boardHeightPx = (maxY - minY) * MM_TO_PX;

      // 计算合适的缩放比例（填充画布的80%）
      const availableWidth = containerSize.width * 0.8;
      const availableHeight = containerSize.height * 0.8;

      const scaleX = availableWidth / boardWidthPx;
      const scaleY = availableHeight / boardHeightPx;
      const optimalZoom = Math.min(scaleX, scaleY, 3); // 最大缩放3倍

      // 计算居中平移值
      const centerX = (minX + maxX) / 2 * MM_TO_PX * optimalZoom;
      const centerY = (minY + maxY) / 2 * MM_TO_PX * optimalZoom;
      const panX = containerSize.width / 2 - centerX;
      const panY = containerSize.height / 2 - centerY;

      console.log('[PCBEditor] Auto-fit settings:', { optimalZoom, panX, panY, boardWidthPx, boardHeightPx });

      setZoom(optimalZoom);
      setPan({ x: panX, y: panY });
    }
  }, [pcbData, viewMode, containerSize]);

  // 自动保存
  useAutoSave({
    pcbData: pcbData || samplePCB,
    projectId: projectId || 'sample',
    enabled: !!projectId,
    interval: 5000,
    onSave: savePCBData
  });

  // 滚轮缩放
  const handleWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const newScale = e.evt.deltaY > 0 ? zoom / scaleBy : zoom * scaleBy;
    setZoom(Math.max(0.1, Math.min(newScale, 10)));
  };

  // 点击空白处取消选择
  const handleStageClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.target === e.target.getStage()) {
      clearSelection();
    }
  };

  // 拖拽平移状态
  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef({ x: 0, y: 0 });
  const panStart = useRef({ x: 0, y: 0 });

  // 处理鼠标按下 - 开始拖拽
  const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    // 只有在点击 Stage 本身（不是元素）时才启动拖拽
    if (e.target === e.target.getStage()) {
      setIsDragging(true);
      dragStartPos.current = { x: e.evt.clientX, y: e.evt.clientY };
      panStart.current = { ...pan };
    }
  };

  // 处理鼠标移动 - 拖拽中
  const handleMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
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

  // 生成网格线 - 在世界坐标系中生成，Layer会处理pan/zoom变换
  const generateGridLines = () => {
    const lines = [];
    // 在世界坐标系中计算网格范围（考虑pan和缩放）
    const viewWidth = containerSize.width / zoom;
    const viewHeight = containerSize.height / zoom;
    const startX = -pan.x / zoom;
    const startY = -pan.y / zoom;

    // 网格间距（像素）
    const gridPixelSize = GRID_SIZE;

    // 计算网格起始点（对齐到网格）
    const gridStartX = Math.floor(startX / gridPixelSize) * gridPixelSize;
    const gridStartY = Math.floor(startY / gridPixelSize) * gridPixelSize;

    // 计算网格结束点
    const gridEndX = gridStartX + viewWidth + gridPixelSize;
    const gridEndY = gridStartY + viewHeight + gridPixelSize;

    // 生成垂直线
    for (let x = gridStartX; x <= gridEndX; x += gridPixelSize) {
      lines.push(
        <Line
          key={`v-${x}`}
          points={[x, startY, x, gridEndY]}
          stroke={GRID_COLOR}
          strokeWidth={1}
          opacity={0.3}
        />
      );
    }

    // 生成水平线
    for (let y = gridStartY; y <= gridEndY; y += gridPixelSize) {
      lines.push(
        <Line
          key={`h-${y}`}
          points={[startX, y, gridEndX, y]}
          stroke={GRID_COLOR}
          strokeWidth={1}
          opacity={0.3}
        />
      );
    }

    return lines;
  };

  // 渲染DRC错误标记
  const renderDRCMarkers = () => {
    if (!drcReport) return null;
    
    const allItems = [...drcReport.errors, ...drcReport.warnings];
    
    return allItems.map((item) => {
      if (!item.position) return null;
      
      const x = item.position.x * MM_TO_PX;
      const y = item.position.y * MM_TO_PX;
      const color = item.severity === 'error' ? '#ff0000' : '#ffaa00';
      
      return (
        <Group key={item.id} x={x} y={y}>
          {/* 外圈 */}
          <Circle
            radius={8}
            fill={color}
            opacity={0.3}
          />
          {/* 内圈 */}
          <Circle
            radius={4}
            fill={color}
          />
          {/* X标记 */}
          <Line
            points={[-4, -4, 4, 4]}
            stroke="#ffffff"
            strokeWidth={1}
          />
          <Line
            points={[4, -4, -4, 4]}
            stroke="#ffffff"
            strokeWidth={1}
          />
        </Group>
      );
    });
  };

  if (!pcbData) {
    return <div style={{ color: '#fff', padding: 40 }}>Loading...</div>;
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1a1a1a', position: 'relative' }}>
      {/* AI 聊天助手浮窗按钮 - 固定在右下角 */}
      <button
        onClick={() => setShowAIChat(!showAIChat)}
        style={{
          position: 'absolute',
          bottom: 20,
          right: 20,
          zIndex: 100,
          padding: '10px 20px',
          backgroundColor: showAIChat ? '#4a9eff' : '#2d2d2d',
          border: '1px solid #4a4a4a',
          borderRadius: 8,
          color: '#fff',
          cursor: 'pointer',
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}
      >
        🤖 AI助手
      </button>

      {/* AI 聊天助手面板 - 右下角浮窗 */}
      {showAIChat && (
        <div style={{
          position: 'absolute',
          bottom: 70,
          right: 20,
          zIndex: 99,
          width: 380,
          height: 500,
        }}>
          <AIChatAssistant
            schematicData={pcbData}
            projectSpec={{ name: projectId || '未命名项目' }}
            onModifySchematic={(modifications) => {
              console.log('AI modifications received:', modifications);
              // 注意：AIChatAssistant 内部会在执行完修改后自动保存 PCB 数据
              // 这里不需要额外调用 savePCBData，避免时序问题
            }}
            defaultExpanded={true}
          />
        </div>
      )}

      {/* 主内容区 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'visible', minWidth: 0, minHeight: 0 }}>
        {/* 左侧工具栏 */}
        <div style={{ display: 'flex', flexDirection: 'column', backgroundColor: '#2d2d2d', borderRight: '1px solid #3d3d3d' }}>
          <SimpleToolbar />

          {/* 2D/3D 视图切换 */}
          <div style={{ display: 'flex', padding: 8, gap: 4, backgroundColor: '#2d2d2d', borderTop: '1px solid #3d3d3d' }}>
            <button
              onClick={() => setViewMode('2d')}
              style={{
                flex: 1,
                padding: '6px 8px',
                backgroundColor: viewMode === '2d' ? '#4a9eff' : '#3d3d3d',
                color: '#ffffff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 11,
              }}
            >
              2D
            </button>
            <button
              onClick={() => setViewMode('3d')}
              style={{
                flex: 1,
                padding: '6px 8px',
                backgroundColor: viewMode === '3d' ? '#4a9eff' : '#3d3d3d',
                color: '#ffffff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 11,
              }}
            >
              3D
            </button>
          </div>
        </div>

        {/* 画布区域 */}
        <div
          ref={containerRef}
          style={{
            flex: 1,
            position: 'relative',
            minWidth: 300,
            minHeight: 300,
            overflow: 'auto',
            width: '100%',
            height: '100%',
            backgroundColor: '#1a1a2e'
          }}
          id="pcb-canvas-container"
          data-container-size={`${containerSize.width}x${containerSize.height}`}
        >
          {/* 缩放显示 */}
          <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(0,0,0,0.7)', color: '#fff', padding: '5px 10px', borderRadius: 4, fontSize: 12 }}>
            Zoom: {(zoom * 100).toFixed(0)}% | Grid: {gridSize}mm {snapToGrid ? '(snap)' : ''}
          </div>

          {(() => {
            const shouldRender = viewMode === '2d' && pcbData && containerSize.width > 0 && containerSize.height > 0;
            if (shouldRender) {
              console.log('[PCBEditor] ===== STAGE RENDER =====', {
                width: containerSize.width,
                height: containerSize.height,
                zoom,
                pan,
                footprints: pcbData.footprints.length,
                tracks: pcbData.tracks.length
              });
            }
            return shouldRender;
          })() && (
            <Stage
              width={containerSize.width}
              height={containerSize.height}
              onWheel={handleWheel}
              onClick={handleStageClick}
              draggable={false}
              onDragEnd={(e) => {
                const stage = e.target;
                setPan({
                  x: stage.x(),
                  y: stage.y()
                });
              }}
              ref={(ref) => {
                // 只更新 ref，不触发 state 变化
                stageRefDirect.current = ref;
              }}
              style={{ background: '#1a1a2e' }}
            >
            {/* 网格层 - 应用 pan 和 zoom 使网格跟随画布移动 */}
            <Layer
              x={pan.x}
              y={pan.y}
              scaleX={zoom}
              scaleY={zoom}
            >
              {generateGridLines()}
            </Layer>

            {/* PCB元素层 - 将 pan 和 zoom 应用在 Layer 上，与 SchematicEditor 一致 */}
            <Layer
              x={pan.x}
              y={pan.y}
              scaleX={zoom}
              scaleY={zoom}
              ref={(layer) => {
                // 只更新 ref，不触发 state 变化
                layerRefDirect.current = layer;
              }}
            >
              <BoardOutlineRenderer outline={pcbData.boardOutline} />

              {pcbData.tracks.map(track => (
                <TrackRenderer key={track.id} track={track} />
              ))}

              {pcbData.vias.map(via => (
                <ViaRenderer key={via.id} via={via} />
              ))}

              {pcbData.footprints.map(footprint => (
                <FootprintRenderer key={footprint.id} footprint={footprint} />
              ))}
            </Layer>

            {/* DRC标记层 - 应用相同的 pan 和 zoom */}
            <Layer
              x={pan.x}
              y={pan.y}
              scaleX={zoom}
              scaleY={zoom}
            >
              {renderDRCMarkers()}
            </Layer>

            {/* 布线工具层 */}
            <RoutingTool active={currentTool === 'route'} />
          </Stage>
          )}

          {/* 3D 视图 */}
          {viewMode === '3d' && (
            <PCBViewer3D
              width={containerSize.width}
              height={containerSize.height}
            />
          )}
        </div>

        {/* 右侧面板 */}
        <div style={{ width: 250, backgroundColor: '#2d2d2d', borderLeft: '1px solid #3d3d3d', display: 'flex', flexDirection: 'column' }}>
          {/* 标签页 */}
          <div style={{ display: 'flex', borderBottom: '1px solid #3d3d3d' }}>
            {(['properties', 'layers', 'drc', 'export'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: activeTab === tab ? '#3d3d3d' : '#2d2d2d',
                  color: activeTab === tab ? '#4a9eff' : '#888',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 11,
                  textTransform: 'capitalize'
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* 面板内容 */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {activeTab === 'properties' && <PropertyPanel pcbData={pcbData} />}
            {activeTab === 'layers' && (
              <LayerPanel
                activeLayer={activeLayer}
                onLayerActivate={setActiveLayer}
              />
            )}
            {activeTab === 'drc' && <DRCPanel onDRCComplete={setDrcReport} />}
            {activeTab === 'export' && <ExportPanel />}
          </div>
        </div>
      </div>

    </div>
  );
};

export default PCBEditor;
