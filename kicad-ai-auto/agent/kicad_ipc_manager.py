"""
KiCad IPC API Manager - 使用官方 kicad-python (kipy) 库
基于 KiCad 9.0+ IPC API 实现
"""

import os
import sys
import logging
import subprocess
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from footprint_library import (
    get_default_footprint,
    find_best_footprint,
    get_footprint_library_manager,
    SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS,
    DEFAULT_FOOTPRINT_MAPPING,
)

# 尝试导入 kicad-python (kipy)
try:
    import kipy
    from kipy.board import Board
    from kipy.client import Client

    HAS_KIPY = True
except ImportError:
    HAS_KIPY = False
    logging.warning("kicad-python (kipy) not installed. Run: pip install kicad-python")

# 尝试导入虚拟显示（用于无头环境）
try:
    from pyvirtualdisplay import Display

    HAS_VIRTUAL_DISPLAY = True
except ImportError:
    HAS_VIRTUAL_DISPLAY = False

logger = logging.getLogger(__name__)


@dataclass
class KiCadConnectionConfig:
    """KiCad 连接配置"""

    kicad_cli_path: Optional[str] = None  # KiCad CLI 路径
    pcb_file_path: Optional[str] = None  # 要打开的 PCB 文件
    use_virtual_display: bool = False  # 是否使用虚拟显示（Docker/无头环境）
    virtual_display_size: Tuple[int, int] = (1920, 1080)
    connection_timeout: int = 30  # 连接超时（秒）


