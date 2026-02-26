"""
芯片资料质量检查服务
检查芯片的datasheet、原理图符号、PCB封装等资料的完整性
"""

import logging
import os
import glob
import json
import hashlib
import asyncio
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path

import httpx
import aiofiles

logger = logging.getLogger(__name__)


class DataSeverity(Enum):
    """数据缺失严重级别"""

    BLOCKER = "blocker"  # 阻断：无法继续设计
    WARNING = "warning"  # 警告：风险提示
    INFO = "info"  # 信息：建议查看


@dataclass
class MissingItem:
    """缺失资料项"""

    data_type: str
    severity: DataSeverity
    message: str
    search_url: str
    upload_enabled: bool = True
    alternatives: List[str] = field(default_factory=list)


@dataclass
class ChipDataScore:
    """芯片资料完整度评分"""

    chip_name: str
    chip_full_name: str = ""
    manufacturer: str = ""

    # 各项资料评分 (0-100)
    datasheet_score: int = 0
    symbol_score: int = 0
    footprint_score: int = 0
    reference_score: int = 0
    price_score: int = 0
    application_note_score: int = 0

    # 缺失项清单
    missing_items: List[MissingItem] = field(default_factory=list)

    # 缓存路径
    cache_dir: str = "./cache"

    def __post_init__(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    @property
    def total_score(self) -> int:
        """计算总评分"""
        return int(
            self.datasheet_score * 0.25
            + self.symbol_score * 0.15
            + self.footprint_score * 0.20
            + self.reference_score * 0.10
            + self.price_score * 0.15
            + self.application_note_score * 0.15
        )

    @property
    def can_proceed(self) -> bool:
        """是否可以继续设计"""
        return not any(
            item.severity == DataSeverity.BLOCKER for item in self.missing_items
        )

    @property
    def has_blockers(self) -> bool:
        """是否有阻断级问题"""
        return any(item.severity == DataSeverity.BLOCKER for item in self.missing_items)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chip_name": self.chip_name,
            "chip_full_name": self.chip_full_name,
            "manufacturer": self.manufacturer,
            "total_score": self.total_score,
            "can_proceed": self.can_proceed,
            "has_blockers": self.has_blockers,
            "scores": {
                "datasheet": self.datasheet_score,
                "symbol": self.symbol_score,
                "footprint": self.footprint_score,
                "reference": self.reference_score,
                "price": self.price_score,
                "application_note": self.application_note_score,
            },
            "missing_items": [
                {
                    "type": item.data_type,
                    "severity": item.severity.value,
                    "message": item.message,
                    "search_url": item.search_url,
                    "upload_enabled": item.upload_enabled,
                    "alternatives": item.alternatives,
                }
                for item in self.missing_items
            ],
        }


