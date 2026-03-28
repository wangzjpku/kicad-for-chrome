/**
 * 网表服务
 * 生成网表、执行ERC检查
 */

import { SchematicData, SchematicComponent, Wire, Net } from '../types';

export interface ERCError {
  id: string;
  type: 'error' | 'warning';
  category: 'unconnected_pin' | 'no_power' | 'no_ground' | 'short_circuit' | 'floating_net';
  message: string;
  elementId?: string;
  pinNumber?: string;
  position?: { x: number; y: number };
}

export interface NetlistResult {
  success: boolean;
  nets: Net[];
  errors: ERCError[];
  warnings: ERCError[];
  componentCount: number;
  pinCount: number;
  connectedPinCount: number;
  unconnectedPinCount: number;
}

/**
 * 生成网表并执行ERC检查
 */
export function generateNetlist(schematicData: SchematicData | null): NetlistResult {
  if (!schematicData) {
    return {
      success: false,
      nets: [],
      errors: [],
      warnings: [],
      componentCount: 0,
      pinCount: 0,
      connectedPinCount: 0,
      unconnectedPinCount: 0,
    };
  }

  const errors: ERCError[] = [];
  const warnings: ERCError[] = [];
  const nets: Map<string, Net> = new Map();

  // 跟踪已连接的引脚
  const connectedPins: Set<string> = new Set();

  // 1. 处理现有网络
  schematicData.nets?.forEach(net => {
    nets.set(net.id, net);
  });

  // 2. 分析连线，识别网络
  const wireConnections = analyzeWireConnections(schematicData.wires);

  // 3. 为每个连线组创建或合并网络
  wireConnections.forEach((wireGroup, index) => {
    const netId = `net-wire-${index}`;
    const netName = `Net-(Wire${index})`;

    nets.set(netId, {
      id: netId,
      name: netName,
    });
  });

  // 4. 检查每个元件的引脚连接状态
  let totalPinCount = 0;
  let connectedPinCount = 0;

  schematicData.components.forEach(component => {
    component.pins?.forEach(pin => {
      totalPinCount++;

      // 检查引脚是否连接到网络
      const pinKey = `${component.id}-${pin.number}`;
      const isConnected = checkPinConnection(
        component,
        pin,
        schematicData.wires,
        wireConnections
      );

      if (isConnected) {
        connectedPins.add(pinKey);
        connectedPinCount++;
      } else {
        // 未连接引脚警告
        // 电源引脚更严格
        if (pin.electricalType === 'power') {
          if (pin.name.toLowerCase().includes('vcc') ||
              pin.name.toLowerCase().includes('vdd')) {
            errors.push({
              id: `erc-${component.id}-pin-${pin.number}`,
              type: 'error',
              category: 'no_power',
              message: `电源引脚 ${pin.name} (引脚${pin.number}) 未连接到电源网络`,
              elementId: component.id,
              pinNumber: pin.number,
              position: {
                x: component.position.x + (pin.position?.x || 0),
                y: component.position.y + (pin.position?.y || 0),
              },
            });
          } else if (pin.name.toLowerCase().includes('gnd') ||
                     pin.name.toLowerCase().includes('vss')) {
            errors.push({
              id: `erc-${component.id}-pin-${pin.number}`,
              type: 'error',
              category: 'no_ground',
              message: `地引脚 ${pin.name} (引脚${pin.number}) 未连接到地网络`,
              elementId: component.id,
              pinNumber: pin.number,
              position: {
                x: component.position.x + (pin.position?.x || 0),
                y: component.position.y + (pin.position?.y || 0),
              },
            });
          }
        } else {
          // 普通未连接引脚警告
          warnings.push({
            id: `erc-${component.id}-pin-${pin.number}`,
            type: 'warning',
            category: 'unconnected_pin',
            message: `${component.reference || component.symbolName} 引脚 ${pin.name} (引脚${pin.number}) 未连接`,
            elementId: component.id,
            pinNumber: pin.number,
            position: {
              x: component.position.x + (pin.position?.x || 0),
              y: component.position.y + (pin.position?.y || 0),
            },
          });
        }
      }
    });
  });

  // 5. 检查是否有电源网络
  const hasPowerNet = Array.from(nets.values()).some(
    net => net.name.toLowerCase().includes('vcc') ||
           net.name.toLowerCase().includes('vdd') ||
           net.name.toLowerCase().includes('+')
  );

  if (!hasPowerNet) {
    warnings.push({
      id: 'erc-no-power',
      type: 'warning',
      category: 'no_power',
      message: '原理图中未检测到电源网络，请添加VCC或电源符号',
    });
  }

  // 6. 检查是否有地网络
  const hasGroundNet = Array.from(nets.values()).some(
    net => net.name.toLowerCase().includes('gnd') ||
           net.name.toLowerCase().includes('vss') ||
           net.name.toLowerCase().includes('ground')
  );

  if (!hasGroundNet) {
    warnings.push({
      id: 'erc-no-ground',
      type: 'warning',
      category: 'no_ground',
      message: '原理图中未检测到地网络，请添加GND或地符号',
    });
  }

  // 7. 检查悬空网络（没有连接到任何引脚的网络）
  wireConnections.forEach((wireGroup, index) => {
    const netId = `net-wire-${index}`;
    const hasConnection = checkNetHasConnection(wireGroup, schematicData.components);

    if (!hasConnection) {
      warnings.push({
        id: `erc-floating-net-${index}`,
        type: 'warning',
        category: 'floating_net',
        message: `检测到悬空网络 (连线组 ${index + 1})，未连接到任何引脚`,
        position: wireGroup[0]?.points[0],
      });
    }
  });

  return {
    success: errors.length === 0,
    nets: Array.from(nets.values()),
    errors,
    warnings,
    componentCount: schematicData.components.length,
    pinCount: totalPinCount,
    connectedPinCount,
    unconnectedPinCount: totalPinCount - connectedPinCount,
  };
}

