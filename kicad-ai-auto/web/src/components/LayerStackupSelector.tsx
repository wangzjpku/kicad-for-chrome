/**
 * Layer Stackup Selector Component
 *
 * Phase 4: 多层板层叠选择器
 * - 支持2层/4层/6层板模板
 * - 显示层叠结构图
 * - 阻抗配置选项
 */

import React, { useState, useEffect } from 'react';
import './LayerStackupSelector.css';

interface Layer {
  name: string;
  type: 'signal' | 'plane' | 'mixed';
  planeType?: 'GND' | 'PWR';
  thickness: number;
}

interface StackupTemplate {
  id: string;
  name: string;
  layerCount: number;
  totalThickness: number;
  layers: Layer[];
  bestFor: string[];
}

const STACKUP_TEMPLATES: StackupTemplate[] = [
  {
    id: '2layer',
    name: '2层板',
    layerCount: 2,
    totalThickness: 1.6,
    layers: [
      { name: 'F.Cu', type: 'signal', thickness: 0.035 },
      { name: 'B.Cu', type: 'signal', thickness: 0.035 },
    ],
    bestFor: ['简单电路', '低成本设计', '原型验证']
  },
  {
    id: '4layer_standard',
    name: '4层板标准',
    layerCount: 4,
    totalThickness: 1.6,
    layers: [
      { name: 'F.Cu', type: 'signal', thickness: 0.035 },
      { name: 'GND', type: 'plane', planeType: 'GND', thickness: 0.035 },
      { name: 'PWR', type: 'plane', planeType: 'PWR', thickness: 0.035 },
      { name: 'B.Cu', type: 'signal', thickness: 0.035 },
    ],
    bestFor: ['高速信号', '电源完整性', 'EMI控制']
  },
  {
    id: '4layer_thin',
    name: '4层板薄型',
    layerCount: 4,
    totalThickness: 1.0,
    layers: [
      { name: 'F.Cu', type: 'signal', thickness: 0.035 },
      { name: 'GND', type: 'plane', planeType: 'GND', thickness: 0.035 },
      { name: 'PWR', type: 'plane', planeType: 'PWR', thickness: 0.035 },
      { name: 'B.Cu', type: 'signal', thickness: 0.035 },
    ],
    bestFor: ['空间受限', '移动设备', '可穿戴设备']
  },
  {
    id: '6layer_standard',
    name: '6层板标准',
    layerCount: 6,
    totalThickness: 1.6,
    layers: [
      { name: 'F.Cu', type: 'signal', thickness: 0.035 },
      { name: 'GND1', type: 'plane', planeType: 'GND', thickness: 0.035 },
      { name: 'In1.Cu', type: 'signal', thickness: 0.035 },
      { name: 'In2.Cu', type: 'signal', thickness: 0.035 },
      { name: 'PWR', type: 'plane', planeType: 'PWR', thickness: 0.035 },
      { name: 'B.Cu', type: 'signal', thickness: 0.035 },
    ],
    bestFor: ['复杂电路', '多电源域', '高速总线']
  },
  {
    id: '6layer_optimized',
    name: '6层板优化',
    layerCount: 6,
    totalThickness: 1.6,
    layers: [
      { name: 'F.Cu', type: 'signal', thickness: 0.035 },
      { name: 'In1.Cu', type: 'signal', thickness: 0.035 },
      { name: 'GND', type: 'plane', planeType: 'GND', thickness: 0.035 },
      { name: 'PWR', type: 'plane', planeType: 'PWR', thickness: 0.035 },
      { name: 'In2.Cu', type: 'signal', thickness: 0.035 },
      { name: 'B.Cu', type: 'signal', thickness: 0.035 },
    ],
    bestFor: ['高频设计', '差分信号', '阻抗控制']
  },
];

interface LayerStackupSelectorProps {
  value?: string;
  onChange?: (templateId: string, template: StackupTemplate) => void;
  showImpedanceOptions?: boolean;
}

const LayerStackupSelector: React.FC<LayerStackupSelectorProps> = ({
  value = '4layer_standard',
  onChange,
  showImpedanceOptions = true
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<string>(value);
  const [expandedView, setExpandedView] = useState(false);

  useEffect(() => {
    const template = STACKUP_TEMPLATES.find(t => t.id === selectedTemplate);
    if (template && onChange) {
      onChange(selectedTemplate, template);
    }
  }, [selectedTemplate]);

  const currentTemplate = STACKUP_TEMPLATES.find(t => t.id === selectedTemplate);

  const getLayerColor = (layer: Layer): string => {
    if (layer.type === 'plane') {
      return layer.planeType === 'GND' ? '#4CAF50' : '#2196F3';
    }
    return '#FFC107'; // Signal layer
  };

  const getLayerTypeName = (layer: Layer): string => {
    if (layer.type === 'plane') {
      return layer.planeType === 'GND' ? '地平面' : '电源平面';
    }
    return '信号层';
  };

  return (
    <div className="layer-stackup-selector">
      <div className="stackup-header">
        <h3>PCB层叠配置</h3>
        <span className="thickness-badge">
          {currentTemplate?.totalThickness}mm
        </span>
      </div>

      {/* Template Selection */}
      <div className="template-grid">
        {STACKUP_TEMPLATES.map(template => (
          <div
            key={template.id}
            className={`template-card ${selectedTemplate === template.id ? 'selected' : ''}`}
            onClick={() => setSelectedTemplate(template.id)}
          >
            <div className="template-header">
              <span className="layer-count">{template.layerCount}层</span>
              <span className="template-name">{template.name}</span>
            </div>
            <div className="template-preview">
              {template.layers.slice(0, 4).map((layer, idx) => (
                <div
                  key={idx}
                  className="preview-layer"
                  style={{ backgroundColor: getLayerColor(layer) }}
                />
              ))}
              {template.layers.length > 4 && (
                <span className="more-layers">+{template.layers.length - 4}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Detailed View */}
      {currentTemplate && (
        <div className="stackup-detail">
          <div className="detail-header">
            <h4>{currentTemplate.name}</h4>
            <button
              className="expand-btn"
              onClick={() => setExpandedView(!expandedView)}
            >
              {expandedView ? '收起' : '展开'}
            </button>
          </div>

          {/* Layer Stackup Diagram */}
          <div className="stackup-diagram">
            {[...currentTemplate.layers].reverse().map((layer, idx) => (
              <div key={idx} className="diagram-layer">
                <div
                  className="layer-bar"
                  style={{ backgroundColor: getLayerColor(layer) }}
                />
                <div className="layer-info">
                  <span className="layer-name">{layer.name}</span>
                  <span className="layer-type">{getLayerTypeName(layer)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Best For Tags */}
          <div className="best-for-section">
            <span className="label">适用场景:</span>
            <div className="tags">
              {currentTemplate.bestFor.map((use, idx) => (
                <span key={idx} className="tag">{use}</span>
              ))}
            </div>
          </div>

          {/* Impedance Options */}
          {showImpedanceOptions && currentTemplate.layerCount >= 4 && (
            <div className="impedance-options">
              <h5>阻抗配置</h5>
              <div className="impedance-presets">
                <div className="preset-item">
                  <span className="preset-name">USB 2.0</span>
                  <span className="preset-value">90Ω 差分</span>
                </div>
                <div className="preset-item">
                  <span className="preset-name">DDR4</span>
                  <span className="preset-value">40Ω 单端</span>
                </div>
                <div className="preset-item">
                  <span className="preset-name">HDMI</span>
                  <span className="preset-value">100Ω 差分</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LayerStackupSelector;
export { STACKUP_TEMPLATES };
export type { StackupTemplate, Layer };