/**
 * KiCad 符号渲染器
 * 根据 KiCad 符号库的真实数据渲染符号
 */

import React, { useEffect, useState } from 'react';
import { Group, Rect, Line, Circle, Text } from 'react-konva';
import { symbolApi, SymbolGraphicsData } from '../services/api';

interface KiCadSymbolRendererProps {
  library: string;
  name: string;
  x: number;
  y: number;
  rotation?: number;
  mirror?: boolean;
  scale?: number;
  selected?: boolean;
  onClick?: () => void;
  onPinClick?: (pinNumber: string, pinName: string, x: number, y: number) => void;
  // 直接传递已加载的符号数据，避免重复加载
  graphicsData?: SymbolGraphicsData | null;
}

// 缩放因子：KiCad使用mm，前端需要转换为像素
// 修复：使用MM_TO_PX=2，配合SchematicSymbol中的scale=5，整体1mm=10px
const MM_TO_PX = 2; // 1mm = 2px

const KiCadSymbolRenderer: React.FC<KiCadSymbolRendererProps> = ({
  library,
  name,
  x,
  y,
  rotation = 0,
  mirror = false,
  scale = 1,
  selected = false,
  onClick,
  onPinClick,
  graphicsData, // 直接传入的符号数据
}) => {
  const [symbolData, setSymbolData] = useState<SymbolGraphicsData | null>(graphicsData || null);
  const [loading, setLoading] = useState(!graphicsData);
  const [error, setError] = useState<string | null>(null);

  // 如果传入了graphicsData，直接使用；否则自己加载
  useEffect(() => {
    // 如果已有传入的数据，跳过加载
    if (graphicsData) {
      setSymbolData(graphicsData);
      setLoading(false);
      setError(null);
      return;
    }

    const loadSymbol = async () => {
      try {
        setLoading(true);
        const data = await symbolApi.getSymbolGraphics(library, name);
        if (data.success) {
          setSymbolData(data);
          setError(null);
        } else {
          setError('Failed to load symbol');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    if (library && name) {
      loadSymbol();
    }
  }, [library, name, graphicsData]);

  if (loading || error || !symbolData) {
    // 加载中或错误时显示占位符
    return (
      <Group
        x={x}
        y={y}
        rotation={rotation}
        scaleX={mirror ? -scale : scale}
        scaleY={scale}
        onClick={onClick}
      >
        <Rect
          width={40}
          height={40}
          x={-20}
          y={-20}
          fill={error ? '#ff0000' : '#444444'}
          stroke={selected ? '#ffffff' : '#888888'}
          strokeWidth={selected ? 2 : 1}
        />
        <Text
          text={error ? '?' : '...'}
          fontSize={12}
          fill="#ffffff"
          x={-6}
          y={-6}
        />
      </Group>
    );
  }

  const { graphics, pins } = symbolData;
  // Use brighter colors for dark background
  const strokeColor = selected ? '#ffffff' : '#00ff00';

  // 计算引脚端点位置（考虑引脚方向和长度）
  const getPinEndPosition = (pin: typeof pins[0]) => {
    const rad = (pin.rotation * Math.PI) / 180;
    const endX = pin.x + Math.cos(rad) * pin.length;
    const endY = pin.y + Math.sin(rad) * pin.length;
    return { x: endX, y: endY };
  };

  return (
    <Group
      x={x}
      y={y}
      rotation={rotation}
      scaleX={mirror ? -scale : scale}
      scaleY={scale}
      onClick={onClick}
    >
      {/* 渲染图形元素 */}
      {graphics.length === 0 && (
        /* 如果 graphics 为空，显示占位符 */
        <Group>
          <Rect
            x={-20}
            y={-20}
            width={40}
            height={40}
            fill="transparent"
            stroke="#00ff00"
            strokeWidth={1.5}
          />
          <Text
            text={name}
            x={-18}
            y={-6}
            fontSize={10}
            fill="#00ff00"
          />
        </Group>
      )}
      {graphics.map((g, index) => {
        const key = `${g.type}-${index}`;

        switch (g.type) {
          case 'rectangle':
            return (
              <Rect
                key={key}
                x={(g.x || 0) * MM_TO_PX}
                y={(g.y || 0) * MM_TO_PX}
                width={(g.width || 0) * MM_TO_PX}
                height={(g.height || 0) * MM_TO_PX}
                stroke={strokeColor}
                strokeWidth={(g.strokeWidth || 0.254) * MM_TO_PX}
                fill={g.fill === 'background' ? '#1a1a1a' : undefined}
              />
            );

          case 'polyline':
            if (!g.points || g.points.length < 2) return null;
            const points = g.points.flatMap(p => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
            return (
              <Line
                key={key}
                points={points}
                stroke={strokeColor}
                strokeWidth={(g.strokeWidth || 0.254) * MM_TO_PX}
                lineCap="round"
                lineJoin="round"
              />
            );

          case 'line':
            // 单条线段 (x1, y1) -> (x2, y2)
            if (g.x1 === undefined || g.y1 === undefined || g.x2 === undefined || g.y2 === undefined) return null;
            return (
              <Line
                key={key}
                points={[g.x1 * MM_TO_PX, g.y1 * MM_TO_PX, g.x2 * MM_TO_PX, g.y2 * MM_TO_PX]}
                stroke={strokeColor}
                strokeWidth={(g.strokeWidth || 0.254) * MM_TO_PX}
                lineCap="round"
              />
            );

          case 'circle':
            return (
              <Circle
                key={key}
                x={(g.cx || 0) * MM_TO_PX}
                y={(g.cy || 0) * MM_TO_PX}
                radius={(g.radius || 0) * MM_TO_PX}
                stroke={strokeColor}
                strokeWidth={(g.strokeWidth || 0.254) * MM_TO_PX}
                fill={g.fill === 'background' ? '#1a1a1a' : undefined}
              />
            );

          case 'arc':
            // 弧线使用多条线段近似
            if (!g.start || !g.end || !g.center) return null;
            const startAngle = Math.atan2(g.start.y - g.center.y, g.start.x - g.center.x);
            const endAngle = Math.atan2(g.end.y - g.center.y, g.end.x - g.center.x);
            const radius = Math.sqrt(
              Math.pow(g.start.x - g.center.x, 2) + Math.pow(g.start.y - g.center.y, 2)
            );

            // 生成弧线点
            const arcPoints: number[] = [];
            const steps = 20;
            const angleDiff = endAngle - startAngle;
            for (let i = 0; i <= steps; i++) {
              const t = i / steps;
              const angle = startAngle + angleDiff * t;
              arcPoints.push(
                (g.center.x + Math.cos(angle) * radius) * MM_TO_PX,
                (g.center.y + Math.sin(angle) * radius) * MM_TO_PX
              );
            }

            return (
              <Line
                key={key}
                points={arcPoints}
                stroke={strokeColor}
                strokeWidth={(g.strokeWidth || 0.254) * MM_TO_PX}
              />
            );

          default:
            return null;
        }
      })}

      {/* 渲染引脚 */}
      {pins.map((pin) => {
        const endPos = getPinEndPosition(pin);
        return (
          <Group key={`pin-${pin.number}`}>
            {/* 引脚线段 */}
            <Line
              points={[
                pin.x * MM_TO_PX,
                pin.y * MM_TO_PX,
                endPos.x * MM_TO_PX,
                endPos.y * MM_TO_PX,
              ]}
              stroke={strokeColor}
              strokeWidth={1}
            />
            {/* 引脚端点（可点击区域） */}
            <Circle
              x={pin.x * MM_TO_PX}
              y={pin.y * MM_TO_PX}
              radius={6}
              fill="transparent"
              onClick={(e) => {
                e.cancelBubble = true;
                onPinClick?.(pin.number, pin.name, pin.x * MM_TO_PX + x, pin.y * MM_TO_PX + y);
              }}
            />
            {/* 引脚名称（仅在选中或放大时显示） */}
            {selected && (
              <Text
                text={pin.name}
                x={endPos.x * MM_TO_PX + 5}
                y={endPos.y * MM_TO_PX - 6}
                fontSize={8}
                fill="#888888"
              />
            )}
          </Group>
        );
      })}
    </Group>
  );
};

export default KiCadSymbolRenderer;
