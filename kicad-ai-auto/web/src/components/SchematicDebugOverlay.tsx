/**
 * 原理图调试工具 - SVG可视化
 * 用于诊断原理图渲染问题
 */

import React, { useMemo } from 'react';

// 调试信息组件
interface DebugInfoProps {
  stageWidth: number;
  stageHeight: number;
  zoom: number;
  pan: { x: number; y: number };
  components: Array<{
    id: string;
    position: { x: number; y: number };
    reference?: string;
    value?: string;
  }>;
}

export const SchematicDebugOverlay: React.FC<DebugInfoProps> = ({
  stageWidth,
  stageHeight,
  zoom,
  pan,
  components,
}) => {
  // 计算元件在视口中的位置
  const componentViews = useMemo(() => {
    return components.map((comp) => {
      const x = comp.position.x * zoom + pan.x;
      const y = comp.position.y * zoom + pan.y;
      const inViewport =
        x >= -50 && x <= stageWidth + 50 &&
        y >= -50 && y <= stageHeight + 50;

      return {
        ...comp,
        viewX: x,
        viewY: y,
        inViewport,
      };
    });
  }, [components, zoom, pan, stageWidth, stageHeight]);

  // 计算内容边界
  const bounds = useMemo(() => {
    if (components.length === 0) {
      return { minX: 0, maxX: stageWidth, minY: 0, maxY: stageHeight };
    }

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    components.forEach((comp) => {
      minX = Math.min(minX, comp.position.x);
      maxX = Math.max(maxX, comp.position.x);
      minY = Math.min(minY, comp.position.y);
      maxY = Math.max(maxY, comp.position.y);
    });

    // 添加边距
    const padding = 50;
    return {
      minX: minX - padding,
      maxX: maxX + padding,
      minY: minY - padding,
      maxY: maxY + padding,
    };
  }, [components, stageWidth, stageHeight]);

  // 计算自动居中的推荐 pan 值
  const recommendedPan = useMemo(() => {
    if (components.length === 0) return { x: 50, y: 50 };

    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;

    return {
      x: stageWidth / 2 - centerX * zoom,
      y: stageHeight / 2 - centerY * zoom,
    };
  }, [components, bounds, zoom, stageWidth, stageHeight]);

  return (
    <div
      style={{
        position: 'absolute',
        top: 10,
        left: 10,
        background: 'rgba(0, 0, 0, 0.85)',
        color: '#00ff00',
        padding: '12px',
        borderRadius: '8px',
        fontSize: '11px',
        fontFamily: 'monospace',
        zIndex: 1000,
        minWidth: '280px',
        border: '1px solid #00ff00',
      }}
    >
      <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#fff' }}>
        🔧 原理图调试信息
      </div>

      {/* 画布状态 */}
      <div style={{ marginBottom: '8px' }}>
        <div style={{ color: '#888' }}>画布尺寸:</div>
        <div>{stageWidth} x {stageHeight} px</div>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={{ color: '#888' }}>缩放 (zoom):</div>
        <div>{(zoom * 100).toFixed(0)}%</div>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={{ color: '#888' }}>平移 (pan):</div>
        <div>x: {pan.x.toFixed(1)}, y: {pan.y.toFixed(1)}</div>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={{ color: '#888' }}>内容边界:</div>
        <div>
          x: {bounds.minX.toFixed(0)} ~ {bounds.maxX.toFixed(0)}
        </div>
        <div>
          y: {bounds.minY.toFixed(0)} ~ {bounds.maxY.toFixed(0)}
        </div>
      </div>

      {/* 推荐值 */}
      <div style={{ marginBottom: '8px', padding: '8px', background: 'rgba(0,100,0,0.3)', borderRadius: '4px' }}>
        <div style={{ color: '#4a9eff', fontWeight: 'bold' }}>推荐设置:</div>
        <div>pan.x: {recommendedPan.x.toFixed(0)}</div>
        <div>pan.y: {recommendedPan.y.toFixed(0)}</div>
      </div>

      {/* 元件列表 */}
      <div style={{ marginTop: '8px' }}>
        <div style={{ color: '#888' }}>元件 ({components.length}):</div>
        {componentViews.map((comp, idx) => (
          <div
            key={comp.id || idx}
            style={{
              padding: '4px',
              margin: '2px 0',
              background: comp.inViewport ? 'rgba(0,255,0,0.1)' : 'rgba(255,0,0,0.2)',
              borderRadius: '2px',
            }}
          >
            <div style={{ color: comp.inViewport ? '#0f0' : '#f55' }}>
              {comp.inViewport ? '✓' : '✗'} {comp.reference || `元件${idx + 1}`}
            </div>
            <div style={{ color: '#888', fontSize: '10px' }}>
              位置: ({comp.position.x.toFixed(0)}, {comp.position.y.toFixed(0)})
            </div>
            <div style={{ color: '#888', fontSize: '10px' }}>
              视图: ({comp.viewX.toFixed(0)}, {comp.viewY.toFixed(0)})
            </div>
            {comp.value && (
              <div style={{ color: '#aaa', fontSize: '10px' }}>
                值: {comp.value}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 问题诊断 */}
      {componentViews.filter(c => !c.inViewport).length > 0 && (
        <div style={{
          marginTop: '8px',
          padding: '8px',
          background: 'rgba(255,100,0,0.2)',
          borderRadius: '4px',
          border: '1px solid #ff6600',
        }}>
          <div style={{ color: '#ff6600', fontWeight: 'bold' }}>⚠️ 问题诊断</div>
          <div style={{ fontSize: '10px' }}>
            {componentViews.filter(c => !c.inViewport).length} 个元件在视口外！
          </div>
          <div style={{ fontSize: '10px', marginTop: '4px' }}>
            点击下方按钮自动调整视图
          </div>
        </div>
      )}
    </div>
  );
};

// 导出推荐视图计算函数
export function calculateRecommendedPan(
  components: Array<{ position: { x: number; y: number } }>,
  stageWidth: number,
  stageHeight: number,
  zoom: number
): { x: number; y: number } {
  if (components.length === 0) {
    return { x: 50, y: 50 };
  }

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  components.forEach((comp) => {
    minX = Math.min(minX, comp.position.x);
    maxX = Math.max(maxX, comp.position.x);
    minY = Math.min(minY, comp.position.y);
    maxY = Math.max(maxY, comp.position.y);
  });

  const padding = 50;
  const contentWidth = maxX - minX + padding * 2;
  const contentHeight = maxY - minY + padding * 2;

  // 计算居中的缩放
  const scaleX = stageWidth / contentWidth;
  const scaleY = stageHeight / contentHeight;
  const autoZoom = Math.min(scaleX, scaleY, 1) * 0.8;

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  return {
    x: stageWidth / 2 - centerX * autoZoom,
    y: stageHeight / 2 - centerY * autoZoom,
  };
}

export default SchematicDebugOverlay;
