/**
 * 铜箔区域渲染器
 * 显示PCB铜箔区域（铺铜）
 */

import React from 'react';
import { Line } from 'react-konva';
import { FullPCBData } from '../services/api';
import { MM_TO_PX } from '../data/samplePCB';

interface ZoneRendererProps {
  zones: FullPCBData['zones'];
  layer?: string;
}

// 默认板框范围（如果没有板框数据）
const DEFAULT_BOARD = {
  x: 0,
  y: 0,
  width: 100,
  height: 80
};

const ZoneRenderer: React.FC<ZoneRendererProps> = ({ zones, layer }) => {
  // 过滤指定层的zone
  const layerZones = zones?.filter(z => !layer || z.layer === layer) || [];

  if (layerZones.length === 0) {
    return null;
  }

  return (
    <>
      {layerZones.map((zone, index) => {
        // 确定层的颜色
        const isTopLayer = zone.layer === 'F.Cu';
        const zoneColor = isTopLayer ? '#FF6B35' : '#35A0FF'; // 顶层橙色，底层蓝色

        return (
          <Line
            key={`zone-${zone.id || index}`}
            points={[
              DEFAULT_BOARD.x * MM_TO_PX,
              DEFAULT_BOARD.y * MM_TO_PX,
              (DEFAULT_BOARD.x + DEFAULT_BOARD.width) * MM_TO_PX,
              DEFAULT_BOARD.y * MM_TO_PX,
              (DEFAULT_BOARD.x + DEFAULT_BOARD.width) * MM_TO_PX,
              (DEFAULT_BOARD.y + DEFAULT_BOARD.height) * MM_TO_PX,
              DEFAULT_BOARD.x * MM_TO_PX,
              (DEFAULT_BOARD.y + DEFAULT_BOARD.height) * MM_TO_PX,
              DEFAULT_BOARD.x * MM_TO_PX,
              DEFAULT_BOARD.y * MM_TO_PX
            ]}
            closed
            fill={zoneColor}
            opacity={0.3}
            stroke={zoneColor}
            strokeWidth={1}
          />
        );
      })}
    </>
  );
};

export default ZoneRenderer;
