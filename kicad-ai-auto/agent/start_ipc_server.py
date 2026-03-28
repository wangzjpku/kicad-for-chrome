"""
自动启动 KiCad External Plugin Server
使用正确的Windows菜单操作方式
"""
import logging
import win32gui
import win32con
import win32api
import time

logger = logging.getLogger(__name__)


def find_pcbnew_window():
    """查找 PCB Editor (Pcbnew) 窗口"""
    def enum_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and ('Pcbnew' in title or 'PCB 编辑器' in title):
                windows.append(hwnd)
        return True

    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows


def find_all_kicad_windows():
    """查找所有KiCad相关窗口"""
    def enum_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and ('KiCad' in title or 'Pcbnew' in title or 'PCB' in title):
                windows.append((hwnd, title))
        return True

    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows


def activate_window(hwnd):
    """激活窗口"""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
    except Exception as e:
        print(f"激活窗口失败: {e}")


def get_menu_item_by_text(hwnd, menubar, target_text):
    """
    通过菜单文本查找菜单项
    返回: (position, menu_id, submenu_handle)
    """
    # Tools菜单通常在位置6
    tools_menu = win32gui.GetSubMenu(menubar, 6)

    if not tools_menu:
        return None

    # 遍历Tools菜单查找External Plugin
    for i in range(20):
        try:
            text = win32gui.GetMenuString(tools_menu, i, win32con.MF_BYPOSITION)
            if text and 'External' in text:
                # 获取子菜单
                submenu = win32gui.GetSubMenu(tools_menu, i)
                if submenu:
                    # 在子菜单中查找Start Server
                    for j in range(10):
                        try:
                            sub_text = win32gui.GetMenuString(submenu, j, win32con.MF_BYPOSITION)
                            if sub_text and 'Start' in sub_text:
                                menu_id = win32gui.GetMenuItemID(submenu, j)
                                return (i, j, menu_id)
                        except Exception as e:
                            logger.debug(f"获取菜单项文本失败: {e}")
        except Exception as e:
            logger.debug(f"枚举菜单失败: {e}")

    return None


def send_menu_command_by_id(hwnd, menu_id):
    """通过菜单ID发送命令"""
    win32api.SendMessage(hwnd, win32con.WM_COMMAND, menu_id, 0)
    time.sleep(0.5)


def click_menu_by_mouse(hwnd, rect, menu_path):
    """
    通过鼠标点击菜单
    menu_path: [(x_percent, y_offset), ...]
    """
    w = rect[2] - rect[0]

    # 1. 点击Tools菜单 (约33%位置)
    tools_x = rect[0] + int(w * 0.33)
    tools_y = rect[1] + 15

    print(f"  点击Tools: ({tools_x}, {tools_y})")
    win32api.SetCursorPos((tools_x, tools_y))
    time.sleep(0.2)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.8)

    # 2. 点击External Plugin (在弹出菜单中向右偏移)
    ep_x = tools_x + 80
    ep_y = tools_y + 100

    print(f"  点击External Plugin: ({ep_x}, {ep_y})")
    win32api.SetCursorPos((ep_x, ep_y))
    time.sleep(0.2)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.8)

    # 3. 点击Start Server (在子菜单中)
    ss_x = ep_x + 80
    ss_y = ep_y + 20

    print(f"  点击Start Server: ({ss_x}, {ss_y})")
    win32api.SetCursorPos((ss_x, ss_y))
    time.sleep(0.2)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(1.0)


def send_keys_via_sendmessage(hwnd):
    """使用SendMessage发送Alt+快捷键序列"""
    # 激活窗口
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.3)

    # 1. 发送Alt键按下
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYDOWN, win32con.VK_MENU, 0)
    time.sleep(0.05)

    # 2. 发送T键 (打开Tools菜单)
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYDOWN, ord('T'), 0)
    time.sleep(0.05)
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYUP, ord('T'), 0)
    time.sleep(0.05)

    # 3. 释放Alt键
    win32api.SendMessage(hwnd, win32con.WM_SYSKEYUP, win32con.VK_MENU, 0)
    time.sleep(0.8)

    # 4. 现在使用方向键导航
    # 向下导航到External Plugin (约10次)
    for i in range(10):
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_DOWN, 0)
        time.sleep(0.1)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_DOWN, 0)
        time.sleep(0.1)

    time.sleep(0.3)

    # 5. 右箭头进入子菜单
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RIGHT, 0)
    time.sleep(0.15)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RIGHT, 0)
    time.sleep(0.3)

    # 6. 向下找到Start Server (约2次)
    for i in range(3):
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_DOWN, 0)
        time.sleep(0.1)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_DOWN, 0)
        time.sleep(0.1)

    time.sleep(0.3)

    # 7. 回车确认
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
    time.sleep(1.0)


def main():
    print("=" * 50)
    print("KiCad External Plugin Server 自动启动")
    print("=" * 50)

    # 1. 查找 KiCad 窗口
    print("\n[1] 查找 KiCad 窗口...")
    all_windows = find_all_kicad_windows()
    print(f"    找到 {len(all_windows)} 个 KiCad 相关窗口:")
    for h, t in all_windows:
        print(f"      - {t}")

    # 2. 查找 Pcbnew 窗口
    print("\n[2] 查找 PCB Editor 窗口...")
    pcbnew_windows = find_pcbnew_window()
    print(f"    找到 {len(pcbnew_windows)} 个 PCB Editor 窗口")

    if not pcbnew_windows:
        print("\n[!] 未找到 PCB Editor 窗口")
        print("    请先在 KiCad 中打开 PCB 编辑器 (Pcbnew)")
        print("    方法: 在KiCad项目管理器中双击一个PCB项目")
        return

    # 3. 激活 Pcbnew 窗口
    hwnd = pcbnew_windows[0]
    title = win32gui.GetWindowText(hwnd)
    print(f"\n[3] 激活窗口: {title}")
    activate_window(hwnd)

    # 获取窗口位置
    rect = win32gui.GetWindowRect(hwnd)
    print(f"    窗口位置: {rect}")

    # 4. 尝试启动 External Plugin Server
    print("\n[4] 启动 External Plugin Server...")

    # 方法1: 尝试使用SendMessage键盘导航
    print("    方法1: 使用键盘导航...")
    send_keys_via_sendmessage(hwnd)

    # 检查是否成功
    time.sleep(1)
    print("\n[!] 请检查 KiCad 窗口是否已启动 External Plugin Server")
    print("    如果未启动，请尝试方法2")

    # 可选：方法2 - 使用鼠标点击（备用）
    # print("\n    方法2: 使用鼠标点击...")
    # activate_window(hwnd)
    # click_menu_by_mouse(hwnd, rect, [])

    print("\n" + "=" * 50)
    print("提示: 如果自动启动失败，请手动操作:")
    print("  1. 在KiCad PCB编辑器窗口中")
    print("  2. 点击菜单: Tools -> External Plugin -> Start Server")
    print("=" * 50)


if __name__ == "__main__":
    main()
