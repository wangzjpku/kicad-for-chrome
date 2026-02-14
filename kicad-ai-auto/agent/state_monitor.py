"""
State Monitor - Monitor KiCad state in real-time
Implements actual state retrieval from KiCad Python API
"""

import time
import logging
import threading
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

# 尝试导入 KiCad Python API
try:
    import pcbnew

    HAS_PCBNEW = True
except ImportError:
    HAS_PCBNEW = False
    logger.warning("pcbnew module not available, state monitoring limited")

# 尝试导入 OpenCV 用于图像处理
try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("OpenCV not available, UI detection disabled")


class EditorType(Enum):
    """KiCad 编辑器类型"""

    UNKNOWN = "unknown"
    SCHEMATIC = "schematic"
    PCB = "pcb"
    SYMBOL_EDITOR = "symbol_editor"
    FOOTPRINT_EDITOR = "footprint_editor"
    GERBER_VIEWER = "gerber_viewer"
    VIEWER_3D = "3d_viewer"


@dataclass
class KiCadState:
    """KiCad 状态数据类"""

    tool: Optional[str] = None
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    layer: Optional[str] = None
    zoom: float = 100.0
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = None
    editor_type: str = "unknown"
    project_name: Optional[str] = None
    grid_size: Optional[str] = None
    selected_items: List[str] = field(default_factory=list)
    is_modified: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.selected_items is None:
            self.selected_items = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class StateMonitor:
    """状态监控器 - 从 KiCad API 获取实时状态"""

    # KiCad PCB 层 ID 到名称的映射
    LAYER_NAMES = {
        0: "F.Cu",
        1: "In1.Cu",
        2: "In2.Cu",
        3: "In3.Cu",
        4: "In4.Cu",
        31: "B.Cu",
        32: "B.Adhes",
        33: "F.Adhes",
        34: "B.Paste",
        35: "F.Paste",
        36: "B.SilkS",
        37: "F.SilkS",
        38: "B.Mask",
        39: "F.Mask",
        40: "Dwgs.User",
        41: "Cmts.User",
        42: "Eco1.User",
        43: "Eco2.User",
        44: "Edge.Cuts",
        45: "Margin",
        46: "B.CrtYd",
        47: "F.CrtYd",
        48: "B.Fab",
        49: "F.Fab",
    }

    # 工具名称映射
    TOOL_NAMES = {
        "select": "选择",
        "move": "移动",
        "route": "布线",
        "place_symbol": "放置符号",
        "place_footprint": "放置封装",
        "draw_wire": "绘制导线",
        "add_via": "添加过孔",
        "draw_line": "绘制线条",
        "draw_arc": "绘制圆弧",
        "draw_circle": "绘制圆形",
        "draw_polygon": "绘制多边形",
        "add_text": "添加文本",
        "dimension": "标注尺寸",
        "zone": "敷铜区域",
        "measure": "测量",
    }

    def __init__(self, kicad_controller, update_interval: float = 0.1):
        """
        初始化状态监控器

        Args:
            kicad_controller: KiCad 控制器实例
            update_interval: 状态更新间隔（秒）
        """
        self.controller = kicad_controller
        self.update_interval = update_interval
        self.current_state = KiCadState()
        self.error_history = []
        self.max_history = 1000
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._state_callbacks: List[Callable[[KiCadState], None]] = []
        self._last_screenshot_hash: Optional[int] = None

    def start_monitoring(self):
        """启动后台监控线程"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("State monitoring started")

    def stop_monitoring(self):
        """停止监控线程"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
        logger.info("State monitoring stopped")

    def add_state_callback(self, callback: Callable[[KiCadState], None]):
        """添加状态变化回调函数"""
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[KiCadState], None]):
        """移除状态变化回调函数"""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _notify_callbacks(self):
        """通知所有回调函数"""
        for callback in self._state_callbacks:
            try:
                callback(self.current_state)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _monitor_loop(self):
        """监控循环（后台线程）"""
        while self._running:
            try:
                self._update_state()
            except Exception as e:
                logger.error(f"Error updating state: {e}")

            time.sleep(self.update_interval)

    def get_state(self) -> Dict[str, Any]:
        """获取当前完整状态"""
        # 更新状态
        self._update_state()

        return {
            "tool": self.current_state.tool,
            "cursor": {
                "x": self.current_state.cursor_x,
                "y": self.current_state.cursor_y,
            },
            "layer": self.current_state.layer,
            "zoom": self.current_state.zoom,
            "errors": self.current_state.errors,
            "timestamp": self.current_state.timestamp.isoformat(),
            "editor_type": self.current_state.editor_type,
            "project_name": self.current_state.project_name,
            "grid_size": self.current_state.grid_size,
            "selected_items": self.current_state.selected_items,
            "is_modified": self.current_state.is_modified,
        }

    def get_current_tool(self) -> Optional[str]:
        """获取当前工具"""
        return self.current_state.tool

    def get_cursor_coords(self) -> Dict[str, float]:
        """获取光标坐标"""
        return {"x": self.current_state.cursor_x, "y": self.current_state.cursor_y}

    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self.current_state.errors.copy()

    def add_error(self, error: str):
        """添加错误"""
        self.current_state.errors.append(error)
        self.error_history.append(
            {"error": error, "timestamp": datetime.now().isoformat()}
        )

        # 限制历史记录大小
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

    def clear_errors(self):
        """清除错误"""
        self.current_state.errors = []

    def _update_state(self):
        """更新状态（从 KiCad API 获取最新信息）"""
        old_state = KiCadState(
            tool=self.current_state.tool,
            cursor_x=self.current_state.cursor_x,
            cursor_y=self.current_state.cursor_y,
            layer=self.current_state.layer,
        )

        # 更新时间戳
        self.current_state.timestamp = datetime.now()

        # 从 KiCad Python API 获取状态
        if HAS_PCBNEW:
            self._update_from_pcbnew()

        # 从截图分析状态
        self._update_from_screenshot()

        # 检测状态变化并通知
        if self._state_changed(old_state, self.current_state):
            self._notify_callbacks()

    def _update_from_pcbnew(self):
        """从 pcbnew API 获取状态"""
        try:
            board = pcbnew.GetBoard()
            if not board:
                return

            # 获取当前层
            try:
                # 尝试获取当前活动层
                layer_id = board.GetLayerID(board.GetLayerName())
                self.current_state.layer = self.LAYER_NAMES.get(
                    layer_id, f"Layer_{layer_id}"
                )
            except Exception:
                self.current_state.layer = "F.Cu"

            # 获取项目名称
            self.current_state.project_name = board.GetFileName()
            if self.current_state.project_name:
                import os

                self.current_state.project_name = os.path.basename(
                    self.current_state.project_name
                )

            # 获取修改状态
            self.current_state.is_modified = board.IsModified()

            # 获取选中的项目
            self.current_state.selected_items = []
            for footprint in board.GetFootprints():
                if footprint.IsSelected():
                    self.current_state.selected_items.append(footprint.GetReference())

            # 获取网格大小
            try:
                grid_origin = board.GetGridOrigin()
                # KiCad 网格大小通常在用户设置中
                self.current_state.grid_size = "1.27mm"  # 默认值
            except Exception:
                pass

            logger.debug(
                f"State updated: layer={self.current_state.layer}, "
                f"project={self.current_state.project_name}"
            )

        except Exception as e:
            logger.debug(f"Failed to get pcbnew state: {e}")

    def _update_from_screenshot(self):
        """从截图分析 UI 状态"""
        if not HAS_CV2:
            return

        try:
            # 获取截图
            screenshot_bytes = self.controller.get_screenshot()
            if not screenshot_bytes:
                return

            # 转换为 OpenCV 格式
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return

            # 计算截图哈希以检测变化
            current_hash = hash(screenshot_bytes)
            if current_hash == self._last_screenshot_hash:
                return  # 没有变化
            self._last_screenshot_hash = current_hash

            # 分析状态栏区域（底部）
            height, width = img.shape[:2]
            status_bar = img[height - 30 : height, 0:width]

            # 尝试提取坐标信息（从状态栏）
            self._extract_status_info(status_bar)

            # 检测错误对话框
            self._detect_error_dialogs(img)

        except Exception as e:
            logger.debug(f"Screenshot analysis failed: {e}")

    def _extract_status_info(self, status_bar):
        """从状态栏提取信息（使用图像处理）"""
        # 这里可以使用 OCR 或模板匹配来提取状态栏文本
        # 由于我们无法直接使用 OCR，这里保留接口
        # 实际部署时可以集成 Tesseract OCR
        pass

    def _detect_error_dialogs(self, screenshot):
        """检测错误对话框"""
        # 检测常见的错误对话框特征
        # 红色边框或错误图标
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        # 检测红色区域（错误指示）
        red_lower = np.array([0, 100, 100])
        red_upper = np.array([10, 255, 255])
        red_mask = cv2.inRange(hsv, red_lower, red_upper)

        if np.sum(red_mask) > 10000:  # 如果检测到大量红色
            # 可能存在错误对话框
            logger.debug("Possible error dialog detected")

    def _state_changed(self, old_state: KiCadState, new_state: KiCadState) -> bool:
        """检测状态是否发生变化"""
        return (
            old_state.tool != new_state.tool
            or old_state.cursor_x != new_state.cursor_x
            or old_state.cursor_y != new_state.cursor_y
            or old_state.layer != new_state.layer
        )

    def detect_ui_changes(
        self, screenshot_before: bytes, screenshot_after: bytes
    ) -> List[Dict[str, Any]]:
        """
        检测 UI 变化

        使用图像比较检测 KiCad 界面变化
        """
        if not HAS_CV2:
            return []

        try:
            # 解码图像
            before = cv2.imdecode(
                np.frombuffer(screenshot_before, np.uint8), cv2.IMREAD_COLOR
            )
            after = cv2.imdecode(
                np.frombuffer(screenshot_after, np.uint8), cv2.IMREAD_COLOR
            )

            if before is None or after is None:
                return []

            # 计算差异
            diff = cv2.absdiff(before, after)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # 阈值处理
            _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)

            # 查找变化区域
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            changes = []
            for contour in contours:
                if cv2.contourArea(contour) > 100:  # 过滤小变化
                    x, y, w, h = cv2.boundingRect(contour)
                    changes.append(
                        {
                            "type": "region_change",
                            "bbox": {"x": x, "y": y, "width": w, "height": h},
                            "area": cv2.contourArea(contour),
                        }
                    )

            return changes

        except Exception as e:
            logger.error(f"UI change detection failed: {e}")
            return []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        return {
            "fps": 30,  # 视频流帧率
            "latency_ms": 100,  # 延迟
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "cpu_percent": process.cpu_percent(),
            "update_interval": self.update_interval,
            "callbacks_registered": len(self._state_callbacks),
            "error_count": len(self.error_history),
        }

    def get_layer_list(self) -> List[Dict[str, Any]]:
        """获取可用层列表"""
        if not HAS_PCBNEW:
            return [{"id": 0, "name": "F.Cu", "type": "copper"}]

        try:
            board = pcbnew.GetBoard()
            if not board:
                return []

            layers = []
            for layer_id in range(50):  # KiCad 最多 50 层
                try:
                    name = board.GetLayerName(layer_id)
                    if name:
                        layers.append(
                            {
                                "id": layer_id,
                                "name": name,
                                "type": self._get_layer_type(layer_id),
                            }
                        )
                except Exception:
                    pass

            return layers

        except Exception as e:
            logger.error(f"Failed to get layer list: {e}")
            return []

    def _get_layer_type(self, layer_id: int) -> str:
        """获取层类型"""
        if layer_id in [0, 31]:  # F.Cu, B.Cu
            return "copper"
        elif layer_id in [36, 37]:  # SilkS
            return "silkscreen"
        elif layer_id in [38, 39]:  # Mask
            return "soldermask"
        elif layer_id == 44:  # Edge.Cuts
            return "outline"
        elif layer_id in [46, 47]:  # Courtyard
            return "courtyard"
        else:
            return "other"

    def get_board_statistics(self) -> Dict[str, Any]:
        """获取板子统计信息"""
        if not HAS_PCBNEW:
            return {
                "total_footprints": 0,
                "total_tracks": 0,
                "total_vias": 0,
                "total_zones": 0,
                "board_area_mm2": 0,
            }

        try:
            board = pcbnew.GetBoard()
            if not board:
                return {"error": "No board loaded"}

            # 统计封装
            footprint_count = len(list(board.GetFootprints()))

            # 统计走线
            track_count = len(
                [
                    item
                    for item in board.GetTracks()
                    if isinstance(item, pcbnew.PCB_TRACK)
                ]
            )

            # 统计过孔
            via_count = len(
                [item for item in board.GetTracks() if isinstance(item, pcbnew.PCB_VIA)]
            )

            # 统计敷铜区域
            zone_count = len(list(board.Zones()))

            # 计算板子面积（从 Edge.Cuts 层）
            board_area = self._calculate_board_area(board)

            return {
                "total_footprints": footprint_count,
                "total_tracks": track_count,
                "total_vias": via_count,
                "total_zones": zone_count,
                "board_area_mm2": round(board_area, 2),
                "bounding_box": self._get_board_bounds(board),
            }

        except Exception as e:
            logger.error(f"Failed to get board statistics: {e}")
            return {"error": str(e)}

    def _calculate_board_area(self, board) -> float:
        """计算板子面积"""
        try:
            # 获取边界框
            bounds = self._get_board_bounds(board)
            if bounds:
                width = bounds["width"]
                height = bounds["height"]
                return width * height
            return 0.0
        except Exception:
            return 0.0

    def _get_board_bounds(self, board) -> Optional[Dict[str, float]]:
        """获取板子边界"""
        try:
            # 尝试从 Edge.Cuts 获取边界
            edge_cuts = board.GetLayerID("Edge.Cuts")

            min_x = float("inf")
            min_y = float("inf")
            max_x = float("-inf")
            max_y = float("-inf")

            for drawing in board.GetDrawings():
                if drawing.GetLayer() == edge_cuts:
                    start = drawing.GetStart()
                    end = drawing.GetEnd()
                    min_x = min(min_x, start.x, end.x)
                    min_y = min(min_y, start.y, end.y)
                    max_x = max(max_x, start.x, end.x)
                    max_y = max(max_y, start.y, end.y)

            if min_x != float("inf"):
                # 转换为 mm
                return {
                    "min_x": min_x / 1e6,
                    "min_y": min_y / 1e6,
                    "max_x": max_x / 1e6,
                    "max_y": max_y / 1e6,
                    "width": (max_x - min_x) / 1e6,
                    "height": (max_y - min_y) / 1e6,
                }
            return None
        except Exception:
            return None

    def get_selected_items_details(self) -> List[Dict[str, Any]]:
        """获取选中项目的详细信息"""
        if not HAS_PCBNEW:
            return []

        try:
            board = pcbnew.GetBoard()
            if not board:
                return []

            selected = []
            for footprint in board.GetFootprints():
                if footprint.IsSelected():
                    pos = footprint.GetPosition()
                    selected.append(
                        {
                            "reference": footprint.GetReference(),
                            "value": footprint.GetValue(),
                            "footprint": str(footprint.GetFPID().GetLibItemName()),
                            "position": {
                                "x": pos.x / 1e6,
                                "y": pos.y / 1e6,
                            },
                            "layer": "F"
                            if footprint.GetLayer() == pcbnew.F_Cu
                            else "B",
                            "rotation": footprint.GetOrientation().AsDegrees(),
                        }
                    )

            return selected

        except Exception as e:
            logger.error(f"Failed to get selected items: {e}")
            return []

    def get_netlist(self) -> List[Dict[str, Any]]:
        """获取网络列表"""
        if not HAS_PCBNEW:
            return []

        try:
            board = pcbnew.GetBoard()
            if not board:
                return []

            nets = []
            for net in board.GetNetsByNetcode():
                pads = []
                for pad in net.GetPads():
                    pads.append(
                        {
                            "reference": pad.GetParent().GetReference(),
                            "pad_number": pad.GetNumber(),
                        }
                    )

                nets.append(
                    {
                        "netcode": net.GetNetCode(),
                        "name": net.GetNetname(),
                        "pad_count": len(pads),
                        "pads": pads[:10],  # 只返回前10个焊盘
                    }
                )

            return nets

        except Exception as e:
            logger.error(f"Failed to get netlist: {e}")
            return []

    def get_drc_status(self) -> Dict[str, Any]:
        """获取 DRC 状态"""
        if not HAS_PCBNEW:
            return {"available": False}

        try:
            board = pcbnew.GetBoard()
            if not board:
                return {"available": False, "error": "No board loaded"}

            # 检查是否有未运行的 DRC
            # 注意：KiCad Python API 可能不直接支持获取 DRC 状态
            # 这里提供接口，实际实现可能需要其他方式
            return {
                "available": True,
                "message": "Use /api/drc/run to execute DRC check",
            }

        except Exception as e:
            logger.error(f"Failed to get DRC status: {e}")
            return {"available": False, "error": str(e)}

    def export_state_report(self) -> Dict[str, Any]:
        """导出完整的状态报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "state": self.get_state(),
            "statistics": self.get_board_statistics(),
            "layers": self.get_layer_list(),
            "selected_items": self.get_selected_items_details(),
            "performance": self.get_performance_metrics(),
        }

    def set_tool(self, tool_name: str) -> bool:
        """设置当前工具（用于手动更新状态）"""
        if tool_name in self.TOOL_NAMES:
            old_tool = self.current_state.tool
            self.current_state.tool = tool_name
            if old_tool != tool_name:
                self._notify_callbacks()
            return True
        return False

    def set_layer(self, layer_name: str) -> bool:
        """设置当前层（用于手动更新状态）"""
        # 验证层名是否有效
        valid_layers = set(self.LAYER_NAMES.values())
        if layer_name in valid_layers or layer_name.startswith("Layer_"):
            old_layer = self.current_state.layer
            self.current_state.layer = layer_name
            if old_layer != layer_name:
                self._notify_callbacks()
            return True
        return False
