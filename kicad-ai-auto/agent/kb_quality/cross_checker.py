# -*- coding: utf-8 -*-
"""
KiCad 库交叉验证器

负责与 KiCad 官方符号库/封装库进行交叉验证，
并将结果缓存到本地 JSON 文件以避免重复解析。
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

logger = logging.getLogger(__name__)

# 缓存文件路径
CACHE_DIR = Path(__file__).parent
SYMBOL_CACHE_PATH = CACHE_DIR / "symbol_cache.json"
FOOTPRINT_CACHE_PATH = CACHE_DIR / "footprint_cache.json"


class CrossChecker:
    """
    KiCad 符号/封装库交叉验证器。

    使用流程:
        1. 优先从本地 JSON 缓存读取（快速）
        2. 若缓存不存在，解析 KiCad 库并生成缓存
        3. 支持增量更新：仅新增/修改的符号

    复用组件:
        - symbol_lib_parser.py: KiCad .kicad_sym 解析
        - footprint_parser.py: KiCad .kicad_mod 解析
    """

    def __init__(self, kicad_symbols_path: Optional[str] = None,
                 kicad_footprints_path: Optional[str] = None):
        """
        Args:
            kicad_symbols_path: KiCad 符号库目录路径，默认从父目录的 kicad-symbols 读取
            kicad_footprints_path: KiCad 封装库目录路径
        """
        self._symbols_path = kicad_symbols_path
        self._footprints_path = kicad_footprints_path

        self._symbol_cache: Dict[str, Any] = {}
        self._footprint_cache: Dict[str, Any] = {}
        self._parser = None
        self._fp_parser = None

        self._load_caches()

    def _load_caches(self) -> None:
        """从磁盘加载缓存"""
        if SYMBOL_CACHE_PATH.exists():
            try:
                with open(SYMBOL_CACHE_PATH, "r", encoding="utf-8") as f:
                    self._symbol_cache = json.load(f)
                logger.info(f"Loaded symbol cache: {len(self._symbol_cache)} libraries")
            except Exception as e:
                logger.warning(f"Failed to load symbol cache: {e}")

        if FOOTPRINT_CACHE_PATH.exists():
            try:
                with open(FOOTPRINT_CACHE_PATH, "r", encoding="utf-8") as f:
                    self._footprint_cache = json.load(f)
                logger.info(f"Loaded footprint cache: {len(self._footprint_cache)} libraries")
            except Exception as e:
                logger.warning(f"Failed to load footprint cache: {e}")

    def save_caches(self) -> None:
        """保存缓存到磁盘"""
        try:
            with open(SYMBOL_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._symbol_cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved symbol cache to {SYMBOL_CACHE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save symbol cache: {e}")

        try:
            with open(FOOTPRINT_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._footprint_cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved footprint cache to {FOOTPRINT_CACHE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save footprint cache: {e}")

    # ─── 符号库 ────────────────────────────────────────────────

    def build_symbol_cache(self, force: bool = False) -> Dict[str, Any]:
        """
        解析 KiCad 符号库并生成缓存。

        复用 symbol_lib_parser.py 的解析逻辑。
        输出: {"Library_Name": {"Symbol_Name": {"pin_count": N, "pins": [...]}}}
        """
        if not force and self._symbol_cache:
            return self._symbol_cache

        try:
            from symbol_lib_parser import get_symbol_parser, SymbolLibParser
        except ImportError as e:
            logger.error(f"Cannot import symbol_lib_parser: {e}")
            return self._symbol_cache

        try:
            parser: SymbolLibParser = get_symbol_parser()
        except Exception as e:
            logger.error(f"Failed to create symbol parser: {e}")
            return self._symbol_cache

        cache: Dict[str, Any] = {}

        try:
            libs = parser.list_available_libraries()
            logger.info(f"Found {len(libs)} KiCad symbol libraries")
        except Exception as e:
            logger.error(f"Failed to list symbol libraries: {e}")
            return self._symbol_cache

        for lib_name in libs:
            lib_symbols: Dict[str, Any] = {}
            try:
                symbols = parser.get_library_symbols(lib_name)
                for sym in symbols:
                    if hasattr(sym, "pins"):
                        lib_symbols[sym.name] = {
                            "pin_count": len(sym.pins),
                            "pin_names": [p.name for p in sym.pins],
                            "pin_types": [p.pin_type for p in sym.pins],
                        }
            except Exception as e:
                logger.warning(f"Error parsing library {lib_name}: {e}")

            if lib_symbols:
                cache[lib_name] = lib_symbols

        self._symbol_cache = cache
        self.save_caches()
        logger.info(f"Built symbol cache: {len(cache)} libraries")
        return cache

    def symbol_exists(self, lib_name: str, symbol_name: str) -> Optional[bool]:
        """
        检查符号是否存在。

        Returns:
            True  = 存在
            False = 不存在
            None  = 缓存未命中（需先调用 build_symbol_cache）
        """
        if lib_name in self._symbol_cache:
            return symbol_name in self._symbol_cache[lib_name]
        return None

    def get_symbol_pin_count(self, lib_name: str, symbol_name: str) -> Optional[int]:
        """获取 KiCad 符号的引脚数"""
        if lib_name in self._symbol_cache:
            sym = self._symbol_cache[lib_name].get(symbol_name)
            if sym:
                return sym.get("pin_count")
        return None

    def list_available_symbol_libs(self) -> List[str]:
        """列出所有可用的符号库"""
        return list(self._symbol_cache.keys())

    # ─── 封装库 ────────────────────────────────────────────────

    def build_footprint_cache(self, force: bool = False) -> Dict[str, Any]:
        """
        解析 KiCad 封装库并生成缓存。

        输出: {"Library_Name": {"Footprint_Name": {"pads": N, "type": "smd/tht"}}}
        """
        if not force and self._footprint_cache:
            return self._footprint_cache

        try:
            from footprint_parser import get_footprint_data, find_footprint_file
        except ImportError as e:
            logger.error(f"Cannot import footprint_parser: {e}")
            return self._footprint_cache

        cache: Dict[str, Any] = {}

        # 从 symbol_cache 中提取 component_db 中所有用到的 footprint，
        # 然后逐个解析，避免全量扫描数百个封装库
        for lib_name, symbols in self._symbol_cache.items():
            pass  # footprint 缓存按需构建，不依赖 symbol_cache

        # 按需构建: 记录已知的 KiCad 封装库列表
        # 这些库来自 KiCad 官方封装库
        try:
            import footprint_parser
            fp_base = getattr(footprint_parser, 'KICAD_FOOTPRINTS', None)
            if fp_base:
                logger.info(f"KiCad footprints base: {fp_base}")
        except Exception as e:
            logger.debug(f"Could not determine footprints base: {e}")

        # 使用 on-demand 方式: 每次 footprint_exists 查询时缓存
        # 先从已知的官方库目录扫描一次
        known_libs = [
            "Package_QFP", "Package_SO", "Package_DFN", "Package_SSOP",
            "Package_TSSOP", "Package_DIP", "Package_TO_SOT_SMD", "Package_TO_SOT_THT",
            "LED_SMD", "LED_THT", "Connector_USB", "Connector", "RF_Module",
            "Driver_Motor", "Sensor", "Clock", "Oscillator",
        ]

        for lib_name in known_libs:
            lib_footprints: Dict[str, Any] = {}
            try:
                # 尝试解析几个知名封装来测试库是否可用
                test_fps = []
                if lib_name == "Package_QFP":
                    test_fps = ["LQFP-48_7x7mm_P0.5mm", "LQFP-64_10x10mm_P0.5mm"]
                elif lib_name == "Package_SO":
                    test_fps = ["SOIC-8_3.9x4.9mm_P1.27mm", "SOIC-16_3.9x9.9mm_P1.27mm"]
                elif lib_name == "Package_DFN":
                    test_fps = ["QFN-24_4x4mm_P0.5mm", "UFQFPN-48_7x7mm_P0.5mm"]
                elif lib_name == "Package_TO_SOT_SMD":
                    test_fps = ["SOT-23", "SOT-223"]
                elif lib_name == "Connector_USB":
                    test_fps = ["USB_C_Receptacle", "USB_Micro-B"]
                elif lib_name == "RF_Module":
                    test_fps = ["ESP32-WROOM-32", "ESP-12F"]
                elif lib_name == "LED_SMD":
                    test_fps = ["LED_0603_1608Metric"]

                for fp_name in test_fps:
                    full_name = f"{lib_name}:{fp_name}"
                    fp_data = get_footprint_data(full_name)
                    if fp_data:
                        pads = fp_data.get("pads", [])
                        lib_footprints[fp_name] = {
                            "pads": len(pads),
                            "type": self._detect_footprint_type(pads),
                        }
            except Exception as e:
                logger.debug(f"Error scanning footprint library {lib_name}: {e}")

            if lib_footprints:
                cache[lib_name] = lib_footprints

        self._footprint_cache = cache
        self.save_caches()
        logger.info(f"Built footprint cache: {len(cache)} libraries")
        return cache

    def _detect_footprint_type(self, pads: List[Dict]) -> str:
        """根据焊盘类型判断是 SMD 还是 THT"""
        if not pads:
            return "unknown"
        smd_count = sum(1 for p in pads if p.get("type", "").lower() == "smd")
        tht_count = sum(1 for p in pads if p.get("type", "").lower() == "thru_hole")
        if smd_count > tht_count:
            return "smd"
        elif tht_count > smd_count:
            return "tht"
        return "mixed"

    def footprint_exists(self, footprint: str) -> Optional[bool]:
        """
        检查封装是否存在。

        footprint 格式: "Library:Footprint" 或 "Footprint"

        Returns:
            True  = 存在
            False = 不存在
            None  = 无法判断
        """
        # 先在缓存中查找
        if ":" in footprint:
            lib, name = footprint.split(":", 1)
            if lib in self._footprint_cache and name in self._footprint_cache[lib]:
                return True
            # 缓存未命中，尝试按需解析
            try:
                from footprint_parser import get_footprint_data
                fp_data = get_footprint_data(footprint)
                if fp_data:
                    # 存入缓存
                    self._footprint_cache.setdefault(lib, {})[name] = {
                        "pads": len(fp_data.get("pads", [])),
                        "type": self._detect_footprint_type(fp_data.get("pads", [])),
                    }
                    return True
            except Exception as e:
                logger.debug(f"解析KiCad封装数据失败 (lib={lib}, name={name}): {e}")
            return False
        else:
            for lib, fps in self._footprint_cache.items():
                if footprint in fps:
                    return True
            return False

    def list_available_footprint_libs(self) -> List[str]:
        """列出所有可用的封装库"""
        return list(self._footprint_cache.keys())

    # ─── 三角验证 ───────────────────────────────────────────────

    def triangle_validate(
        self,
        component: Dict[str, Any],
        name: str,
    ) -> Dict[str, Any]:
        """
        三角验证: Schematic Symbol ↔ component_db Pins ↔ PCB Footprint Pads

        检查引脚数在三个维度上是否一致。
        """
        result = {
            "component": name,
            "symbol_checked": False,
            "footprint_checked": False,
            "pin_count_aligned": True,
            "issues": [],
        }

        pins = component.get("pins", [])
        if not isinstance(pins, list):
            result["issues"].append("pins field is not a list")
            result["pin_count_aligned"] = False
            return result

        pin_count = len(pins)

        # Symbol 检查
        symbol_lib = component.get("symbol_library", "")
        symbol_name = component.get("symbol_name", name)
        if symbol_lib:
            result["symbol_checked"] = True
            kicad_count = self.get_symbol_pin_count(symbol_lib, symbol_name)
            if kicad_count is not None:
                if kicad_count != pin_count:
                    result["issues"].append(
                        f"Symbol pin mismatch: KB={pin_count}, {symbol_lib}:{symbol_name}={kicad_count}"
                    )
                    result["pin_count_aligned"] = False

        # Footprint 检查
        footprint = component.get("footprint", "")
        if footprint:
            result["footprint_checked"] = True
            fp_data = self._find_footprint_data(footprint)
            if fp_data:
                pad_count = fp_data.get("pads", 0)
                # 注意: 封装焊盘数和符号引脚数不一定相等（有机械孔、热焊盘等）
                # 仅在差异 > 10% 时警告
                if pad_count > 0 and abs(pad_count - pin_count) > pin_count * 0.1:
                    result["issues"].append(
                        f"Footprint pad ({pad_count}) differs significantly from symbol pins ({pin_count})"
                    )

        return result

    def _find_footprint_data(self, footprint: str) -> Optional[Dict]:
        """在缓存中查找封装数据"""
        if ":" in footprint:
            lib, name = footprint.split(":", 1)
            return self._footprint_cache.get(lib, {}).get(name)
        else:
            for fps in self._footprint_cache.values():
                if footprint in fps:
                    return fps[footprint]
        return None
