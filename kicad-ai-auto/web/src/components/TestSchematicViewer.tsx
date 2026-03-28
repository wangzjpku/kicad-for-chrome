/**
 * 原理图渲染修复演示
 * 展示自动视图调整功能
 */

import React, { useState, useEffect } from 'react';
import { Stage, Layer, Rect, Line, Text, Group, Circle } from 'react-konva';

// 测试数据 - 模拟 AI 生成的 LED 电路
const testComponents = [
  { id: '1', reference: 'LED1', value: 'Red LED', position: { x: 150, y: 150 }, category: 'led' },
  { id: '2', reference: 'R1', value: '1kΩ', position: { x: 250, y: 150 }, category: 'resistor' },
  { id: '3', reference: 'V1', value: '5V', position: { x: 100, y: 150 }, category: 'power' },
];

const TestSchematicViewer: React.FC = () => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [showDebug, setShowDebug] = useState(true);

  // 自动调整视图
  useEffect(() => {
    // 计算内容边界
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    testComponents.forEach(comp => {
      minX = Math.min(minX, comp.position.x);
      maxX = Math.max(maxX, comp.position.x);
      minY = Math.min(minY, comp.position.y);
      maxY = Math.max(maxY, comp.position.y);
    });

    // 计算居中的视图
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const stageWidth = 600;
    const stageHeight = 400;

    setPan({
      x: stageWidth / 2 - centerX,
      y: stageHeight / 2 - centerY,
    });
  }, []);

  // 滚轮缩放
  const handleWheel = (e: any) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const newScale = e.evt.deltaY > 0 ? zoom / scaleBy : zoom * scaleBy;
    setZoom(Math.max(0.1, Math.min(newScale, 5)));
  };

  // 渲染元件
  const renderComponent = (comp: typeof testComponents[0]) => {
    const colors: Record<string, string> = {
      led: '#ff0000',
      resistor: '#00ff00',
      power: '#ff6600',
    };

    return (
      <Group
        key={comp.id}
        x={comp.position.x}
        y={comp.position.y}
      >
        {/* 调试边框 */}
        <Rect
          x={-30}
          y={-20}
          width={60}
          height={40}
          stroke="#00ff00"
          strokeWidth={1}
          dash={[4, 4]}
        />

        {/* 元件符号 */}
        {comp.category === 'led' && (
          <>
            {/* LED 三角形 */}
            <Line
              points={[-15, -8, -15, 8, 0, 0]}
              closed
              fill={colors.led}
              stroke={colors.led}
            />
            <Line points={[0, -8, 0, 8]} stroke={colors.led} />
          </>
        )}

        {comp.category === 'resistor' && (
          <Rect
            x={-15}
            y={-8}
            width={30}
            height={16}
            fill="transparent"
            stroke={colors.resistor}
          />
        )}

        {comp.category === 'power' && (
          <>
            <Line points={[0, -15, -5, -5]} stroke={colors.power} />
            <Line points={[0, -15, 5, -5]} stroke={colors.power} />
            <Text text={comp.value} x={-10} y={-25} fill={colors.power} fontSize={12} />
          </>
        )}

        {/* 引脚 */}
        <Circle x={-25} y={0} radius={3} fill="#ffcc00" />
        <Circle x={25} y={0} radius={3} fill="#ffcc00" />

        {/* 标签 */}
        <Text
          text={comp.reference}
          x={-20}
          y={-35}
          fill="#00aaff"
          fontSize={11}
          fontStyle="bold"
        />
        <Text
          text={comp.value}
          x={-20}
          y={15}
          fill="#888888"
          fontSize={9}
        />
      </Group>
    );
  };

  return (
    <div style={{ padding: '20px', background: '#1a1a1a', minHeight: '100vh' }}>
      <h2 style={{ color: '#fff', marginBottom: '10px' }}>🔧 原理图渲染修复演示</h2>

      <div style={{ color: '#888', marginBottom: '20px' }}>
        <p>修复前问题: 元件数据已加载，但画布显示空白</p>
        <p>修复方案: 自动计算内容边界并调整视图到中心</p>
      </div>

      {/* 调试信息 */}
      {showDebug && (
        <div style={{
          position: 'absolute',
          top: '120px',
          left: '30px',
          background: 'rgba(0,0,0,0.85)',
          color: '#00ff00',
          padding: '15px',
          borderRadius: '8px',
          fontSize: '12px',
          fontFamily: 'monospace',
          border: '1px solid #00ff00',
          zIndex: 1000,
        }}>
          <div style={{ fontWeight: 'bold', color: '#fff', marginBottom: '8px' }}>
            🔧 调试信息
          </div>
          <div>缩放: {(zoom * 100).toFixed(0)}%</div>
          <div>平移: x={pan.x.toFixed(0)}, y={pan.y.toFixed(0)}</div>
          <div>元件数: {testComponents.length}</div>
          <div style={{ marginTop: '8px', color: '#4a9eff' }}>
            ✓ 自动视图已应用
          </div>
        </div>
      )}

      {/* 画布 */}
      <div style={{ border: '2px solid #333', borderRadius: '8px', overflow: 'hidden' }}>
        <Stage
          width={600}
          height={400}
          onWheel={handleWheel}
          scaleX={zoom}
          scaleY={zoom}
          x={pan.x}
          y={pan.y}
          draggable
          onDragEnd={(e) => setPan({ x: e.target.x(), y: e.target.y() })}
        >
          <Layer>
            {/* 网格 */}
            {Array.from({ length: 40 }).map((_, i) => (
              <Line
                key={`v${i}`}
                points={[i * 20, 0, i * 20, 600]}
                stroke="#333"
                strokeWidth={0.5}
              />
            ))}
            {Array.from({ length: 30 }).map((_, i) => (
              <Line
                key={`h${i}`}
                points={[0, i * 20, 800, i * 20]}
                stroke="#333"
                strokeWidth={0.5}
              />
            ))}

            {/* 导线（连接元件） */}
            <Line
              points={[100, 150, 120, 150]}
              stroke="#00ff00"
              strokeWidth={2}
            />
            <Line
              points={[180, 150, 220, 150]}
              stroke="#00ff00"
              strokeWidth={2}
            />
            <Line
              points={[280, 150, 320, 150]}
              stroke="#00ff00"
              strokeWidth={2}
            />

            {/* 元件 */}
            {testComponents.map(renderComponent)}
          </Layer>
        </Stage>
      </div>

      {/* 控制按钮 */}
      <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
        <button
          onClick={() => setZoom(z => Math.min(z * 1.2, 5))}
          style={{
            padding: '8px 16px',
            background: '#333',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          放大 +
        </button>
        <button
          onClick={() => setZoom(z => Math.max(z / 1.2, 0.1))}
          style={{
            padding: '8px 16px',
            background: '#333',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          缩小 -
        </button>
        <button
          onClick={() => {
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            testComponents.forEach(comp => {
              minX = Math.min(minX, comp.position.x);
              maxX = Math.max(maxX, comp.position.x);
              minY = Math.min(minY, comp.position.y);
              maxY = Math.max(maxY, comp.position.y);
            });
            setPan({
              x: 300 - (minX + maxX) / 2,
              y: 200 - (minY + maxY) / 2,
            });
            setZoom(1);
          }}
          style={{
            padding: '8px 16px',
            background: '#4a9eff',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          重置视图
        </button>
        <button
          onClick={() => setShowDebug(!showDebug)}
          style={{
            padding: '8px 16px',
            background: showDebug ? '#ff6600' : '#333',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          {showDebug ? '关闭调试' : '显示调试'}
        </button>
      </div>

      {/* 电路信息 */}
      <div style={{ marginTop: '20px', color: '#888', fontSize: '14px' }}>
        <div style={{ color: '#fff', fontWeight: 'bold' }}>当前电路: LED指示电路</div>
        <div>包含: LED1 (红色发光二极管), R1 (1kΩ限流电阻), 5V电源</div>
      </div>
    </div>
  );
};

export default TestSchematicViewer;
