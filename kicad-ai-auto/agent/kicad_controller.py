"""
KiCad Controller - Core control logic for KiCad automation
Includes retry logic, error handling, and resolution adaptation
"""

import os
import time
import subprocess
import base64
import io
import logging
import functools
from typing import Optional, Dict, List, Any, Tuple, Callable
from PIL import Image
import pyautogui

# 平台检测和导入
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# X11 导入 (仅 Linux)
HAS_XLIB = False
if IS_LINUX:
    try:
        from Xlib import display, X
        from Xlib.ext import composite

        HAS_XLIB = True
    except ImportError:
        logging.warning("python-xlib not available, using fallback screenshot")

# Windows 特定导入
if IS_WINDOWS:
    try:
        import win32gui
        import win32con
        import win32api
        import win32ui
        from win32gui import (
            GetWindowRect,
            FindWindow,
            GetWindowDC,
            ReleaseDC,
            DeleteObject,
        )
        from win32ui import CreateDCFromHandle, CreateBitmap

        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
        logging.warning("pywin32 not available, using fallback methods")

# 尝试导入 pyperclip 用于中文输入支持
try:
    import pyperclip

    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False
    logging.warning("pyperclip not available, Chinese input may not work")

# 导入自定义异常
from middleware import (
    KiCadError,
    KiCadNotRunningError,
    KiCadTimeoutError,
    KiCadCommandError,
    ProjectNotFoundError,
)

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,),
):
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 延迟增长因子
        exceptions: 需要重试的异常类型
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            raise last_exception

        return wrapper

    return decorator


