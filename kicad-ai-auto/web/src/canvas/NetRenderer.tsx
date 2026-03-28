/**
 * 网络渲染器 - 显示PCB网络连接
 * 包括鼠线(ratsnest)和网络高亮
 */

import React, { useMemo } from 'react';
import { Line } from 'react-konva';
import { FullPCBData } from '../services/api';
import { MM_TO_PX } from '../data/samplePCB';

interface NetRendererProps {
  fullPCBData: FullPCBData | null;
  highlightedNet: string | null;
  showRatsnest?: boolean;
}

// 计算两个焊盘之间的鼠线
// 注意：当前IPC API返回的数据中焊盘没有netId，这里简化处理
const calculateRatsnest = (fullPCBData: FullPCBData) => {
  if (!fullPCBData.footprints || !fullPCBData.nets) return [];

  const ratsnestLines: { x1: number; y1: number; x2: number; y2: number; netName: string }[] = [];

  // 简化处理：获取所有焊盘位置
  const allPads: Array<{ x: number; y: number; ref: string; pad: string }> = [];

  for (const fp of fullPCBData.footprints) {
    if (!fp.pad) continue;
    for (const pad of fp.pad) {
      allPads.push({
        x: pad.position.x,
        y: pad.position.y,
        ref: fp.reference,
        pad: pad.number
      });
    }
  }

  // 简单绘制：连接相邻焊盘作为示例
  // 完整实现需要从tracks中获取实际连接信息
  if (allPads.length >= 2) {
    for (let i = 0; i < Math.min(allPads.length - 1, 10); i++) {
      ratsnestLines.push({
        x1: allPads[i].x * MM_TO_PX,
        y1: allPads[i].y * MM_TO_PX,
        x2: allPads[i + 1].x * MM_TO_PX,
        y2: allPads[i + 1].y * MM_TO_PX,
        netName: 'NET'
      });
    }
  }

  return ratsnestLines;
};

const NetRenderer: React.FC<NetRendererProps> = ({
  fullPCBData,
  highlightedNet,
  showRatsnest = true
}) => {
  // 计算鼠线
  const ratsnestLines = useMemo(() => {
    if (!fullPCBData || !showRatsnest) return [];
    return calculateRatsnest(fullPCBData);
  }, [fullPCBData, showRatsnest]);

  // 如果没有网络数据，不渲染
  if (!fullPCBData?.nets || fullPCBData.nets.length === 0) {
    return null;
  }

  return (
    <>
      {/* 鼠线层 - 显示未布线的连接 */}
      {ratsnestLines.map((line, index) => {
        const isHighlighted = highlightedNet && line.netName === highlightedNet;
        return (
          <Line
            key={`ratsnest-${index}`}
            points={[line.x1, line.y1, line.x2, line.y2]}
            stroke={isHighlighted ? '#FFFF00' : '#888888'}
            strokeWidth={isHighlighted ? 0.5 : 0.3}
            dash={isHighlighted ? undefined : [2, 2]}
            opacity={isHighlighted ? 1 : 0.5}
          />
        );
      })}
    </>
  );
};

export default NetRenderer;
