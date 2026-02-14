/**
 * 简单画布组件 (Task 1.2)
 * 黑色背景 + 网格显示
 */

import React from 'react';
import { Stage, Layer, Line } from 'react-konva';

interface SimpleCanvasProps {
  width?: number;
  height?: number;
  gridSize?: number;
  gridColor?: string;
}

const SimpleCanvas: React.FC<SimpleCanvasProps> = ({
  width = 1000,
  height = 800,
  gridSize = 10,
  gridColor = '#333333',
}) => {
  // 生成网格线
  const generateGridLines = () => {
    const lines = [];
    
    // 垂直线
    for (let x = 0; x <= width; x += gridSize) {
      lines.push(
        <Line
          key={`v-${x}`}
          points={[x, 0, x, height]}
          stroke={gridColor}
          strokeWidth={1}
        />
      );
    }
    
    // 水平线
    for (let y = 0; y <= height; y += gridSize) {
      lines.push(
        <Line
          key={`h-${y}`}
          points={[0, y, width, y]}
          stroke={gridColor}
          strokeWidth={1}
        />
      );
    }
    
    return lines;
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#000000',
        overflow: 'hidden',
      }}
    >
      <Stage width={width} height={height}>
        <Layer>{generateGridLines()}</Layer>
      </Stage>
    </div>
  );
};

export default SimpleCanvas;
