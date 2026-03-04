/**
 * 原理图元件符号渲染器
 * 根据元件类型渲染真实的电路符号，而不是简单的矩形框
 */

import React, { useState, useEffect } from 'react';
import { Group, Rect, Line, Text, Circle, Shape } from 'react-konva';
import Konva from 'konva';
import KiCadSymbolRenderer from './KiCadSymbolRenderer';
import { symbolApi, SymbolGraphicsData } from '../services/api';

interface Pin {
  id: string;
  number: string;
  name: string;
  position: { x: number; y: number };
  electricalType?: string;
}

interface SchematicComponent {
  id: string;
  name: string;
  model: string;
  reference: string;  // 修改为required，用于识别元件类型
  value?: string;
  position: { x: number; y: number };
  rotation?: number;
  mirror?: boolean;
  pins?: Pin[];
  footprint?: string;
  category?: string;
  symbolName?: string;
  symbol_library?: string;
}

interface SchematicSymbolProps {
  component: SchematicComponent;
  selected?: boolean;
  onClick?: () => void;
  onDragEnd?: (e: Konva.KonvaEventObject<DragEvent>) => void;
  draggable?: boolean;
}

// 比例因子 - 保留用于未来缩放功能
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const SCALE = 1;

/**
 * 根据元件信息确定符号类型
 * 修复：添加reference参数来识别元件类型
 */
function getSymbolType(component: SchematicComponent): string {
  const name = (component.name || '').toLowerCase();
  const model = (component.model || '').toLowerCase();
  const reference = (component.reference || '').toLowerCase();
  const category = (component.category || '').toLowerCase();
  const symbolName = (component.symbolName || '').toLowerCase();
  const symbolLibrary = (component.symbol_library || '').toLowerCase();

  // 修复：优先使用reference判断元件类型（R=电阻, C=电容, U=IC, D=二极管等）
  if (reference) {
    // 电阻：R开头（R1, R2, R5等）
    if (/^r\d*/.test(reference)) return 'resistor';
    // 电容：C开头
    if (/^c\d*/.test(reference)) return 'capacitor';
    // 电感：L开头
    if (/^l\d*/.test(reference)) return 'inductor';
    // 二极管：D开头
    if (/^d\d*/.test(reference)) return 'diode';
    // LED：LED开头或包含led
    if (reference.startsWith('led')) return 'led';
    // IC/芯片：U或IC开头
    if (/^u\d*/.test(reference) || reference.startsWith('ic')) return 'ic';
    // 连接器：J或CON开头
    if (/^j\d*/.test(reference) || reference.startsWith('con')) return 'connector';
    // 晶振：Y或X开头
    if (/^[yx]\d*/.test(reference)) return 'crystal';
    // 电源：VCC, VDD, 3V3等
    if (reference.startsWith('vcc') || reference.startsWith('vdd') || reference.includes('3v3')) return 'power_vcc';
    // 地：GND
    if (reference.startsWith('gnd')) return 'power_gnd';
  }
  
  // 优先使用 symbol_library
  if (symbolLibrary) {
    if (symbolLibrary.includes(':r') && !symbolLibrary.includes(':r_')) return 'resistor';
    if (symbolLibrary.includes(':c') && !symbolLibrary.includes(':c_')) return 'capacitor';
    if (symbolLibrary.includes(':l') && !symbolLibrary.includes(':l_')) return 'inductor';
    if (symbolLibrary.includes(':led')) return 'led';
    if (symbolLibrary.includes(':d') && !symbolLibrary.includes(':d_')) return 'diode';
    if (symbolLibrary.includes(':crystal')) return 'crystal';
    if (symbolLibrary.includes(':conn')) return 'connector';
    if (symbolLibrary.includes(':vcc') || symbolLibrary.includes(':power')) return 'power_vcc';
    if (symbolLibrary.includes(':gnd')) return 'power_gnd';
  }
  
  // 优先使用 symbolName
  if (symbolName) {
    if (symbolName.includes('resistor') || symbolName === 'r') return 'resistor';
    if (symbolName.includes('capacitor') || symbolName === 'c') return 'capacitor';
    if (symbolName.includes('inductor') || symbolName === 'l') return 'inductor';
    if (symbolName.includes('diode') || symbolName === 'd') return 'diode';
    if (symbolName.includes('led')) return 'led';
    if (symbolName.includes('transistor') || symbolName.includes('mosfet')) return 'transistor';
    if (symbolName.includes('crystal') || symbolName === 'y') return 'crystal';
    if (symbolName.includes('connector') || symbolName === 'j') return 'connector';
    if (symbolName.includes('switch') || symbolName.includes('button')) return 'switch';
    if (symbolName.includes('power') || symbolName.includes('gnd')) return 'power';
  }
  
  // 根据名称判断
  if (name.includes('电阻') || name.includes('resistor') || name.includes('res')) return 'resistor';
  if (name.includes('电容') || name.includes('capacitor') || name.includes('cap')) return 'capacitor';
  if (name.includes('电感') || name.includes('inductor') || name.includes('ind')) return 'inductor';
  if (name.includes('二极管') || name.includes('diode')) return 'diode';
  if (name.includes('led') || name.includes('发光') || name.includes('灯')) return 'led';
  if (name.includes('三极管') || name.includes('mos') || name.includes('transistor')) return 'transistor';
  if (name.includes('晶振') || name.includes('crystal')) return 'crystal';
  if (name.includes('连接器') || name.includes('接口') || name.includes('usb') || name.includes('connector')) return 'connector';
  if (name.includes('开关') || name.includes('按键') || name.includes('button')) return 'switch';
  if (name.includes('vcc') || name.includes('电源')) return 'power_vcc';
  if (name.includes('gnd') || name.includes('地')) return 'power_gnd';
  
  // 根据型号判断
  if (model.includes('r') && /\d+/.test(model)) return 'resistor';
  if (model.includes('c') && /\d+/.test(model)) return 'capacitor';
  if (model.includes('led')) return 'led';
  if (model.includes('1n') || model.includes('ss') || model.includes('bat')) return 'diode';
  
  // 根据类别判断
  if (category.includes('passive')) return 'passive';
  if (category.includes('led')) return 'led';
  if (category.includes('mcu') || category.includes('ic')) return 'ic';
  if (category.includes('power')) return 'power_ic';
  if (category.includes('interface')) return 'ic';
  if (category.includes('connector')) return 'connector';
  
  // 默认为IC
  return 'ic';
}

