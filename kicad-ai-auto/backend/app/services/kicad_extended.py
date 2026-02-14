"""
扩展的 KiCad IPC 管理器
支持完整 PCB 操作
"""

import os
import sys
import logging
import subprocess
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

# 尝试导入 kicad-python (kipy)
try:
    import kipy
    from kipy.board import Board, FootprintInstance, Track, Via, Zone
    from kipy.client import Client
    from kipy.common import Vector2
    from kipy.utils import from_mm, to_mm

    HAS_KIPY = True
except ImportError:
    HAS_KIPY = False
    logging.warning("kicad-python (kipy) not installed")

logger = logging.getLogger(__name__)


@dataclass
class KiCadConnectionConfig:
    """KiCad 连接配置"""

    kicad_cli_path: Optional[str] = None
    pcb_file_path: Optional[str] = None
    use_virtual_display: bool = False
    virtual_display_size: Tuple[int, int] = (1920, 1080)
    connection_timeout: int = 30


class KiCadExtendedManager:
    """
    扩展的 KiCad IPC 管理器
    支持完整的 PCB 编辑功能
    """

    def __init__(self, config: Optional[KiCadConnectionConfig] = None):
        self.config = config or KiCadConnectionConfig()
        self.client: Optional["Client"] = None
        self.board: Optional["Board"] = None
        self.kicad_process: Optional[subprocess.Popen] = None
        self._connected = False

    def start_kicad(self, pcb_file: Optional[str] = None) -> bool:
        """启动 KiCad 并建立 IPC 连接"""
        if pcb_file:
            self.config.pcb_file_path = pcb_file

        try:
            # 构建启动命令
            kicad_cmd = self._get_kicad_command()

            # 启动 KiCad
            logger.info(f"Starting KiCad: {kicad_cmd}")
            if self.config.pcb_file_path and os.path.exists(self.config.pcb_file_path):
                self.kicad_process = subprocess.Popen(
                    [kicad_cmd, self.config.pcb_file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                self.kicad_process = subprocess.Popen(
                    [kicad_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            # 等待启动
            time.sleep(5)

            # 建立 IPC 连接
            return self._connect_ipc()

        except Exception as e:
            logger.error(f"Failed to start KiCad: {e}")
            self.cleanup()
            return False

    def _get_kicad_command(self) -> str:
        """获取 KiCad 可执行文件路径"""
        if self.config.kicad_cli_path:
            base_dir = os.path.dirname(self.config.kicad_cli_path)
            if sys.platform == "win32":
                pcbnew_path = os.path.join(base_dir, "pcbnew.exe")
            elif sys.platform == "darwin":
                pcbnew_path = os.path.join(base_dir, "..", "MacOS", "pcbnew")
            else:
                pcbnew_path = os.path.join(base_dir, "pcbnew")

            if os.path.exists(pcbnew_path):
                return pcbnew_path

        # 默认路径
        default_paths = {
            "win32": [
                r"C:\Program Files\KiCad\9.0\bin\pcbnew.exe",
                r"C:\Program Files\KiCad\8.0\bin\pcbnew.exe",
            ],
            "darwin": [
                "/Applications/KiCad/pcbnew.app/Contents/MacOS/pcbnew",
            ],
            "linux": [
                "/usr/bin/pcbnew",
                "/usr/local/bin/pcbnew",
            ],
        }

        platform = sys.platform if sys.platform != "linux" else "linux"
        for path in default_paths.get(platform, []):
            if os.path.exists(path):
                return path

        return "pcbnew"

    def _connect_ipc(self) -> bool:
        """建立 IPC 连接"""
        if not HAS_KIPY:
            logger.error("kicad-python (kipy) not installed")
            return False

        try:
            logger.info("Connecting to KiCad via IPC...")
            start_time = time.time()

            while time.time() - start_time < self.config.connection_timeout:
                try:
                    self.client = Client()
                    version = self.client.get_version()
                    logger.info(f"Connected to KiCad {version}")
                    self._connected = True
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
            open_docs = self.client.get_open_documents()
            if open_docs:
                for doc in open_docs:
                    if doc.type == "pcb":
                        self.board = doc
                        logger.info(f"Current PCB: {doc.path}")
                        break
        except Exception as e:
            logger.warning(f"Could not get current board: {e}")

    # ==================== 封装操作 ====================

    def create_footprint(
        self,
        footprint_name: str,
        position: Tuple[float, float],
        layer: str = "F.Cu",
        reference: str = "",
        value: str = "",
    ) -> Dict[str, Any]:
        """创建封装"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            fpi = FootprintInstance()
            fpi.footprint_id = footprint_name
            fpi.position = Vector2(from_mm(position[0]), from_mm(position[1]))
            fpi.layer = layer

            created = self.board.create_items([fpi])

            if created:
                return {
                    "success": True,
                    "item_id": str(created[0].id),
                    "position": position,
                    "reference": reference,
                    "value": value,
                }
            return {"success": False, "error": "Creation returned empty"}

        except Exception as e:
            logger.error(f"Failed to create footprint: {e}")
            return {"success": False, "error": str(e)}

    def move_footprint(
        self, item_id: str, new_position: Tuple[float, float]
    ) -> Dict[str, Any]:
        """移动封装"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id and item.type == "footprint":
                    item.position = Vector2(
                        from_mm(new_position[0]), from_mm(new_position[1])
                    )
                    self.board.update_items([item])
                    return {
                        "success": True,
                        "item_id": item_id,
                        "new_position": new_position,
                    }

            return {"success": False, "error": f"Footprint {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to move footprint: {e}")
            return {"success": False, "error": str(e)}

    def rotate_footprint(self, item_id: str, angle: float) -> Dict[str, Any]:
        """旋转封装"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id and item.type == "footprint":
                    item.rotation = from_mm(angle)
                    self.board.update_items([item])
                    return {"success": True, "item_id": item_id, "rotation": angle}

            return {"success": False, "error": f"Footprint {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to rotate footprint: {e}")
            return {"success": False, "error": str(e)}

    def flip_footprint(self, item_id: str) -> Dict[str, Any]:
        """翻转封装到另一面"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id and item.type == "footprint":
                    # 切换层
                    item.layer = "B.Cu" if item.layer == "F.Cu" else "F.Cu"
                    self.board.update_items([item])
                    return {"success": True, "item_id": item_id, "layer": item.layer}

            return {"success": False, "error": f"Footprint {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to flip footprint: {e}")
            return {"success": False, "error": str(e)}

    def delete_footprint(self, item_id: str) -> Dict[str, Any]:
        """删除封装"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id and item.type == "footprint":
                    self.board.delete_items([item])
                    return {"success": True, "message": f"Footprint {item_id} deleted"}

            return {"success": False, "error": f"Footprint {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to delete footprint: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 走线操作 ====================

    def create_track(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        layer: str = "F.Cu",
        width: float = 0.25,
        net_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建走线"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
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
            return {"success": False, "error": "Track creation returned empty"}

        except Exception as e:
            logger.error(f"Failed to create track: {e}")
            return {"success": False, "error": str(e)}

    def delete_track(self, item_id: str) -> Dict[str, Any]:
        """删除走线"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            items = self.board.get_items()
            for item in items:
                if str(item.id) == item_id and item.type == "track":
                    self.board.delete_items([item])
                    return {"success": True, "message": f"Track {item_id} deleted"}

            return {"success": False, "error": f"Track {item_id} not found"}

        except Exception as e:
            logger.error(f"Failed to delete track: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 过孔操作 ====================

    def create_via(
        self,
        position: Tuple[float, float],
        size: float = 0.8,
        drill: float = 0.4,
        start_layer: str = "F.Cu",
        end_layer: str = "B.Cu",
        via_type: str = "through",
        net_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建过孔"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            via = Via()
            via.position = Vector2(from_mm(position[0]), from_mm(position[1]))
            via.size = from_mm(size)
            via.drill = from_mm(drill)
            via.layers = (start_layer, end_layer)

            created = self.board.create_items([via])

            if created:
                return {
                    "success": True,
                    "item_id": str(created[0].id),
                    "position": position,
                    "size": size,
                    "drill": drill,
                    "type": via_type,
                }
            return {"success": False, "error": "Via creation returned empty"}

        except Exception as e:
            logger.error(f"Failed to create via: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 铜皮操作 ====================

    def create_zone(
        self,
        outline: List[Tuple[float, float]],
        layer: str,
        net_id: Optional[str] = None,
        priority: int = 0,
    ) -> Dict[str, Any]:
        """创建铜皮区域"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            # 注意: kipy 可能不支持 Zone 操作，这里作为示例
            zone = Zone()
            zone.layer = layer
            zone.priority = priority

            created = self.board.create_items([zone])

            if created:
                return {
                    "success": True,
                    "item_id": str(created[0].id),
                    "layer": layer,
                    "priority": priority,
                }
            return {"success": False, "error": "Zone creation not supported or failed"}

        except Exception as e:
            logger.error(f"Failed to create zone: {e}")
            return {"success": False, "error": str(e)}

    def refill_zones(self) -> Dict[str, Any]:
        """重新灌铜"""
        if not self._connected or not self.board:
            return {"success": False, "error": "Not connected"}

        try:
            # 执行重新灌铜动作
            result = self.client.run_action("pcbnew.RefillAllZones", {})
            return {"success": True, "message": "Zones refilled", "result": result}

        except Exception as e:
            logger.error(f"Failed to refill zones: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 状态查询 ====================

    def get_board_status(self) -> Dict[str, Any]:
        """获取板子状态"""
        if not self._connected or not self.board:
            return {"connected": False, "error": "Not connected"}

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
                        "layer": getattr(item, "layer", None),
                    }
                    for item in items[:100]
                ]
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

    def get_statistics(self) -> Dict[str, Any]:
        """获取板子统计信息"""
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
            logger.error(f"Failed to get statistics: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 通用操作 ====================

    def save_board(self) -> Dict[str, Any]:
        """保存板子"""
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

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.client is not None

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up KiCad IPC connection...")

        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None

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

        self._connected = False
        logger.info("Cleanup complete")


# 单例模式
_kicad_manager: Optional[KiCadExtendedManager] = None


def get_kicad_manager() -> KiCadExtendedManager:
    """获取 KiCad 管理器单例"""
    global _kicad_manager
    if _kicad_manager is None:
        config = KiCadConnectionConfig(
            kicad_cli_path=os.getenv("KICAD_CLI_PATH"),
            use_virtual_display=os.getenv("USE_VIRTUAL_DISPLAY", "false").lower()
            == "true",
        )
        _kicad_manager = KiCadExtendedManager(config)
    return _kicad_manager
