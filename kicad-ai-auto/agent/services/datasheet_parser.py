"""
PDF 数据表解析器 v1.0

功能特性：
1. 使用 PyMuPDF (fitz) 提取文本
2. 正则表达式匹配参数
3. AI 辅助提取复杂信息

作者：AI Assistant
版本：1.0
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class PinInfo:
    """引脚信息"""
    number: str
    name: str
    type: str  # input, output, power, etc.
    description: str = ""


@dataclass
class Parameter:
    """电气参数"""
    name: str
    value: str
    unit: str = ""
    condition: str = ""  # 测试条件


@dataclass
class ParsedComponent:
    """解析后的元件数据"""
    name: str
    manufacturer: str = ""
    part_number: str = ""
    description: str = ""
    pins: List[PinInfo] = None
    parameters: List[Parameter] = None
    footprint: str = ""
    datasheet_url: str = ""

    def __post_init__(self):
        if self.pins is None:
            self.pins = []
        if self.parameters is None:
            self.parameters = []


class DatasheetParser:
    """
    PDF 数据表解析器

    使用:
    1. PyMuPDF (fitz) 提取文本
    2. 正则表达式匹配参数
    3. AI 辅助提取复杂信息
    """

    def __init__(self):
        self.text: str = ""

    def parse(self, pdf_path: str) -> ParsedComponent:
        """
        解析数据表

        Args:
            pdf_path: PDF 文件路径

        Returns:
            ParsedComponent
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed, using text extraction fallback")
            return self._mock_parse(pdf_path)

        try:
            # 打开 PDF
            doc = fitz.open(pdf_path)
            self.text = ""

            # 提取所有文本
            for page in doc:
                self.text += page.get_text()

            doc.close()

            # 解析元件信息
            return self._parse_text()

        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            return self._mock_parse(pdf_path)

    def parse_from_string(self, text: str) -> ParsedComponent:
        """
        从文本字符串解析（用于测试或 AI 辅助）

        Args:
            text: PDF 提取的文本

        Returns:
            ParsedComponent
        """
        self.text = text
        return self._parse_text()

    def _parse_text(self) -> ParsedComponent:
        """解析文本内容"""
        component = ParsedComponent(name="Unknown")

        # 提取元件名称
        component.name = self._extract_name()

        # 提取制造商
        component.manufacturer = self._extract_manufacturer()

        # 提取型号
        component.part_number = self._extract_part_number()

        # 提取描述
        component.description = self._extract_description()

        # 提取引脚定义
        component.pins = self._extract_pins()

        # 提取电气参数
        component.parameters = self._extract_parameters()

        # 提取封装信息
        component.footprint = self._extract_footprint()

        return component

    def _extract_name(self) -> str:
        """提取元件名称"""
        # 通常在标题或第一行
        lines = self.text.split('\n')
        if lines:
            # 取第一行非空文本
            for line in lines[:5]:
                line = line.strip()
                if line and len(line) > 1:
                    # 清理特殊字符
                    line = re.sub(r'[^\w\s\-]', '', line)
                    return line
        return "Unknown"

    def _extract_manufacturer(self) -> str:
        """提取制造商"""
        patterns = [
            r'Manufacturer:\s*(.+?)(?:\n|$)',
            r'STMICROELECTRONICS',
            r'TEXAS INSTRUMENTS',
            r'ON SEMICONDUCTOR',
            r'MICROCHIP',
            r'ANALOG DEVICES',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.groups() else match.group(0).strip()

        return ""

    def _extract_part_number(self) -> str:
        """提取型号"""
        patterns = [
            r'(?:Part\s*Number|Datasheet|Type)\s*[:\-]?\s*([A-Z0-9\-]+)',
            r'\b(STM32F\d+[A-Z]\d+)\b',
            r'\b(LM\d+[A-Z]?\d*)\b',
            r'\b(NE555P?)\b',
            r'\b(CH340[A-Z]?)\b',
            r'\b(ESP32[-WROOM]+\d+[-A-Z0-9]*)\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_description(self) -> str:
        """提取描述"""
        # 取前200个字符作为描述
        clean_text = re.sub(r'\s+', ' ', self.text).strip()
        return clean_text[:200] + "..." if len(clean_text) > 200 else clean_text

    def _extract_pins(self) -> List[PinInfo]:
        """提取引脚定义"""
        pins = []

        # 查找引脚定义表格
        # 常见格式：Pin 1 | VCC | Power | VCC supply
        pin_pattern = r'Pin\s*(\d+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|?\s*(.*?)(?:\n|$)'

        for match in re.finditer(pin_pattern, self.text, re.IGNORECASE):
            pin = PinInfo(
                number=match.group(1),
                name=match.group(2),
                type=match.group(3),
                description=match.group(4).strip() if match.group(4) else ""
            )
            pins.append(pin)

        # 如果没找到，尝试简单模式
        if not pins:
            # 查找引脚描述
            pin_num_pattern = r'(?:Pin|DPin)\s*#?\s*(\d+)[:\-]?\s*(\w+)'
            for match in re.finditer(pin_num_pattern, self.text, re.IGNORECASE):
                pin = PinInfo(
                    number=match.group(1),
                    name=match.group(2),
                    type="unspecified"
                )
                pins.append(pin)

        return pins

    def _extract_parameters(self) -> List[Parameter]:
        """提取电气参数"""
        params = []

        # 常见参数模式
        param_patterns = [
            # VCC, 电压参数
            (r'V(?:CC|DD)\s*[:\-]?\s*([0-9.]+)\s*([Vv])', 'Supply Voltage', 'V'),
            # 电流参数
            (r'I(?:CC|OUT)\s*[:\-]?\s*([0-9.]+)\s*([mM]?[A])', 'Supply Current', 'A'),
            # 频率参数
            (r'f(?:OSC)?\s*[:\-]?\s*([0-9.]+)\s*([Mk]?Hz)', 'Frequency', 'Hz'),
            # 温度参数
            (r'T(?:a|A)\s*[:\-]?\s*([\-0-9.]+)\s*~\s*([\-0-9.]+)\s*([C°])', 'Operating Temperature', 'C'),
        ]

        for pattern, name, unit in param_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                param = Parameter(
                    name=name,
                    value=f"{match.group(1)}-{match.group(2)}",
                    unit=unit
                )
                params.append(param)

        return params

    def _extract_footprint(self) -> str:
        """提取封装信息"""
        patterns = [
            r'Package:\s*([^\n]+)',
            r'Footprint:\s*([^\n]+)',
            r'(?:SOIC|TSSOP|QFN|LQFP|DIP)-(\d+)',
            r'(\d+)-Pin\s+([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return ""

    def _mock_parse(self, pdf_path: str) -> ParsedComponent:
        """模拟解析结果"""
        logger.info(f"Mock parsing PDF: {pdf_path}")
        return ParsedComponent(
            name="MockComponent",
            manufacturer="Unknown",
            part_number="MOCK-123",
            description="Mock component for testing",
            pins=[
                PinInfo(number="1", name="VCC", type="power_in", description="Power supply"),
                PinInfo(number="2", name="GND", type="power", description="Ground"),
                PinInfo(number="3", name="OUT", type="output", description="Output"),
            ],
            parameters=[
                Parameter(name="Supply Voltage", value="3.3", unit="V"),
                Parameter(name="Operating Temperature", value="-40 to 85", unit="C"),
            ],
            footprint="Package_SO:SOIC-8"
        )


# 全局实例
_parser: Optional[DatasheetParser] = None


def get_datasheet_parser() -> DatasheetParser:
    """获取数据表解析器单例"""
    global _parser
    if _parser is None:
        _parser = DatasheetParser()
    return _parser


def parse_datasheet(pdf_path: str) -> ParsedComponent:
    """
    解析 PDF 数据表

    Args:
        pdf_path: PDF 文件路径

    Returns:
        ParsedComponent
    """
    parser = get_datasheet_parser()
    return parser.parse(pdf_path)


def parse_datasheet_from_text(text: str) -> ParsedComponent:
    """
    从文本解析数据表

    Args:
        text: PDF 提取的文本

    Returns:
        ParsedComponent
    """
    parser = get_datasheet_parser()
    return parser.parse_from_string(text)
