/**
 * 完整版 PCBEditor (整合所有功能)
 */

import React, { useState, useEffect } from 'react';
import { Stage, Layer, Line, Text, Group, Circle } from 'react-konva';
import type { Stage as StageType } from 'konva/lib/Stage';

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
import { DRCReport, DRCItem } from '../types';
import { MM_TO_PX } from '../data/samplePCB';

const GRID_SIZE = 10;
const GRID_COLOR = '#333333';

const PCBEditor: React.FC = () => {
  const [stageRef, setStageRef] = useState<StageType | null>(null);
  const [activeTab, setActiveTab] = useState<'properties' | 'layers' | 'drc' | 'export'>('properties');
  const [activeLayer, setActiveLayer] = useState('F.Cu');
  const [drcReport, setDrcReport] = useState<DRCReport | null>(null);
  const [viewMode, setViewMode] = useState<'2d' | '3d'>('2d');
  const [showAIChat, setShowAIChat] = useState(false);
  
  const {
    pcbData,
    setPCBData,
    loadPCBData,
    savePCBData,
    selectedIds,
    clearSelection,
    currentTool,
    zoom,
    pan,
    setZoom,
    setPan,
    gridSize,
    snapToGrid,
    undo,
    redo,
    canUndo,
    canRedo,
    removeSelectedElements,
    isSaving,
    lastSaved,
    projectId
  } = usePCBStore();

  // 初始化加载数据
  useEffect(() => {
    if (projectId) {
      loadPCBData(projectId);
    } else {
      // 使用示例数据
      setPCBData(samplePCB);
    }
  }, [projectId]);

  // 自动保存
  useAutoSave({
    pcbData: pcbData || samplePCB,
    projectId: projectId || 'sample',
    enabled: !!projectId,
    interval: 5000,
    onSave: savePCBData
  });

  // 滚轮缩放
  const handleWheel = (e: any) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const newScale = e.evt.deltaY > 0 ? zoom / scaleBy : zoom * scaleBy;
    setZoom(Math.max(0.1, Math.min(newScale, 10)));
  };

  // 点击空白处取消选择
  const handleStageClick = (e: any) => {
    if (e.target === e.target.getStage()) {
      clearSelection();
    }
  };

  // 生成网格线
  const generateGridLines = () => {
    if (!stageRef) return [];
    const lines = [];
    const width = stageRef.width();
    const height = stageRef.height();
    const gridPixelSize = GRID_SIZE * zoom;
    const offsetX = pan.x % gridPixelSize;
    const offsetY = pan.y % gridPixelSize;
    
    for (let x = offsetX; x <= width; x += gridPixelSize) {
      lines.push(
        <Line key={`v-${x}`} points={[x, 0, x, height]} stroke={GRID_COLOR} strokeWidth={1 / zoom} />
      );
    }
    for (let y = offsetY; y <= height; y += gridPixelSize) {
      lines.push(
        <Line key={`h-${y}`} points={[0, y, width, y]} stroke={GRID_COLOR} strokeWidth={1 / zoom} />
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
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
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
        <div style={{ flex: 1, position: 'relative' }} id="pcb-canvas-container">
          {viewMode === '2d' ? (
            <Stage
              width={800}
              height={600}
              onWheel={handleWheel}
              onClick={handleStageClick}
              draggable
              onDragEnd={(e) => {
                setPan({
                  x: e.target.x(),
                  y: e.target.y()
                });
              }}
              x={pan.x}
              y={pan.y}
              ref={(ref) => setStageRef(ref)}
            >
            {/* 网格层 */}
            <Layer>{generateGridLines()}</Layer>

            {/* PCB元素层 */}
            <Layer scaleX={zoom} scaleY={zoom}>
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

            {/* DRC标记层 */}
            <Layer scaleX={zoom} scaleY={zoom}>
              {renderDRCMarkers()}
            </Layer>

            {/* 布线工具层 */}
            <RoutingTool active={currentTool === 'route'} />
          </Stage>
          ) : (
            /* 3D 视图 */
            <PCBViewer3D
              width={800}
              height={600}
            />
          )}

          {/* 缩放显示 */}
          <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(0,0,0,0.7)', color: '#fff', padding: '5px 10px', borderRadius: 4, fontSize: 12 }}>
            Zoom: {(zoom * 100).toFixed(0)}% | Grid: {gridSize}mm {snapToGrid ? '(snap)' : ''}
          </div>
        </div>

        {/* 右侧面板 */}
        <div style={{ width: 250, backgroundColor: '#2d2d2d', borderLeft: '1px solid #3d3d3d', display: 'flex', flexDirection: 'column' }}>
          {/* 标签页 */}
          <div style={{ display: 'flex', borderBottom: '1px solid #3d3d3d' }}>
            {['properties', 'layers', 'drc', 'export'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as any)}
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
