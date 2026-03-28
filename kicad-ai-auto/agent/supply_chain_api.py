"""
元件供应链查询服务 - 查询元件供货状态和价格

功能:
1. 查询DigiKey库存和价格
2. 查询Mouser库存和价格
3. 查询LCSC库存和价格
4. 提供替代料建议
5. 供货状态预警
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class PartInfo:
    """元件信息"""

    part_number: str
    manufacturer: str
    description: str
    stock: int
    price: float
    currency: str = "USD"
    lead_time: Optional[str] = None
    status: str = "unknown"  # "in_stock", "low_stock", "out_of_stock", "obsolete"
    source: str = ""  # "digikey", "mouser", "lcsc"
    alternatives: Optional[List[str]] = None

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


@dataclass
class SupplyChainReport:
    """供应链报告"""

    chip_name: str
    parts: List[PartInfo]
    best_price: Optional[PartInfo] = None
    in_stock_count: int = 0
    total_suppliers: int = 0

    def __post_init__(self):
        if self.parts:
            self.total_suppliers = len(self.parts)
            in_stock = [p for p in self.parts if p.stock > 0]
            self.in_stock_count = len(in_stock)
            if in_stock:
                # 找最便宜的
                self.best_price = min(in_stock, key=lambda x: x.price)


class SupplyChainAPI:
    """供应链API集成"""

    # API密钥(需要从环境变量或配置文件获取)
    DIGIKEY_API_KEY = os.environ.get("DIGIKEY_API_KEY", "")
    MOUSER_API_KEY = os.environ.get("MOUSER_API_KEY", "")

    def __init__(self):
        """初始化"""
        self.cache: Dict[str, SupplyChainReport] = {}
        self.cache_ttl = 3600  # 缓存1小时

    def search(self, chip_name: str) -> SupplyChainReport:
        """
        搜索元件供货情况

        Args:
            chip_name: 芯片名称

        Returns:
            供应链报告
        """
        # 检查缓存
        if chip_name in self.cache:
            logger.info(f"使用缓存的供应链信息: {chip_name}")
            return self.cache[chip_name]

        parts = []

        # 1. 先从本地知识库获取替代芯片
        from chip_quality_validator import get_validator

        validator = get_validator()
        chip_info = validator.get_chip_info(chip_name)

        if chip_info:
            alternatives = chip_info.get("alternative_chips", [])
            # 添加主芯片
            parts.append(
                PartInfo(
                    part_number=chip_name,
                    manufacturer=chip_info.get("manufacturer", "Unknown"),
                    description=chip_info.get("description", ""),
                    stock=-1,  # 未知
                    price=-1,  # 未知
                    currency="USD",
                    status="unknown",
                    source="knowledge_base",
                    alternatives=alternatives,
                )
            )

        # 2. 尝试从外部API获取真实价格(需要API Key)
        if self.DIGIKEY_API_KEY:
            dk_parts = self._search_digikey(chip_name)
            parts.extend(dk_parts)

        if self.MOUSER_API_KEY:
            mo_parts = self._search_mouser(chip_name)
            parts.extend(mo_parts)

        # 3. 尝试从LCSC获取(免费API)
        lcsc_parts = self._search_lcsc(chip_name)
        parts.extend(lcsc_parts)

        report = SupplyChainReport(chip_name=chip_name, parts=parts)

        # 缓存结果
        self.cache[chip_name] = report

        return report

    def _search_digikey(self, chip_name: str) -> List[PartInfo]:
        """搜索DigiKey"""
        # DigiKey API需要付费订阅,这里提供接口框架
        # 实际使用时需要申请API Key
        logger.info(f"搜索DigiKey: {chip_name}")

        # 模拟返回(实际需要API调用)
        # try:
        #     response = requests.get(
        #         'https://api.digikey.com/products/v4/search',
        #         headers={'X-DIGIKEY-Client-Id': self.DIGIKEY_API_KEY},
        #         params={'keywords': chip_name}
        #     )
        #     ...
        # except Exception as e:
        #     logger.warning(f"DigiKey API调用失败: {e}")

        return []

    def _search_mouser(self, chip_name: str) -> List[PartInfo]:
        """搜索Mouser"""
        # Mouser API需要API Key
        logger.info(f"搜索Mouser: {chip_name}")
        return []

    def _search_lcsc(self, chip_name: str) -> List[PartInfo]:
        """搜索LCSC"""
        # LCSC有免费API,这里提供接口
        logger.info(f"搜索LCSC: {chip_name}")

        # 实际实现需要调用LCSC API
        # 这里返回模拟数据作为示例
        parts = []

        # 模拟从LCSC返回数据
        # 实际项目中可以替换为真实API调用
        common_chips = {
            "STM32F103C8T6": {"stock": 12500, "price": 3.85, "vendor": "LCSC"},
            "ESP32-WROOM-32": {"stock": 8300, "price": 2.15, "vendor": "LCSC"},
            "AMS1117-3.3": {"stock": 50000, "price": 0.12, "vendor": "LCSC"},
            "CH340G": {"stock": 45000, "price": 0.35, "vendor": "LCSC"},
            "CP2102": {"stock": 28000, "price": 1.20, "vendor": "LCSC"},
        }

        if chip_name in common_chips:
            info = common_chips[chip_name]
            status = "in_stock" if info["stock"] > 1000 else "low_stock"
            parts.append(
                PartInfo(
                    part_number=chip_name,
                    manufacturer="Various",
                    description=f"chip: {chip_name}",
                    stock=info["stock"],
                    price=info["price"],
                    currency="CNY",
                    status=status,
                    source="lcsc",
                )
            )

        return parts

    def get_alternatives(self, chip_name: str) -> List[str]:
        """获取替代料建议"""
        from chip_quality_validator import get_validator

        validator = get_validator()

        chip_info = validator.get_chip_info(chip_name)
        if chip_info and chip_info.get("alternative_chips"):
            return chip_info["alternative_chips"]

        # 尝试搜索同类别芯片
        search_results = validator.search_chips(chip_name)
        alternatives = []
        for sr in search_results[:5]:
            if sr["name"] != chip_name:
                alternatives.append(sr["name"])

        return alternatives

    def check_availability(self, chip_name: str) -> Dict[str, Any]:
        """检查供货可用性"""
        report = self.search(chip_name)

        result = {
            "chip_name": chip_name,
            "available": report.in_stock_count > 0,
            "supplier_count": report.total_suppliers,
            "in_stock_count": report.in_stock_count,
            "best_price": None,
            "warnings": [],
        }

        if report.best_price:
            result["best_price"] = {
                "price": report.best_price.price,
                "currency": report.best_price.currency,
                "stock": report.best_price.stock,
                "source": report.best_price.source,
            }

        # 生成警告
        if report.in_stock_count == 0:
            result["warnings"].append(f"⚠️ {chip_name} 当前所有渠道缺货!")
            result["warnings"].append("建议考虑替代芯片或等待供货")
        elif report.in_stock_count < 3:
            result["warnings"].append(
                f"⚠️ {chip_name} 仅有 {report.in_stock_count} 个供应商有货"
            )

        # 检查是否在知识库中
        from chip_quality_validator import get_validator

        validator = get_validator()
        chip_info = validator.get_chip_info(chip_name)
        if not chip_info:
            result["warnings"].append(f"⚠️ {chip_name} 不在知识库中,建议添加")

        return result

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()


# 全局实例
_supply_chain: Optional[SupplyChainAPI] = None


def get_supply_chain() -> SupplyChainAPI:
    """获取供应链API实例"""
    global _supply_chain
    if _supply_chain is None:
        _supply_chain = SupplyChainAPI()
    return _supply_chain


def check_availability(chip_name: str) -> Dict[str, Any]:
    """检查元件可用性"""
    return get_supply_chain().check_availability(chip_name)


def get_alternatives(chip_name: str) -> List[str]:
    """获取替代料"""
    return get_supply_chain().get_alternatives(chip_name)
