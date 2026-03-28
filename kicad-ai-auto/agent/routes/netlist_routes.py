"""
网表管理API路由

提供网表的导入、导出和验证功能
"""

import os
import re
import uuid
import json
import subprocess
import tempfile

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# KiCad 原理图生成配置
KICAD_SYMBOL_DIR = os.environ.get("KICAD_SYMBOL_DIR")
_kicad_sch_api = None

router = APIRouter(prefix="/api/v1/netlist", tags=["Netlist"])


def _get_kicad_cli_path() -> str:
    """获取 KiCad CLI 路径（优先使用 settings，fallback 到环境变量）"""
    from settings import get_settings
    settings = get_settings()
    return settings.kicad_cli_path or os.environ.get("KICAD_CLI_PATH") or ""


def _get_kicad_sch_api():
    """获取 kicad_sch_api 模块，设置符号库路径"""
    global _kicad_sch_api
    if _kicad_sch_api is None:
        os.environ['KICAD_SYMBOL_DIR'] = KICAD_SYMBOL_DIR
        import kicad_sch_api as ksa
        _kicad_sch_api = ksa
        
        # 初始化符号库缓存
        cache = ksa.get_symbol_cache()
        cache.discover_libraries([KICAD_SYMBOL_DIR])
        logger.info(f'KiCad 符号库已加载: {KICAD_SYMBOL_DIR}')
    
    return _kicad_sch_api


def _simplify_wire_points(points: list) -> list:
    """
    简化导线路径：移除重复点、相邻同方向点、共线点。
    只保留起点、拐点和终点。
    """
    if len(points) < 2:
        return points

    result = [points[0]]  # 保留起点

    for i in range(1, len(points) - 1):
        prev = points[i - 1]
        curr = points[i]
        next_p = points[i + 1]

        # 检查当前点是否是拐点（非共线）
        # 向量: prev→curr 和 curr→next
        dx1 = float(curr.get('x', 0)) - float(prev.get('x', 0))
        dy1 = float(curr.get('y', 0)) - float(prev.get('y', 0))
        dx2 = float(next_p.get('x', 0)) - float(curr.get('x', 0))
        dy2 = float(next_p.get('y', 0)) - float(curr.get('y', 0))

        # 跳过完全重复的点
        if abs(dx1) < 0.1 and abs(dy1) < 0.1 and abs(dx2) < 0.1 and abs(dy2) < 0.1:
            continue

        # 计算叉积判断是否共线（共线则叉积≈0）
        cross = dx1 * dy2 - dy1 * dx2
        # 如果叉积不为0，或方向改变，则当前点是拐点
        if abs(cross) > 0.1 or (dx1 != 0 and dx2 == 0) or (dy1 != 0 and dy2 == 0):
            result.append(curr)

    result.append(points[-1])  # 保留终点
    return result