/**
 * 渲染电阻符号 - KiCad标准 (矩形，垂直放置)
 * 修复：统一尺寸，与KiCad符号协调
 */
const ResistorSymbol: React.FC<{ selected: boolean }> = ({ selected }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1.5;
  // 修复：缩小尺寸，与电容一致
  const rectWidth = 20;   // 宽度
  const rectHeight = 14;  // 高度，与电容的lineGap(12)接近
  const leadLength = 10;  // 引线长度

  return (
    <>
      {/* 电阻本体 - 矩形 */}
      <Rect
        x={-rectWidth/2}
        y={-rectHeight/2}
        width={rectWidth}
        height={rectHeight}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />

      {/* 引线 - 上方 */}
      <Line points={[0, -rectHeight/2, 0, -rectHeight/2 - leadLength]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 引线 - 下方 */}
      <Line points={[0, rectHeight/2, 0, rectHeight/2 + leadLength]} stroke={strokeColor} strokeWidth={strokeWidth} />
    </>
  );
};

/**
 * 渲染电容符号 - KiCad标准 (垂直两条平行线)
 * 统一尺寸：与电阻、二极管保持一致
 */
const CapacitorSymbol: React.FC<{ selected: boolean; polarized?: boolean }> = ({ selected, polarized }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1.5;
  // 统一尺寸：与电阻、二极管一致
  const lineWidth = 24;      // 极板宽度
  const lineGap = 12;        // 极板间距
  const pinLength = 12;      // 引线长度

  return (
    <>
      {/* 电容极板 - 上方水平线 */}
      <Line
        points={[-lineWidth/2, -lineGap/2, lineWidth/2, -lineGap/2]}
        stroke={strokeColor}
        strokeWidth={polarized ? strokeWidth * 1.5 : strokeWidth}
      />
      {/* 电容极板 - 下方水平线 */}
      <Line
        points={[-lineWidth/2, lineGap/2, lineWidth/2, lineGap/2]}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />

      {/* 引线 - 上方 */}
      <Line points={[0, -lineGap/2, 0, -lineGap/2 - pinLength]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 引线 - 下方 */}
      <Line points={[0, lineGap/2, 0, lineGap/2 + pinLength]} stroke={strokeColor} strokeWidth={strokeWidth} />

      {/* 极性标记 (电解电容) */}
      {polarized && (
        <Text text="+" x={-lineWidth/2 - 12} y={-lineGap/2 - 6} fontSize={10} fill={strokeColor} fontWeight="bold" />
      )}

      {/* 引脚端点 */}
      <Circle x={0} y={-lineGap/2 - pinLength} radius={3} fill="#ffcc00" />
      <Circle x={0} y={lineGap/2 + pinLength} radius={3} fill="#ffcc00" />
    </>
  );
};