class KiCadIPCManager:
    """
    KiCad IPC API 管理器

    功能：
    - 启动/连接 KiCad 实例
    - 管理 kipy 客户端连接
    - 提供简化的 API 接口给 FastAPI 使用
    """

    def __init__(self, config: Optional[KiCadConnectionConfig] = None):
        self.config = config or KiCadConnectionConfig()
        self.client: Optional["Client"] = None
        self.board: Optional["Board"] = None
        self.kicad_process: Optional[subprocess.Popen] = None
        self.virtual_display: Optional["Display"] = None
        self._connected = False

    def start_kicad(self, pcb_file: Optional[str] = None) -> bool:
        """
        启动 KiCad 并建立 IPC 连接

        Args:
            pcb_file: 要打开的 PCB 文件路径（可选）

        Returns:
            bool: 是否成功启动
        """
        if pcb_file:
            self.config.pcb_file_path = pcb_file

        try:
            # 1. 启动虚拟显示（如果需要）
            if self.config.use_virtual_display and HAS_VIRTUAL_DISPLAY:
                logger.info("Starting virtual display...")
                self.virtual_display = Display(
                    visible=0, size=self.config.virtual_display_size
                )
                self.virtual_display.start()
                os.environ["DISPLAY"] = f":{self.virtual_display.display}"
                time.sleep(1)

            # 2. 构建 KiCad 启动命令
            kicad_cmd = self._get_kicad_command()

            # 3. 启动 KiCad
            logger.info(f"Starting KiCad: {kicad_cmd}")
            if self.config.pcb_file_path and os.path.exists(self.config.pcb_file_path):
                self.kicad_process = subprocess.Popen(
                    [kicad_cmd, self.config.pcb_file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                self.kicad_process = subprocess.Popen(
                    [kicad_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

            # 4. 等待 KiCad 启动
            logger.info("Waiting for KiCad to start...")
            time.sleep(5)  # 给 KiCad 启动时间

            # 5. 建立 IPC 连接
            return self._connect_ipc()

        except Exception as e:
            logger.error(f"Failed to start KiCad: {e}")
            self.cleanup()
            return False

    def _get_kicad_command(self) -> str:
        """获取 KiCad 可执行文件路径"""
        if self.config.kicad_cli_path:
            # 从 CLI 路径推断 pcbnew 路径
            base_dir = os.path.dirname(self.config.kicad_cli_path)
            if sys.platform == "win32":
                pcbnew_path = os.path.join(base_dir, "pcbnew.exe")
            elif sys.platform == "darwin":
                # macOS
                pcbnew_path = os.path.join(base_dir, "..", "MacOS", "pcbnew")
            else:
                # Linux
                pcbnew_path = os.path.join(base_dir, "pcbnew")

            if os.path.exists(pcbnew_path):
                return pcbnew_path

        # 尝试从 PATH 查找
        if sys.platform == "win32":
            # Windows 默认安装路径
            default_paths = [
                r"C:\Program Files\KiCad\9.0\bin\pcbnew.exe",
                r"C:\Program Files\KiCad\8.0\bin\pcbnew.exe",
            ]
        elif sys.platform == "darwin":
            # macOS
            default_paths = [
                "/Applications/KiCad/pcbnew.app/Contents/MacOS/pcbnew",
                "/Applications/KiCad/KiCad.app/Contents/MacOS/pcbnew",
            ]
        else:
            # Linux
            default_paths = [
                "/usr/bin/pcbnew",
                "/usr/local/bin/pcbnew",
            ]

        for path in default_paths:
            if os.path.exists(path):
                return path

        # 最后尝试从 PATH 查找
        return "pcbnew"

    def _connect_ipc(self) -> bool:
        """建立 IPC 连接"""
        if not HAS_KIPY:
            logger.error("kicad-python (kipy) not installed")
            return False

        try:
            logger.info("Connecting to KiCad via IPC...")

            # 尝试连接
            start_time = time.time()
            while time.time() - start_time < self.config.connection_timeout:
                try:
                    self.client = Client()
                    # 验证连接 - 获取 KiCad 版本
                    version = self.client.get_version()
                    logger.info(f"Connected to KiCad {version}")
                    self._connected = True

                    # 获取当前打开的板子
                    self._get_current_board()
                    return True

                except Exception as e:
                    logger.debug(f"Connection attempt failed: {e}")
                    time.sleep(1)

            logger.error(
                f"Failed to connect within {self.config.connection_timeout} seconds"
            )
            return False

        except Exception as e:
            logger.error(f"IPC connection error: {e}")
            return False

    def _get_current_board(self):
        """获取当前打开的 PCB"""
        if not self.client:
            return

        try:
            # 获取打开的文件列表
            open_docs = self.client.get_open_documents()
            if open_docs:
                for doc in open_docs:
                    if doc.type == "pcb":
                        self.board = doc
                        logger.info(f"Current PCB: {doc.path}")
                        break
        except Exception as e:
            logger.warning(f"Could not get current board: {e}")

    def get_board_status(self) -> Dict[str, Any]:
        """
        获取 PCB 状态信息

        Returns:
            Dict 包含板子状态、选中项、层信息等
        """
        if not self._connected or not self.board:
            return {"error": "Not connected to KiCad"}

        try:
            status = {
                "connected": True,
                "board_path": self.board.path if self.board else None,
                "items": [],
                "selection": [],
                "layers": [],
            }

            # 获取所有项目
            try:
                items = self.board.get_items()
                status["items"] = [
                    {
                        "id": str(item.id),
                        "type": item.type,
                        "layer": item.layer if hasattr(item, "layer") else None,
                    }
                    for item in items[:100]
                ]  # 限制数量避免过大
                status["item_count"] = len(items)
            except Exception as e:
                logger.warning(f"Could not get items: {e}")

            # 获取选中项
            try:
                selection = self.board.get_selection()
                status["selection"] = [str(item.id) for item in selection]
            except Exception as e:
                logger.warning(f"Could not get selection: {e}")

            return status

        except Exception as e:
            logger.error(f"Error getting board status: {e}")
            return {"error": str(e)}

    def execute_action(
        self, action_name: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行 KiCad 动作

        Args:
            action_name: 动作名称，如 'pcbnew.PlaceFootprint'
            params: 动作参数

        Returns:
            执行结果
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        try:
            # 使用 KiCad 的动作系统
            result = self.client.run_action(action_name, params or {})
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {"success": False, "error": str(e)}

    def create_footprint(
        self, footprint_name: str, position: Tuple[float, float], layer: str = "F.Cu"
    ) -> Dict[str, Any]:
        """
        创建封装（器件）

        Args:
            footprint_name: 封装名称，如 "R_0603_1608Metric"
            position: (x, y) 位置（单位：mm）
            layer: 层

        Returns:
            创建结果和器件 ID
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            # 创建封装实例
            from kipy.board import FootprintInstance
            from kipy.common import Vector2
            from kipy.utils import from_mm

            fpi = FootprintInstance()
            fpi.footprint_id = footprint_name
            fpi.position = Vector2(from_mm(position[0]), from_mm(position[1]))
            fpi.layer = layer

            # 创建项目
            created = self.board.create_items([fpi])

            if created:
                return {
                    "success": True,
                    "item_id": str(created[0].id),
                    "position": position,
                }
            else:
                return {"success": False, "error": "Creation returned empty"}

        except Exception as e:
            logger.error(f"Failed to create footprint: {e}")
            return {"success": False, "error": str(e)}

    def get_screenshot_via_cli(self, output_path: str) -> bool:
        """
        使用 KiCad CLI 获取截图

        Args:
            output_path: 截图保存路径

        Returns:
            bool: 是否成功
        """
        if not self.config.kicad_cli_path:
            logger.error("KiCad CLI path not configured")
            return False

        try:
            cmd = [
                self.config.kicad_cli_path,
                "pcb",
                "export",
                "svg",
                "--page-size",
                "A4",
                "--output",
                output_path,
                self.config.pcb_file_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False

    def delete_item(self, item_id: str) -> Dict[str, Any]:
        """
        删除项目

        Args:
            item_id: 项目 ID

        Returns:
            删除结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            # 尝试查找并删除项目
            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id:
                    self.board.delete_items([item])
                    return {"success": True, "message": f"Item {item_id} deleted"}

            return {"success": False, "error": f"Item {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to delete item: {e}")
            return {"success": False, "error": str(e)}

    def move_item(
        self, item_id: str, new_position: Tuple[float, float]
    ) -> Dict[str, Any]:
        """
        移动项目到新位置

        Args:
            item_id: 项目 ID
            new_position: (x, y) 新位置（单位：mm）

        Returns:
            移动结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            from kipy.common import Vector2
            from kipy.utils import from_mm

            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id:
                    item.position = Vector2(
                        from_mm(new_position[0]), from_mm(new_position[1])
                    )
                    self.board.update_items([item])
                    return {
                        "success": True,
                        "item_id": item_id,
                        "new_position": new_position,
                    }

            return {"success": False, "error": f"Item {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to move item: {e}")
            return {"success": False, "error": str(e)}

    def create_track(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        layer: str = "F.Cu",
        width: float = 0.25,
    ) -> Dict[str, Any]:
        """
        创建走线

        Args:
            start: (x, y) 起点（单位：mm）
            end: (x, y) 终点（单位：mm）
            layer: 层
            width: 线宽（mm）

        Returns:
            创建结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            from kipy.board import Track
            from kipy.common import Vector2
            from kipy.utils import from_mm

            track = Track()
            track.start = Vector2(from_mm(start[0]), from_mm(start[1]))
            track.end = Vector2(from_mm(end[0]), from_mm(end[1]))
            track.layer = layer
            track.width = from_mm(width)

            created = self.board.create_items([track])

            if created:
                return {
                    "success": True,
                    "item_id": str(created[0].id),
                    "start": start,
                    "end": end,
                    "layer": layer,
                    "width": width,
                }
            else:
                return {"success": False, "error": "Track creation returned empty"}

        except Exception as e:
            logger.error(f"Failed to create track: {e}")
            return {"success": False, "error": str(e)}

    def create_via(
        self, position: Tuple[float, float], size: float = 0.8, drill: float = 0.4
    ) -> Dict[str, Any]:
        """
        创建过孔

        Args:
            position: (x, y) 位置（单位：mm）
            size: 过孔外径（mm）
            drill: 钻孔直径（mm）

        Returns:
            创建结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            from kipy.board import Via
            from kipy.common import Vector2
            from kipy.utils import from_mm

            via = Via()
            via.position = Vector2(from_mm(position[0]), from_mm(position[1]))
            via.size = from_mm(size)
            via.drill = from_mm(drill)
            via.layers = ("F.Cu", "B.Cu")  # 默认通孔

            created = self.board.create_items([via])

            if created:
                return {
                    "success": True,
                    "item_id": str(created[0].id),
                    "position": position,
                    "size": size,
                    "drill": drill,
                }
            else:
                return {"success": False, "error": "Via creation returned empty"}

        except Exception as e:
            logger.error(f"Failed to create via: {e}")
            return {"success": False, "error": str(e)}

    def save_board(self) -> Dict[str, Any]:
        """
        保存当前板子

        Returns:
            保存结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            self.board.save()
            return {
                "success": True,
                "message": "Board saved successfully",
                "path": self.board.path,
            }

        except Exception as e:
            logger.error(f"Failed to save board: {e}")
            return {"success": False, "error": str(e)}

    def get_board_statistics(self) -> Dict[str, Any]:
        """
        获取板子统计信息

        Returns:
            统计信息字典
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()

            footprint_count = sum(1 for item in items if item.type == "footprint")
            track_count = sum(1 for item in items if item.type == "track")
            via_count = sum(1 for item in items if item.type == "via")
            zone_count = sum(1 for item in items if item.type == "zone")

            return {
                "success": True,
                "total_items": len(items),
                "footprints": footprint_count,
                "tracks": track_count,
                "vias": via_count,
                "zones": zone_count,
                "selection_count": len(self.board.get_selection()),
            }

        except Exception as e:
            logger.error(f"Failed to get board statistics: {e}")
            return {"success": False, "error": str(e)}

    def select_items(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        选择项目

        Args:
            item_ids: 项目 ID 列表

        Returns:
            选择结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()
            selected = []

            for item in items:
                if str(item.id) in item_ids:
                    item.select()
                    selected.append(str(item.id))

            return {
                "success": True,
                "selected_count": len(selected),
                "selected_ids": selected,
            }

        except Exception as e:
            logger.error(f"Failed to select items: {e}")
            return {"success": False, "error": str(e)}

    def clear_selection(self) -> Dict[str, Any]:
        """
        清除选择

        Returns:
            操作结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            self.board.clear_selection()
            return {"success": True, "message": "Selection cleared"}

        except Exception as e:
            logger.error(f"Failed to clear selection: {e}")
            return {"success": False, "error": str(e)}

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.client is not None

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up KiCad IPC connection...")

        # 关闭客户端连接
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None

        # 关闭 KiCad 进程
        if self.kicad_process:
            try:
                self.kicad_process.terminate()
                self.kicad_process.wait(timeout=5)
            except:
                try:
                    self.kicad_process.kill()
                except:
                    pass
            self.kicad_process = None

        # 关闭虚拟显示
        if self.virtual_display:
            try:
                self.virtual_display.stop()
            except:
                pass
            self.virtual_display = None

        self._connected = False
        logger.info("Cleanup complete")

    def __del__(self):
        """析构时清理"""
        self.cleanup()


# 单例模式 - 用于 FastAPI
_kicad_manager: Optional[KiCadIPCManager] = None


def get_kicad_manager() -> KiCadIPCManager:
    """获取 KiCad 管理器单例（用于 FastAPI Depends）"""
    global _kicad_manager
    if _kicad_manager is None:
        config = KiCadConnectionConfig(
            kicad_cli_path=os.getenv("KICAD_CLI_PATH"),
            use_virtual_display=os.getenv("USE_VIRTUAL_DISPLAY", "false").lower()
            == "true",
        )
        _kicad_manager = KiCadIPCManager(config)
    return _kicad_manager


def reset_kicad_manager():
    """重置管理器（用于测试或重新连接）"""
    global _kicad_manager
    if _kicad_manager:
        _kicad_manager.cleanup()
    _kicad_manager = None


# ========== 封装库 API 方法 ==========


def get_footprint_recommendations(
    component_name: str, component_value: str = None, package: str = None
) -> Dict[str, Any]:
    """
    获取元件的推荐封装

    这是 AI 生成时调用的主要方法，会：
    1. 尝试在 KiCad 封装库中搜索匹配
    2. 如果没有找到，使用内置的默认映射

    Args:
        component_name: 元件名称/型号
        component_value: 元件值（可选）
        package: 指定封装（可选）

    Returns:
        包含推荐封装和建议的字典
    """
    result = {
        "component_name": component_name,
        "component_value": component_value,
        "package": package,
        "recommendation": None,
        "source": None,  # "library" | "default_mapping" | "fallback"
        "alternatives": [],
        "message": "",
    }

    # 1. 首先尝试在 KiCad 封装库中搜索
    try:
        lib_manager = get_footprint_library_manager()

        # 搜索关键词
        search_terms = [component_name]
        if component_value:
            search_terms.append(component_value)
        if package:
            search_terms.append(package)

        search_keyword = " ".join(search_terms)
        library_results = lib_manager.search_footprints(search_keyword)

        if library_results:
            result["recommendation"] = library_results[0]
            result["alternatives"] = library_results[1:6]  # 最多5个备选
            result["source"] = "library"
            result["message"] = f"从 KiCad 封装库找到 {len(library_results)} 个匹配"
            logger.info(
                f"Found {len(library_results)} footprints in library for '{search_keyword}'"
            )
            return result
    except Exception as e:
        logger.warning(f"Failed to search KiCad footprint library: {e}")

    # 2. 使用内置的符号到封装推荐表
    if component_name in SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS:
        result["recommendation"] = SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS[component_name]
        result["source"] = "default_mapping"
        result["message"] = "使用内置符号-封装映射"
        return result

    # 3. 使用智能推断 + 默认封装
    try:
        footprint = find_best_footprint(component_name, component_value, package)
        result["recommendation"] = footprint
        result["source"] = "fallback"
        result["message"] = "使用默认封装（智能推断）"
        return result
    except Exception as e:
        logger.warning(f"Failed to find default footprint: {e}")

    # 4. 最终 fallback
    result["recommendation"] = "Resistor_SMD:R_0603_1608Metric"
    result["source"] = "fallback"
    result["message"] = "使用通用 fallback 封装"

    return result


def search_footprint_library(keyword: str, limit: int = 20) -> List[str]:
    """
    搜索 KiCad 封装库

    优先使用内置封装映射表搜索，如果没有结果再尝试系统库

    Args:
        keyword: 搜索关键词
        limit: 返回结果数量限制

    Returns:
        封装名称列表
    """
    results: List[str] = []
    keyword_lower = keyword.lower()

    # 1. 首先在内置封装映射表中搜索
    for component_type, mapping in DEFAULT_FOOTPRINT_MAPPING.items():
        # 检查类型名是否匹配
        if keyword_lower in component_type.lower():
            for pkg, footprint in mapping.items():
                if footprint and footprint not in results:
                    results.append(footprint)

        # 检查封装名是否匹配
        for pkg, footprint in mapping.items():
            if footprint and (
                keyword_lower in pkg.lower() or keyword_lower in footprint.lower()
            ):
                if footprint not in results:
                    results.append(footprint)

    # 2. 在符号-封装推荐表中搜索
    for symbol, footprint in SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS.items():
        if keyword_lower in symbol.lower() or keyword_lower in footprint.lower():
            if footprint not in results:
                results.append(footprint)

    # 3. 尝试搜索系统 KiCad 封装库
    try:
        lib_manager = get_footprint_library_manager()
        library_results = lib_manager.search_footprints(keyword)
        for fp in library_results:
            if fp not in results:
                results.append(fp)
    except Exception as e:
        logger.debug(f"System library search failed: {e}")

    return results[:limit]


def get_all_libraries() -> List[str]:
    """获取所有封装库名称"""
    try:
        lib_manager = get_footprint_library_manager()
        return lib_manager.get_libraries()
    except Exception as e:
        logger.error(f"Failed to get libraries: {e}")
        return []


def get_default_footprint_for_component(
    component_type: str, package: str = None
) -> str:
    """
    获取元件类型的默认封装

    Args:
        component_type: 元件类型 (resistor, capacitor, ic 等)
        package: 封装大小 (可选)

    Returns:
        封装名称
    """
    return get_default_footprint(component_type, package)