def _infer_wire_connections(schematic_data: dict) -> dict:
    """
    从导线的points格式推断出引脚连接。
    优先使用 KiCad 符号库中的真实引脚位置（Solution A），
    fallback 到 AI 生成的引脚数据。

    返回: {
        'wire-1': {'from_conn': 'R2.1', 'to_conn': 'R4.1'},
        ...
    }
    """
    import math

    components = schematic_data.get('components', [])
    wires = schematic_data.get('wires', [])

    # 计算所有引脚位置
    all_pins = []

    # 尝试加载 KiCad 符号库（Solution A）
    symbol_parser = None
    try:
        from symbol_lib_parser import get_symbol_parser
        symbol_parser = get_symbol_parser()
    except Exception as e:
        logger.debug(f'SymbolLibParser 加载失败: {e}')

    for comp in components:
        ref = comp.get('reference')
        comp_pos = comp.get('position', {})

        # 尝试从 KiCad 符号库获取真实引脚位置（Solution A）
        lib_id = comp.get('symbol_library', '') or ''
        symbol_name = comp.get('symbol_name') or comp.get('symbol') or ''

        # 解析 lib_id，格式可能为 "Library:SymbolName" 或分开提供
        if ':' in lib_id:
            kb_lib, kb_sym = lib_id.split(':', 1)
            if not symbol_name:
                symbol_name = kb_sym
        else:
            kb_lib = lib_id

        # 应用 KB → KiCad 实际库名映射
        KB_TO_KICAD_LIB = {
            "MCU_ST_STM32": "MCU_ST_STM32F1",
            "MCU_ST": "MCU_ST_STM32F1",
            "MCU_Microchip_AVR": "MCU_Microchip_ATmega",
            "MCU_Espressif": "MCU_Espressif",
        }
        if kb_lib in KB_TO_KICAD_LIB:
            kb_lib = KB_TO_KICAD_LIB[kb_lib]

        real_pins = None
        if symbol_parser and kb_lib and symbol_name:
            # 尝试多个可能的符号名（KiCad IC 符号将引脚定义在 _1_1 变体中）
            candidates = [
                symbol_name,
                f"{symbol_name}_1_1",     # IC 多单元符号的单元1变体
                f"{symbol_name}_0_1",      # 电源单元
                symbol_name.replace("_1_1", ""),  # 去掉 _1_1 后缀
            ]
            for cand in candidates:
                symbol = symbol_parser.get_symbol(kb_lib, cand)
                if symbol and symbol.pins:
                    real_pins = {p.number: p.position for p in symbol.pins}
                    logger.debug(f'使用 KiCad 库获取引脚: {kb_lib}:{cand} ({len(real_pins)} 个引脚)')
                    break

        # 如果有真实引脚位置，使用符号库坐标 + 元件放置位置
        if real_pins:
            for pin_num, pin_pos in real_pins.items():
                abs_x = comp_pos.get('x', 0) + pin_pos['x']
                abs_y = comp_pos.get('y', 0) + pin_pos['y']
                all_pins.append({
                    'ref': ref,
                    'pin': str(pin_num),
                    'x': abs_x,
                    'y': abs_y,
                    'source': 'kicad_lib'
                })
        else:
            # Fallback：使用 AI 生成的引脚数据
            if not comp.get('pins'):
                logger.debug(f'无法获取引脚位置，跳过: {ref} ({kb_lib}:{symbol_name})')
                continue
            for pin in comp.get('pins', []):
                pin_pos = pin.get('position', {})
                abs_x = comp_pos.get('x', 0) + pin_pos.get('x', 0)
                abs_y = comp_pos.get('y', 0) + pin_pos.get('y', 0)
                all_pins.append({
                    'ref': ref,
                    'pin': str(pin.get('number', '')),
                    'x': abs_x,
                    'y': abs_y,
                    'source': 'ai'
                })

    # 对每条导线，找到最近的引脚
    inferred = {}
    # 阈值：KiCad 真实坐标误差小(50 internal units)，AI 坐标误差大(500)
    THRESHOLD_KICAD = 50   # ~0.05mm in KiCad internal units
    THRESHOLD_AI = 500     # ~0.5mm，AI 坐标可能有较大偏差

    for wire in wires:
        wire_id = wire.get('id', '')
        points = wire.get('points', [])
        if len(points) < 2:
            continue

        start = points[0]
        end = points[-1]

        # 找起点最近的引脚
        start_pin = None
        min_dist = float('inf')
        for pin in all_pins:
            dist = math.sqrt((start['x']-pin['x'])**2 + (start['y']-pin['y'])**2)
            if dist < min_dist:
                min_dist = dist
                start_pin = pin

        # 找终点最近的引脚
        end_pin = None
        min_dist = float('inf')
        for pin in all_pins:
            dist = math.sqrt((end['x']-pin['x'])**2 + (end['y']-pin['y'])**2)
            if dist < min_dist:
                min_dist = dist
                end_pin = pin

        # 使用对应阈值的判断
        start_threshold = THRESHOLD_KICAD if (start_pin and start_pin.get('source') == 'kicad_lib') else THRESHOLD_AI
        end_threshold = THRESHOLD_KICAD if (end_pin and end_pin.get('source') == 'kicad_lib') else THRESHOLD_AI

        if start_pin and min_dist < start_threshold:
            start_conn = f"{start_pin['ref']}.{start_pin['pin']}"
            logger.debug(f'导线 {wire_id} 起点匹配 {start_conn} (dist={min_dist:.1f}, src={start_pin.get("source")})')
        else:
            start_conn = None
            logger.debug(f'导线 {wire_id} 起点无匹配 (best={start_pin["ref"]}.{start_pin["pin"] if start_pin else "?"}, dist={min_dist:.1f})')

        if end_pin and min_dist < end_threshold:
            end_conn = f"{end_pin['ref']}.{end_pin['pin']}"
            logger.debug(f'导线 {wire_id} 终点匹配 {end_conn} (dist={min_dist:.1f}, src={end_pin.get("source")})')
        else:
            end_conn = None
            logger.debug(f'导线 {wire_id} 终点无匹配 (best={end_pin["ref"]}.{end_pin["pin"] if end_pin else "?"}, dist={min_dist:.1f})')

        if start_conn and end_conn:
            inferred[wire_id] = {
                'from_conn': start_conn,
                'to_conn': end_conn
            }

    return inferred