class KiCadController:
    """
    KiCad 控制器
    通过 X11 和 PyAutoGUI 控制 KiCad 应用

    Features:
    - 自动分辨率适配
    - 重试机制
    - 详细错误处理
    - 操作日志
    """

    # 菜单坐标映射（基于 1920x1080 分辨率的相对坐标）
    MENU_COORDS_REL = {
        "file": {"x": 0.0156, "y": 0.0278},
        "edit": {"x": 0.0365, "y": 0.0278},
        "view": {"x": 0.0573, "y": 0.0278},
        "place": {"x": 0.0833, "y": 0.0278},
        "route": {"x": 0.1094, "y": 0.0278},
        "tools": {"x": 0.1354, "y": 0.0278},
        "help": {"x": 0.1615, "y": 0.0278},
    }

    # 菜单项映射（相对坐标）
    MENU_ITEMS_REL = {
        "file": {
            "new": {"x": 0.0156, "y": 0.0556},
            "open": {"x": 0.0156, "y": 0.0741},
            "save": {"x": 0.0156, "y": 0.0926},
            "export": {"x": 0.0156, "y": 0.1296},
        },
        "place": {
            "symbol": {"x": 0.0833, "y": 0.0556},
            "footprint": {"x": 0.0833, "y": 0.0741},
            "wire": {"x": 0.0833, "y": 0.0926},
            "text": {"x": 0.0833, "y": 0.1111},
        },
        "tools": {
            "drc": {"x": 0.1354, "y": 0.0556},
        },
    }

    # 工具快捷键映射
    TOOL_HOTKEYS = {
        "select": "esc",
        "move": "m",
        "route": "x",
        "place_symbol": "a",
        "place_footprint": "p",
        "draw_wire": "w",
        "add_via": "v",
        "drc": ["ctrl", "d"],
        "save": ["ctrl", "s"],
        "undo": ["ctrl", "z"],
        "redo": ["ctrl", "y"],
        "zoom_in": ["ctrl", "+"],
        "zoom_out": ["ctrl", "-"],
        "zoom_fit": ["ctrl", "home"],
        "copy": ["ctrl", "c"],
        "paste": ["ctrl", "v"],
        "delete": ["delete"],
    }

    def __init__(
        self, display_id: str = ":99", resolution: Tuple[int, int] = (1920, 1080)
    ):
        self.display_id = display_id
        self.resolution = resolution
        self.kicad_process: Optional[subprocess.Popen] = None
        self.x_display = None
        self.current_project: Optional[str] = None
        self._startup_timeout = 30  # 启动超时（秒）
        self._kicad_window_handle = None  # Windows 窗口句柄

        # 设置 PyAutoGUI
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        # 计算实际坐标
        self._update_menu_coords()

    def _update_menu_coords(self):
        """根据分辨率更新菜单坐标"""
        width, height = self.resolution

        self.MENU_COORDS = {
            menu: {"x": int(coords["x"] * width), "y": int(coords["y"] * height)}
            for menu, coords in self.MENU_COORDS_REL.items()
        }

        self.MENU_ITEMS = {}
        for menu, items in self.MENU_ITEMS_REL.items():
            self.MENU_ITEMS[menu] = {
                item: {"x": int(coords["x"] * width), "y": int(coords["y"] * height)}
                for item, coords in items.items()
            }

    def start(self, project_path: Optional[str] = None):
        """启动 KiCad"""
        if self.kicad_process and self.kicad_process.poll() is None:
            logger.info("KiCad is already running")
            return

        logger.info(f"Starting KiCad (Platform: {platform.system()})")

        # 设置环境变量
        env = os.environ.copy()

        # Windows 下使用完整路径
        kicad_exe = r"E:\Program Files\KiCad\9.0\bin\kicad.exe"

        # 构建命令
        cmd = [kicad_exe]
        if project_path and os.path.exists(project_path):
            cmd.append(project_path)
            self.current_project = project_path

        # 启动 KiCad
        self.kicad_process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # 等待 KiCad 启动
        time.sleep(3)

        # 连接 X11 (仅 Linux)
        if IS_LINUX and HAS_XLIB:
            try:
                env["DISPLAY"] = self.display_id
                self.x_display = display.Display(self.display_id)
                logger.info("Connected to X11 display")
            except Exception as e:
                logger.error(f"Failed to connect to X11: {e}")

        # Windows 下查找窗口句柄
        if IS_WINDOWS:
            self._find_kicad_window()

        logger.info("KiCad started successfully")

    def _find_kicad_window(self):
        """查找 KiCad 窗口句柄 (Windows)"""
        if not IS_WINDOWS:
            return

        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "KiCad" in title:
                    self._kicad_window_handle = hwnd
                    return False
            return True

        if HAS_WIN32:
            try:
                win32gui.EnumWindows(callback, None)
                if self._kicad_window_handle:
                    logger.info(f"Found KiCad window: {self._kicad_window_handle}")
            except Exception as e:
                logger.warning(f"Failed to find KiCad window: {e}")

    def is_running(self) -> bool:
        """检查 KiCad 是否正在运行"""
        if not self.kicad_process:
            return False
        return self.kicad_process.poll() is None

    def close(self):
        """关闭 KiCad"""
        logger.info("Closing KiCad...")

        if self.kicad_process:
            # 尝试优雅关闭
            self.kicad_process.terminate()

            # 等待最多 5 秒
            try:
                self.kicad_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 强制关闭
                self.kicad_process.kill()
                self.kicad_process.wait()

        self.kicad_process = None
        self.current_project = None

        logger.info("KiCad closed")

    def open_project(self, project_path: str):
        """打开项目"""
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project not found: {project_path}")

        # 使用菜单打开文件
        self.click_menu("file", "open")
        time.sleep(0.5)

        # 输入文件路径（假设文件对话框已打开）
        self.type_text(project_path)
        time.sleep(0.2)

        # 按 Enter 确认
        self.press_key("return")
        time.sleep(2)

        self.current_project = project_path
        logger.info(f"Opened project: {project_path}")

    def save_project(self):
        """保存项目"""
        self.activate_tool("save")
        time.sleep(0.5)
        logger.info("Project saved")

    def get_project_info(self) -> Dict[str, Any]:
        """获取项目信息"""
        return {
            "path": self.current_project,
            "name": os.path.basename(self.current_project)
            if self.current_project
            else None,
            "running": self.is_running(),
            "modified": None,  # TODO: 获取实际修改时间
        }

    # ========== 菜单操作 ==========

    def click_menu(self, menu: str, item: Optional[str] = None):
        """点击菜单"""
        if menu not in self.MENU_COORDS:
            raise ValueError(f"Unknown menu: {menu}")

        coords = self.MENU_COORDS[menu]
        pyautogui.click(coords["x"], coords["y"])
        time.sleep(0.2)

        if item:
            if menu not in self.MENU_ITEMS or item not in self.MENU_ITEMS[menu]:
                raise ValueError(f"Unknown menu item: {menu}.{item}")

            item_coords = self.MENU_ITEMS[menu][item]
            pyautogui.click(item_coords["x"], item_coords["y"])
            time.sleep(0.2)

        logger.debug(f"Clicked menu: {menu}.{item}")

    # ========== 工具操作 ==========

    def activate_tool(self, tool: str, params: Dict[str, Any] = None):
        """激活工具（修复版：正确处理组合键）"""
        if tool not in self.TOOL_HOTKEYS:
            raise ValueError(f"Unknown tool: {tool}")

        hotkey = self.TOOL_HOTKEYS[tool]

        # 修复：使用 hotkey() 正确处理组合键
        if isinstance(hotkey, list):
            pyautogui.hotkey(*hotkey)  # 使用 hotkey 而不是 keyDown/keyUp
        else:
            pyautogui.press(hotkey)

        time.sleep(0.1)
        logger.debug(f"Activated tool: {tool}")

    # ========== 鼠标操作 ==========

    def mouse_click(self, x: int, y: int, button: str = "left"):
        """鼠标点击"""
        pyautogui.click(x, y, button=button)
        logger.debug(f"Mouse click at ({x}, {y})")

    def mouse_double_click(self, x: int, y: int):
        """鼠标双击"""
        pyautogui.doubleClick(x, y)
        logger.debug(f"Mouse double-click at ({x}, {y})")

    def mouse_move(self, x: int, y: int):
        """鼠标移动"""
        pyautogui.moveTo(x, y)
        logger.debug(f"Mouse move to ({x}, {y})")

    def mouse_drag(self, x: int, y: int, duration: float = 0.5):
        """鼠标拖拽"""
        pyautogui.dragTo(x, y, duration=duration)
        logger.debug(f"Mouse drag to ({x}, {y})")

    def mouse_down(self, x: int, y: int):
        """鼠标按下"""
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()

    def mouse_up(self, x: int, y: int):
        """鼠标释放"""
        pyautogui.moveTo(x, y)
        pyautogui.mouseUp()

    # ========== 键盘操作 ==========

    def press_keys(self, keys: List[str]):
        """按下多个键（修复版：正确处理组合键）"""
        if len(keys) > 1:
            # 组合键使用 hotkey
            pyautogui.hotkey(*keys)
        else:
            # 单个键直接按下
            pyautogui.press(keys[0])
        logger.debug(f"Pressed keys: {keys}")

    def press_key(self, key: str):
        """按下单个键"""
        pyautogui.press(key)
        logger.debug(f"Pressed key: {key}")

    def type_text(self, text: str):
        """
        输入文本（支持中文）

        对于 ASCII 文本，使用 pyautogui.typewrite
        对于包含中文或其他非 ASCII 字符的文本，使用剪贴板粘贴
        """
        # 检查是否包含非 ASCII 字符
        if text.isascii():
            pyautogui.typewrite(text, interval=0.01)
        else:
            # 使用 pyperclip 支持中文输入
            if HAS_PYPERCLIP:
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)  # 给粘贴操作一点时间
            else:
                # 如果没有 pyperclip，尝试使用 ibus 或其他输入法
                logger.warning("pyperclip not available, Chinese input may fail")
                pyautogui.typewrite(text, interval=0.01)

        logger.debug(f"Typed text: {text[:50]}...")

    # ========== 屏幕截图 ==========

    def get_screenshot(self) -> bytes:
        """获取屏幕截图（PNG 格式）"""
        if HAS_XLIB and self.x_display:
            return self._get_screenshot_xlib()
        elif IS_WINDOWS and HAS_WIN32:
            return self._get_screenshot_windows()
        else:
            return self._get_screenshot_fallback()

    def get_screenshot_base64(self) -> str:
        """获取 Base64 编码的截图"""
        screenshot = self.get_screenshot()
        return base64.b64encode(screenshot).decode("utf-8")

    def _get_screenshot_xlib(self) -> bytes:
        """使用 Xlib 截图"""
        try:
            root = self.x_display.screen().root

            # 获取屏幕图像
            raw = root.get_image(
                0, 0, self.resolution[0], self.resolution[1], X.ZPixmap, 0xFFFFFFFF
            )

            # 转换为 PIL Image
            image = Image.frombytes("RGB", self.resolution, raw.data, "raw", "BGRX")

            # 转换为 bytes
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Xlib screenshot failed: {e}")
            return self._get_screenshot_fallback()

    def _get_screenshot_windows(self) -> bytes:
        """Windows 窗口截图 - 精确捕获 KiCad 窗口"""
        try:
            # 查找 KiCad 窗口句柄
            hwnd = self._find_kicad_window()

            if not hwnd:
                logger.warning("未找到 KiCad 窗口，使用全屏截图")
                return self._get_screenshot_fallback()

            # 首先尝试使用 PrintWindow API - 可以在窗口不在前端时截图
            try:
                logger.debug("尝试使用 PrintWindow 截图...")
                return self._get_screenshot_printwindow(hwnd)
            except Exception as e:
                logger.debug(f"PrintWindow 失败，使用传统方法: {e}")

            # 保存当前前台窗口
            current_foreground = win32gui.GetForegroundWindow()

            # 确保窗口可见并置顶
            # 1. 先恢复窗口（如果最小化）
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

            # 2. 置顶窗口
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
            )
            time.sleep(0.1)

            # 3. 激活窗口
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.3)  # 给窗口渲染时间

            # 获取窗口位置和大小
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            logger.debug(f"传统截图方法，窗口大小: {width}x{height}")

            # 检查窗口尺寸
            if width < 400 or height < 300:
                logger.warning(
                    f"窗口尺寸太小 ({width}x{height})，可能不是 KiCad 主窗口"
                )
                raise Exception(f"窗口尺寸无效: {width}x{height}")

            # 创建设备上下文 - 使用窗口DC而非客户区DC
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # 创建位图
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # 截图（使用 SRCCOPY 复制源像素）
            # 从 (0,0) 开始复制整个窗口（包括标题栏和非客户区）
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

            # 转换为 PIL Image
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)

            logger.debug(
                f"BitBlt 成功，位图大小: {bmpinfo['bmWidth']}x{bmpinfo['bmHeight']}"
            )

            # 清理资源
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            # 创建 PIL Image
            image = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            # 转换为 PNG bytes
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            screenshot_bytes = buffer.getvalue()

            logger.debug(f"传统截图成功，大小: {len(screenshot_bytes)} bytes")

            # 恢复原来的窗口状态
            if current_foreground and current_foreground != hwnd:
                try:
                    win32gui.SetWindowPos(
                        hwnd,
                        win32con.HWND_NOTOPMOST,
                        0,
                        0,
                        0,
                        0,
                        win32con.SWP_NOMOVE
                        | win32con.SWP_NOSIZE
                        | win32con.SWP_SHOWWINDOW,
                    )
                    win32gui.SetForegroundWindow(current_foreground)
                except:
                    pass

            return screenshot_bytes

        except Exception as e:
            logger.error(f"Windows 窗口截图失败: {e}")
            return self._get_screenshot_fallback()

    def _get_screenshot_printwindow(self, hwnd: int) -> bytes:
        """
        使用 PrintWindow API 截图 - 可以在窗口不在前端时截图
        这是 Windows 8+ 支持的功能
        """
        try:
            import ctypes
            from ctypes import windll

            # 获取窗口大小
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            logger.debug(f"PrintWindow 截图窗口大小: {width}x{height}")

            # 检查窗口尺寸是否有效
            if width < 100 or height < 100:
                raise Exception(
                    f"窗口尺寸太小 ({width}x{height})，可能不是 KiCad 主窗口"
                )

            # 创建设备上下文
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # 创建位图
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # 使用 PrintWindow API (PW_RENDERFULLCONTENT = 0x00000002)
            # 这个标志可以捕获窗口的完整内容，包括被遮挡的部分
            PW_RENDERFULLCONTENT = 0x00000002
            result = windll.user32.PrintWindow(
                hwnd, saveDC.GetSafeHdc(), PW_RENDERFULLCONTENT
            )

            if result == 0:
                # PrintWindow 失败，尝试旧版本 (0 = 仅客户区)
                logger.debug("PW_RENDERFULLCONTENT 失败，尝试普通模式...")
                result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

            if result == 0:
                raise Exception("PrintWindow API 调用失败")

            # 转换为 PIL Image
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)

            logger.debug(
                f"PrintWindow 成功，位图大小: {bmpinfo['bmWidth']}x{bmpinfo['bmHeight']}"
            )

            # 清理资源
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            # 创建图像
            image = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            # 转换为 PNG
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            screenshot_bytes = buffer.getvalue()

            logger.debug(f"PrintWindow 截图成功，大小: {len(screenshot_bytes)} bytes")

            # 检查截图是否为空（白色）
            if len(screenshot_bytes) < 1000:
                raise Exception(
                    f"截图数据太小 ({len(screenshot_bytes)} bytes)，可能是空白"
                )

            return screenshot_bytes

        except Exception as e:
            logger.warning(f"PrintWindow 截图失败: {e}")
            raise

    def _find_kicad_window(self) -> int:
        """查找 KiCad 主窗口句柄"""
        try:
            # 尝试不同的窗口标题模式，按优先级排序
            # 主窗口优先级最高
            window_patterns = [
                ("KiCad PCB Editor", True),  # PCB 编辑器（最高优先级）
                ("KiCad Schematic Editor", True),  # 原理图编辑器
                ("KiCad", False),  # 主窗口（仅当没有其他匹配时）
                ("Symbol Editor", True),  # 符号编辑器
                ("Footprint Editor", True),  # 封装编辑器
            ]

            logger.debug("开始查找 KiCad 窗口...")

            # 方法 1: 查找所有可见的 KiCad 窗口，选择最大的
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # 只考虑有标题的窗口
                        for pattern, exact in window_patterns:
                            if exact:
                                if pattern in title:
                                    # 获取窗口大小
                                    try:
                                        left, top, right, bottom = (
                                            win32gui.GetWindowRect(hwnd)
                                        )
                                        width = right - left
                                        height = bottom - top
                                        # 过滤掉太小的窗口（可能是控件或对话框）
                                        if width > 400 and height > 300:
                                            windows.append(
                                                (
                                                    hwnd,
                                                    title,
                                                    width * height,
                                                    width,
                                                    height,
                                                )
                                            )
                                    except:
                                        pass
                            else:
                                if pattern in title and pattern == title.strip():
                                    try:
                                        left, top, right, bottom = (
                                            win32gui.GetWindowRect(hwnd)
                                        )
                                        width = right - left
                                        height = bottom - top
                                        if width > 400 and height > 300:
                                            windows.append(
                                                (
                                                    hwnd,
                                                    title,
                                                    width * height,
                                                    width,
                                                    height,
                                                )
                                            )
                                    except:
                                        pass
                return True

            windows = []
            win32gui.EnumWindows(callback, windows)

            logger.debug(f"找到 {len(windows)} 个候选窗口")

            if windows:
                # 按窗口面积从大到小排序，返回最大的
                windows.sort(key=lambda x: x[2], reverse=True)
                hwnd, title, area, width, height = windows[0]
                logger.info(
                    f"找到 KiCad 主窗口: {title} ({width}x{height}, 句柄: {hwnd})"
                )
                return hwnd

            # 方法 2: 尝试精确匹配
            for pattern, exact in window_patterns:
                if exact:
                    hwnd = win32gui.FindWindow(None, pattern)
                    if hwnd:
                        try:
                            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                            width = right - left
                            height = bottom - top
                            if width > 400 and height > 300:
                                logger.info(
                                    f"找到 KiCad 窗口 (精确匹配): {pattern} ({width}x{height})"
                                )
                                return hwnd
                        except:
                            pass

            logger.warning("未找到 KiCad 主窗口（可能需要启动 KiCad 或打开项目）")
            return 0

        except Exception as e:
            logger.error(f"查找 KiCad 窗口时出错: {e}")
            return 0

    def _get_screenshot_fallback(self) -> bytes:
        """备用截图方法"""
        # 使用 PyAutoGUI 截图
        screenshot = pyautogui.screenshot()

        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        return buffer.getvalue()

    # ========== DRC ==========

    def run_drc(self) -> Dict[str, Any]:
        """运行 DRC 检查"""
        # 打开 DRC 对话框
        self.click_menu("tools", "drc")
        time.sleep(0.5)

        # 点击运行按钮
        pyautogui.click(400, 500)  # DRC 运行按钮位置
        time.sleep(2)

        # 关闭对话框
        self.press_key("esc")

        return {"success": True, "message": "DRC check completed"}

    def get_drc_report(self) -> Dict[str, Any]:
        """获取 DRC 报告"""
        # 这里需要解析 KiCad 生成的 DRC 报告文件
        # 暂时返回空结果
        return {"error_count": 0, "warning_count": 0, "errors": [], "warnings": []}

    # ========== 导出 ==========

    def export_gerber(
        self, output_dir: str, layers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """导出 Gerber 文件（使用 Python API）"""
        try:
            import pcbnew

            # 获取当前板子
            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            # 创建绘图控制器
            plot_controller = pcbnew.PLOT_CONTROLLER(board)
            plot_options = plot_controller.GetPlotOptions()
            plot_options.SetOutputDirectory(output_dir)

            # 层映射
            layer_map = {
                "F.Cu": pcbnew.F_Cu,
                "B.Cu": pcbnew.B_Cu,
                "F.SilkS": pcbnew.F_SilkS,
                "B.SilkS": pcbnew.B_SilkS,
                "F.Mask": pcbnew.F_Mask,
                "B.Mask": pcbnew.B_Mask,
                "Edge.Cuts": pcbnew.Edge_Cuts,
            }

            exported_files = []

            for layer_name, layer_id in layer_map.items():
                if layers is None or layer_name in layers:
                    plot_controller.SetLayer(layer_id)
                    plot_controller.OpenPlotfile(
                        layer_name, pcbnew.PLOT_FORMAT_GERBER, layer_name
                    )
                    plot_controller.PlotLayer()
                    exported_files.append(
                        {"layer": layer_name, "file": plot_controller.GetPlotFileName()}
                    )

            plot_controller.ClosePlot()

            return {"success": True, "files": exported_files, "output_dir": output_dir}

        except ImportError:
            logger.error("pcbnew module not available")
            return {"success": False, "error": "pcbnew module not available"}
        except Exception as e:
            logger.error(f"Failed to export Gerber: {e}")
            return {"success": False, "error": str(e)}

    def export_drill(self, output_dir: str) -> Dict[str, Any]:
        """导出钻孔文件"""
        try:
            import pcbnew

            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            drill_writer = pcbnew.EXCELLON_WRITER(board)
            drill_writer.SetMapFileFormat(pcbnew.PLOT_FORMAT_PDF)

            # 生成钻孔文件
            drill_writer.CreateDrillandMapFilesSet(
                output_dir,
                True,  # generate NPTH
                True,  # generate TH
            )

            return {
                "success": True,
                "files": [f"{output_dir}/drill.drl", f"{output_dir}/drill_map.pdf"],
            }

        except Exception as e:
            logger.error(f"Failed to export drill: {e}")
            return {"success": False, "error": str(e)}

    def export_bom(self, output_path: str) -> Dict[str, Any]:
        """导出物料清单"""
        try:
            import pcbnew
            import csv

            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            components = []

            for footprint in board.GetFootprints():
                component = {
                    "reference": footprint.GetReference(),
                    "value": footprint.GetValue(),
                    "footprint": str(footprint.GetFPID().GetLibItemName()),
                    "layer": "F" if footprint.GetLayer() == pcbnew.F_Cu else "B",
                }
                components.append(component)

            # 保存为 CSV
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["reference", "value", "footprint", "layer"]
                )
                writer.writeheader()
                writer.writerows(components)

            return {
                "success": True,
                "file": output_path,
                "component_count": len(components),
            }

        except Exception as e:
            logger.error(f"Failed to export BOM: {e}")
            return {"success": False, "error": str(e)}

    def export_pickplace(self, output_path: str) -> Dict[str, Any]:
        """导出 Pick & Place 文件"""
        try:
            import pcbnew
            import csv

            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            components = []

            for footprint in board.GetFootprints():
                pos = footprint.GetPosition()
                rotation = footprint.GetOrientation().AsDegrees()
                layer = "Top" if footprint.GetLayer() == pcbnew.F_Cu else "Bottom"

                component = {
                    "reference": footprint.GetReference(),
                    "value": footprint.GetValue(),
                    "footprint": str(footprint.GetFPID().GetLibItemName()),
                    "x": pos.x / 1000000.0,  # 转换为 mm
                    "y": pos.y / 1000000.0,
                    "rotation": rotation,
                    "layer": layer,
                }
                components.append(component)

            # 保存为 CSV
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "reference",
                        "value",
                        "footprint",
                        "x",
                        "y",
                        "rotation",
                        "layer",
                    ],
                )
                writer.writeheader()
                writer.writerows(components)

            return {
                "success": True,
                "file": output_path,
                "component_count": len(components),
            }

        except Exception as e:
            logger.error(f"Failed to export Pick & Place: {e}")
            return {"success": False, "error": str(e)}

    def export_pdf(self, output_path: str) -> Dict[str, Any]:
        """导出 PDF 文件"""
        try:
            import pcbnew

            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            plot_controller = pcbnew.PLOT_CONTROLLER(board)
            plot_options = plot_controller.GetPlotOptions()
            plot_options.SetOutputDirectory(os.path.dirname(output_path))

            # 导出当前层为 PDF
            plot_controller.SetLayer(pcbnew.F_Cu)
            plot_controller.OpenPlotfile("output", pcbnew.PLOT_FORMAT_PDF, "PCB Output")
            plot_controller.PlotLayer()
            plot_controller.ClosePlot()

            return {"success": True, "file": output_path}

        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            return {"success": False, "error": str(e)}

    def export_svg(self, output_path: str) -> Dict[str, Any]:
        """导出 SVG 文件"""
        try:
            import pcbnew

            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            plot_controller = pcbnew.PLOT_CONTROLLER(board)
            plot_options = plot_controller.GetPlotOptions()
            plot_options.SetOutputDirectory(os.path.dirname(output_path))

            # 导出当前层为 SVG
            plot_controller.SetLayer(pcbnew.F_Cu)
            plot_controller.OpenPlotfile("output", pcbnew.PLOT_FORMAT_SVG, "PCB Output")
            plot_controller.PlotLayer()
            plot_controller.ClosePlot()

            return {"success": True, "file": output_path}

        except Exception as e:
            logger.error(f"Failed to export SVG: {e}")
            return {"success": False, "error": str(e)}

    def export_step(self, output_path: str) -> Dict[str, Any]:
        """导出 STEP 3D 文件"""
        try:
            import pcbnew

            board = pcbnew.GetBoard()
            if not board:
                raise RuntimeError("No PCB board loaded")

            # 使用 KiCad 的 3D 导出功能
            exporter = pcbnew.STEP_EXPORTER(board)
            exporter.Export(output_path)

            return {"success": True, "file": output_path}

        except Exception as e:
            logger.error(f"Failed to export STEP: {e}")
            return {"success": False, "error": str(e)}
