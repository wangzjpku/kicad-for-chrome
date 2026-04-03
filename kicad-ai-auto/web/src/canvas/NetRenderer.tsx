/**
 * 网络渲染器 - 显示PCB网络连接
 * 包括鼠线(ratsnest)和网络高亮
 *
 * Phase 2.4: 真实的 ratsnest 实现
 * - 基于网络表计算连接
 * - 使用 MST (最小生成树) 算法
 * - 只显示未布线的连接
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

interface PadLocation {
  x: number;
  y: number;
  ref: string;
  padNumber: string;
  netName?: string;
}

interface RatsnestLine {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  netName: string;
  netId: string;
}

/**
 * 计算两点之间的欧几里得距离
 */
function distance(p1: { x: number; y: number }, p2: { x: number; y: number }): number {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Kruskal's MST 算法实现
 * 返回连接点的边集合，使得所有点连通且总长度最小
 */
function computeMST(pads: PadLocation[]): Array<[PadLocation, PadLocation]> {
  if (pads.length < 2) return [];
  if (pads.length === 2) return [[pads[0], pads[1]]];

  // 构建所有可能的边
  interface Edge {
    from: number;
    to: number;
    weight: number;
  }

  const edges: Edge[] = [];
  for (let i = 0; i < pads.length; i++) {
    for (let j = i + 1; j < pads.length; j++) {
      edges.push({
        from: i,
        to: j,
        weight: distance(pads[i], pads[j])
      });
    }
  }

  // 按权重排序
  edges.sort((a, b) => a.weight - b.weight);

  // Union-Find 数据结构
  const parent: number[] = Array.from({ length: pads.length }, (_, i) => i);
  const rank: number[] = new Array(pads.length).fill(0);

  function find(x: number): number {
    if (parent[x] !== x) {
      parent[x] = find(parent[x]); // Path compression
    }
    return parent[x];
  }

  function union(x: number, y: number): boolean {
    const px = find(x);
    const py = find(y);
    if (px === py) return false;
    // Union by rank
    if (rank[px] < rank[py]) {
      parent[px] = py;
    } else if (rank[px] > rank[py]) {
      parent[py] = px;
    } else {
      parent[py] = px;
      rank[px]++;
    }
    return true;
  }

  // Kruskal 算法主循环
  const mstEdges: Array<[PadLocation, PadLocation]> = [];
  for (const edge of edges) {
    if (union(edge.from, edge.to)) {
      mstEdges.push([pads[edge.from], pads[edge.to]]);
      if (mstEdges.length === pads.length - 1) break;
    }
  }

  return mstEdges;
}

/**
 * 检查两个焊盘之间是否已有走线连接
 */
function isConnectedByTrack(
  pad1: PadLocation,
  pad2: PadLocation,
  tracks: Array<{ start?: { x: number; y: number }; end?: { x: number; y: number }; points?: Array<{ x: number; y: number }> }>
): boolean {
  // 简化检测：如果两点之间有大致相同坐标的走线，认为已连接
  const threshold = 0.5; // 0.5mm 容差

  for (const track of tracks) {
    let trackPoints: Array<{ x: number; y: number }> = [];

    if (track.points && track.points.length >= 2) {
      trackPoints = track.points;
    } else if (track.start && track.end) {
      trackPoints = [track.start, track.end];
    }

    if (trackPoints.length < 2) continue;

    // 检查走线的起点和终点是否连接了这两个焊盘
    const start = trackPoints[0];
    const end = trackPoints[trackPoints.length - 1];

    const startMatchesPad1 = distance(start, pad1) < threshold;
    const endMatchesPad2 = distance(end, pad2) < threshold;
    const startMatchesPad2 = distance(start, pad2) < threshold;
    const endMatchesPad1 = distance(end, pad1) < threshold;

    if ((startMatchesPad1 && endMatchesPad2) || (startMatchesPad2 && endMatchesPad1)) {
      return true;
    }
  }

  return false;
}

/**
 * 计算鼠线（ratsnest）
 * 真实实现：基于网络表 + MST 算法 + 过滤已布线连接
 */
const calculateRatsnest = (fullPCBData: FullPCBData): RatsnestLine[] => {
  if (!fullPCBData.footprints || !fullPCBData.nets) return [];

  const ratsnestLines: RatsnestLine[] = [];

  // 1. 收集所有焊盘，按网络分组
  const padsByNet: Map<string, PadLocation[]> = new Map();

  for (const fp of fullPCBData.footprints) {
    // fp.pad 是后端返回的字段名
    const pads = fp.pad;
    if (!pads) continue;
    for (const pad of pads) {
      const netName = pad.netId || '';
      if (!netName) continue;

      if (!padsByNet.has(netName)) {
        padsByNet.set(netName, []);
      }
      padsByNet.get(netName)!.push({
        x: pad.position.x,
        y: pad.position.y,
        ref: fp.reference,
        padNumber: pad.number,
        netName: netName
      });
    }
  }

  // 2. 获取已有走线
  const existingTracks = fullPCBData.tracks || [];

  // 3. 对每个网络计算 MST 并过滤已布线连接
  for (const [netName, pads] of padsByNet) {
    if (pads.length < 2) continue;

    // 计算 MST
    const mstEdges = computeMST(pads);

    // 过滤已布线的连接
    for (const [pad1, pad2] of mstEdges) {
      if (!isConnectedByTrack(pad1, pad2, existingTracks)) {
        ratsnestLines.push({
          x1: pad1.x * MM_TO_PX,
          y1: pad1.y * MM_TO_PX,
          x2: pad2.x * MM_TO_PX,
          y2: pad2.y * MM_TO_PX,
          netName: netName,
          netId: netName
        });
      }
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
            key={`ratsnest-${line.netId}-${index}`}
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
