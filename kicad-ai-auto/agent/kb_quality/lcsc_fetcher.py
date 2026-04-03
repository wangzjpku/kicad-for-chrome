# -*- coding: utf-8 -*-
"""
LCSC API 元件数据获取器

从 LCSC (LCEDA) API 获取元件数据，用于知识库数据校验和自动填充。
API 文档: https://www.lcsc.com/api/v1/products

注意: LCSC API 可能需要认证 Token，请设置 LCSC_API_KEY 环境变量。
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class LCSCChip:
    """LCSC 元件数据"""

    part_number: str
    manufacturer: str
    description: str
    package: str               # 封装
    datasheet_url: str
    stock: int = 0
    price: float = 0.0
    product_url: str = ""
    # 扩展字段
    sweep_status: str = ""
    brand: str = ""
    series: str = ""
    category: str = ""


class LcscFetcher:
    """
    LCSC API 元件数据获取器。

    使用方法:
        # 方式1: 使用环境变量 LCSC_API_KEY
        import os
        os.environ["LCSC_API_KEY"] = "<your-api-key>"
        fetcher = LcscFetcher()

        # 方式2: 直接传入API Key
        fetcher = LcscFetcher(api_key=os.environ.get("LCSC_API_KEY"))

        chip = fetcher.fetch_component("C204471")
        print(chip.datasheet_url)

        # 批量同步
        fetcher.batch_sync(["C204471", "C26290"], "component_db.json")
    """

    BASE_URL = "https://www.lcsc.com/api/v1"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 10.0):
        """
        Args:
            api_key: LCSC API Key (或设置 LCSC_API_KEY 环境变量)
            timeout: 请求超时时间（秒）
        """
        self._api_key = api_key or os.environ.get("LCSC_API_KEY", "")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "KiCad-AutoPCB/kb_quality",
        })
        if self._api_key:
            self._session.headers["Authorization"] = f"Bearer {self._api_key}"

    def fetch_component(self, part_number: str) -> Optional[LCSCChip]:
        """
        获取单个元件数据。

        Args:
            part_number: LCSC 元件编号 (如 "C204471")

        Returns:
            LCSCChip 或 None (未找到或请求失败)
        """
        try:
            resp = self._session.get(
                f"{self.BASE_URL}/products/{part_number}",
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"LCSC API request failed for {part_number}: {e}")
            return None

        if resp.status_code == 404:
            logger.debug(f"LCSC part not found: {part_number}")
            return None

        if resp.status_code != 200:
            logger.warning(f"LCSC API error {resp.status_code}: {resp.text[:200]}")
            return None

        try:
            data = resp.json()
            return self._parse_response(data, part_number)
        except Exception as e:
            logger.warning(f"Failed to parse LCSC response for {part_number}: {e}")
            return None

    def search_components(self, keyword: str, limit: int = 20) -> List[LCSCChip]:
        """
        搜索元件。

        Args:
            keyword: 搜索关键词（型号、描述等）
            limit: 返回结果上限

        Returns:
            LCSCChip 列表
        """
        try:
            resp = self._session.get(
                f"{self.BASE_URL}/products/search",
                params={"keyword": keyword, "page_size": limit},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"LCSC search failed for '{keyword}': {e}")
            return []

        if resp.status_code != 200:
            logger.warning(f"LCSC search error {resp.status_code}")
            return []

        try:
            results = resp.json()
            chips = []
            for item in results if isinstance(results, list) else results.get("data", []):
                try:
                    chip = self._parse_response(item, item.get("part_number", ""))
                    if chip:
                        chips.append(chip)
                except Exception:
                    continue
            return chips
        except Exception as e:
            logger.warning(f"Failed to parse LCSC search results: {e}")
            return []

    def batch_sync(
        self,
        part_numbers: List[str],
        db_path: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        批量同步元件数据到 component_db.json。

        Args:
            part_numbers: LCSC 元件编号列表
            db_path: component_db.json 路径
            dry_run: True=仅返回变更，False=直接写入

        Returns:
            包含 found/updated/skipped/not_found 统计的字典
        """
        import json
        from pathlib import Path

        found = 0
        not_found = []
        updated = 0
        skipped = 0
        updates: Dict[str, Dict[str, Any]] = {}

        for pn in part_numbers:
            chip = self.fetch_component(pn)
            if chip:
                found += 1
                update = {
                    "datasheet_url": chip.datasheet_url,
                    "manufacturer": chip.manufacturer,
                    "description": chip.description,
                    "footprint": chip.package,
                }
                update = {k: v for k, v in update.items() if v}
                if update:
                    updates[pn] = update
                    logger.info(f"LCSC {pn}: {list(update.keys())}")

                if not dry_run and db_path:
                    db_file = Path(db_path)
                    if db_file.exists():
                        with open(db_file, "r", encoding="utf-8") as f:
                            db = json.load(f)
                        comps = db.get("components", {})
                        matched = False
                        for name, comp in comps.items():
                            if comp.get("lcsc_part") == pn:
                                comps[name].update(update)
                                comps[name]["source"] = "lcsc"
                                updated += 1
                                matched = True
                        if matched:
                            with open(db_file, "w", encoding="utf-8") as f:
                                json.dump(db, f, ensure_ascii=False, indent=2)
                            logger.info(f"Updated component '{matched}' with LCSC data for {pn}")
                        else:
                            skipped += 1
            else:
                not_found.append(pn)
                skipped += 1

        if not dry_run and db_path:
            logger.info(f"LCSC batch sync complete: {found} found, {updated} updated, {skipped} skipped")

        return {
            "found": found,
            "not_found": not_found,
            "updated": updated,
            "skipped": skipped,
        }

    def _parse_response(self, data: Dict[str, Any], fallback_pn: str) -> Optional[LCSCChip]:
        """解析 LCSC API 响应"""
        try:
            pn = data.get("part_number", fallback_pn)
            if not pn:
                return None

            # 提取 datasheet URL (多个字段尝试)
            datasheet = (
                data.get("datasheet_url")
                or data.get("datasheet")
                or data.get("datasheet_link")
                or ""
            )
            if isinstance(datasheet, list) and datasheet:
                datasheet = datasheet[0]

            return LCSCChip(
                part_number=pn,
                manufacturer=data.get("manufacturer", ""),
                description=data.get("description", ""),
                package=data.get("package", data.get("package_type", "")),
                datasheet_url=datasheet,
                stock=int(data.get("stock", 0)),
                price=float(data.get("price", 0.0)),
                product_url=data.get("product_url", f"https://www.lcsc.com/product/{pn}.html"),
                sweep_status=data.get("sweep_status", ""),
                brand=data.get("brand", ""),
                series=data.get("series", ""),
                category=data.get("category", ""),
            )
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    def verify_connectivity(self) -> tuple:
        """验证 API 连接性，返回 (是否成功, 延迟ms)"""
        import time
        try:
            start = time.time()
            resp = self._session.get(
                f"{self.BASE_URL}/products/C204471",
                timeout=5.0,
            )
            latency = (time.time() - start) * 1000
            return (resp.status_code in (200, 404), latency)
        except requests.exceptions.RequestException:
            return (False, 0.0)
