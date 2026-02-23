/**
 * 原理图元件符号渲染器
 * 根据元件类型渲染真实的电路符号，而不是简单的矩形框
 */

import React from 'react';
import { Group, Rect, Line, Text, Circle, Shape } from 'react-konva';
import Konva from 'konva';

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
  reference?: string;
  value?: string;
  position: { x: number; y: number };
  rotation?: number;
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

// 比例因子
const SCALE = 1;

/**
 * 根据元件信息确定符号类型
 */
function getSymbolType(component: SchematicComponent): string {
  const name = (component.name || '').toLowerCase();
  const model = (component.model || '').toLowerCase();
  const category = (component.category || '').toLowerCase();
  const symbolName = (component.symbolName || '').toLowerCase();
  const symbolLibrary = (component.symbol_library || '').toLowerCase();
  
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
 * 符号定义: rectangle from (-1.016, -2.54) to (1.016, 2.54)
 * 引脚: Pin1在上方(0, 3.81), Pin2在下方(0, -3.81)
 */
const ResistorSymbol: React.FC<{ selected: boolean }> = ({ selected }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 0.254;
  const scale = 20; // 缩放因子
  
  // KiCad标准电阻是矩形，垂直放置
  // 矩形尺寸: 宽2.032, 高5.08 (单位mm)
  const rectWidth = 1.016 * 2 * scale;  // 约40px
  const rectHeight = 2.54 * 2 * scale;  // 约100px
  
  return (
    <>
      {/* 引线 - 上方 */}
      <Line points={[0, -rectHeight/2, 0, -rectHeight/2 - 30]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 引线 - 下方 */}
      <Line points={[0, rectHeight/2, 0, rectHeight/2 + 30]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 电阻本体 - 矩形 (KiCad标准) */}
      <Rect
        x={-rectWidth/2}
        y={-rectHeight/2}
        width={rectWidth}
        height={rectHeight}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />
      
      {/* 引脚 - 上方 Pin1 */}
      <Circle x={0} y={-rectHeight/2 - 30} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
      {/* 引脚 - 下方 Pin2 */}
      <Circle x={0} y={rectHeight/2 + 30} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
    </>
  );
};

/**
 * 渲染电容符号 - KiCad标准 (垂直两条平行线)
 * 符号定义: 两条水平线，垂直放置
 * 线1: (-2.032, 0.762) 到 (2.032, 0.762), stroke width 0.508
 * 线2: (-2.032, -0.762) 到 (2.032, -0.762), stroke width 0.508
 * 引脚: Pin1在上方(0, 3.81), Pin2在下方(0, -3.81)
 */
const CapacitorSymbol: React.FC<{ selected: boolean; polarized?: boolean }> = ({ selected, polarized }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const strokeWidth = selected ? 2 : 0.508;
  const scale = 15; // 缩放因子
  
  // KiCad标准电容是两条水平平行线，垂直放置
  const lineWidth = 2.032 * 2 * scale;  // 约60px
  const lineGap = 0.762 * 2 * scale;    // 约23px
  const pinLength = 2.794 * scale;      // 引线长度
  
  return (
    <>
      {/* 引线 - 上方 */}
      <Line points={[0, -lineGap/2, 0, -lineGap/2 - pinLength]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 引线 - 下方 */}
      <Line points={[0, lineGap/2, 0, lineGap/2 + pinLength]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 极性标记 (电解电容) - 上方极板加粗 */}
      {polarized && (
        <>
          <Text text="+" x={-lineWidth/2 - 15} y={-lineGap/2 - 5} fontSize={12} fill={strokeColor} fontWeight="bold" />
        </>
      )}
      
      {/* 电容极板 - 上方水平线 */}
      <Line 
        points={[-lineWidth/2, -lineGap/2, lineWidth/2, -lineGap/2]} 
        stroke={strokeColor} 
        strokeWidth={polarized ? strokeWidth * 2 : strokeWidth} 
      />
      {/* 电容极板 - 下方水平线 */}
      <Line 
        points={[-lineWidth/2, lineGap/2, lineWidth/2, lineGap/2]} 
        stroke={strokeColor} 
        strokeWidth={strokeWidth} 
      />
      
      {/* 引脚 - 上方 Pin1 */}
      <Circle x={0} y={-lineGap/2 - pinLength} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
      {/* 引脚 - 下方 Pin2 */}
      <Circle x={0} y={lineGap/2 + pinLength} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
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
        fill={selected ? '#00ff00' : 'transparent'}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />
      {/* 阴极线 */}
      <Line points={[5, -12, 5, 12]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 左引线 (阳极) */}
      <Line points={[-30, 0, -15, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 右引线 (阴极) */}
      <Line points={[5, 0, 30, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 引脚 */}
      <Circle x={-30} y={0} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
      <Circle x={30} y={0} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
    </>
  );
};

/**
 * 渲染IC/芯片符号 (矩形框+引脚)
 */
const ICSymbol: React.FC<{ 
  selected: boolean; 
  pins?: Pin[];
  componentName?: string;
}> = ({ selected, pins = [], componentName }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const fillColor = selected ? '#1a4a7a' : '#1a2a3a';
  const strokeWidth = selected ? 2 : 1;
  
  // 根据引脚数量确定尺寸
  const pinCount = pins.length || 8;
  const leftPins = pins.filter(p => p.position?.x && p.position.x < 0).length || Math.ceil(pinCount / 2);
  const rightPins = pins.filter(p => p.position?.x && p.position.x > 0).length || Math.floor(pinCount / 2);
  
  const width = 80;
  const height = Math.max(60, Math.max(leftPins, rightPins) * 15 + 20);
  
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
      <Line points={[-30, 0, -10, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* 右引线 */}
      <Line points={[10, 0, 30, 0]} stroke={strokeColor} strokeWidth={strokeWidth} />
      
      {/* 晶振外壳 */}
      <Rect
        x={-10}
        y={-15}
        width={20}
        height={30}
        fill={selected ? '#1a4a7a' : 'transparent'}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />
      
      {/* 内部晶体 */}
      <Line points={[-5, -10, -5, 10]} stroke={strokeColor} strokeWidth={2} />
      <Line points={[5, -10, 5, 10]} stroke={strokeColor} strokeWidth={2} />
      
      {/* 引脚 */}
      <Circle x={-30} y={0} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
      <Circle x={30} y={0} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
    </>
  );
};

/**
 * 渲染连接器符号
 */
const ConnectorSymbol: React.FC<{ selected: boolean; pins?: number }> = ({ selected, pins = 2 }) => {
  const strokeColor = selected ? '#ffffff' : '#00ff00';
  const fillColor = selected ? '#1a4a7a' : '#1a2a3a';
  const strokeWidth = selected ? 2 : 1;
  const pinCount = Math.max(2, Math.min(pins, 10));
  const height = pinCount * 12 + 10;
  
  return (
    <>
      {/* 连接器外壳 */}
      <Rect
        x={-20}
        y={-height/2}
        width={40}
        height={height}
        fill={fillColor}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        cornerRadius={2}
      />
      
      {/* 引脚 */}
      {[...Array(pinCount)].map((_, i) => {
        const py = -height/2 + 10 + i * 12;
        return (
          <Group key={i}>
            <Line points={[-30, py, -20, py]} stroke={strokeColor} strokeWidth={1} />
            <Circle x={-30} y={py} radius={3} fill="#ffcc00" stroke={strokeColor} strokeWidth={1} />
            <Text text={`${i + 1}`} x={-15} y={py - 4} fontSize={8} fill="#aaaaaa" />
          </Group>
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
 */
const SchematicSymbol: React.FC<SchematicSymbolProps> = ({
  component,
  selected = false,
  onClick,
  onDragEnd,
  draggable = true,
}) => {
  const symbolType = getSymbolType(component);
  const x = component.position?.x || 0;
  const y = component.position?.y || 0;
  const rotation = component.rotation || 0;
  
  // 渲染符号
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
    >
      {/* 符号本体 */}
      {renderSymbol()}
      
      {/* 位号 (Reference) */}
      <Text
        text={component.reference || ''}
        x={-30}
        y={labelPos.refY}
        fontSize={11}
        fill={selected ? '#ffffff' : '#00aaff'}
        fontStyle="bold"
      />
      
      {/* 值/型号 */}
      <Text
        text={component.value || component.model || ''}
        x={-30}
        y={labelPos.valueY}
        fontSize={9}
        fill={selected ? '#cccccc' : '#888888'}
      />
      
      {/* 封装信息 */}
      {component.footprint && (
        <Text
          text={component.footprint}
          x={-30}
          y={labelPos.valueY + 12}
          fontSize={7}
          fill="#666666"
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