/**
 * 分析连线连接关系
 * 返回连通的连线组
 */
function analyzeWireConnections(wires: Wire[]): Wire[][] {
  const groups: Wire[][] = [];
  const visited: Set<string> = new Set();

  wires.forEach(wire => {
    if (visited.has(wire.id)) return;

    const group: Wire[] = [];
    const queue: Wire[] = [wire];
    visited.add(wire.id);

    while (queue.length > 0) {
      const current = queue.shift()!;
      group.push(current);

      // 查找与当前连线相连的其它连线
      wires.forEach(other => {
        if (visited.has(other.id)) return;
        if (areWiresConnected(current, other)) {
          visited.add(other.id);
          queue.push(other);
        }
      });
    }

    groups.push(group);
  });

  return groups;
}

/**
 * 检查两条连线是否相连
 */
function areWiresConnected(wire1: Wire, wire2: Wire): boolean {
  // 获取所有端点
  const points1 = wire1.points;
  const points2 = wire2.points;

  // 检查是否有端点重合（在一定容差范围内）
  const tolerance = 0.5; // 0.5mm 容差

  for (const p1 of points1) {
    for (const p2 of points2) {
      const distance = Math.sqrt(
        Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2)
      );
      if (distance <= tolerance) {
        return true;
      }
    }
  }

  return false;
}

/**
 * 检查引脚是否连接到连线
 */
function checkPinConnection(
  component: SchematicComponent,
  pin: { number: string; position?: { x: number; y: number } },
  wires: Wire[],
  wireConnections: Wire[][]
): boolean {
  if (!pin.position) return false;

  // 计算引脚在原理图中的绝对位置
  const pinX = component.position.x + pin.position.x;
  const pinY = component.position.y + pin.position.y;

  // 检查引脚是否在任一网络上
  for (const wire of wires) {
    for (const point of wire.points) {
      const distance = Math.sqrt(
        Math.pow(pinX - point.x, 2) + Math.pow(pinY - point.y, 2)
      );
      if (distance <= 0.5) { // 0.5mm 容差
        return true;
      }
    }
  }

  return false;
}

/**
 * 检查网络是否有连接到引脚
 */
function checkNetHasConnection(
  wireGroup: Wire[],
  components: SchematicComponent[]
): boolean {
  for (const wire of wireGroup) {
    for (const point of wire.points) {
      for (const component of components) {
        for (const pin of component.pins || []) {
          if (!pin.position) continue;

          const pinX = component.position.x + pin.position.x;
          const pinY = component.position.y + pin.position.y;

          const distance = Math.sqrt(
            Math.pow(pinX - point.x, 2) + Math.pow(pinY - point.y, 2)
          );

          if (distance <= 0.5) {
            return true;
          }
        }
      }
    }
  }

  return false;
}

/**
 * 导出网表为KiCad格式
 */
export function exportNetlistKiCad(nets: Net[]): string {
  let output = '(\n'; // Netlist in KiCad format

  nets.forEach(net => {
    output += `  (net (code "${net.id}") (name "${net.name}")\n`;
    // 添加网络节点信息
    output += '  )\n';
  });

  output += ')\n';
  return output;
}
