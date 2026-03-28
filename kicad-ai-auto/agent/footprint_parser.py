"""
KiCad Footprint Parser
解析 .kicad_mod 文件，提取焊盘和图形数据
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# KiCad footprint 库路径
DEFAULT_KICAD_FOOTPRINT_PATH = os.environ.get("KICAD_FOOTPRINT_DIR", r"E:\Program Files\KiCad\9.0\share\kicad\footprints")

# 缓存已解析的封装
_footprint_cache: Dict[str, Dict[str, Any]] = {}


class FootprintParser:
    """KiCad 封装解析器"""

    def __init__(self, footprint_path: str = None):
        self.footprint_path = footprint_path or DEFAULT_KICAD_FOOTPRINT_PATH
        # 验证路径
        if not os.path.exists(self.footprint_path):
            logger.warning(f"Footprint path not found: {self.footprint_path}")
            self.footprint_path = None

    def list_libraries(self) -> List[str]:
        """列出所有可用的封装库"""
        if not self.footprint_path:
            return []
        try:
            dirs = os.listdir(self.footprint_path)
            return [d.replace('.pretty', '') for d in dirs if d.endswith('.pretty')]
        except Exception as e:
            logger.error(f"Error listing footprint libraries: {e}")
            return []

    def list_footprints(self, library: str) -> List[str]:
        """列出指定库中的所有封装"""
        if not self.footprint_path:
            return []
        lib_path = os.path.join(self.footprint_path, f"{library}.pretty")
        if not os.path.exists(lib_path):
            return []
        try:
            files = os.listdir(lib_path)
            return [f.replace('.kicad_mod', '') for f in files if f.endswith('.kicad_mod')]
        except Exception as e:
            logger.error(f"Error listing footprints in {library}: {e}")
            return []

    def get_footprint(self, library: str, name: str) -> Optional[Dict[str, Any]]:
        """获取指定封装的详细信息"""
        cache_key = f"{library}:{name}"
        if cache_key in _footprint_cache:
            return _footprint_cache[cache_key]

        if not self.footprint_path:
            return None

        # 尝试多个可能的文件名
        possible_files = [
            f"{name}.kicad_mod",
            f"{name.replace('_', '-')}.kicad_mod",
        ]

        lib_path = os.path.join(self.footprint_path, f"{library}.pretty")
        if not os.path.exists(lib_path):
            return None

        for filename in possible_files:
            fp_path = os.path.join(lib_path, filename)
            if os.path.exists(fp_path):
                try:
                    with open(fp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    footprint = self._parse_kicad_mod(content, name, library)
                    _footprint_cache[cache_key] = footprint
                    return footprint
                except Exception as e:
                    logger.error(f"Error parsing footprint {library}/{name}: {e}")
                    return None

        return None

    def find_footprint(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称查找封装（搜索所有库）"""
        # 先尝试直接匹配
        if ':' in name:
            parts = name.split(':')
            if len(parts) == 2:
                fp = self.get_footprint(parts[0], parts[1])
                if fp:
                    return fp

        # 搜索所有库
        for library in self.list_libraries():
            footprints = self.list_footprints(library)
            for fp_name in footprints:
                if fp_name.lower() == name.lower() or name.lower() in fp_name.lower():
                    fp = self.get_footprint(library, fp_name)
                    if fp:
                        return fp

        return None

    def _parse_kicad_mod(self, content: str, name: str, library: str) -> Dict[str, Any]:
        """解析 kicad_mod 文件内容"""
        graphics = []
        pads = []

        # 解析焊盘 (pad) - 处理多行格式
        # 格式: (pad "1" smd roundrect (at -0.825 0) (size 0.8 0.95) (layers "F.Cu" "F.Mask" "F.Paste"))
        # 使用状态机来解析每个 pad 块
        lines = content.replace('\r\n', '\n').split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('(pad '):
                # 收集整个 pad 块
                pad_block = line
                depth = line.count('(') - line.count(')')
                i += 1
                while depth > 0 and i < len(lines):
                    next_line = lines[i].strip()
                    pad_block += ' ' + next_line
                    depth += next_line.count('(') - next_line.count(')')
                    i += 1

                # 解析 pad 块
                try:
                    # 提取 pad 编号
                    num_match = re.search(r'\(pad\s+"([^"]+)"', pad_block)
                    pad_num = num_match.group(1) if num_match else '1'

                    # 提取 pad 类型
                    type_match = re.search(r'\(pad\s+"[^"]+"\s+(\w+)', pad_block)
                    pad_type = type_match.group(1).lower() if type_match else 'smd'

                    # 提取位置 (at x y)
                    pos_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\)', pad_block)
                    if pos_match:
                        x = float(pos_match.group(1))
                        y = float(pos_match.group(2))
                    else:
                        x, y = 0, 0

                    # 提取尺寸 (size x y) - 注意没有括号
                    size_match = re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)\)', pad_block)
                    if size_match:
                        sx = float(size_match.group(1))
                        sy = float(size_match.group(2))
                    else:
                        sx, sy = 1.0, 1.0

                    # 提取 layers
                    layers_match = re.search(r'\(layers\s+([^)]+)\)', pad_block)
                    layers = ['F.Cu', 'F.Pasteask']
                    if layers_match:
                        layers_str = layers_match.group(1)
                        # 解析层', 'F.M列表
                        layer_list = re.findall(r'"([^"]+)"', layers_str)
                        if layer_list:
                            layers = layer_list

                    # 判断形状
                    shape = 'rect'
                    if 'roundrect' in pad_block.lower():
                        shape = 'roundrect'
                    elif 'circle' in pad_block.lower():
                        shape = 'circle'

                    pad = {
                        'number': pad_num,
                        'type': pad_type,
                        'shape': shape,
                        'position': {'x': x, 'y': y},
                        'size': {'x': sx, 'y': sy},
                        'layers': layers,
                    }
                    pads.append(pad)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Failed to parse pad block: {e}")
            else:
                i += 1

        # 解析线条 (segment)
        seg_pattern = r'\(segment\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+\(layer\s+(\w+)\)\s+\(width\s+([-\d.]+)\)'
        for match in re.finditer(seg_pattern, content, re.IGNORECASE):
            x1, y1, x2, y2, layer, width = match.groups()
            try:
                graphics.append({
                    'type': 'line',
                    'start': {'x': float(x1), 'y': float(y1)},
                    'end': {'x': float(x2), 'y': float(y2)},
                    'layer': layer,
                    'width': float(width),
                })
            except (ValueError, TypeError):
                pass

        # 解析矩形 (rect)
        rect_pattern = r'\(rect\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+\(layer\s+(\w+)\)\s+\(width\s+([-\d.]+)\)'
        for match in re.finditer(rect_pattern, content, re.IGNORECASE):
            x1, y1, x2, y2, layer, width = match.groups()
            try:
                # 转换为 lines
                graphics.append({
                    'type': 'line',
                    'start': {'x': float(x1), 'y': float(y1)},
                    'end': {'x': float(x2), 'y': float(y1)},
                    'layer': layer,
                    'width': float(width),
                })
                graphics.append({
                    'type': 'line',
                    'start': {'x': float(x2), 'y': float(y1)},
                    'end': {'x': float(x2), 'y': float(y2)},
                    'layer': layer,
                    'width': float(width),
                })
                graphics.append({
                    'type': 'line',
                    'start': {'x': float(x2), 'y': float(y2)},
                    'end': {'x': float(x1), 'y': float(y2)},
                    'layer': layer,
                    'width': float(width),
                })
                graphics.append({
                    'type': 'line',
                    'start': {'x': float(x1), 'y': float(y2)},
                    'end': {'x': float(x1), 'y': float(y1)},
                    'layer': layer,
                    'width': float(width),
                })
            except (ValueError, TypeError):
                pass

        # 解析圆 (circle)
        circle_pattern = r'\(circle\s+\(center\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+\(layer\s+(\w+)\)\s+\(width\s+([-\d.]+)\)'
        for match in re.finditer(circle_pattern, content, re.IGNORECASE):
            cx, cy, ex, ey, layer, width = match.groups()
            try:
                # 计算半径
                radius = ((float(ex) - float(cx))**2 + (float(ey) - float(cy))**2) ** 0.5
                graphics.append({
                    'type': 'circle',
                    'center': {'x': float(cx), 'y': float(cy)},
                    'radius': radius,
                    'layer': layer,
                    'width': float(width),
                })
            except (ValueError, TypeError):
                pass

        # 解析文字 (text)
        text_pattern = r'\(text\s+"([^"]+)"\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)?\)'
        for match in re.finditer(text_pattern, content, re.IGNORECASE):
            text, x, y, rot = match.groups()
            try:
                graphics.append({
                    'type': 'text',
                    'text': text,
                    'position': {'x': float(x), 'y': float(y)},
                    'layer': 'F.SilkS',
                })
            except (ValueError, TypeError):
                pass

        return {
            'name': name,
            'description': f'{library}/{name}',
            'tags': [],
            'graphics': graphics,
            'pads': pads,
        }


# 全局解析器实例
_parser: Optional[FootprintParser] = None


def get_footprint_parser() -> FootprintParser:
    """获取全局封装解析器实例"""
    global _parser
    if _parser is None:
        _parser = FootprintParser()
    return _parser


def get_footprint(library: str, name: str) -> Optional[Dict[str, Any]]:
    """获取指定封装"""
    return get_footprint_parser().get_footprint(library, name)


def find_footprint(name: str) -> Optional[Dict[str, Any]]:
    """查找封装"""
    return get_footprint_parser().find_footprint(name)


def list_libraries() -> List[str]:
    """列出所有库"""
    return get_footprint_parser().list_libraries()
