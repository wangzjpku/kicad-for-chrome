/**
 * 板框渲染器 (Task 1.3)
 */

import React from 'react';
import { Line } from 'react-konva';
import { Point2D } from '../types';
import { MM_TO_PX } from '../data/samplePCB';

interface BoardOutlineRendererProps {
  outline: Point2D[];
  color?: string;
  strokeWidth?: number;
}

const BoardOutlineRenderer: React.FC<BoardOutlineRendererProps> = ({
  outline,
  color = '#4A5568', // 深灰色
  strokeWidth = 2,
}) => {
  // 将轮廓点转换为像素坐标
  const points = outline.flatMap((p) => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
  
  // 闭合轮廓
  if (outline.length > 0) {
    points.push(outline[0].x * MM_TO_PX, outline[0].y * MM_TO_PX);
  }

  return (
    <Line
      points={points}
      stroke={color}
      strokeWidth={strokeWidth}
      closed={false}
    />
  );
};

export default BoardOutlineRenderer;