def _add_power_symbols(sch, schematic_data: dict, component_map: dict) -> int:
    """
    添加电源符号并连接到元件的电源引脚

    Args:
        sch: kicad_sch_api创建的原理图对象
        schematic_data: 原理图数据
        component_map: 元件映射 {reference: {lib_id, ...}}

    Returns:
        添加的电源符号数量
    """
    power_symbols = schematic_data.get('powerSymbols', [])
    if not power_symbols:
        # 如果没有电源符号但有VCC/GND网络，创建默认的电源符号
        nets = schematic_data.get('nets', [])
        has_vcc = any(n.get('name', '').upper() in ['VCC', '+5V', '+3V3', '+12V'] for n in nets)
        has_gnd = any(n.get('name', '').upper() == 'GND' for n in nets)

        if has_vcc or has_gnd:
            power_symbols = []
            if has_vcc:
                power_symbols.append({'id': 'vcc-default', 'netName': 'VCC', 'position': {'x': 50, 'y': 25}, 'type': 'vcc'})
            if has_gnd:
                power_symbols.append({'id': 'gnd-default', 'netName': 'GND', 'position': {'x': 50, 'y': 550}, 'type': 'gnd'})

    if not power_symbols:
        return 0

    power_refs = {}  # {net_name: power_symbol_reference}

    for i, ps in enumerate(power_symbols):
        net_name = ps.get('netName', '')
        ps_type = ps.get('type', 'vcc')
        pos = ps.get('position', {})
        x = float(pos.get('x', 100))
        y = float(pos.get('y', 100))

        # 确定KiCad电源符号的lib_id
        if ps_type == 'gnd':
            lib_id = 'power:GND'
        else:
            # VCC或其他电源符号
            if net_name.upper() in ['VCC', '+5V', '+3V3', '+12V', '+24V']:
                lib_id = 'power:VCC'
            elif net_name.upper() == 'VSS':
                lib_id = 'power:VSS'
            elif net_name.upper() == 'VEE':
                lib_id = 'power:VEE'
            else:
                lib_id = 'power:VCC'  # 默认使用VCC

        power_ref = f'#FL{i+1}'
        try:
            sch.components.add(
                lib_id=lib_id,
                reference=power_ref,
                value=net_name,
                position=(x, y)
            )
            power_refs[net_name] = power_ref
            logger.info(f'添加电源符号: {power_ref} ({lib_id}) = {net_name}')
        except Exception as e:
            logger.warning(f'添加电源符号失败: {ps.get("id")} - {e}')

    # 连接元件的电源引脚到电源符号
    components = schematic_data.get('components', [])
    connected_count = 0

    for comp in components:
        ref = comp.get('reference', '')
        if ref not in component_map:
            continue

        comp_pos = comp.get('position', {})
        pins = comp.get('pins', [])

        for pin in pins:
            pin_number = str(pin.get('number', ''))
            pin_name = pin.get('name', '').upper()
            pin_type = pin.get('type', '').lower()
            pin_pos = pin.get('position', {})

            # 计算引脚绝对位置
            abs_x = comp_pos.get('x', 0) + pin_pos.get('x', 0)
            abs_y = comp_pos.get('y', 0) + pin_pos.get('y', 0)

            # 判断是否为电源引脚（结合引脚名称和类型）
            # 知识库的 pin_type: 'power_in', 'power_out', 'input', 'output', 'passive', 'gnd'
            is_power_pin = pin_type in ['power_in', 'power_out']
            is_gnd_pin_type = pin_type == 'gnd'

            is_vcc_pin = (
                any(keyword in pin_name for keyword in ['VCC', '3V3', '5V', '12V', '24V', 'VDD']) or
                (is_power_pin and any(keyword in pin_name for keyword in ['VCC', 'VDD', '+', 'POWER']))
            )
            is_gnd_pin = (
                any(keyword in pin_name for keyword in ['GND', 'VSS', 'VEE', 'AGND', 'GROUND']) or
                is_gnd_pin_type or
                (is_power_pin and any(keyword in pin_name for keyword in ['GND', 'VSS']))
            )

            target_net = None
            if is_vcc_pin and not is_gnd_pin:
                # 找到对应的VCC电源符号
                for net_name, power_ref in power_refs.items():
                    if any(v in net_name.upper() for v in ['VCC', '+5V', '+3V3', '+12V', '+24V', 'VDD']):
                        target_net = net_name
                        break
            elif is_gnd_pin:
                # 找到GND电源符号
                for net_name, power_ref in power_refs.items():
                    if net_name.upper() in ['GND', 'VSS', 'VEE', 'AGND', 'GROUND']:
                        target_net = net_name
                        break

            if target_net and target_net in power_refs:
                try:
                    power_ref = power_refs[target_net]
                    sch.add_wire_between_pins(ref, pin_number, power_ref, '1')
                    connected_count += 1
                    logger.info(f'电源连接: {ref}.{pin_number} -> {power_ref} (net={target_net})')
                except Exception as e:
                    logger.warning(f'电源连接失败: {ref}.{pin_number} -> {power_ref} - {e}')

    return len(power_refs)


