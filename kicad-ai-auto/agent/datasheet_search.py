"""
Datasheet搜索服务 - 为未知芯片搜索datasheet

功能:
1. 搜索芯片的datasheet
2. 从搜索结果中提取datasheet链接
3. 提供PDF下载或在线查看
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class DatasheetResult:
    """Datasheet搜索结果"""

    chip_name: str
    title: str
    manufacturer: str
    url: str
    source: str  # "digikey", "mouser", "octopart", "google"
    pdf_url: Optional[str] = None
    description: Optional[str] = None


class DatasheetSearcher:
    """Datasheet搜索引擎"""

    # 常用的电子元件搜索引擎
    SEARCH_URLS = {
        "google": "https://www.google.com/search?q={query}+datasheet+filetype:pdf",
        "digikey": "https://www.digikey.com/en/products?keywords={query}",
        "mouser": "https://www.mouser.com/c/?q={query}",
        "octopart": "https://octopart.com/search?q={query}",
        "lcsc": "https://www.lcsc.com/search?query={query}",
    }

    # 常用的datasheet网站
    DATASHEET_SITES = [
        "datasheets.com",
        "datasheet4u.com",
        "datasheetcafe.com",
        "alldatasheet.com",
        "pdf.nocue.com",
    ]

    def __init__(self):
        """初始化搜索器"""
        self.cache: Dict[str, List[DatasheetResult]] = {}

    def search(self, chip_name: str, use_web: bool = False) -> List[DatasheetResult]:
        """
        搜索芯片的datasheet

        Args:
            chip_name: 芯片名称
            use_web: 是否使用网络搜索(需要配置API)

        Returns:
            datasheet搜索结果列表
        """
        # 检查缓存
        if chip_name in self.cache:
            logger.info(f"使用缓存的datasheet搜索结果: {chip_name}")
            return self.cache[chip_name]

        results = []

        # 1. 首先检查本地知识库
        from chip_quality_validator import get_validator

        validator = get_validator()
        chip_info = validator.get_chip_info(chip_name)

        if chip_info and chip_info.get("datasheet_url"):
            results.append(
                DatasheetResult(
                    chip_name=chip_name,
                    title=f"{chip_name} Datasheet",
                    manufacturer=chip_info.get("manufacturer", "Unknown"),
                    url=chip_info.get("datasheet_url", ""),
                    source="knowledge_base",
                    description=chip_info.get("description", ""),
                )
            )
            self.cache[chip_name] = results
            return results

        # 2. 尝试从本地数据库模糊匹配
        search_results = validator.search_chips(chip_name)
        for sr in search_results:
            if sr.get("datasheet_url"):
                results.append(
                    DatasheetResult(
                        chip_name=sr["name"],
                        title=f"{sr['name']} Datasheet",
                        manufacturer=sr.get("manufacturer", "Unknown"),
                        url=sr.get("datasheet_url", ""),
                        source="knowledge_base_fuzzy",
                        description=sr.get("description", ""),
                    )
                )

        # 3. 如果use_web=True，使用网络搜索
        if use_web:
            web_results = self._web_search(chip_name)
            results.extend(web_results)

        # 缓存结果
        self.cache[chip_name] = results
        return results

    def _web_search(self, chip_name: str) -> List[DatasheetResult]:
        """网络搜索datasheet"""
        results = []

        try:
            # 使用exa_web_search_exa搜索(如果可用)
            try:
                from exa_web_search_exa import exa_web_search_exa

                search_results = exa_web_search_exa(
                    numResults=5, query=f"{chip_name} datasheet PDF"
                )

                for result in search_results:
                    results.append(
                        DatasheetResult(
                            chip_name=chip_name,
                            title=result.get("title", ""),
                            manufacturer=self._extract_manufacturer(
                                result.get("title", "")
                            ),
                            url=result.get("url", ""),
                            source="web_search",
                            description=result.get("snippet", ""),
                        )
                    )
            except ImportError:
                # exa_web_search_exa not available
                logger.info("网络搜索功能不可用(exa_web_search_exa)")

        except Exception as e:
            logger.warning(f"网络搜索失败: {e}")

        return results

    def _extract_manufacturer(self, title: str) -> str:
        """从标题提取制造商"""
        manufacturers = [
            "STMicroelectronics",
            "TI",
            "Texas Instruments",
            "Microchip",
            "Nordic",
            "NXP",
            "Infineon",
            "Maxim",
            "Analog Devices",
            "Renesas",
            "Espressif",
            "Raspberry Pi",
            "WCH",
            "GigaDevice",
            "Bosch",
            "Vishay",
            "Melexis",
            "AMS",
            "Allegro",
        ]

        title_upper = title.upper()
        for mfr in manufacturers:
            if mfr.upper() in title_upper:
                return mfr

        return "Unknown"

    def get_datasheet_url(self, chip_name: str) -> Optional[str]:
        """获取datasheet的直接链接"""
        results = self.search(chip_name)

        if not results:
            return None

        # 优先返回第一个有效结果
        for r in results:
            if r.url:
                return r.url

        return None

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()


# 全局搜索器
_searcher: Optional[DatasheetSearcher] = None


def get_datasheet_searcher() -> DatasheetSearcher:
    """获取搜索器单例"""
    global _searcher
    if _searcher is None:
        _searcher = DatasheetSearcher()
    return _searcher


def search_datasheet(chip_name: str, use_web: bool = False) -> List[DatasheetResult]:
    """搜索datasheet"""
    return get_datasheet_searcher().search(chip_name, use_web)


def get_datasheet_url(chip_name: str) -> Optional[str]:
    """获取datasheet链接"""
    return get_datasheet_searcher().get_datasheet_url(chip_name)
