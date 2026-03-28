"""
Smart KiCad IPC Server Starter
使用多种方法尝试启动IPC服务
"""
import logging
import win32gui
import win32con
import win32api
import time
import os

logger = logging.getLogger(__name__)


def find_pcb_editor():
    """找到PCB编辑器窗口"""
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and ('Pcbnew' in title or 'PCB' in title):
                windows.append((hwnd, title))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows[0] if windows else (None, None)


def activate_window(hwnd):
    """激活窗口"""
    if hwnd:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            logger.debug(f"激活窗口失败: {e}")
        time.sleep(0.3)


def click_at_percentage(hwnd, x_percent, y_offset=15):
    """根据窗口宽度百分比点击"""
    rect = win32gui.GetWindowRect(hwnd)
    width = rect[2] - rect[0]

    x = rect[0] + int(width * x_percent)
    y = rect[1] + y_offset

    win32api.SetCursorPos((x, y))
    time.sleep(0.2)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.8)

    return x, y


def method1_keyboard_navigation(hwnd):
    """方法1: 使用键盘导航"""
    print("  Method 1: Keyboard navigation...")

    activate_window(hwnd)
    time.sleep(0.3)

    # Alt+T 打开Tools菜单
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYDOWN, win32con.VK_MENU, 0)
    time.sleep(0.05)
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYDOWN, ord('T'), 0)
    time.sleep(0.05)
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYUP, ord('T'), 0)
    time.sleep(0.05)
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYUP, win32con.VK_MENU, 0)
    time.sleep(1.0)

    # 向下查找External Plugin
    for _ in range(12):
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_DOWN, 0)
        time.sleep(0.12)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_DOWN, 0)
        time.sleep(0.08)

    # 右箭头进入子菜单
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RIGHT, 0)
    time.sleep(0.15)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RIGHT, 0)
    time.sleep(0.5)

    # 向下找到Start Server
    for _ in range(3):
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_DOWN, 0)
        time.sleep(0.12)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_DOWN, 0)
        time.sleep(0.08)

    # 回车确认
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
    time.sleep(2.0)


def method2_mouse_click(hwnd):
    """方法2: 使用鼠标点击"""
    print("  Method 2: Mouse click...")

    activate_window(hwnd)

    # KiCad菜单布局: File, Edit, View, Tools, Place, Route, Inspect, Help
    # Tools 约在 30-35% 位置

    # 1. 点击Tools菜单 (32%位置)
    print("    Clicking Tools menu...")
    tx, ty = click_at_percentage(hwnd, 0.32, 15)

    # 2. 点击External Plugin (在弹出菜单中)
    # 弹出菜单位于Tools下方约80-120像素
    ep_x = tx + 60
    ep_y = ty + 100
    print(f"    Clicking External Plugin at ({ep_x}, {ep_y})...")
    win32api.SetCursorPos((ep_x, ep_y))
    time.sleep(0.3)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(1.0)

    # 3. 点击Start Server
    ss_x = ep_x + 80
    ss_y = ep_y + 20
    print(f"    Clicking Start Server at ({ss_x}, {ss_y})...")
    win32api.SetCursorPos((ss_x, ss_y))
    time.sleep(0.3)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(2.0)


def method3_alt_keyboard(hwnd):
    """方法3: 使用Alt+快捷键直接选择"""
    print("  Method 3: Alt+keyboard shortcuts...")

    activate_window(hwnd)
    time.sleep(0.3)

    # 直接发送Alt+对应菜单项的快捷键
    # Tools = Alt+T, E = External Plugin, S = Start Server

    # 打开Tools菜单
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYDOWN, 0x12, 0)  # Alt
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_CHAR, ord('T'), 0)  # T
    time.sleep(0.8)
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYUP, 0x12, 0)  # Release Alt
    time.sleep(0.5)

    # 现在菜单应该打开了，发送E选择External Plugin
    win32api.SendMessage(hwnd, win32con.WM_CHAR, ord('E'), 0)
    time.sleep(1.0)

    # 发送S选择Start Server
    win32api.SendMessage(hwnd, win32con.WM_CHAR, ord('S'), 0)
    time.sleep(2.0)


def check_socket_exists():
    """检查socket文件是否存在"""
    temp = os.environ.get('TEMP') or os.environ.get('TMP')
    socket_path = os.path.join(temp, 'kicad', 'api.sock')
    exists = os.path.exists(socket_path)

    # 也检查Windows命名管道
    # nng可能使用不同的命名方式

    return exists


def main():
    print("=" * 60)
    print("Smart KiCad IPC Server Starter")
    print("=" * 60)

    # 1. 查找窗口
    print("\n[1] Finding PCB Editor window...")
    hwnd, title = find_pcb_editor()

    if not hwnd:
        print("  ERROR: PCB Editor not found!")
        print("  Please open a PCB project in KiCad first.")
        return

    print(f"  Found: {title} (HWND: {hwnd})")

    # 2. 尝试多种方法
    print("\n[2] Starting IPC Server...")

    # 尝试方法1
    method1_keyboard_navigation(hwnd)
    if check_socket_exists():
        print("  SUCCESS!")
        return

    # 尝试方法2
    method2_mouse_click(hwnd)
    if check_socket_exists():
        print("  SUCCESS!")
        return

    # 尝试方法3
    method3_alt_keyboard(hwnd)
    if check_socket_exists():
        print("  SUCCESS!")
        return

    # 3. 检查结果
    print("\n[3] Checking result...")
    if check_socket_exists():
        print("  SUCCESS: IPC Server is running!")
    else:
        print("  FAILED: Could not start IPC Server automatically")
        print("\n  Please try manually:")
        print("    1. Click on KiCad PCB Editor window")
        print("    2. Press Alt+T to open Tools menu")
        print("    3. Find and click 'External Plugin'")
        print("    4. Click 'Start Server'")


if __name__ == "__main__":
    main()