def _fix_schematic_components(sch, file_path: str) -> None:
    """
    修复 kicad_sch_api.save() 缺失的组件实例部分。

    kicad_sch_api.save() 只写入 lib_symbols 和 wires，
    但不写入组件实例 (symbol (lib_id ...) 块)。
    这些实例块是 KiCad GUI 渲染原理图的必要部分。

    KiCad 原理图格式中，组件实例是直接的 (symbol (lib_id ...) 块，
    不像旧版那样包装在 (components ...) 中。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已有组件实例
        if '(symbol (lib_id' in content:
            return  # 已有组件实例，无需修复

        # 提取原理图 UUID
        uuid_match = re.search(r'\(uuid "([^"]+)"', content)
        schematic_uuid = uuid_match.group(1) if uuid_match else ''
        project_path = f"/{schematic_uuid}"

        # 生成组件实例 S-表达式
        instances_lines = []
        for comp in sch.components:
            lib_id = comp.lib_id if comp.lib_id else f"{comp.library}:{comp.symbol_name}"
            ref = comp.reference or '?'
            value = comp.value or ''
            pos = comp.position
            x = float(getattr(pos, 'x', 0) or 0)
            y = float(getattr(pos, 'y', 0) or 0)
            rot = getattr(comp, 'rotation', 0.0) or 0.0
            comp_uuid = str(comp.uuid) if comp.uuid else uuid.uuid4().hex

            # 参考编号文字位置（元件左上方偏移）
            ref_x = x - 2.0
            ref_y = y + 2.0

            lines = [
                f'  (symbol (lib_id "{lib_id}") (at {x:.3f} {y:.3f} {rot:.1f}) (unit 1)',
                '    (in_bom yes) (on_board yes) (dnp no)',
                f'    (uuid {comp_uuid})',
                f'    (property "Reference" "{ref}" (at {ref_x:.3f} {ref_y:.3f} 0)',
                '      (effects (font (size 1.27 1.27)))',
                '    )',
                f'    (property "Value" "{value}" (at {x:.3f} {y:.3f} 0)',
                '      (effects (font (size 1.27 1.27)))',
                '    )',
                '    (property "Footprint" "" (at 0 0 0)',
                '      (effects (font (size 1.27 1.27)))',
                '    )',
                '    (property "Datasheet" "" (at 0 0 0)',
                '      (effects (font (size 1.27 1.27)))',
                '    )',
                '    (instances',
                '      (project ""',
                f'        (path "{project_path}"',
                f'          (reference "{ref}") (unit 1)',
                '        )',
                '      )',
                '    )',
                '  )',
            ]
            instances_lines.extend(lines)

        if not instances_lines:
            logger.debug('无组件实例可添加')
            return

        # 找到 sheet_instances 的位置，在它之前插入组件实例
        sheet_idx = content.rfind('(sheet_instances')
        if sheet_idx == -1:
            # 没有 sheet_instances，找最后一个 ) 之前
            last_paren = content.rfind(')')
            insert_idx = last_paren
        else:
            insert_idx = sheet_idx

        new_content = (
            content[:insert_idx]
            + '\n\n  '
            + '\n  '.join(instances_lines)
            + '\n'
            + content[insert_idx:]
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info(f'已修复原理图组件实例，共 {len(list(sch.components))} 个')

    except Exception as e:
        logger.warning(f'修复原理图组件实例失败: {e}')


def generate_kicad_schematic_file(schematic_data: dict, output_path: str, title: str = 'AI Generated Circuit') -> dict:
    """
    使用 kicad_sch_api 生成真实的 KiCad 原理图文件

    Args:
        schematic_data: 原理图数据字典
        output_path: 输出文件路径
        title: 原理图标题

    Returns:
        生成结果
    """
    try:
        ksa = _get_kicad_sch_api()

        # 创建原理图
        sch = ksa.create_schematic(title)
        logger.info(f'创建原理图: {title}')

        # 添加元件
        component_map = {}
        for i, comp in enumerate(schematic_data.get('components', [])):
            try:
                # 获取符号库和符号名
                symbol_library = comp.get('symbol_library', 'Device')
                symbol_name = comp.get('symbol_name') or comp.get('symbol') or comp.get('model', 'R')

                # 知识库补充：如果缺少symbol_name或引脚信息，重新查询知识库
                comp_model = comp.get('model', '')
                if (not symbol_name or symbol_name == comp_model or not comp.get('pins')) and comp_model:
                    try:
                        from routes.ai_routes import get_component_info
                        kb_info = get_component_info(comp_model)
                        if kb_info:
                            if not symbol_name or symbol_name == comp_model:
                                kb_symbol_name = kb_info.get('symbol_name', '')
                                if kb_symbol_name:
                                    symbol_name = kb_symbol_name
                            if not comp.get('pins') and kb_info.get('pins'):
                                comp['pins'] = kb_info['pins']
                            if not symbol_library or symbol_library == 'Device':
                                kb_lib = kb_info.get('symbol_library', '')
                                if kb_lib:
                                    symbol_library = kb_lib
                    except Exception as e:
                        logger.warning(f'知识库查询失败: {e}')

                # 应用知识库到KiCad库名映射
                KB_TO_KICAD_LIB = {
                    "MCU_ST_STM32": "MCU_ST_STM32F1",
                    "MCU_ST": "MCU_ST_STM32F1",
                    "MCU_Microchip_AVR": "MCU_Microchip_ATmega",
                    # 符号名称纠正
                    "Connector:USB_Micro-B": "Connector:USB_B_Micro",  # USB接口符号名称纠正
                    # 555定时器没有标准KiCad符号，使用占位符
                    "Timer:NE555": None,  # 不存在，使用Device作为fallback
                }
                if symbol_library in KB_TO_KICAD_LIB:
                    mapped_lib = KB_TO_KICAD_LIB[symbol_library]
                    if mapped_lib is None:
                        # 符号不存在，使用Device作为fallback
                        symbol_library = "Device"
                        symbol_name = symbol_name or model.split()[0] if model else "R"
                    else:
                        symbol_library = mapped_lib

                # 构造 lib_id：如果 symbol_library 已包含冒号(完整lib_id格式)，直接使用
                # 否则拼接 symbol_library:symbol_name
                # power 库在 KiCad 中是全小写 'power'，其他库是 PascalCase (如 'Regulator_Linear')
                if ':' in symbol_library:
                    parts = symbol_library.split(':')
                    lib_name_lower = parts[0].lower()
                    if lib_name_lower == 'power':
                        parts[0] = 'power'
                    else:
                        parts[0] = lib_name_lower
                    lib_id = ':'.join(parts)
                else:
                    lib_name_lower = symbol_library.lower()
                    if lib_name_lower == 'power':
                        lib_id = f'power:{symbol_name}' if symbol_name else 'power'
                    else:
                        lib_id = f'{symbol_library}:{symbol_name}' if symbol_name else symbol_library

                reference = comp.get('reference', f'U{i+1}')
                value = comp.get('value', comp.get('model', comp.get('name', '')))

                # 获取位置
                pos = comp.get('position', comp.get('pos', {}))
                x = float(pos.get('x', 100 * (i % 4)))
                y = float(pos.get('y', 100 * (i // 4)))

                footprint = comp.get('footprint', '')

                # 添加元件
                instance = sch.components.add(
                    lib_id=lib_id,
                    reference=reference,
                    value=value,
                    position=(x, y),
                    footprint=footprint if footprint else None,
                )

                component_map[reference] = {'lib_id': lib_id}
                logger.info(f'添加元件: {reference} ({lib_id})')

            except Exception as e:
                logger.warning(f'添加元件失败: {e}')

        # 推断导线连接（用于points格式的导线）
        inferred_connections = _infer_wire_connections(schematic_data)
        logger.info(f'从points格式推断出 {len(inferred_connections)} 条导线连接')

        # 添加导线 - 支持三种格式
        # 格式1: {"from_conn": "U1.16", "to_conn": "C1.1"} - 元件.引脚 (SchematicWire格式)
        # 格式2: {"from": "U1.16", "to": "C1.1"} - 元件.引脚
        # 格式3: {"points": [{"x": 1000, "y": 1000}, ...]} - 点列表 (需要推断连接)
        wire_count = 0
        for wire in schematic_data.get('wires', []):
            try:
                wire_id = wire.get('id', '')
                from_conn = wire.get('from_conn') or wire.get('from', '')
                to_conn = wire.get('to_conn') or wire.get('to', '')

                # 格式1: 元件.引脚格式 - 直接使用
                if from_conn and to_conn and '.' in from_conn and '.' in to_conn:
                    ref1, pin1 = from_conn.split('.', 1)
                    ref2, pin2 = to_conn.split('.', 1)
                    sch.add_wire_between_pins(ref1, pin1, ref2, pin2)
                    wire_count += 1

                # 格式3: 点列表格式 - 使用推断的连接
                elif 'points' in wire and wire_id in inferred_connections:
                    inferred = inferred_connections[wire_id]
                    ref1, pin1 = inferred['from_conn'].split('.', 1)
                    ref2, pin2 = inferred['to_conn'].split('.', 1)
                    sch.add_wire_between_pins(ref1, pin1, ref2, pin2)
                    wire_count += 1
                    logger.info(f'导线 {wire_id}: {inferred["from_conn"]} <-> {inferred["to_conn"]}')

                # 格式3 fallback: 如果推断失败，使用点格式（仅画线）
                # 先简化线段：移除重复点和共线中间点
                elif 'points' in wire:
                    simplified = _simplify_wire_points(wire.get('points', []))
                    if len(simplified) >= 2:
                        # 画简化的 L 形线（起点→拐点→终点）
                        p_start = simplified[0]
                        p_end = simplified[-1]
                        x1 = float(p_start.get('x', 0))
                        y1 = float(p_start.get('y', 0))
                        x2 = float(p_end.get('x', 0))
                        y2 = float(p_end.get('y', 0))
                        # L 形：第一段水平，第二段垂直
                        if len(simplified) == 2:
                            sch.wires.add(start=(x1, y1), end=(x2, y1))
                            sch.wires.add(start=(x2, y1), end=(x2, y2))
                        else:
                            # 多段简化：起点→第一个拐点→终点
                            mid = simplified[len(simplified)//2]
                            mx = float(mid.get('x', 0))
                            my = float(mid.get('y', 0))
                            sch.wires.add(start=(x1, y1), end=(mx, my))
                            sch.wires.add(start=(mx, my), end=(x2, y2))
                        wire_count += 1
                    logger.warning(f'导线 {wire_id} 无法推断连接，使用简化点格式 (原始 {len(wire.get("points", []))} 点 → 简化 {len(simplified)} 点)')

            except Exception as e:
                logger.warning(f'添加导线失败: {e}')

        logger.info(f'添加了 {wire_count} 条导线')

        # 添加电源符号
        power_symbol_count = _add_power_symbols(sch, schematic_data, component_map)
        logger.info(f'添加了 {power_symbol_count} 个电源符号')

        # 保存文件
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sch.save(output_path)
        logger.info(f'KiCad 原理图已保存: {output_path}')

        # 修复 kicad_sch_api.save() 缺失的组件实例部分
        _fix_schematic_components(sch, output_path)

        return {
            'success': True,
            'output_path': output_path,
            'component_count': len(component_map),
            'wire_count': wire_count,
            'power_symbol_count': power_symbol_count,
        }

    except Exception as e:
        logger.error(f'生成 KiCad 原理图失败: {e}', exc_info=True)
        return {'success': False, 'error': str(e)}




# ============ 导入部分 ============

# 延迟导入避免循环依赖
_schematic_parser = None
_netlist_exporter = None
_netlist_validator = None


def _get_schematic_parser():
    """获取原理图解析器"""
    global _schematic_parser
    if _schematic_parser is None:
        from schematic_parser import SchematicParser
        _schematic_parser = SchematicParser()
    return _schematic_parser


def _get_netlist_exporter():
    """获取网表导出器"""
    global _netlist_exporter
    if _netlist_exporter is None:
        from netlist_exporter import NetlistExporter
        _netlist_exporter = NetlistExporter()
    return _netlist_exporter


def _get_netlist_validator():
    """获取网表验证器"""
    global _netlist_validator
    if _netlist_validator is None:
        from netlist_validator import NetlistValidator
        _netlist_validator = NetlistValidator()
    return _netlist_validator


# ============ 数据模型 ============


class DesignInfo(BaseModel):
    """设计信息"""
    title: Optional[str] = ""
    date: Optional[str] = ""
    revision: Optional[str] = ""
    company: Optional[str] = ""
    comment1: Optional[str] = ""
    comment2: Optional[str] = ""
    comment3: Optional[str] = ""
    comment4: Optional[str] = ""


class NetlistExportRequest(BaseModel):
    """网表导出请求"""
    schematic_data: dict
    pcb_data: Optional[dict] = None
    design_info: Optional[DesignInfo] = None
    format: str = "xml"  # xml, csv, json


class NetlistValidationRequest(BaseModel):
    """网表验证请求"""
    schematic_data: dict
    pcb_data: dict


# ============ API 端点 ============


@router.get("/health")
async def netlist_health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "netlist",
        "features": ["parse", "export", "validate"]
    }


@router.post("/parse-schematic")
async def parse_schematic(file: UploadFile = File(...)):
    """
    解析KiCad原理图文件，提取网表信息

    上传 .kicad_sch 文件，返回元件和网络信息
    """
    try:
        # 读取上传的文件内容
        content = await file.read()

        # 使用唯一文件名避免Windows文件锁定
        tmp_filename = f"schematic_{uuid.uuid4().hex}.kicad_sch"
        tmp_path = os.path.join(os.path.dirname(__file__), tmp_filename)

        try:
            # 写入临时文件
            with open(tmp_path, 'wb') as f:
                f.write(content)

            # 解析文件
            parser = _get_schematic_parser()
            schematic = parser.parse_file(tmp_path)
            result = parser.get_netlist_dict()

            return {
                "success": True,
                "filename": file.filename,
                "data": result
            }
        finally:
            # 删除临时文件
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError as e:
                logger.warning(f"清理临时文件失败: {tmp_path}: {e}")

    except Exception as e:
        logger.error(f"解析原理图失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.post("/export")
async def export_netlist(request: NetlistExportRequest):
    """
    导出网表

    根据格式导出为XML、CSV或JSON格式
    """
    from netlist_exporter import create_netlist_from_schematic

    # 验证格式
    valid_formats = {"xml", "csv", "json"}
    if request.format.lower() not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"无效的格式: {request.format}。支持的格式: xml, csv, json"
        )

    try:
        # 设计信息
        design_info = None
        if request.design_info:
            design_info = request.design_info.model_dump()

        # 直接返回内容,不写入文件(避免Windows文件锁定问题)
        content = create_netlist_from_schematic(
            request.schematic_data,
            output_path=None,  # 不写文件
            design_info=design_info,
            return_content=True
        )

        return {
            "success": True,
            "format": request.format,
            "content": content
        }

    except Exception as e:
        logger.error(f"导出网表失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/validate")
async def validate_netlist(request: NetlistValidationRequest):
    """
    验证网表一致性

    检查原理图和PCB之间的网络连接是否一致
    """
    try:
        from netlist_validator import validate_netlists

        result = validate_netlists(request.schematic_data, request.pcb_data)

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        logger.error(f"验证网表失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.get("/example")
async def get_netlist_example():
    """
    获取网表示例数据

    返回示例性的原理图和PCB数据，用于测试
    """
    schematic_example = {
        "name": "Example PCB",
        "components": [
            {
                "reference": "U1",
                "value": "STM32F103C8T6",
                "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
                "symbol_library": "MCU_ST_STM32",
                "symbol_name": "STM32F103C8T6"
            },
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "symbol_library": "Device",
                "symbol_name": "R"
            },
            {
                "reference": "C1",
                "value": "10uF",
                "footprint": "Capacitor_SMD:C_0603_1608Metric",
                "symbol_library": "Device",
                "symbol_name": "C"
            }
        ],
        "nets": [
            {
                "name": "VCC",
                "connections": [
                    {"reference": "U1", "pin": "VDD"},
                    {"reference": "R1", "pin": "1"},
                    {"reference": "C1", "pin": "1"}
                ]
            },
            {
                "name": "GND",
                "connections": [
                    {"reference": "U1", "pin": "VSS"},
                    {"reference": "R1", "pin": "2"},
                    {"reference": "C1", "pin": "2"}
                ]
            }
        ]
    }

    pcb_example = {
        "footprints": [
            {"reference": "U1", "module": "LQFP-48_7x7mm_P0.5mm"},
            {"reference": "R1", "module": "R_0603_1608Metric"},
            {"reference": "C1", "module": "C_0603_1608Metric"}
        ],
        "nets": [
            {
                "name": "VCC",
                "connections": [
                    {"reference": "U1", "pin": "VDD"},
                    {"reference": "R1", "pin": "1"},
                    {"reference": "C1", "pin": "1"}
                ]
            },
            {
                "name": "GND",
                "connections": [
                    {"reference": "U1", "pin": "VSS"},
                    {"reference": "R1", "pin": "2"},
                    {"reference": "C1", "pin": "2"}
                ]
            }
        ]
    }

    return {
        "success": True,
        "schematic": schematic_example,
        "pcb": pcb_example
    }


# ============ KiCad 原生网表获取 ============


@router.post("/export-from-kicad")
async def export_netlist_from_kicad(
    project_id: str = Query(..., description="项目ID"),
    schematic_path: str = Query(None, description="原理图文件路径，如果为空则从项目目录查找")
):
    """
    从 KiCad 原理图导出网表（原生KiCad功能）
    
    使用 kicad-cli sch export netlist 命令获取真实的网表数据
    """
    logger.info(f"从KiCad导出网表: project_id={project_id}")
    
    # 查找原理图文件
    if not schematic_path:
        # 尝试从项目目录查找
        projects_dir = Path(os.environ.get("PROJECTS_DIR", "./projects"))
        project_dir = projects_dir / project_id
        
        # 查找原理图文件
        for sch_file in project_dir.glob("*.kicad_sch"):
            schematic_path = str(sch_file)
            break
    
    if not schematic_path or not Path(schematic_path).exists():
        raise HTTPException(status_code=404, detail=f"原理图文件不存在: {schematic_path}")
    
    # 使用 kicad-cli 导出网表
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
            output_file = tmp.name
        
        # 执行导出命令
        cmd = [
            _get_kicad_cli_path(), "sch", "export", "netlist",
            "-o", output_file,
            "--format", "kicadxml",  # 使用XML格式便于解析
            schematic_path
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"网表导出失败: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"网表导出失败: {result.stderr}")
        
        # 解析XML网表
        tree = ET.parse(output_file)
        root = tree.getroot()
        
        # 提取元件信息
        components = []
        for comp in root.findall(".//comp"):
            ref = comp.get("ref", "")
            value = comp.findtext("value", "")
            footprint = comp.findtext("footprint", "")
            lib_id = comp.get("libsource", "")
            
            components.append({
                "reference": ref,
                "value": value,
                "footprint": footprint,
                "lib_id": lib_id
            })
        
        # 提取网络信息
        nets = []
        for net in root.findall(".//net"):
            net_name = net.get("name", "")
            code = net.get("code", "")
            
            # 提取连接的引脚
            nodes = []
            for node in net.findall("node"):
                ref = node.get("ref", "")
                pin = node.get("pin", "")
                nodes.append({"reference": ref, "pin": pin})
            
            nets.append({
                "name": net_name,
                "code": int(code) if code.isdigit() else 0,
                "nodes": nodes
            })
        
        # 清理临时文件
        try:
            os.unlink(output_file)
        except OSError as e:
            logger.warning(f"清理临时文件失败: {output_file}: {e}")
        
        return {
            "success": True,
            "source": "kicad",
            "components": components,
            "nets": nets,
            "component_count": len(components),
            "net_count": len(nets)
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="网表导出超时")
    except Exception as e:
        logger.error(f"网表导出异常: {e}")
        raise HTTPException(status_code=500, detail=f"网表导出异常: {str(e)}")


@router.post("/run-erc-from-kicad")
async def run_erc_from_kicad(
    project_id: str = Query(..., description="项目ID"),
    schematic_path: str = Query(None, description="原理图文件路径")
):
    """
    从 KiCad 运行 ERC 电气规则检查（原生KiCad功能）
    
    使用 kicad-cli sch run erc 命令
    """
    logger.info(f"从KiCad运行ERC: project_id={project_id}")
    
    # 查找原理图文件
    if not schematic_path:
        projects_dir = Path(os.environ.get("PROJECTS_DIR", "./projects"))
        project_dir = projects_dir / project_id
        
        for sch_file in project_dir.glob("*.kicad_sch"):
            schematic_path = str(sch_file)
            break
    
    if not schematic_path or not Path(schematic_path).exists():
        raise HTTPException(status_code=404, detail=f"原理图文件不存在")
    
    try:
        # 使用 kicad-cli 运行 ERC，使用JSON格式输出
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            erc_output = tmp.name
        
        cmd = [
            _get_kicad_cli_path(), "sch", "run", "erc",
            "--format", "json",
            "-o", erc_output,
            schematic_path
        ]
        
        logger.info(f"执行ERC命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # 解析ERC输出
        output = result.stdout + result.stderr
        
        # 提取错误和警告
        errors = []
        warnings = []
        
        # 简单的解析（实际可能需要更复杂的解析）
        lines = output.split('\n')
        for line in lines:
            if 'ERROR' in line.upper():
                errors.append({"message": line.strip()})
            elif 'WARNING' in line.upper() or 'WARN' in line.upper():
                warnings.append({"message": line.strip()})
        
        # 如果没有解析到错误，检查返回码
        if result.returncode != 0 and not errors:
            errors.append({"message": f"ERC检查失败，返回码: {result.returncode}"})
        
        return {
            "success": result.returncode == 0,
            "source": "kicad",
            "errors": errors,
            "warnings": warnings,
            "output": output,
            "error_count": len(errors),
            "warning_count": len(warnings)
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="ERC检查超时")
    except Exception as e:
        logger.error(f"ERC检查异常: {e}")
        raise HTTPException(status_code=500, detail=f"ERC检查异常: {str(e)}")


# ============ 保存原理图为KiCad文件并获取网表 ============

@router.post("/save-schematic-and-get-netlist")
async def save_schematic_and_get_netlist(
    project_id: str = Query(..., description="项目ID"),
    schematic_data: Optional[dict] = Body(None),  # 如果不提供，则从项目数据中获取
    name: str = Query(None, description="原理图文件名（不含扩展名）")
):
    """
    1. 将原理图数据保存为KiCad原理图文件
    2. 从KiCad导出网表
    
    这是完整的使用KiCad原生功能的流程
    """
    logger.info(f"保存原理图并获取网表: project_id={project_id}")
    
    # 导入必要的模块
    from routes.project_routes import _schematic_data, _projects
    
    # 获取原理图数据
    if not schematic_data:
        if project_id in _schematic_data:
            schematic_data = _schematic_data[project_id]
        else:
            raise HTTPException(status_code=404, detail="未找到原理图数据")
    
    # 创建项目目录
    import uuid
    projects_base = Path(os.environ.get("PROJECTS_DIR", "./projects"))
    project_dir = projects_base / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成原理图文件名
    schematic_name = name or f"schematic_{project_id[:8]}"
    schematic_file = project_dir / f"{schematic_name}.kicad_sch"
    
    # 使用 kicad_sch_api 生成真实的 KiCad 原理图文件
    # 使用环境变量或默认路径作为基础日志目录
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f'[DEBUG] project_id={project_id}, schematic_data type={type(schematic_data)}, keys={list(schematic_data.keys()) if schematic_data else None}')
    schematic_result = generate_kicad_schematic_file(
        schematic_data,
        str(schematic_file),
        title=schematic_name
    )
    logger.debug(f'[DEBUG] result={schematic_result}')
    
    if not schematic_result.get('success'):
        return {
            'success': False,
            'error': schematic_result.get('error', '原理图生成失败')
        }
    
    logger.info(f"原理图文件已保存: {schematic_file}")
    
    # 保存到内存中的schematic_data
    _schematic_data[project_id] = schematic_data
    
    # 保存到文件
    try:
        from routes.project_routes import _save_schematic_data
        _save_schematic_data()
        logger.info("原理图数据已保存到文件")
    except Exception as e:
        logger.warning(f"保存原理图数据失败: {e}")
    
    # 使用 kicad-cli 导出网表，使用上下文管理器确保临时文件正确关闭
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, close=False) as tmp:
            output_file = tmp.name
            tmp.close()  # 显式关闭文件句柄

        cmd = [
            _get_kicad_cli_path(), "sch", "export", "netlist",
            "-o", output_file,
            "--format", "kicadxml",
            str(schematic_file)
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.warning(f"网表导出失败: {result.stderr}")
            # 即使导出失败，也返回原理图文件信息
            return {
                "success": True,
                "schematic_file": str(schematic_file),
                "netlist_export": "failed",
                "error": result.stderr,
                "message": "原理图已保存，但网表导出失败"
            }
        
        # 解析XML网表
        tree = ET.parse(output_file)
        root = tree.getroot()
        
        # 提取元件信息
        components = []
        for comp in root.findall(".//comp"):
            ref = comp.get("ref", "")
            value = comp.findtext("value", "")
            footprint = comp.findtext("footprint", "")
            
            components.append({
                "reference": ref,
                "value": value,
                "footprint": footprint
            })
        
        # 提取网络信息
        nets = []
        for net in root.findall(".//net"):
            net_name = net.get("name", "")
            code = net.get("code", "")
            
            nodes = []
            for node in net.findall("node"):
                ref = node.get("ref", "")
                pin = node.get("pin", "")
                nodes.append({"reference": ref, "pin": pin})
            
            nets.append({
                "name": net_name,
                "code": int(code) if code.isdigit() else 0,
                "nodes": nodes
            })
        
        # 清理临时文件
        try:
            os.unlink(output_file)
        except OSError as e:
            logger.warning(f"清理临时文件失败: {output_file}: {e}")
        
        return {
            "success": True,
            "source": "kicad",
            "schematic_file": str(schematic_file),
            "components": components,
            "nets": nets,
            "component_count": len(components),
            "net_count": len(nets)
        }
        
    except Exception as e:
        logger.error(f"处理异常: {e}")
        return {
            "success": True,
            "schematic_file": str(schematic_file),
            "error": str(e)
        }


def generate_kicad_schematic(schematic_data: dict, name: str) -> str:
    """
    生成KiCad原理图文件内容
    
    注意：真实的KiCad原理图文件(.kicad_sch)是JSON格式的，
    这里生成简化版本用于测试网表导出功能
    """
    import json
    from datetime import datetime
    
    # 构建原理图结构 (KiCad 8.0+ JSON格式)
    schematic = {
        "meta": {
            "version": 1,
            "creator": "KiCad AI Auto"
        },
        "schematic": {
            "version": 20240101,
            "generator": "kicad.ai.auto"
        },
        "project": {
            "name": name,
            "date": datetime.now().isoformat(),
            "revision": "v1.0"
        },
        "components": [],
        "nets": []
    }
    
    # 添加元件
    for i, comp in enumerate(schematic_data.get("components", [])):
        ref = comp.get("reference", f"U{i+1}")
        value = comp.get("value", comp.get("model", ""))
        footprint = comp.get("footprint", "")
        
        # 简化处理
        x = comp.get("x", 1000 * (i % 4))
        y = comp.get("y", 1000 * (i // 4))
        
        comp_entry = {
            "libId": f"Device:U{comp.get('category', 'IC')}",
            "name": ref,
            "fields": {
                "Reference": ref,
                "Value": value,
                "Footprint": footprint
            },
            "uuid": str(uuid.uuid4()),
            "transform": {
                "x": x,
                "y": y,
                "angle": 0
            }
        }
        schematic["components"].append(comp_entry)
    
    # 添加网络
    net_code = 1
    for net in schematic_data.get("nets", []):
        net_name = net.get("name", "")
        
        net_entry = {
            "name": net_name,
            "code": net_code,
            "items": []
        }
        schematic["nets"].append(net_entry)
        net_code += 1
    
    return json.dumps(schematic, indent=2)
