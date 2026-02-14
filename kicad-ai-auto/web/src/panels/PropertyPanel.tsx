/**
 * 属性面板 (Task 3.1 + 3.2)
 * 显示和编辑选中元素的属性
 */

import React, { useState, useEffect } from 'react';
import { PCBData, Footprint, Track, Via } from '../types';
import { samplePCB } from '../data/samplePCB';
import { usePCBStore } from '../stores/pcbStore';

interface PropertyPanelProps {
  pcbData: PCBData;
}

const PropertyPanel: React.FC<PropertyPanelProps> = ({ pcbData }) => {
  const { selectedIds, clearSelection, updateFootprintPosition, updateFootprintRotation, removeSelectedElements, pushHistory } = usePCBStore();
  const [localPositions, setLocalPositions] = useState<Record<string, { x: string; y: string }>>({});
  const [localRotations, setLocalRotations] = useState<Record<string, string>>({});

  // 获取选中的元素
  const selectedElements = [
    ...pcbData.footprints.filter((f) => selectedIds.includes(f.id)),
    ...pcbData.tracks.filter((t) => selectedIds.includes(t.id)),
    ...pcbData.vias.filter((v) => selectedIds.includes(v.id)),
  ];

  const selectedElement = selectedElements[0]; // 只编辑第一个选中的

  // 初始化本地值
  useEffect(() => {
    if (selectedElement) {
      const positions: Record<string, { x: string; y: string }> = {};
      const rotations: Record<string, string> = {};
      selectedElements.forEach((el) => {
        if ('position' in el) {
          positions[el.id] = {
            x: el.position.x.toFixed(2),
            y: el.position.y.toFixed(2),
          };
        }
        if ('rotation' in el) {
          rotations[el.id] = el.rotation.toFixed(1);
        }
      });
      setLocalPositions(positions);
      setLocalRotations(rotations);
    }
  }, [selectedElement?.id]);

  // 处理位置输入变化
  const handlePositionChange = (id: string, axis: 'x' | 'y', value: string) => {
    setLocalPositions((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        [axis]: value,
      },
    }));
  };

  // 应用位置变化
  const applyPositionChange = (id: string) => {
    const pos = localPositions[id];
    if (!pos) return;
    
    const x = parseFloat(pos.x);
    const y = parseFloat(pos.y);
    
    if (!isNaN(x) && !isNaN(y)) {
      pushHistory(); // 保存历史记录
      updateFootprintPosition(id, { x, y });
    }
  };

  // 处理旋转输入变化
  const handleRotationChange = (id: string, value: string) => {
    setLocalRotations((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  // 应用旋转变化
  const applyRotationChange = (id: string) => {
    const rot = localRotations[id];
    if (!rot) return;
    
    const rotation = parseFloat(rot);
    
    if (!isNaN(rotation)) {
      pushHistory(); // 保存历史记录
      updateFootprintRotation(id, rotation);
    }
  };

  // 处理删除
  const handleDelete = () => {
    if (selectedIds.length > 0) {
      pushHistory(); // 保存历史记录
      removeSelectedElements();
    }
  };

  if (!selectedElement) {
    return (
      <div style={{ padding: 16, color: '#888888', fontSize: 12 }}>
        请选择一个元素查看属性
      </div>
    );
  }

  return (
    <div style={{ padding: 16, color: '#ffffff' }}>
      <h3 style={{ fontSize: 14, marginBottom: 16, color: '#4a9eff' }}>
        属性
      </h3>

      {/* 元素类型 */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
          类型
        </label>
        <div style={{ fontSize: 12, color: '#ffffff' }}>
          {selectedElement.type === 'footprint' && '封装'}
          {selectedElement.type === 'track' && '走线'}
          {selectedElement.type === 'via' && '过孔'}
        </div>
      </div>

      {/* ID */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
          ID
        </label>
        <div style={{ fontSize: 11, color: '#cccccc', wordBreak: 'break-all' }}>
          {selectedElement.id}
        </div>
      </div>

      {/* 封装特有属性 */}
      {selectedElement.type === 'footprint' && (
        <>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
              位号
            </label>
            <div style={{ fontSize: 12, color: '#ffffff' }}>
              {(selectedElement as Footprint).reference}
            </div>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
              值
            </label>
            <div style={{ fontSize: 12, color: '#ffffff' }}>
              {(selectedElement as Footprint).value}
            </div>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
              封装
            </label>
            <div style={{ fontSize: 12, color: '#ffffff' }}>
              {(selectedElement as Footprint).footprintName}
            </div>
          </div>
        </>
      )}

      {/* 层 */}
      {'layer' in selectedElement && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
            层
          </label>
          <div style={{ fontSize: 12, color: '#ffffff' }}>
            {(selectedElement as Footprint | Track).layer}
          </div>
        </div>
      )}

      {/* 位置编辑 */}
      {'position' in selectedElement && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
            位置 (mm)
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: 10, color: '#666666' }}>X</span>
              <input
                type="text"
                value={localPositions[selectedElement.id]?.x || ''}
                onChange={(e) => handlePositionChange(selectedElement.id, 'x', e.target.value)}
                onBlur={() => applyPositionChange(selectedElement.id)}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  fontSize: 12,
                  backgroundColor: '#3d3d3d',
                  border: '1px solid #4d4d4d',
                  borderRadius: 4,
                  color: '#ffffff',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: 10, color: '#666666' }}>Y</span>
              <input
                type="text"
                value={localPositions[selectedElement.id]?.y || ''}
                onChange={(e) => handlePositionChange(selectedElement.id, 'y', e.target.value)}
                onBlur={() => applyPositionChange(selectedElement.id)}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  fontSize: 12,
                  backgroundColor: '#3d3d3d',
                  border: '1px solid #4d4d4d',
                  borderRadius: 4,
                  color: '#ffffff',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* 旋转 */}
      {selectedElement.type === 'footprint' && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
            旋转 (°)
          </label>
          <input
            type="text"
            value={localRotations[selectedElement.id] || ''}
            onChange={(e) => handleRotationChange(selectedElement.id, e.target.value)}
            onBlur={() => applyRotationChange(selectedElement.id)}
            style={{
              width: '100%',
              padding: '4px 8px',
              fontSize: 12,
              backgroundColor: '#3d3d3d',
              border: '1px solid #4d4d4d',
              borderRadius: 4,
              color: '#ffffff',
              boxSizing: 'border-box',
            }}
          />
        </div>
      )}

      {/* 网络 */}
      {'netId' in selectedElement && (selectedElement as Track | Via).netId && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
            网络
          </label>
          <div style={{ fontSize: 12, color: '#ffffff' }}>
            {(selectedElement as Track | Via).netId}
          </div>
        </div>
      )}

      {/* 线宽 */}
      {selectedElement.type === 'track' && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
            线宽
          </label>
          <div style={{ fontSize: 12, color: '#ffffff' }}>
            {(selectedElement as Track).width} mm
          </div>
        </div>
      )}

      {/* 过孔尺寸 */}
      {selectedElement.type === 'via' && (
        <>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
              外径
            </label>
            <div style={{ fontSize: 12, color: '#ffffff' }}>
              {(selectedElement as Via).size} mm
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#888888', display: 'block', marginBottom: 4 }}>
              钻孔
            </label>
            <div style={{ fontSize: 12, color: '#ffffff' }}>
              {(selectedElement as Via).drill} mm
            </div>
          </div>
        </>
      )}

      {/* 操作按钮组 */}
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button
          onClick={clearSelection}
          style={{
            flex: 1,
            padding: '8px',
            backgroundColor: '#4d4d4d',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          清除选择
        </button>
        <button
          onClick={handleDelete}
          style={{
            flex: 1,
            padding: '8px',
            backgroundColor: '#ff4444',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          删除
        </button>
      </div>
    </div>
  );
};

export default PropertyPanel;