/**
 * 渲染LED符号 (二极管+箭头)
 */
const LEDSymbol: React.FC<{ selected: boolean; color?: string }> = ({ selected, color = '#ff0000' }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1.5;
  
  // 根据颜色选择填充色
  const fillColor = color.toLowerCase().includes('green') ? '#00ff00' :
                    color.toLowerCase().includes('blue') ? '#0088ff' :
                    color.toLowerCase().includes('yellow') ? '#ffff00' :
                    '#ff0000'; // 默认红色
  
  return (
    <>
      {/* 二极管三角形 */}
      <Shape
        sceneFunc={(context, shape) => {
          context.beginPath();
          context.moveTo(-15, -12);
          context.lineTo(-15, 12);
          context.lineTo(5, 0);
          context.closePath();
          context.fillStrokeShape(shape);
        }}
        fill={selected ? fillColor : 'transparent'}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />
      {/* 阴极线 */}
      <Line points={[5, -12, 5, 12]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 左引线 (阳极) */}
      <Line points={[-30, 0, -15, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 右引线 (阴极) */}
      <Line points={[5, 0, 30, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 发光箭头 */}
      <Line points={[0, -15, 12, -25]} stroke={fillColor} strokeWidth={1.5} />
      <Shape
        sceneFunc={(context, shape) => {
          context.beginPath();
          context.moveTo(8, -22);
          context.lineTo(12, -25);
          context.lineTo(15, -20);
          context.closePath();
          context.fillStrokeShape(shape);
        }}
        fill={fillColor}
        stroke={fillColor}
      />
      <Line points={[8, -8, 20, -18]} stroke={fillColor} strokeWidth={1.5} />
      <Shape
        sceneFunc={(context, shape) => {
          context.beginPath();
          context.moveTo(16, -15);
          context.lineTo(20, -18);
          context.lineTo(23, -13);
          context.closePath();
          context.fillStrokeShape(shape);
        }}
        fill={fillColor}
        stroke={fillColor}
      />
      
      {/* 引脚 */}
      <Circle x={-30} y={0} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
      <Circle x={30} y={0} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
    </>
  );
};

/**
 * 渲染二极管符号
 */
const DiodeSymbol: React.FC<{ selected: boolean }> = ({ selected }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1.5;

  return (
    <>
      {/* 二极管三角形 - 统一尺寸 */}
      <Shape
        sceneFunc={(context, shape) => {
          context.beginPath();
          context.moveTo(-12, -12);
          context.lineTo(-12, 12);
          context.lineTo(12, 0);
          context.closePath();
          context.fillStrokeShape(shape);
        }}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />
      {/* 阴极线 */}
      <Line points={[12, -12, 12, 12]} stroke={strokeColor} strokeWidth={strokeWidth} />

      {/* 左引线 (阳极) */}
      <Line points={[-24, 0, -12, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 右引线 (阴极) */}
      <Line points={[12, 0, 24, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
    </>
  );
};

/**
 * 渲染IC/芯片符号 (矩形框+引脚)
 * 修复：使用更粗的线宽和明显的填充色
 */
const ICSymbol: React.FC<{
  selected: boolean;
  pins?: Pin[];
  componentName?: string;
}> = ({ selected, pins = [], componentName }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  // 修复：使用透明背景，与其他符号保持一致
  const fillColor = selected ? '#1a4a7a' : 'transparent';
  const strokeWidth = selected ? 3 : 2;
  
  // 根据引脚数量确定尺寸 - 修复：统一尺寸，与其他符号保持一致
  const pinCount = pins.length || 8;
  const leftPins = pins.filter(p => p.position?.x && p.position.x < 0).length || Math.ceil(pinCount / 2);
  const rightPins = pins.filter(p => p.position?.x && p.position.x > 0).length || Math.floor(pinCount / 2);

  // 修复：基础尺寸缩小，与电阻/二极管(24x24)保持一致
  const baseWidth = 36;
  const baseHeight = 30;
  const width = baseWidth;
  const height = Math.max(baseHeight, Math.max(leftPins, rightPins) * 12 + 16);
  
  // 缺口标记 (IC方向)
  const notchRadius = 6;
  
  return (
    <>
      {/* IC主体 */}
      <Rect
        x={-width/2}
        y={-height/2}
        width={width}
        height={height}
        fill={fillColor}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        cornerRadius={3}
      />
      
      {/* 缺口 (Pin 1 标记) */}
      <Circle
        x={-width/2 + 15}
        y={-height/2}
        radius={notchRadius}
        fill="#1a1a1a"
        stroke={strokeColor}
        strokeWidth={1}
      />
      
      {/* Pin 1 标记点 */}
      <Circle
        x={-width/2 + 15}
        y={-height/2 + 15}
        radius={3}
        fill="#ffcc00"
      />
      
      {/* 引脚 - 如果有传入引脚数据则使用 */}
      {pins.length > 0 ? pins.map((pin, i) => {
        const px = pin.position?.x || 0;
        const py = pin.position?.y || 0;
        const isLeft = px < 0;
        
        return (
          <Group key={pin.id || i}>
            {/* 引脚线 */}
            <Line
              points={[px, py, isLeft ? -width/2 : width/2, py]}
              stroke={strokeColor}
              strokeWidth={1}
            />
            {/* 引脚圆点 */}
            <Circle
              x={px}
              y={py}
              radius={3}
              fill="#ffcc00"
              stroke={strokeColor}
              strokeWidth={1}
            />
            {/* 引脚编号 */}
            <Text
              text={pin.number}
              x={isLeft ? px - 15 : px + 5}
              y={py - 5}
              fontSize={8}
              fill="#aaaaaa"
            />
            {/* 引脚名称 */}
            <Text
              text={pin.name}
              x={isLeft ? -width/2 + 5 : width/2 - 35}
              y={py - 5}
              fontSize={7}
              fill="#888888"
            />
          </Group>
        );
      }) : (
        <>
          {/* 默认引脚布局 */}
          {/* 左侧引脚 */}
          {[...Array(leftPins)].map((_, i) => {
            const py = -height/2 + 15 + i * 15;
            return (
              <Group key={`left-${i}`}>
                <Line points={[-50, py, -width/2, py]} stroke={strokeColor} strokeWidth={1} />
                <Circle x={-50} y={py} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
                <Text text={`${i + 1}`} x={-55} y={py - 5} fontSize={8} fill="#aaaaaa" />
              </Group>
            );
          })}
          {/* 右侧引脚 */}
          {[...Array(rightPins)].map((_, i) => {
            const py = -height/2 + 15 + i * 15;
            return (
              <Group key={`right-${i}`}>
                <Line points={[width/2, py, 50, py]} stroke={strokeColor} strokeWidth={1} />
                <Circle x={50} y={py} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
                <Text text={`${leftPins + i + 1}`} x={52} y={py - 5} fontSize={8} fill="#aaaaaa" />
              </Group>
            );
          })}
        </>
      )}
    </>
  );
};

/**
 * 渲染晶振符号
 */
const CrystalSymbol: React.FC<{ selected: boolean }> = ({ selected }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1.5;

  return (
    <>
      {/* 左引线 */}
      <Line points={[-24, 0, -12, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 右引线 */}
      <Line points={[12, 0, 24, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />

      {/* 晶振外壳 - 统一透明背景 */}
      <Rect
        x={-12}
        y={-12}
        width={24}
        height={24}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />

      {/* 内部晶体 */}
      <Line points={[-6, -8, -6, 8]} stroke={strokeColor} strokeWidth={2} />
      <Line points={[6, -8, 6, 8]} stroke={strokeColor} strokeWidth={2} />
    </>
  );
};

/**
 * 渲染连接器符号
 * 修复：统一尺寸，与KiCad符号协调
 */
const ConnectorSymbol: React.FC<{ selected: boolean; pins?: number }> = ({ selected, pins = 2 }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1;
  const pinCount = Math.max(2, Math.min(pins, 4)); // 最多显示4个引脚
  // 修复：统一尺寸，与其他符号保持一致
  const pinSpacing = 12;
  const width = 24;  // 缩小宽度，与二极管一致
  const height = pinCount * pinSpacing + 10;

  return (
    <>
      {/* 连接器外壳 - 改为透明背景，与其他无源元件一致 */}
      <Rect
        x={-width/2}
        y={-height/2}
        width={width}
        height={height}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        cornerRadius={2}
      />

      {/* 引脚 - 简化，不使用黄色圆点 */}
      {[...Array(pinCount)].map((_, i) => {
        const py = -height/2 + 8 + i * pinSpacing;
        return (
          <Line key={i} points={[-width/2 - 12, py, -width/2, py]} stroke={strokeColor} strokeWidth={1} />
        );
      })}
    </>
  );
};

/**
 * 渲染VCC电源符号
 */
const VCCSymbol: React.FC<{ selected: boolean; voltage?: string }> = ({ selected, voltage = 'VCC' }) => {
  const strokeColor = selected ? '#ffffff' : '#ff6600';
  const strokeWidth = selected ? 2 : 1.5;
  
  return (
    <>
      {/* 上箭头 */}
      <Line points={[0, -20, -8, -8]} stroke={strokeColor} strokeWidth={strokeWidth} />
      <Line points={[0, -20, 8, -8]} stroke={strokeColor} strokeWidth={strokeWidth} />
      <Line points={[0, -20, 0, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 电压标签 */}
      <Text text={voltage} x={-15} y={-35} fontSize={12} fill={strokeColor} fontStyle="bold" />
      
      {/* 引脚 */}
      <Circle x={0} y={10} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
      <Line points={[0, 0, 0, 10]} stroke={strokeColor} strokeWidth={strokeWidth} />
    </>
  );
};

/**
 * 渲染GND电源符号
 */
const GNDSymbol: React.FC<{ selected: boolean }> = ({ selected }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 1.5;
  
  return (
    <>
      {/* 三条横线 (三角形地) */}
      <Line points={[-15, 0, 15, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      <Line points={[-10, 6, 10, 6]} stroke={strokeColor} strokeWidth={strokeWidth} />
      <Line points={[-5, 12, 5, 12]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 连接线 */}
      <Line points={[0, 0, 0, -15]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* GND标签 */}
      <Text text="GND" x={-12} y={-28} fontSize={10} fill={strokeColor} fontStyle="bold" />
      
      {/* 引脚 */}
      <Circle x={0} y={-15} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
    </>
  );
};

/**
 * 主组件 - 根据元件类型渲染对应符号
 *
 * 注意：传入的position是毫米坐标(mm)，需要乘以MM_TO_PX转换为像素坐标
 */
const SchematicSymbol: React.FC<SchematicSymbolProps> = ({
  component,
  selected = false,
  onClick,
  onDragEnd,
  draggable = true,
}) => {
  const symbolType = getSymbolType(component);

  // KiCad符号数据
  const [kicadSymbol, setKicadSymbol] = useState<SymbolGraphicsData | null>(null);
  // 修复：默认使用硬编码符号，避免异步加载导致闪烁
  const [useKiCadRenderer, setUseKiCadRenderer] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 尝试从KiCad库获取符号 - 修复：加载完成后才切换渲染器，避免空白
  useEffect(() => {
    let mounted = true;
    const loadKiCadSymbol = async () => {
      // 先显示硬编码符号，避免空白
      setUseKiCadRenderer(false);
      setIsLoading(true);

      // 优先使用symbol_library
      if (component.symbol_library) {
        const parts = component.symbol_library.split(':');
        if (parts.length === 2) {
          try {
            const data = await symbolApi.getSymbolGraphics(parts[0], parts[1]);
            if (mounted && data.success) {
              setKicadSymbol(data);
              setUseKiCadRenderer(true);
              setIsLoading(false);
              return;
            }
          } catch (err) {
            console.warn(`[SchematicSymbol] Failed to load KiCad symbol: ${component.symbol_library}`, err);
          }
        }
      }

      // 尝试根据名称查找符号
      try {
        const data = await symbolApi.findSymbol(component.name, component.model);
        if (mounted && data) {
          setKicadSymbol(data);
          setUseKiCadRenderer(true);
          setIsLoading(false);
          return;
        }
      } catch (err) {
        console.warn(`[SchematicSymbol] Failed to find symbol for: ${component.name}`, err);
      }

      // 回退到硬编码符号
      if (mounted) {
        setUseKiCadRenderer(false);
        setIsLoading(false);
      }
    };

    loadKiCadSymbol();
    return () => { mounted = false; };
  }, [component.symbol_library, component.name, component.model]);

  // 毫米到像素的转换因子（与SchematicEditor一致）
  const MM_TO_PX = 0.5;

  // 将毫米坐标转换为像素坐标
  const x = (component.position?.x || 0) * MM_TO_PX;
  const y = (component.position?.y || 0) * MM_TO_PX;
  const rotation = component.rotation || 0;
  const mirror = component.mirror || false;

  // 调试日志 - 打印关键信息
  const hasKiCadGraphics = kicadSymbol?.graphics?.length > 0;
  console.log(`[SchematicSymbol] Component ${component.id}: symbolType=${symbolType}, useKiCad=${useKiCadRenderer}, hasGraphics=${hasKiCadGraphics}, isLoading=${isLoading}, mmPos=(${component.position?.x}, ${component.position?.y}), pxPos=(${x}, ${y}), name=${component.name}`);
  if (kicadSymbol && !hasKiCadGraphics) {
    console.warn(`[SchematicSymbol] KiCad symbol ${kicadSymbol.library}:${kicadSymbol.name} has no graphics, falling back to hardcoded symbol`);
  }

  // 修复：只有在成功加载KiCad符号且graphics不为空后才使用KiCad渲染器，否则使用硬编码符号
  // 注意：KiCadSymbolRenderer使用MM_TO_PX=2，这里scale=5使得整体1mm=10px
  if (useKiCadRenderer && kicadSymbol && hasKiCadGraphics && !isLoading) {
    return (
      <Group
        x={x}
        y={y}
        rotation={rotation}
        draggable={draggable}
        onDragEnd={onDragEnd}
        onClick={onClick}
        onTap={onClick}
      >
        <KiCadSymbolRenderer
          library={kicadSymbol.library}
          name={kicadSymbol.name}
          x={0}
          y={0}
          rotation={0}
          mirror={mirror}
          scale={2}
          selected={selected}
          graphicsData={kicadSymbol}
        />
        {/* 标签 */}
        <Text
          text={component.reference || ''}
          x={-30}
          y={-50}
          fontSize={10}
          fill={selected ? '#ffffff' : '#cccccc'}
          fontStyle="bold"
        />
        <Text
          text={component.value || component.model || ''}
          x={-30}
          y={-35}
          fontSize={9}
          fill={selected ? '#cccccc' : '#888888'}
        />
      </Group>
    );
  }

  // 渲染符号（回退到硬编码）
  const renderSymbol = () => {
    switch (symbolType) {
      case 'resistor':
        return <ResistorSymbol selected={selected} />;
      case 'capacitor': {
        // 判断是否为电解电容
        const isPolarized = (component.model || '').toLowerCase().includes('uf') ||
                           (component.model || '').toLowerCase().includes('电解') ||
                           (component.name || '').includes('滤波');
        return <CapacitorSymbol selected={selected} polarized={isPolarized} />;
      }
      case 'led': {
        const color = component.model || component.name || 'red';
        return <LEDSymbol selected={selected} color={color} />;
      }
      case 'diode':
        return <DiodeSymbol selected={selected} />;
      case 'transistor':
        return <ICSymbol selected={selected} pins={component.pins} componentName={component.name} />;
      case 'crystal':
        return <CrystalSymbol selected={selected} />;
      case 'connector':
        return <ConnectorSymbol selected={selected} pins={component.pins?.length || 2} />;
      case 'power_vcc': {
        const voltage = component.value || component.model || 'VCC';
        return <VCCSymbol selected={selected} voltage={voltage} />;
      }
      case 'power_gnd':
        return <GNDSymbol selected={selected} />;
      case 'passive':
        // 默认无源元件显示为简单矩形
        return (
          <Rect
            x={-30}
            y={-20}
            width={60}
            height={40}
            fill="transparent"
            stroke={selected ? '#ffffff' : '#00ff00'}
            strokeWidth={2}
          />
        );
      case 'ic':
      case 'power_ic':
      case 'mcu':
      case 'interface':
      case 'active':
      default:
        return <ICSymbol selected={selected} pins={component.pins} componentName={component.name} />;
    }
  };
  
  // 根据符号类型确定标签位置
  const getLabelPosition = () => {
    switch (symbolType) {
      case 'resistor':
      case 'capacitor':
      case 'diode':
      case 'led':
        return { refY: -25, valueY: 15 };
      case 'crystal':
        return { refY: -25, valueY: 20 };
      default:
        return { refY: -50, valueY: 40 };
    }
  };
  
  const labelPos = getLabelPosition();
  
  return (
    <Group
      x={x}
      y={y}
      rotation={rotation}
      onClick={onClick}
      onTap={onClick}
      draggable={draggable}
      onDragEnd={onDragEnd}
      visible={true}
    >
      {/* 移除调试背景框，保持简洁 */}
      {/* 符号本体 */}
      {renderSymbol()}

      {/* 位号 (Reference) */}
      <Text
        text={component.reference || 'REF?'}
        x={-30}
        y={labelPos.refY}
        fontSize={11}
        fill={selected ? '#ffffff' : '#00aaff'}
        fontStyle="bold"
        background="#1a1a1a"
      />

      {/* 值/型号 */}
      <Text
        text={component.value || component.model || 'VALUE?'}
        x={-30}
        y={labelPos.valueY}
        fontSize={9}
        fill={selected ? '#cccccc' : '#888888'}
        background="#1a1a1a"
      />

      {/* 封装信息 */}
      {component.footprint && (
        <Text
          text={component.footprint}
          x={-30}
          y={labelPos.valueY + 12}
          fontSize={9}
          fill="#888888"
          fontStyle="italic"
        />
      )}

      {/* 符号库信息 */}
      {component.symbol_library && (
        <Text
          text={component.symbol_library}
          x={-30}
          y={labelPos.valueY + 22}
          fontSize={6}
          fill="#555555"
        />
      )}
    </Group>
  );
};

export default SchematicSymbol;

// 导出类型
export type { SchematicComponent, Pin };
export { getSymbolType };
