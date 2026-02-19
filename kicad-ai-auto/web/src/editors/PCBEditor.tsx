/**
 * 完整版 PCBEditor (整合所有功能)
 */

import React, { useState, useEffect } from 'react';
import { Stage, Layer, Line, Text, Group, Circle } from 'react-konva';
import type { Stage as StageType } from 'konva/lib/Stage';

import { usePCBStore } from '../stores/pcbStore';
import { samplePCB } from '../data/samplePCB';

import MenuBar from '../components/MenuBar';
import SimpleToolbar from '../components/SimpleToolbar';
import PropertyPanel from '../panels/PropertyPanel';
import LayerPanel from '../panels/LayerPanel';
import DRCPanel from '../panels/DRCPanel';
import ExportPanel from '../panels/ExportPanel';
import RoutingTool from '../canvas/RoutingTool';
import PCBViewer3D from '../components/PCBViewer3D';

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
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#1a1a1a' }}>
      {/* 菜单栏 */}
      <MenuBar />

      {/* 工具栏 */}
      <div style={{ height: 40, backgroundColor: '#2d2d2d', display: 'flex', alignItems: 'center', padding: '0 16px', borderBottom: '1px solid #3d3d3d' }}>
        <span style={{ color: '#fff', marginRight: 16 }}>KiCad Web Editor</span>
        <span style={{ color: '#888', fontSize: 12 }}>Tool: {currentTool}</span>
        <div style={{ flex: 1 }} />
        
        {/* 撤销/重做按钮 */}
        <button onClick={undo} disabled={!canUndo} style={{ marginRight: 8, opacity: canUndo ? 1 : 0.5 }}>↩ Undo</button>
        <button onClick={redo} disabled={!canRedo} style={{ marginRight: 16, opacity: canRedo ? 1 : 0.5 }}>↪ Redo</button>
        
        {/* 保存状态 */}
        {isSaving && <span style={{ color: '#4a9eff', fontSize: 12 }}>Saving...</span>}
        {lastSaved && !isSaving && (
          <span style={{ color: '#666', fontSize: 11 }}>
            Saved {lastSaved.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 左侧工具栏 */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
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
        <div style={{ flex: 1, position: 'relative' }}>
          {viewMode === '2d' ? (
            <Stage
              width={window.innerWidth - 470}
              height={window.innerHeight - 70}
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
              width={window.innerWidth - 470} 
              height={window.innerHeight - 70} 
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

      {/* 底部状态栏 */}
      <div style={{ height: 30, backgroundColor: '#2d2d2d', borderTop: '1px solid #3d3d3d', display: 'flex', alignItems: 'center', padding: '0 16px', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 16 }}>
          <span style={{ color: '#888', fontSize: 12 }}>{pcbData.footprints.length} Footprints</span>
          <span style={{ color: '#888', fontSize: 12 }}>{pcbData.tracks.length} Tracks</span>
          <span style={{ color: '#888', fontSize: 12 }}>{pcbData.vias.length} Vias</span>
          {selectedIds.length > 0 && (
            <span style={{ color: '#4a9eff', fontSize: 12 }}>{selectedIds.length} Selected</span>
          )}
        </div>
        <span style={{ color: '#4a9eff', fontSize: 12 }}>Active: {activeLayer}</span>
      </div>
    </div>
  );
};

export default PCBEditor;
