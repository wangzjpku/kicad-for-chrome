"""
KiCad IPC 自动启动器
自动完成：启动 KiCad → 启用 IPC Server
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入 GUI 自动化库
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not available, will use manual mode")

try:
    import win32gui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("win32gui not available")


class AutoIPCStarter:
    """自动启动 KiCad IPC"""

    def __init__(self, kicad_path: str = None):
        if kicad_path is None:
            # 默认路径
            self.kicad_path = Path("E:/Program Files/KiCad/9.0/bin/kicad.exe")
        else:
            self.kicad_path = Path(kicad_path)

        self.kicad_process: Optional[subprocess.Popen] = None
        self.max_wait = 60  # 最大等待秒数

    def find_kicad_window(self) -> Optional[int]:
        """查找 KiCad 主窗口"""
        if not WIN32_AVAILABLE:
            return None

        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and "kicad" in title.lower():
                    windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        return windows[0] if windows else None

    def wait_for_window(self, timeout: int = 30) -> bool:
        """等待 KiCad 窗口出现"""
        logger.info("等待 KiCad 窗口出现...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            hwnd = self.find_kicad_window()
            if hwnd:
                logger.info(f"KiCad 窗口已找到: {hwnd}")
                # 额外等待确保窗口完全加载
                time.sleep(2)
                return True
            time.sleep(1)

        logger.warning("等待窗口超时")
        return False

    def click_menu_item(self, menu_path: list) -> bool:
        """
        点击菜单项
        menu_path: ["Tools", "External Plugin", "Start Server"]
        """
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI 不可用，无法自动点击菜单")
            return False

        try:
            # 获取屏幕尺寸
            screen_width, screen_height = pyautogui.size()
            logger.info(f"屏幕尺寸: {screen_width}x{screen_height}")

            # 方法1: 使用 alt 键打开菜单
            # KiCad 菜单通常可以用 Alt+字母快捷键访问
            # Tools = Alt+T

            # 点击菜单栏的 Tools
            logger.info("点击 Tools 菜单...")

            # 尝试查找菜单位置 - 需要先激活窗口
            hwnd = self.find_kicad_window()
            if hwnd:
                # 激活窗口
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.5)

            # 使用键盘快捷键打开 Tools 菜单
            pyautogui.press('alt')
            time.sleep(0.3)
            pyautogui.press('t')
            time.sleep(0.5)

            # 输入向下键选择 External Plugin
            logger.info("选择 External Plugin...")
            # Tools 菜单打开后，需要按 P 选择 External Plugin (P)
            pyautogui.press('p')
            time.sleep(0.5)

            # 按 S 选择 Start Server
            logger.info("选择 Start Server...")
            pyautogui.press('s')
            time.sleep(1)

            logger.info("IPC Server 启动命令已发送")
            return True

        except Exception as e:
            logger.error(f"点击菜单失败: {e}")
            return False

    def auto_start_ipc(self) -> Tuple[bool, str]:
        """
        自动启动 KiCad 和 IPC
        返回: (成功标志, 消息)
        """
        # 检查 KiCad 是否存在
        if not self.kicad_path.exists():
            return False, f"KiCad 未找到: {self.kicad_path}"

        # 检查是否已经运行
        hwnd = self.find_kicad_window()
        if hwnd:
            logger.info("KiCad 已在运行")
        else:
            # 启动 KiCad
            logger.info(f"启动 KiCad: {self.kicad_path}")
            try:
                self.kicad_process = subprocess.Popen(
                    [str(self.kicad_path)],
                    cwd=str(self.kicad_path.parent),
                    start_new_session=True
                )
            except Exception as e:
                return False, f"启动 KiCad 失败: {e}"

            # 等待窗口出现
            if not self.wait_for_window(self.max_wait):
                return False, "等待 KiCad 窗口超时，请手动启动"

        # 如果没有 PyAutoGUI，提示用户手动操作
        if not PYAUTOGUI_AVAILABLE:
            return False, "请在 KiCad 中手动操作: Tools → External Plugin → Start Server"

        # 自动点击菜单
        success = self.click_menu_item(["Tools", "External Plugin", "Start Server"])

        if success:
            return True, "IPC Server 已自动启动"
        else:
            return False, "自动启动失败，请手动操作"

    def check_ipc_status(self) -> bool:
        """检查 IPC 是否已启用"""
        try:
            import requests
            response = requests.get(
                "http://localhost:8000/api/kicad-ipc/status",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("connected", False)
        except:
            pass
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="KiCad IPC 自动启动器")
    parser.add_argument("--kicad-path", help="KiCad 可执行文件路径")
    parser.add_argument("--wait", type=int, default=30, help="等待 KiCad 启动的超时时间")
    args = parser.parse_args()

    starter = AutoIPCStarter(args.kicad_path)
    starter.max_wait = args.wait

    success, message = starter.auto_start_ipc()

    if success:
        logger.info(f"✅ {message}")

        # 检查 IPC 状态
        logger.info("检查 IPC 连接状态...")
        for i in range(10):
            if starter.check_ipc_status():
                logger.info("✅ IPC 连接成功!")
                return 0
            time.sleep(1)

        logger.warning("IPC 已启用但连接未建立，请确保后端服务已启动")
    else:
        logger.error(f"❌ {message}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
