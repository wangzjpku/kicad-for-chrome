/**
 * 原理图编辑器 (SchematicEditor)
 * 基于 Konva 的原理图编辑画布
 */

import React, { useEffect, useRef, useState } from 'react';
import { Stage, Layer, Line, Text, Group, Circle, Rect } from 'react-konva';
import type { Stage as StageType } from 'konva/lib/Stage';
import type { KonvaEventObject } from 'konva/lib/Node';
import Konva from 'konva';

import { useSchematicStore } from '../stores/schematicStore';
import { SchematicComponent, Wire, Label, Point2D } from '../types';
import { v4 as uuidv4 } from 'uuid';
import AIChatAssistant from '../components/AIChatAssistant';
import SchematicSymbol from '../components/SchematicSymbol';

// 原理图使用1:1像素坐标（AI生成的是像素坐标）
const MM_TO_PX = 1;

// 网格配置
const GRID_SIZE = 10;
const GRID_COLOR = '#333333';

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
  width = 800,
  height = 600
}) => {
  const stageRef = useRef<StageType>(null);
  const [stageRef2, setStageRef] = useState<StageType | null>(null);
  const [showAIChat, setShowAIChat] = useState(false);

  const {
    schematicData,
    setSchematicData,
    loadSchematicData,
    projectId,
    selectedIds,
    setSelectedIds,
    toggleSelection,
    clearSelection,
    currentTool,
    setCurrentTool,
    zoom,
    setZoom,
    pan,
    setPan,
    addComponent,
    addWire,
    addLabel,
    removeSelectedElements,
    canUndo,
    canRedo,
    undo,
    redo,
    updateComponent,
    updateWire,
    updateLabel
  } = useSchematicStore();

  // 获取当前选中的元素（在 useSchematicStore 调用之后）
  const selectedComponent = schematicData?.components.find(c => selectedIds.includes(c.id));
  const selectedWire = schematicData?.wires.find(w => selectedIds.includes(w.id));
  const selectedLabel = schematicData?.labels.find(l => selectedIds.includes(l.id));
  const selectedElement = selectedComponent || selectedWire || selectedLabel;
  
  // 初始化数据 - 加载项目数据或使用示例数据
  useEffect(() => {
    if (projectId) {
      loadSchematicData(projectId);
    } else if (!schematicData) {
      setSchematicData(createEmptySchematic());
    }
  }, [projectId]);
  
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
      if (e.key === 'Delete' || e.key === 'Backspace') {
        removeSelectedElements();
      } else if (e.key === 'Escape') {
        setCurrentTool('select');
        clearSelection();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [removeSelectedElements, setCurrentTool, clearSelection]);
  
  // 生成网格
  const generateGridLines = () => {
    const lines = [];
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
  
  // 渲染元件 - 使用新的符号渲染器
  const renderComponent = (comp: SchematicComponent) => {
    // 安全检查：确保 position 存在
    const selected = selectedIds.includes(comp.id);
    
    // 拖拽结束处理
    const handleDragEnd = (e: KonvaEventObject<DragEvent>) => {
      const node = e.target;
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
          position: { x: (comp.position?.x ?? 0) * MM_TO_PX, y: (comp.position?.y ?? 0) * MM_TO_PX },
          rotation: comp.rotation,
          pins: comp.pins?.map(p => ({
            id: p.id,
            number: p.number,
            name: p.name,
            position: p.position || { x: 0, y: 0 },
            electricalType: p.electricalType
          })),
          footprint: comp.footprint,
          category: comp.libraryName,
          symbolName: comp.symbolName
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
    const points = wire.points.flatMap(p => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
    
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
    const x = label.position.x * MM_TO_PX;
    const y = label.position.y * MM_TO_PX;
    const selected = selectedIds.includes(label.id);
    
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
            schematicData={schematicData}
            projectSpec={{ name: projectId || '未命名项目' }}
            onModifySchematic={(modifications) => {
              console.log('AI modifications:', modifications);
            }}
            defaultExpanded={true}
          />
        </div>
      )}
      
      {/* 画布区域 */}
      <div style={{ flex: 1, position: 'relative', display: 'flex' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Stage
            width={width}
            height={height}
            onWheel={handleWheel}
            onClick={currentTool === 'place_symbol' ? handlePlaceSymbol : handleStageClick}
            draggable={currentTool === 'select'}
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

            {/* 原理图元素层 */}
            <Layer scaleX={zoom} scaleY={zoom}>
              {/* 导线 */}
              {schematicData.wires.map(renderWire)}

              {/* 元件 */}
              {schematicData.components.map(renderComponent)}

              {/* 标签 */}
              {schematicData.labels.map(renderLabel)}
            </Layer>
          </Stage>

          {/* 状态信息 */}
          <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(0,0,0,0.7)', color: '#fff', padding: '5px 10px', borderRadius: 4, fontSize: 12 }}>
            Zoom: {(zoom * 100).toFixed(0)}% | {schematicData.components.length} 元件 | {schematicData.wires.length} 导线
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

export default SchematicEditor;
