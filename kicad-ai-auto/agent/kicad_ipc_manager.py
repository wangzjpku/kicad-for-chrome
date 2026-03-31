"""
KiCad IPC API Manager - 使用官方 kicad-python (kipy) 库
基于 KiCad 9.0+ IPC API 实现
"""

import os
import sys
import logging
import subprocess
import threading
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
    from kipy.client import KiCadClient as Client

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
        self._lock = threading.Lock()  # 保护 _connected 和 client 的线程安全访问

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
        """获取 KiCad 可执行文件路径

        优先级：
        1. 环境变量 KICAD_PATH / KICAD_CLI_PATH
        2. 配置文件 self.config.kicad_cli_path
        3. 系统默认安装路径
        4. PATH 中查找
        """
        # 1. 首先检查环境变量
        env_path = os.environ.get("KICAD_CLI_PATH") or os.environ.get("KICAD_PATH")
        if env_path:
            if os.path.exists(env_path):
                logger.info(f"Using KiCad from environment variable: {env_path}")
                return env_path
            else:
                logger.warning(
                    f"KICAD_PATH environment variable set but file not found: {env_path}"
                )

        # 2. 从配置文件路径推断
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

            # 尝试连接，使用指数退避
            start_time = time.time()
            retry_delay = 1.0  # 初始重试间隔
            max_retry_delay = 10.0  # 最大重试间隔
            attempt = 0

            while time.time() - start_time < self.config.connection_timeout:
                attempt += 1
                try:
                    self.client = Client()
                    # 验证连接 - 获取 KiCad 版本
                    version = self.client.get_version()
                    logger.info(
                        f"Connected to KiCad {version} after {attempt} attempts"
                    )
                    with self._lock:
                        self._connected = True

                    # 获取当前打开的板子
                    self._get_current_board()
                    return True

                except Exception as e:
                    logger.debug(f"Connection attempt {attempt} failed: {e}")
                    # 指数退避：延迟逐渐增加到最大值
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, max_retry_delay)

            logger.error(
                f"Failed to connect within {self.config.connection_timeout} seconds after {attempt} attempts"
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

    def get_full_pcb_data(self) -> Dict[str, Any]:
        """
        获取完整的PCB数据，包括所有层、网络、铜箔等

        Returns:
            完整的PCB数据字典
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected to KiCad"}

        try:
            result = {
                "success": True,
                "layers": [],
                "nets": [],
                "footprints": [],
                "tracks": [],
                "vias": [],
                "zones": [],
                "board_outline": [],
                "texts": [],
                "dimensions": {},
            }

            # 1. 获取层信息
            try:
                layers = self.board.layers
                for layer in layers:
                    result["layers"].append({
                        "id": layer.id,
                        "name": layer.name,
                        "type": getattr(layer, "type", "signal"),
                        "color": getattr(layer, "color", "#000000"),
                        "visible": getattr(layer, "visible", True),
                    })
            except Exception as e:
                logger.warning(f"Could not get layers: {e}")

            # 2. 获取网络信息
            try:
                nets = self.board.nets
                for net in nets:
                    result["nets"].append({
                        "id": str(net.id),
                        "name": net.name,
                        "code": getattr(net, "code", 0),
                    })
            except Exception as e:
                logger.warning(f"Could not get nets: {e}")

            # 3. 获取所有PCB项目
            try:
                items = self.board.get_items()
                for item in items:
                    item_type = getattr(item, "type", "unknown")
                    item_layer = getattr(item, "layer", "unknown")

                    # 封装
                    if item_type == "footprint":
                        try:
                            footprint_data = {
                                "id": str(item.id),
                                "reference": getattr(item, "reference", ""),
                                "value": getattr(item, "value", ""),
                                "footprint": getattr(item, "footprint", ""),
                                "layer": item_layer,
                                "position": {
                                    "x": getattr(item, "x", 0),
                                    "y": getattr(item, "y", 0),
                                },
                                "rotation": getattr(item, "rotation", 0),
                                "pad": [],
                            }
                            # 获取焊盘信息
                            try:
                                pads = getattr(item, "pads", [])
                                for pad in pads:
                                    footprint_data["pad"].append({
                                        "number": getattr(pad, "number", ""),
                                        "name": getattr(pad, "name", ""),
                                        "type": getattr(pad, "type", "smd"),
                                        "shape": getattr(pad, "shape", "rect"),
                                        "position": {
                                            "x": getattr(pad, "x", 0),
                                            "y": getattr(pad, "y", 0),
                                        },
                                        "size": {
                                            "x": getattr(pad, "size_x", 1),
                                            "y": getattr(pad, "size_y", 1),
                                        },
                                    })
                            except Exception as e:
                                logger.debug(f"Could not get pads: {e}")

                            result["footprints"].append(footprint_data)
                        except Exception as e:
                            logger.debug(f"Could not process footprint: {e}")

                    # 走线
                    elif item_type == "track":
                        try:
                            result["tracks"].append({
                                "id": str(item.id),
                                "net": getattr(item, "net", ""),
                                "layer": item_layer,
                                "width": getattr(item, "width", 0.25),
                                "start": {
                                    "x": getattr(item, "start_x", 0),
                                    "y": getattr(item, "start_y", 0),
                                },
                                "end": {
                                    "x": getattr(item, "end_x", 0),
                                    "y": getattr(item, "end_y", 0),
                                },
                            })
                        except Exception as e:
                            logger.debug(f"Could not process track: {e}")

                    # 过孔
                    elif item_type == "via":
                        try:
                            result["vias"].append({
                                "id": str(item.id),
                                "net": getattr(item, "net", ""),
                                "position": {
                                    "x": getattr(item, "x", 0),
                                    "y": getattr(item, "y", 0),
                                },
                                "size": getattr(item, "diameter", 0.8),
                                "drill": getattr(item, "drill", 0.4),
                                "layers": getattr(item, "layers", ["F.Cu", "B.Cu"]),
                            })
                        except Exception as e:
                            logger.debug(f"Could not process via: {e}")

                    # 铜箔区域
                    elif item_type == "zone" or item_type == "polygon":
                        try:
                            result["zones"].append({
                                "id": str(item.id),
                                "net": getattr(item, "net", ""),
                                "layer": item_layer,
                                "priority": getattr(item, "priority", 0),
                            })
                        except Exception as e:
                            logger.debug(f"Could not process zone: {e}")

                    # 文本
                    elif item_type == "text" or item_type == "text_box":
                        try:
                            result["texts"].append({
                                "id": str(item.id),
                                "text": getattr(item, "text", ""),
                                "layer": item_layer,
                                "position": {
                                    "x": getattr(item, "x", 0),
                                    "y": getattr(item, "y", 0),
                                },
                                "rotation": getattr(item, "rotation", 0),
                            })
                        except Exception as e:
                            logger.debug(f"Could not process text: {e}")

            except Exception as e:
                logger.warning(f"Could not get items: {e}")

            # 4. 获取板框信息
            try:
                # 获取板子边界
                board_edges = self.board.get_board_edges()
                if board_edges:
                    outline_points = []
                    for edge in board_edges:
                        outline_points.append({
                            "x": getattr(edge, "x", 0),
                            "y": getattr(edge, "y", 0),
                        })
                    result["board_outline"] = outline_points
            except Exception as e:
                logger.warning(f"Could not get board outline: {e}")

            # 添加统计信息
            result["statistics"] = {
                "total_footprints": len(result["footprints"]),
                "total_tracks": len(result["tracks"]),
                "total_vias": len(result["vias"]),
                "total_zones": len(result["zones"]),
                "total_nets": len(result["nets"]),
                "total_layers": len(result["layers"]),
            }

            return result

        except Exception as e:
            logger.error(f"Error getting full PCB data: {e}")
            return {"success": False, "error": str(e)}

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

        if not self.config.pcb_file_path:
            logger.error("PCB file path not configured")
            return False

        try:
            # 安全验证：确保路径是有效的
            pcb_path = Path(self.config.pcb_file_path).resolve()
            if not pcb_path.exists():
                logger.error(f"PCB file does not exist: {pcb_path}")
                return False
            if not pcb_path.is_file():
                logger.error(f"PCB path is not a file: {pcb_path}")
                return False
            if not str(pcb_path).endswith((".kicad_pcb", ".pcb")):
                logger.error(f"Invalid PCB file extension: {pcb_path}")
                return False

            # 验证输出路径
            out_path = Path(output_path).resolve()
            if not str(out_path).endswith(".svg"):
                logger.error(f"Output must be SVG file: {out_path}")
                return False

            # 验证输出目录是否在允许的白名单内
            import tempfile

            allowed_output_dirs = [
                Path(tempfile.gettempdir()).resolve(),
                Path(
                    os.getenv("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
                ).resolve(),
                Path.cwd() / "output",
            ]

            is_allowed = False
            for allowed_dir in allowed_output_dirs:
                try:
                    if out_path.is_relative_to(allowed_dir):
                        is_allowed = True
                        break
                except (OSError, ValueError):
                    continue

            if not is_allowed:
                logger.error(f"Output path not in allowed directories: {out_path}")
                return False

            # 验证 KiCad CLI 路径
            cli_path = Path(self.config.kicad_cli_path).resolve()
            if not cli_path.exists():
                logger.error(f"KiCad CLI does not exist: {cli_path}")
                return False
            if not cli_path.is_file():
                logger.error(f"KiCad CLI path is not a file: {cli_path}")
                return False

            # 验证可执行权限（非Windows）或文件扩展名（Windows）
            import platform

            if platform.system() != "Windows":
                if not os.access(cli_path, os.X_OK):
                    logger.error(f"KiCad CLI is not executable: {cli_path}")
                    return False
            else:
                # Windows: 验证扩展名
                if not str(cli_path).lower().endswith((".exe", ".bat", ".cmd")):
                    logger.error(
                        f"KiCad CLI must be executable file (.exe, .bat, .cmd): {cli_path}"
                    )
                    return False

            cmd = [
                str(cli_path),
                "pcb",
                "export",
                "svg",
                "--page-size",
                "A4",
                "--output",
                str(out_path),
                str(pcb_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("Screenshot command timed out")
            return False
        except subprocess.SubprocessError as e:
            logger.error(f"Subprocess error during screenshot: {e}")
            return False
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

    def auto_route(
        self,
        net_class: str = "default",
        ripup_days: bool = False,
        stability: int = 50,
        max_iterations: int = 100,
    ) -> Dict[str, Any]:
        """
        执行自动布线（使用推挤式布线算法）

        Args:
            net_class: 网络类名称
            ripup_days: 是否允许拆线重布
            stability: 稳定性参数 (0-100)
            max_iterations: 最大迭代次数

        Returns:
            布线结果
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            # 导入推挤式布线器
            from routing.push_router import get_push_router, Segment, Point, Obstacle

            # 获取所有网络
            nets = self.board.nets
            if not nets:
                return {"success": False, "error": "No nets found"}

            # 收集现有的走线作为障碍物
            router = get_push_router()
            router.clear_obstacles()

            # 从现有走线创建障碍物
            existing_tracks = self.board.tracks
            for track in existing_tracks:
                seg = Segment(
                    start=Point(track.start.x, track.start.y),
                    end=Point(track.end.x, track.end.y),
                    layer=track.layer,
                    width=track.width,
                )
                router.add_obstacle(Obstacle(segment=seg, priority=1))

            # 获取封装焊盘作为起点/终点
            footprints = self.board.footprints
            pads = []
            for fp in footprints:
                for pad in fp.pads:
                    pads.append({
                        "position": (pad.position.x, pad.position.y),
                        "net": pad.net,
                        "layer": pad.layer,
                    })

            # 对每个网络进行布线
            routed_count = 0
            failed_nets = []
            total_length = 0
            total_vias = 0

            for net in nets[:20]:  # 限制最多20个网络
                if not net or not net.items:
                    continue

                # 获取网络的焊盘
                net_pads = [p for p in pads if p["net"] == net.name]
                if len(net_pads) < 2:
                    continue

                # 使用 A* 布线
                start = net_pads[0]["position"]
                end = net_pads[1]["position"]

                result = router.route(
                    start=start,
                    end=end,
                    start_layer=net_pads[0].get("layer", "F.Cu"),
                    end_layer=net_pads[1].get("layer", "F.Cu"),
                    net_name=net.name,
                )

                if result.success:
                    # 在 KiCad 中创建走线
                    for seg in result.routed_segments:
                        track_result = self.create_track(
                            start=(seg.start.x, seg.start.y),
                            end=(seg.end.x, seg.end.y),
                            layer=seg.layer,
                            width=seg.width,
                        )
                        if track_result.get("success"):
                            routed_count += 1
                            total_length += seg.length

                    total_vias += result.via_count
                else:
                    failed_nets.append(net.name)

            return {
                "success": True,
                "message": f"Routed {routed_count} tracks",
                "routed_count": routed_count,
                "failed_nets": failed_nets,
                "total_length": total_length,
                "via_count": total_vias,
            }

        except Exception as e:
            logger.error(f"Auto-route failed: {e}")
            return {"success": False, "error": str(e)}

    def clear_all_tracks(self) -> Dict[str, Any]:
        """清除所有走线"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            # 获取所有走线并删除
            tracks = self.board.tracks
            deleted_count = 0
            for track in tracks:
                try:
                    self.board.delete_item(track.id)
                    deleted_count += 1
                except Exception as e:
                    logger.debug(f"Failed to delete track: {e}")

            return {
                "success": True,
                "message": f"Deleted {deleted_count} tracks",
                "deleted_count": deleted_count,
            }

        except Exception as e:
            logger.error(f"Failed to clear tracks: {e}")
            return {"success": False, "error": str(e)}

    def auto_place(self, topology_aware: bool = True) -> Dict[str, Any]:
        """
        自动布局元件

        Args:
            topology_aware: 是否使用拓扑感知布局 (默认 True)

        Returns:
            布局结果，包含位置和分区信息
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected to KiCad"}

        try:
            from placement.netlist_topology import NetlistTopologyAnalyzer
            from placement.topology_placement import TopologyAwarePlacementEngine
            from placement.smart_placement_engine import (
                Component, SmartPlacementEngine,
            )

            # 获取 PCB 数据
            board_data = self.get_full_pcb_data()
            footprints = board_data.get("footprints", [])

            if not footprints:
                return {"success": False, "error": "No footprints on board"}

            # 获取板子尺寸
            board_outline = board_data.get("board_outline", {})
            board_width = 100.0
            board_height = 80.0
            if board_outline.get("points"):
                pts = board_outline["points"]
                xs = [p.get("x", 0) for p in pts]
                ys = [p.get("y", 0) for p in pts]
                board_width = max(xs) - min(xs) if xs else 100.0
                board_height = max(ys) - min(ys) if ys else 80.0

            # 转换为 Component 对象
            components = []
            for fp in footprints:
                ref = fp.get("reference", "")
                value = fp.get("value", "")
                fp_name = fp.get("footprint", "")
                pos = fp.get("position", {})
                pads = fp.get("pads", [])
                nets = list(set(p.get("net", "") for p in pads if p.get("net")))

                # 估算元件尺寸
                bounds = fp.get("bounding_box", {})
                w = bounds.get("width", 5.0)
                h = bounds.get("height", 5.0)

                components.append(Component(
                    reference=ref,
                    footprint=fp_name,
                    value=value,
                    width=w,
                    height=h,
                    nets=nets,
                    pins=pads,
                ))

            if topology_aware:
                # 拓扑感知布局
                nets_data = self._extract_nets_from_board(board_data)

                engine = TopologyAwarePlacementEngine(
                    board_width=board_width,
                    board_height=board_height,
                )
                result = engine.place(components, nets_data)

                # 应用位置到 KiCad
                moved = 0
                for ref, pos in result.positions.items():
                    try:
                        move_result = self.move_item(
                            item_id=ref,
                            x=pos["x"],
                            y=pos["y"],
                        )
                        if move_result.get("success"):
                            moved += 1
                    except Exception as e:
                        logger.debug(f"Failed to move {ref}: {e}")

                return {
                    "success": True,
                    "topology_aware": True,
                    "placed_count": moved,
                    "total_count": len(components),
                    "score": result.score,
                    "zones": [
                        {
                            "name": z.name,
                            "group": z.group.value,
                            "x": z.x, "y": z.y,
                            "width": z.width, "height": z.height,
                            "color": z.color,
                        }
                        for z in result.zones
                    ],
                    "isolation_slots": [
                        {
                            "x": s.x, "y": s.y,
                            "width": s.width, "height": s.height,
                            "voltage_label": s.voltage_label,
                        }
                        for s in result.isolation_slots
                    ],
                    "positions": {
                        ref: {"x": p["x"], "y": p["y"], "rotation": p.get("rotation", 0)}
                        for ref, p in result.positions.items()
                    },
                    "statistics": result.statistics,
                }
            else:
                # 回退到 SmartPlacementEngine
                engine = SmartPlacementEngine(
                    board_width=board_width,
                    board_height=board_height,
                )
                result = engine.place(components)

                moved = 0
                for ref, pos in result.positions.items():
                    try:
                        move_result = self.move_item(
                            item_id=ref,
                            x=pos["x"],
                            y=pos["y"],
                        )
                        if move_result.get("success"):
                            moved += 1
                    except Exception as e:
                        logger.debug(f"Failed to move {ref}: {e}")

                return {
                    "success": True,
                    "topology_aware": False,
                    "placed_count": moved,
                    "total_count": len(components),
                    "score": result.score,
                    "positions": {
                        ref: {"x": p["x"], "y": p["y"], "rotation": p.get("rotation", 0)}
                        for ref, p in result.positions.items()
                    },
                    "statistics": result.statistics,
                }

        except ImportError as e:
            logger.error(f"Missing placement module: {e}")
            return {"success": False, "error": f"Missing module: {e}"}
        except Exception as e:
            logger.error(f"Auto-place failed: {e}")
            return {"success": False, "error": str(e)}

    def _extract_nets_from_board(self, board_data: Dict = None) -> List[Dict]:
        """从板数据中提取网络信息"""
        if board_data is None:
            board_data = self.get_full_pcb_data()

        nets_map: Dict[str, List[Dict]] = {}

        # 从焊盘收集网络
        for fp in board_data.get("footprints", []):
            ref = fp.get("reference", "")
            for pad in fp.get("pads", []):
                net = pad.get("net", "")
                if net:
                    nets_map.setdefault(net, []).append({
                        "ref": ref,
                        "pin": pad.get("number", pad.get("pin", "")),
                    })

        # 从走线收集网络
        for track in board_data.get("tracks", []):
            net = track.get("net", "")
            if net and net not in nets_map:
                nets_map[net] = []

        return [
            {"name": name, "nodes": nodes}
            for name, nodes in nets_map.items()
        ]

    def create_zone(self, net_name: str, layer: str,
                    boundary_points: List[Dict],
                    clearance: float = 0.3,
                    thermal_relief: bool = True,
                    hatched: bool = False,
                    hatch_width: float = 1.0,
                    hatch_gap: float = 0.5) -> Dict[str, Any]:
        """
        通过 IPC 创建铺铜区域

        Args:
            net_name: 网络名称 (如 GND)
            layer: 层名称 (如 B.Cu)
            boundary_points: 边界点列表 [{"x": ..., "y": ...}]
            clearance: 间距 (mm)
            thermal_relief: 是否使用热焊盘
            hatched: 是否使用网格铺铜
            hatch_width: 网格线宽 (mm)
            hatch_gap: 网格间距 (mm)
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            from routing.copper_pour import CopperPourEngine, PourType

            engine = CopperPourEngine(board_width=100, board_height=80)

            pour_type = PourType.HATCHED if hatched else PourType.SOLID

            # 创建 GND 铺铜
            if net_name.upper() in ("GND", "AGND", "DGND"):
                result = engine.create_ground_pour(
                    layer=layer,
                    clearance=clearance,
                    thermal_style="four_spoke" if thermal_relief else None,
                )
            else:
                result = engine.create_power_pour(
                    net_name=net_name,
                    layer=layer,
                    clearance=clearance,
                    thermal_style="four_spoke" if thermal_relief else None,
                )

            # 转换为 KiCad 格式
            kicad_zone = engine.to_kicad_zone(result, net_name, layer)

            return {
                "success": True,
                "net_name": net_name,
                "layer": layer,
                "zone_data": kicad_zone,
                "area": result.area if hasattr(result, 'area') else 0,
            }

        except ImportError as e:
            return {"success": False, "error": f"Missing copper_pour module: {e}"}
        except Exception as e:
            logger.error(f"Failed to create zone: {e}")
            return {"success": False, "error": str(e)}

    def create_stitching_vias(self, zone_boundary: List[Dict],
                              spacing: float = 1.0,
                              via_size: float = 0.6,
                              via_drill: float = 0.3) -> Dict[str, Any]:
        """
        在铺铜区域内生成缝合过孔网格

        Args:
            zone_boundary: 区域边界点
            spacing: 过孔间距 (mm)
            via_size: 过孔外径 (mm)
            via_drill: 过孔钻径 (mm)
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            created_vias = []

            # 从边界点计算区域范围
            if not zone_boundary:
                return {"success": False, "error": "No boundary points"}

            xs = [p.get("x", 0) for p in zone_boundary]
            ys = [p.get("y", 0) for p in zone_boundary]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            # 在区域内生成过孔网格
            x = min_x + spacing
            while x < max_x - spacing:
                y = min_y + spacing
                while y < max_y - spacing:
                    # 创建过孔
                    via_result = self.create_via(
                        x=x, y=y,
                        size=via_size,
                        drill=via_drill,
                        net="GND",
                    )
                    if via_result.get("success"):
                        created_vias.append({"x": x, "y": y})
                    y += spacing
                x += spacing

            return {
                "success": True,
                "created_count": len(created_vias),
                "spacing": spacing,
                "vias": created_vias,
            }

        except Exception as e:
            logger.error(f"Failed to create stitching vias: {e}")
            return {"success": False, "error": str(e)}

    def auto_copper_pour(self, nets: List[str] = None,
                         layers: List[str] = None,
                         hatched: bool = False,
                         stitch_spacing: float = 1.0) -> Dict[str, Any]:
        """
        一键铺铜: GND底层 + 电源顶层 + 缝合过孔

        Args:
            nets: 要铺铜的网络列表 (默认 ["GND"])
            layers: 要铺铜的层列表 (默认 ["B.Cu"])
            hatched: 是否使用网格铺铜
            stitch_spacing: 缝合过孔间距 (mm)
        """
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            if nets is None:
                nets = ["GND"]
            if layers is None:
                layers = ["B.Cu"]

            results = []

            for net in nets:
                for layer in layers:
                    # 获取板子边界
                    board_data = self.get_full_pcb_data()
                    outline = board_data.get("board_outline", {})
                    boundary = outline.get("points", [])

                    if not boundary:
                        # 使用默认边界
                        bw = 100.0
                        bh = 80.0
                        m = 1.0
                        boundary = [
                            {"x": m, "y": m},
                            {"x": bw - m, "y": m},
                            {"x": bw - m, "y": bh - m},
                            {"x": m, "y": bh - m},
                        ]

                    # 创建铺铜
                    zone_result = self.create_zone(
                        net_name=net,
                        layer=layer,
                        boundary_points=boundary,
                        hatched=hatched,
                    )

                    # 添加缝合过孔
                    stitch_result = None
                    if stitch_spacing > 0:
                        stitch_result = self.create_stitching_vias(
                            zone_boundary=boundary,
                            spacing=stitch_spacing,
                        )

                    results.append({
                        "net": net,
                        "layer": layer,
                        "zone": zone_result.get("success", False),
                        "stitching_vias": stitch_result.get("created_count", 0) if stitch_result else 0,
                    })

            return {
                "success": True,
                "results": results,
                "total_zones": len(results),
            }

        except Exception as e:
            logger.error(f"Auto copper pour failed: {e}")
            return {"success": False, "error": str(e)}

    def is_connected(self) -> bool:
        """检查是否已连接"""
        with self._lock:
            return self._connected and self.client is not None

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up KiCad IPC connection...")

        # 关闭客户端连接
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.debug(f"Error closing client: {e}")
            self.client = None

        # 关闭 KiCad 进程
        if self.kicad_process:
            try:
                self.kicad_process.terminate()
                self.kicad_process.wait(timeout=5)
            except Exception as e:
                logger.debug(f"Error terminating process: {e}")
                try:
                    self.kicad_process.kill()
                except Exception as e2:
                    logger.debug(f"Error killing process: {e2}")
            self.kicad_process = None

        # 关闭虚拟显示
        if self.virtual_display:
            try:
                self.virtual_display.stop()
            except Exception as e:
                logger.debug(f"Error stopping virtual display: {e}")
            self.virtual_display = None

        with self._lock:
            self._connected = False
        logger.info("Cleanup complete")

    def __del__(self):
        """析构时清理"""
        self.cleanup()


# 单例模式 - 用于 FastAPI（线程安全版本）

_kicad_manager: Optional[KiCadIPCManager] = None
_manager_lock = threading.Lock()


def get_kicad_manager() -> KiCadIPCManager:
    """获取 KiCad 管理器单例（用于 FastAPI Depends）- 线程安全版本"""
    global _kicad_manager
    if _kicad_manager is None:
        with _manager_lock:
            # 双重检查锁定
            if _kicad_manager is None:
                try:
                    config = KiCadConnectionConfig(
                        kicad_cli_path=os.getenv("KICAD_CLI_PATH"),
                        use_virtual_display=os.getenv(
                            "USE_VIRTUAL_DISPLAY", "false"
                        ).lower()
                        == "true",
                    )
                    _kicad_manager = KiCadIPCManager(config)
                except Exception as e:
                    logger.error(f"Failed to initialize KiCad manager: {e}")
                    _kicad_manager = None
                    raise RuntimeError(
                        f"Failed to initialize KiCad manager: {e}"
                    ) from e
    return _kicad_manager


def reset_kicad_manager():
    """重置管理器（用于测试或重新连接）- 线程安全版本"""
    global _kicad_manager
    with _manager_lock:
        if _kicad_manager:
            _kicad_manager.cleanup()
        _kicad_manager = None


# ========== 封装库 API 方法 ==========


def get_footprint_recommendations(
    component_name: str,
    component_value: Optional[str] = None,
    package: Optional[str] = None,
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
