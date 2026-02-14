/**
 * 简化版工具栏组件 (Task 2.6)
 * 集成到 PCBEditor 中
 */

import React from 'react';
import { usePCBStore, ToolType } from '../stores/pcbStore';
import { Footprint } from '../types';

const SimpleToolbar: React.FC = () => {
  const { 
    currentTool, 
    setCurrentTool, 
    selectedIds, 
    clearSelection,
    addFootprint, 
    pushHistory, 
    setSelectedIds, 
    pcbData 
  } = usePCBStore();

  const tools: { type: ToolType; name: string; icon: string }[] = [
    { type: 'select', name: '选择', icon: '↖' },
    { type: 'move', name: '移动', icon: '✥' },
    { type: 'route', name: '布线', icon: '╱' },
    { type: 'place_footprint', name: '放置封装', icon: '□' },
  ];

  // 处理添加封装
  const handleAddFootprint = () => {
    if (!pcbData) return;
    
    // 生成唯一ID
    const id = `FP${Date.now()}`;
    
    // 计算新封装的序号
    const footprintCount = pcbData.footprints.filter(fp => fp.reference.startsWith('FP')).length;
    const reference = `FP${footprintCount + 1}`;
    
    // 创建新封装（放在画布中心附近，稍微偏移以避免重叠）
    const offsetX = (footprintCount % 5) * 5; // 5mm间隔
    const offsetY = Math.floor(footprintCount / 5) * 5;
    
    const newFootprint: Footprint = {
      id,
      type: 'footprint',
      libraryName: 'Custom',
      footprintName: 'Generic_0603',
      fullFootprintName: 'Custom:Generic_0603',
      reference,
      value: '10k',
      position: { x: 50 + offsetX, y: 40 + offsetY }, // 画布中心附近
      rotation: 0,
      layer: 'F.Cu',
      pads: [
        {
          id: `${id}_pad1`,
          number: '1',
          type: 'smd',
          shape: 'rect',
          position: { x: -0.8, y: 0 },
          size: { x: 1.0, y: 1.0 },
          layers: ['F.Cu'],
        },
        {
          id: `${id}_pad2`,
          number: '2',
          type: 'smd',
          shape: 'rect',
          position: { x: 0.8, y: 0 },
          size: { x: 1.0, y: 1.0 },
          layers: ['F.Cu'],
        },
      ],
      attributes: {},
    };
    
    pushHistory(); // 保存历史
    addFootprint(newFootprint);
    setSelectedIds([id]); // 自动选中新添加的封装
  };

  return (
    <div
      style={{
        width: 50,
        height: '100%',
        backgroundColor: '#2d2d2d',
        borderRight: '1px solid #3d3d3d',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '8px 0',
      }}
    >
      {tools.map((tool) => (
        <button
          key={tool.type}
          onClick={() => setCurrentTool(tool.type)}
          style={{
            width: 36,
            height: 36,
            marginBottom: 8,
            backgroundColor: currentTool === tool.type ? '#4a9eff' : '#3d3d3d',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            transition: 'background-color 0.2s',
          }}
          title={tool.name}
        >
          <span>{tool.icon}</span>
        </button>
      ))}

      <div style={{ flex: 1 }} />

      {/* 添加封装按钮 */}
      <button
        onClick={handleAddFootprint}
        style={{
          width: 36,
          height: 36,
          marginBottom: 16,
          backgroundColor: '#4CAF50',
          color: '#ffffff',
          border: 'none',
          borderRadius: 4,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 20,
          transition: 'background-color 0.2s',
        }}
        title="添加封装 (+)"
      >
        +
      </button>

      {/* 选中信息 */}
      {selectedIds.length > 0 && (
        <div
          style={{
            padding: '8px 4px',
            backgroundColor: '#3d3d3d',
            borderRadius: 4,
            marginBottom: 8,
            textAlign: 'center',
          }}
        >
          <span style={{ color: '#ffffff', fontSize: 10 }}>
            {selectedIds.length} 选中
          </span>
          <button
            onClick={clearSelection}
            style={{
              marginTop: 4,
              padding: '2px 4px',
              fontSize: 10,
              backgroundColor: '#ff4444',
              color: '#ffffff',
              border: 'none',
              borderRadius: 2,
              cursor: 'pointer',
            }}
          >
            清除
          </button>
        </div>
      )}
    </div>
  );
};

export default SimpleToolbar;