class ChipDataChecker:
    """芯片资料完整性检查器"""

    # 外部数据源搜索URL
    SEARCH_SOURCES = {
        "datasheet": {
            "alldatasheet": "https://www.alldatasheet.com/search.jsp?searchwords={}",
            "datasheetpdf": "https://www.datasheetpdf.com/{}",
            " lcsc": "https://www.lcsc.com/products/{}",
        },
        "symbol": {
            "samacsys": "https://www.samacsys.com/kicad-library-loader/",
            "kicad": "https://kicad.org/libraries/",
        },
        "footprint": {
            "ultralibrarian": "https://www.ultralibrarian.com/",
            "samacsys": "https://www.samacsys.com/kicad-library-loader/",
            "kicad": "https://kicad.org/libraries/",
        },
        "price": {
            "digikey": "https://www.digikey.com/",
            "mouser": "https://www.mouser.cn/",
            "lcsc": "https://www.lcsc.com/",
        },
    }

    # 常用芯片替代关系
    CHIP_ALTERNATIVES = {
        "STM32F103C8T6": ["GD32F103C8T6", "N76E003", "CH32F103"],
        "AMS1117-5V": ["LM1117-5V", "RT9080-5V", "BL1117-5V"],
        "LM7805": ["LM7805", "AMS7805", "MC7805"],
        "ESP32-WROOM-32": ["ESP32-WROOM-32E", "ESP32-S3", "ESP32-C3"],
        "CH340G": ["CH340E", "CP2102", "FT232RL"],
    }

    def __init__(self, kicad_library_path: str = "./kicad-libraries"):
        self.kicad_library_path = kicad_library_path
        self.cache_dir = "./cache"
        self.datasheet_cache = os.path.join(self.cache_dir, "datasheet")
        os.makedirs(self.datasheet_cache, exist_ok=True)

    async def check_chip(
        self, chip_name: str, full_name: str = "", manufacturer: str = ""
    ) -> ChipDataScore:
        """检查芯片资料完整度"""
        chip_name = chip_name.strip().upper()
        score = ChipDataScore(
            chip_name=chip_name,
            chip_full_name=full_name,
            manufacturer=manufacturer,
            cache_dir=self.cache_dir,
        )

        # 并行执行所有检查
        await asyncio.gather(
            self._check_datasheet(score),
            self._check_symbol(score),
            self._check_footprint(score),
            self._check_reference_design(score),
            self._check_price_availability(score),
            self._check_application_notes(score),
        )

        return score

    async def _check_datasheet(self, score: ChipDataScore) -> None:
        """检查datasheet"""
        chip_name = score.chip_name

        # 1. 检查本地缓存
        local_files = glob.glob(f"{self.datasheet_cache}/{chip_name}*.pdf")
        local_files.extend(glob.glob(f"{self.datasheet_cache}/*{chip_name}*.pdf"))

        if local_files:
            score.datasheet_score = 100
            return

        # 2. 尝试网络检查
        try:
            async with httpx.AsyncClient() as client:
                # 尝试访问LCSC API
                response = await client.get(
                    f"https://www.lcsc.com/api/product/search",
                    params={"keyword": chip_name},
                    timeout=10,
                )
                if response.status_code == 200:
                    score.datasheet_score = 80
                    score.missing_items.append(
                        MissingItem(
                            data_type="datasheet",
                            severity=DataSeverity.BLOCKER,
                            message=f"缺少 {chip_name} 的数据手册 (datasheet)。Datasheet是芯片选型的核心依据，包含电气参数、封装尺寸等关键信息。",
                            search_url=self.SEARCH_SOURCES["datasheet"]["lcsc"].format(
                                chip_name
                            ),
                            upload_enabled=True,
                            alternatives=self.CHIP_ALTERNATIVES.get(chip_name, []),
                        )
                    )
                    return
        except Exception:
            pass

        # 未找到
        score.datasheet_score = 0
        score.missing_items.append(
            MissingItem(
                data_type="datasheet",
                severity=DataSeverity.BLOCKER,
                message=f"缺少 {chip_name} 的数据手册 (datasheet)。这是最关键的缺失，无法验证芯片参数。",
                search_url=self.SEARCH_SOURCES["datasheet"]["alldatasheet"].format(
                    chip_name
                ),
                upload_enabled=True,
                alternatives=self.CHIP_ALTERNATIVES.get(chip_name, []),
            )
        )

    def _check_symbol(self, score: ChipDataScore) -> None:
        """检查原理图符号"""
        chip_name = score.chip_name

        # 1. 检查本地KiCad符号库
        if os.path.exists(self.kicad_library_path):
            symbol_patterns = [
                f"{self.kicad_library_path}/symbols/{chip_name}.kicad_sym",
                f"{self.kicad_library_path}/symbols/*/{chip_name}.kicad_sym",
            ]
            for pattern in symbol_patterns:
                if glob.glob(pattern):
                    score.symbol_score = 100
                    return

        # 2. 检查缓存
        symbol_cache = os.path.join(self.cache_dir, "symbols")
        if os.path.exists(symbol_cache):
            cached = glob.glob(f"{symbol_cache}/*{chip_name}*")
            if cached:
                score.symbol_score = 80
                return

        # 未找到
        score.symbol_score = 0
        score.missing_items.append(
            MissingItem(
                data_type="symbol",
                severity=DataSeverity.BLOCKER,
                message=f"缺少 {chip_name} 的原理图符号，无法在原理图中使用。",
                search_url=self.SEARCH_SOURCES["symbol"]["samacsys"],
                upload_enabled=True,
                alternatives=[],
            )
        )

    def _check_footprint(self, score: ChipDataScore) -> None:
        """检查PCB封装"""
        chip_name = score.chip_name

        # 1. 检查本地KiCad封装库
        if os.path.exists(self.kicad_library_path):
            footprint_patterns = [
                f"{self.kicad_library_path}/footprints/{chip_name}.kicad_mod",
                f"{self.kicad_library_path}/footprints/*/{chip_name}.kicad_mod",
                f"{self.kicad_library_path}/footprints/*/*/{chip_name}.kicad_mod",
            ]
            for pattern in footprint_patterns:
                if glob.glob(pattern):
                    score.footprint_score = 100
                    return

        # 2. 检查常见封装
        common_footprints = self._get_common_footprints(chip_name)
        if common_footprints:
            score.footprint_score = 60
            score.missing_items.append(
                MissingItem(
                    data_type="footprint",
                    severity=DataSeverity.WARNING,
                    message=f"未找到 {chip_name} 专用封装，但系统有常见封装: {', '.join(common_footprints[:3])}",
                    search_url=self.SEARCH_SOURCES["footprint"]["ultralibrarian"],
                    upload_enabled=True,
                    alternatives=[],
                )
            )
            return

        # 未找到
        score.footprint_score = 0
        score.missing_items.append(
            MissingItem(
                data_type="footprint",
                severity=DataSeverity.BLOCKER,
                message=f"缺少 {chip_name} 的PCB封装，无法进行PCB布局。",
                search_url=self.SEARCH_SOURCES["footprint"]["ultralibrarian"],
                upload_enabled=True,
                alternatives=[],
            )
        )

    def _get_common_footprints(self, chip_name: str) -> List[str]:
        """获取常见封装列表"""
        common = {
            "STM32": ["LQFP-48", "LQFP-64", "VFQFPN-32"],
            "AMS1117": ["SOT-223", "SOT-89"],
            "ESP32": ["Module", "QFN-48"],
            "CH340": ["SOP-16", "ESSOP-10"],
            "LM7805": ["TO-220", "TO-263"],
            "NE555": ["DIP-8", "SOIC-8"],
        }
        for key, footprints in common.items():
            if key in chip_name:
                return footprints
        return []

    async def _check_reference_design(self, score: ChipDataScore) -> None:
        """检查参考设计"""
        chip_name = score.chip_name

        # 检查本地参考设计
        ref_dir = os.path.join(self.cache_dir, "reference")
        if os.path.exists(ref_dir):
            refs = glob.glob(f"{ref_dir}/*{chip_name}*")
            if refs:
                score.reference_score = 100
                return

        # 尝试网络搜索
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://www.google.com/search",
                    params={"q": f"{chip_name} reference design PCB"},
                    timeout=10,
                )
                if response.status_code == 200:
                    score.reference_score = 50
                    score.missing_items.append(
                        MissingItem(
                            data_type="reference",
                            severity=DataSeverity.INFO,
                            message=f"未找到本地参考设计，可以使用搜索引擎查找。",
                            search_url=f"https://www.google.com/search?q={chip_name}+reference+design",
                            upload_enabled=False,
                            alternatives=[],
                        )
                    )
                    return
        except Exception as e:
            logger.warning(f"检查本地参考设计时出错: {e}")

        score.reference_score = 0
        score.missing_items.append(
            MissingItem(
                data_type="reference",
                severity=DataSeverity.INFO,
                message=f"未找到 {chip_name} 的参考设计。参考设计可大幅提高设计质量和效率。",
                search_url=f"https://www.google.com/search?q={chip_name}+reference+design+KiCad",
                upload_enabled=False,
                alternatives=[],
            )
        )

    async def _check_price_availability(self, score: ChipDataScore) -> None:
        """检查价格和供货情况"""
        chip_name = score.chip_name

        # 模拟价格检查（实际应该调用电商API）
        try:
            async with httpx.AsyncClient() as client:
                # 尝试访问LCSC
                response = await client.get(
                    f"https://www.lcsc.com/search?keyword={chip_name}", timeout=10
                )
                if response.status_code == 200:
                    # 假设有货
                    score.price_score = 80
                    return
        except httpx.TimeoutException:
            logger.warning(f"检查 {chip_name} 价格超时")
        except httpx.RequestError as e:
            logger.warning(f"检查 {chip_name} 价格失败: {e}")
        except Exception as e:
            logger.warning(f"检查 {chip_name} 价格时出错: {e}")

        # 无法确定，标记为警告
        score.price_score = 50
        score.missing_items.append(
            MissingItem(
                data_type="price",
                severity=DataSeverity.WARNING,
                message=f"无法确认 {chip_name} 的供货情况。建议在购买前确认库存和价格。",
                search_url=self.SEARCH_SOURCES["price"]["digikey"],
                upload_enabled=False,
                alternatives=self.CHIP_ALTERNATIVES.get(chip_name, []),
            )
        )

    async def _check_application_notes(self, score: ChipDataScore) -> None:
        """检查应用笔记"""
        chip_name = score.chip_name

        # 应用笔记检查
        score.application_note_score = 50  # 默认50分
        score.missing_items.append(
            MissingItem(
                data_type="application_note",
                severity=DataSeverity.INFO,
                message=f"建议查看 {chip_name} 的应用笔记(AN)以获得更好的设计指导。",
                search_url=f"https://www.google.com/search?q={chip_name}+application+note+pdf",
                upload_enabled=False,
                alternatives=[],
            )
        )

    async def upload_datasheet(
        self, chip_name: str, file_content: bytes, filename: str
    ) -> bool:
        """上传并缓存datasheet"""
        chip_name = chip_name.strip().upper()

        # 生成唯一文件名
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        safe_name = "".join(c for c in chip_name if c.isalnum())
        if not safe_name:
            safe_name = "unknown"
        save_filename = f"{safe_name}_{file_hash}.pdf"
        save_path = os.path.join(self.datasheet_cache, save_filename)

        # 验证路径仍在预期目录内（防止目录遍历攻击）
        real_save_path = os.path.realpath(save_path)
        real_cache_dir = os.path.realpath(self.datasheet_cache)
        if not real_save_path.startswith(real_cache_dir + os.sep):
            # 使用 repr() 防止日志注入攻击
            logger.error(f"Path traversal attempt detected: {repr(save_path)}")
            return False

        try:
            async with aiofiles.open(save_path, "wb") as f:
                await f.write(file_content)
            return True
        except Exception as e:
            logger.error(f"Error saving datasheet: {e}")
            return False

    async def check_multiple_chips(
        self, chips: List[Dict[str, str]]
    ) -> List[ChipDataScore]:
        """批量检查多个芯片"""
        tasks = [
            self.check_chip(
                chip.get("name", ""),
                chip.get("full_name", ""),
                chip.get("manufacturer", ""),
            )
            for chip in chips
        ]
        return await asyncio.gather(*tasks)


# 全局实例 - 线程安全版本
_chip_checker: Optional[ChipDataChecker] = None
_chip_checker_lock = threading.Lock()


def get_chip_checker() -> ChipDataChecker:
    """获取芯片检查器实例 - 线程安全版本"""
    global _chip_checker
    if _chip_checker is None:
        with _chip_checker_lock:
            # 双重检查锁定
            if _chip_checker is None:
                _chip_checker = ChipDataChecker()
    return _chip_checker


def reset_chip_checker():
    """重置芯片检查器（用于测试）"""
    global _chip_checker
    with _chip_checker_lock:
        _chip_checker = None
