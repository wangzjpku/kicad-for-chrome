"""
知识库集成模块
集成 GerberGPT 项目的芯片数据库和外围电路设计知识库
"""

import os
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# GerberGPT 数据路径
GERBERGPT_PATH = r"E:\0-007-MyAIOS\projects\2-GerberGPT"

# 芯片数据库缓存
_chip_database: List[Dict[str, str]] = []

# 外围电路知识库缓存
_peripheral_circuits: Dict[str, Any] = {}


def load_chip_database() -> List[Dict[str, str]]:
    """加载芯片数据库"""
    global _chip_database

    if _chip_database:
        return _chip_database

    csv_path = os.path.join(GERBERGPT_PATH, "chip-datasheet", "chip_database.csv")

    if not os.path.exists(csv_path):
        logger.warning(f"Chip database not found: {csv_path}")
        return []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            _chip_database = list(reader)
        logger.info(f"Loaded {_chip_database} chips from database")
        return _chip_database
    except Exception as e:
        logger.error(f"Failed to load chip database: {e}")
        return []


def search_chips(keyword: str) -> List[Dict[str, str]]:
    """根据关键词搜索芯片"""
    chips = load_chip_database()
    if not chips:
        return []

    keyword_lower = keyword.lower()
    results = []

    for chip in chips:
        # 搜索型号、描述、类别
        model = chip.get('型号', '').lower()
        desc = chip.get('描述', '').lower()
        category = chip.get('类别', '').lower()

        if (keyword_lower in model or
            keyword_lower in desc or
            keyword_lower in category):
            results.append(chip)

    return results


def get_chip_by_model(model: str) -> Optional[Dict[str, str]]:
    """根据型号获取芯片信息"""
    chips = load_chip_database()
    if not chips:
        return None

    model_lower = model.lower()
    for chip in chips:
        if chip.get('型号', '').lower() == model_lower:
            return chip

    return None


def get_chips_by_category(category: str) -> List[Dict[str, str]]:
    """获取指定类别的所有芯片"""
    chips = load_chip_database()
    if not chips:
        return []

    category_lower = category.lower()
    return [c for c in chips if c.get('类别', '').lower() == category_lower]


def load_peripheral_circuits() -> Dict[str, Any]:
    """加载外围电路知识库"""
    global _peripheral_circuits

    if _peripheral_circuits:
        return _peripheral_circuits

    md_path = os.path.join(GERBERGPT_PATH, "chip-datasheet", "外围电路设计知识库.md")

    if not os.path.exists(md_path):
        logger.warning(f"Peripheral circuits not found: {md_path}")
        return {}

    try:
        # 简单解析Markdown，提取标题和内容
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 按章节分割
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## '):
                # 保存之前的章节
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                # 开始新章节
                current_section = line[3:].strip()
                current_content = []
            elif line.startswith('### '):
                # 子章节
                if current_section:
                    current_content.append(line)
            elif current_section:
                current_content.append(line)

        # 保存最后一个章节
        if current_section:
            sections[current_section] = '\n'.join(current_content)

        _peripheral_circuits = sections
        logger.info(f"Loaded {len(sections)} peripheral circuit sections")
        return sections

    except Exception as e:
        logger.error(f"Failed to load peripheral circuits: {e}")
        return {}


def get_peripheral_circuit(circuit_type: str) -> Optional[str]:
    """获取指定类型的外围电路设计参考"""
    circuits = load_peripheral_circuits()
    return circuits.get(circuit_type)


def get_mcu_peripheral_design(mcu_type: str) -> Optional[str]:
    """获取MCU外围电路设计参考"""
    circuits = load_peripheral_circuits()

    # 查找相关的MCU设计
    for title, content in circuits.items():
        if mcu_type.lower() in title.lower() or mcu_type.lower() in content.lower():
            return f"## {title}\n\n{content}"

    return None


def get_power_circuit_design(power_type: str) -> Optional[str]:
    """获取电源电路设计参考"""
    circuits = load_peripheral_circuits()

    for title, content in circuits.items():
        if '电源' in title or 'power' in title.lower():
            if power_type.lower() in content.lower():
                return f"## {title}\n\n{content}"

    return None


def get_chip_reference(chip_model: str) -> Dict[str, Any]:
    """获取芯片的完整参考信息"""
    result = {
        "chip_info": get_chip_by_model(chip_model),
        "datasheet": None,
        "peripheral_circuit": None,
    }

    # 查找芯片信息
    if result["chip_info"]:
        category = result["chip_info"].get('类别', '')

        # 尝试查找数据手册PDF
        pdf_path = find_datasheet_pdf(chip_model)
        if pdf_path:
            result["datasheet"] = pdf_path

        # 尝试查找外围电路
        if 'MCU' in category or 'mcu' in category.lower():
            result["peripheral_circuit"] = get_mcu_peripheral_design(chip_model)
        elif '电源' in category or 'Power' in category:
            result["peripheral_circuit"] = get_power_circuit_design(chip_model)

    return result


def find_datasheet_pdf(chip_model: str) -> Optional[str]:
    """查找芯片数据手册PDF路径"""
    downloads_dir = os.path.join(GERBERGPT_PATH, "chip-datasheet", "downloads")

    if not os.path.exists(downloads_dir):
        # 尝试其他可能的位置
        downloads_dir = os.path.join(GERBERGPT_PATH, "chip-datasheet")

    # 清理型号名称用于搜索
    search_names = [
        chip_model.upper(),
        chip_model.upper().replace('-', ''),
        chip_model.upper().replace('_', ''),
    ]

    # 遍历目录查找PDF
    for root, dirs, files in os.walk(downloads_dir):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                filename_upper = filename.upper()
                for search_name in search_names:
                    if search_name.upper() in filename_upper:
                        return os.path.join(root, filename)

    return None


def get_all_categories() -> List[str]:
    """获取所有芯片类别"""
    chips = load_chip_database()
    categories = set()

    for chip in chips:
        category = chip.get('类别', '')
        if category:
            categories.add(category)

    return sorted(list(categories))


def get_popular_chips(limit: int = 20) -> List[Dict[str, str]]:
    """获取常用芯片列表"""
    chips = load_chip_database()

    # 按类别优先返回一些常用芯片
    priority_categories = ['MCU', 'Power_LDO', 'Power_DCDC']

    result = []
    for category in priority_categories:
        category_chips = get_chips_by_category(category)
        result.extend(category_chips[:5])

    # 添加其他类别
    for chip in chips:
        if chip not in result:
            result.append(chip)
            if len(result) >= limit:
                break

    return result


# 导出常用函数
__all__ = [
    'load_chip_database',
    'search_chips',
    'get_chip_by_model',
    'get_chips_by_category',
    'load_peripheral_circuits',
    'get_peripheral_circuit',
    'get_mcu_peripheral_design',
    'get_power_circuit_design',
    'get_chip_reference',
    'find_datasheet_pdf',
    'get_all_categories',
    'get_popular_chips',
]


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    print("=== 芯片数据库测试 ===")
    chips = load_chip_database()
    print(f"Loaded {len(chips)} chips")

    print("\n=== 搜索NE555 ===")
    results = search_chips("555")
    for c in results:
        print(f"  {c.get('型号')}: {c.get('描述')}")

    print("\n=== 获取STM32F103 ===")
    chip = get_chip_by_model("STM32F103C8T6")
    if chip:
        print(f"  {chip}")

    print("\n=== 常用芯片 ===")
    popular = get_popular_chips(10)
    for c in popular:
        print(f"  {c.get('型号')} - {c.get('类别')}")
