"""
KiCad 截图诊断工具
用于排查截图白屏问题
"""

import sys
import os

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kicad_controller import KiCadController
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def diagnose_screenshot():
    """诊断截图问题"""
    print("=" * 60)
    print("KiCad 截图诊断工具")
    print("=" * 60)

    # 创建控制器
    controller = KiCadController()

    # 1. 检查窗口查找
    print("\n[1/4] 查找 KiCad 窗口...")
    hwnd = controller._find_kicad_window()
    if hwnd:
        print(f"✓ 找到窗口句柄: {hwnd}")
        try:
            import win32gui

            title = win32gui.GetWindowText(hwnd)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            print(f"  窗口标题: {title}")
            print(f"  窗口大小: {width}x{height}")
            if width < 400 or height < 300:
                print(f"  ⚠️ 警告: 窗口太小，可能不是主窗口!")
        except Exception as e:
            print(f"  ✗ 获取窗口信息失败: {e}")
    else:
        print("✗ 未找到 KiCad 窗口")
        print("  请确保 KiCad 已启动并打开了项目")
        return

    # 2. 测试 PrintWindow 截图
    print("\n[2/4] 测试 PrintWindow 截图...")
    try:
        screenshot = controller._get_screenshot_printwindow(hwnd)
        print(f"✓ PrintWindow 成功，截图大小: {len(screenshot)} bytes")
        # 保存截图
        with open("test_printwindow.png", "wb") as f:
            f.write(screenshot)
        print("  截图已保存到: test_printwindow.png")
    except Exception as e:
        print(f"✗ PrintWindow 失败: {e}")

    # 3. 测试传统截图方法
    print("\n[3/4] 测试传统截图方法...")
    try:
        screenshot = controller._get_screenshot_windows()
        print(f"✓ 传统方法成功，截图大小: {len(screenshot)} bytes")
        # 保存截图
        with open("test_windows.png", "wb") as f:
            f.write(screenshot)
        print("  截图已保存到: test_windows.png")
    except Exception as e:
        print(f"✗ 传统方法失败: {e}")

    # 4. 测试后备方法
    print("\n[4/4] 测试后备截图方法 (PyAutoGUI)...")
    try:
        screenshot = controller._get_screenshot_fallback()
        print(f"✓ 后备方法成功，截图大小: {len(screenshot)} bytes")
        # 保存截图
        with open("test_fallback.png", "wb") as f:
            f.write(screenshot)
        print("  截图已保存到: test_fallback.png")
    except Exception as e:
        print(f"✗ 后备方法失败: {e}")

    print("\n" + "=" * 60)
    print("诊断完成!")
    print("=" * 60)
    print("\n请检查生成的截图文件:")
    print("  - test_printwindow.png (PrintWindow API)")
    print("  - test_windows.png (传统方法)")
    print("  - test_fallback.png (全屏截图)")
    print("\n如果所有截图都是白色或很小，请确保:")
    print("  1. KiCad 已启动")
    print("  2. KiCad 窗口可见（未被最小化）")
    print("  3. KiCad 中已打开项目")


if __name__ == "__main__":
    diagnose_screenshot()
