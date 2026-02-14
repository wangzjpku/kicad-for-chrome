/**
 * 层管理面板 (Task 3.3)
 */

import React from 'react';
import { Layer } from '../types';
import { sampleLayers } from '../data/samplePCB';

interface LayerPanelProps {
  layers?: Layer[];
  activeLayer?: string;
  onLayerToggle?: (layerId: string) => void;
  onLayerActivate?: (layerId: string) => void;
}

const LayerPanel: React.FC<LayerPanelProps> = ({
  layers = sampleLayers,
  activeLayer = 'F.Cu',
  onLayerToggle,
  onLayerActivate,
}) => {
  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ fontSize: 14, marginBottom: 16, color: '#4a9eff' }}>
        层管理
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {layers.map((layer) => (
          <div
            key={layer.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '8px',
              backgroundColor: activeLayer === layer.id ? '#3d3d3d' : 'transparent',
              borderRadius: 4,
              cursor: 'pointer',
            }}
            onClick={() => onLayerActivate?.(layer.id)}
          >
            {/* 可见性复选框 */}
            <input
              type="checkbox"
              checked={layer.visible}
              onChange={(e) => {
                e.stopPropagation();
                onLayerToggle?.(layer.id);
              }}
              style={{
                marginRight: 8,
                cursor: 'pointer',
              }}
            />

            {/* 颜色指示器 */}
            <div
              style={{
                width: 16,
                height: 16,
                backgroundColor: layer.color,
                borderRadius: 2,
                marginRight: 8,
                border: '1px solid #666666',
              }}
            />

            {/* 层名称 */}
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontSize: 12,
                  color: activeLayer === layer.id ? '#4a9eff' : '#ffffff',
                  fontWeight: activeLayer === layer.id ? 500 : 400,
                }}
              >
                {layer.name}
              </div>
              <div style={{ fontSize: 10, color: '#888888' }}>
                {layer.type === 'signal' && '信号层'}
                {layer.type === 'power' && '电源层'}
                {layer.type === 'dielectric' && '介质层'}
              </div>
            </div>

            {/* 激活指示器 */}
            {activeLayer === layer.id && (
              <div
                style={{
                  width: 8,
                  height: 8,
                  backgroundColor: '#4a9eff',
                  borderRadius: '50%',
                }}
              />
            )}
          </div>
        ))}
      </div>

      {/* 层操作按钮 */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button
          style={{
            flex: 1,
            padding: '6px',
            fontSize: 11,
            backgroundColor: '#3d3d3d',
            color: '#ffffff',
            border: '1px solid #4d4d4d',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          显示全部
        </button>
        <button
          style={{
            flex: 1,
            padding: '6px',
            fontSize: 11,
            backgroundColor: '#3d3d3d',
            color: '#ffffff',
            border: '1px solid #4d4d4d',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          隐藏全部
        </button>
      </div>
    </div>
  );
};

export default LayerPanel;
