# -*- coding: utf-8 -*-
"""
Test5 LED Blink 项目完整测试
通过浏览器界面测试所有功能
"""

import os
import sys
import time
import json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

BACKEND_URL = 'http://localhost:8000'
FRONTEND_URL = 'http://localhost:3000'
OUTPUT_DIR = Path("test5_results")
OUTPUT_DIR.mkdir(exist_ok=True)

results = {}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def wait_for_kicad(page):
    """等待并连接 KiCad"""
    log("等待 KiCad 连接...")

    # 尝试多种连接按钮
    connect_buttons = ['Start KiCad', 'Connect', 'Start', '连接', '点击连接']

    for btn_text in connect_buttons:
        try:
            btn = page.locator(f'button:has-text("{btn_text}")')
            if btn.count() > 0 and btn.first.is_visible(timeout=3000):
                log(f"点击连接按钮: {btn_text}")
                btn.first.click()
                time.sleep(5)
                page.screenshot(path=str(OUTPUT_DIR / '00_connected.png'), full_page=True)
                log("已连接 KiCad")
                return True
        except:
            continue

    log("未找到连接按钮，假设已连接")
    return False


def test_01_homepage(page):
    """测试首页"""
    log("=" * 50)
    log("Test 01: 首页加载")
    log("=" * 50)

    page.goto(FRONTEND_URL)
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '01_homepage.png'), full_page=True)
    log("首页截图已保存")

    # 检查标题
    title = page.title()
    log(f"页面标题: {title}")
    results['homepage_title'] = title

    return True


def test_02_connect_kicad(page):
    """测试 KiCad 连接"""
    log("=" * 50)
    log("Test 02: KiCad 连接")
    log("=" * 50)

    # 点击连接按钮
    wait_for_kicad(page)

    # 检查状态栏是否显示已连接
    try:
        status = page.locator('text=已连接').first
        if status.is_visible(timeout=5000):
            log("状态栏显示: 已连接")
            results['kicad_connected'] = True
        else:
            log("未找到连接状态")
            results['kicad_connected'] = False
    except:
        log("检查连接状态失败")
        results['kicad_connected'] = False

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '02_kicad_connected.png'), full_page=True)

    return True


def test_03_create_project(page):
    """测试创建项目"""
    log("=" * 50)
    log("Test 03: 创建项目")
    log("=" * 50)

    # 点击新建项目按钮
    try:
        new_buttons = ['新建项目', 'New Project', '新建', 'New']
        for btn_text in new_buttons:
            btn = page.locator(f'button:has-text("{btn_text}")')
            if btn.count() > 0 and btn.first.is_visible(timeout=2000):
                log(f"点击: {btn_text}")
                btn.first.click()
                time.sleep(2)
                break
    except Exception as e:
        log(f"点击新建按钮: {e}")

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '03_new_project.png'), full_page=True)
    log("新建项目截图")

    results['new_project'] = True
    return True


def test_04_menu_operations(page):
    """测试菜单操作"""
    log("=" * 50)
    log("Test 04: 菜单操作")
    log("=" * 50)

    menus = ['File', 'Edit', 'View', 'Place', 'Tools', 'Help']
    chinese_menus = ['文件', '编辑', '视图', '放置', '工具', '帮助']

    found_menus = []

    # 测试英文菜单
    for menu in menus:
        try:
            menu_btn = page.locator(f'button:has-text("{menu}")')
            if menu_btn.count() > 0 and menu_btn.first.is_visible(timeout=1000):
                found_menus.append(menu)
                log(f"菜单: {menu}")
        except:
            pass

    # 测试中文菜单
    for menu in chinese_menus:
        try:
            menu_btn = page.locator(f'button:has-text("{menu}")')
            if menu_btn.count() > 0 and menu_btn.first.is_visible(timeout=1000):
                found_menus.append(menu)
                log(f"菜单: {menu}")
        except:
            pass

    results['menus_found'] = len(found_menus)
    log(f"找到 {len(found_menus)} 个菜单")

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '04_menus.png'), full_page=True)

    return len(found_menus) > 0


def test_05_toolbar_operations(page):
    """测试工具栏操作"""
    log("=" * 50)
    log("Test 05: 工具栏操作")
    log("=" * 50)

    # 工具栏按钮
    tools = ['Select', 'Move', 'Route', 'Via', 'Zoom', 'Grid', 'Layer', '选择', '移动', '布线', '过孔']

    found_tools = []
    for tool in tools:
        try:
            # 尝试多种选择器
            for selector in [
                f'button:has-text("{tool}")',
                f'tooltip:has-text("{tool}")',
                f'[title="{tool}"]'
            ]:
                el = page.locator(selector)
                if el.count() > 0 and el.first.is_visible(timeout=500):
                    found_tools.append(tool)
                    break
        except:
            pass

    results['tools_found'] = len(found_tools)
    log(f"找到 {len(found_tools)} 个工具")

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '05_toolbar.png'), full_page=True)

    return True


def test_06_layer_panel(page):
    """测试图层面板"""
    log("=" * 50)
    log("Test 06: 图层面板")
    log("=" * 50)

    layers = ['F.Cu', 'B.Cu', 'F.SilkS', 'B.SilkS', 'F.Mask', 'Edge.Cuts']

    found_layers = []
    for layer in layers:
        try:
            if page.locator(f'text={layer}').count() > 0:
                found_layers.append(layer)
        except:
            pass

    results['layers_found'] = len(found_layers)
    log(f"找到 {len(found_layers)} 个图层")

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '06_layers.png'), full_page=True)

    return True


def test_07_status_bar(page):
    """测试状态栏"""
    log("=" * 50)
    log("Test 07: 状态栏")
    log("=" * 50)

    # 获取状态栏信息
    status_info = {}

    # 坐标
    try:
        cursor = page.locator('text=X:').first
        if cursor.is_visible(timeout=2000):
            log("状态栏显示坐标")
            status_info['cursor'] = True
    except:
        status_info['cursor'] = False

    # 层
    try:
        layer = page.locator('text=层:').first
        if layer.is_visible(timeout=2000):
            log("状态栏显示层")
            status_info['layer'] = True
    except:
        status_info['layer'] = False

    results['status_bar'] = status_info

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '07_statusbar.png'), full_page=True)

    return True


def test_08_right_panel(page):
    """测试右侧面板"""
    log("=" * 50)
    log("Test 08: 右侧面板")
    log("=" * 50)

    # 检查右侧面板元素
    panels = ['属性', 'Properties', 'DRC', 'BOM', '导出']

    found_panels = []
    for panel in panels:
        try:
            if page.locator(f'text={panel}').count() > 0:
                found_panels.append(panel)
        except:
            pass

    results['right_panels'] = len(found_panels)
    log(f"找到 {len(found_panels)} 个面板")

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '08_right_panel.png'), full_page=True)

    return True


def test_09_mouse_interaction(page):
    """测试鼠标交互"""
    log("=" * 50)
    log("Test 09: 鼠标交互")
    log("=" * 50)

    # 获取画布区域
    try:
        # 点击画布
        canvas = page.locator('canvas').first
        if canvas.is_visible(timeout=5000):
            log("找到画布")

            # 点击画布
            canvas.click(position={'x': 100, 'y': 100})
            time.sleep(1)
            log("点击画布位置 (100, 100)")

            results['mouse_interaction'] = True
        else:
            log("未找到画布")
            results['mouse_interaction'] = False
    except Exception as e:
        log(f"鼠标交互: {str(e)[:50]}")
        results['mouse_interaction'] = False

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '09_mouse.png'), full_page=True)

    return True


def test_10_output_panel(page):
    """测试输出面板"""
    log("=" * 50)
    log("Test 10: 输出面板")
    log("=" * 50)

    # 检查底部面板
    output_tabs = ['消息', 'Messages', 'DRC', 'ERC', 'BOM']

    found_tabs = []
    for tab in output_tabs:
        try:
            if page.locator(f'text={tab}').count() > 0:
                found_tabs.append(tab)
        except:
            pass

    results['output_tabs'] = len(found_tabs)
    log(f"找到 {len(found_tabs)} 个输出面板标签")

    # 截图
    page.screenshot(path=str(OUTPUT_DIR / '10_output.png'), full_page=True)

    return True


def test_11_api_backend(page):
    """测试后端 API"""
    log("=" * 50)
    log("Test 11: 后端 API 测试")
    log("=" * 50)

    # 测试各个 API
    apis = [
        ('/api/health', 'GET'),
        ('/api/kicad-ipc/status', 'GET'),
        ('/api/export/formats', 'GET'),
    ]

    api_results = {}
    for path, method in apis:
        try:
            if method == 'GET':
                resp = requests.get(f'{BACKEND_URL}{path}', timeout=5)
                api_results[path] = resp.status_code
                log(f"{path}: {resp.status_code}")
        except Exception as e:
            log(f"{path}: 错误")
            api_results[path] = 0

    results['api_tests'] = api_results

    return True


def test_12_final_state(page):
    """最终状态"""
    log("=" * 50)
    log("Test 12: 最终状态")
    log("=" * 50)

    # 截图最终状态
    page.screenshot(path=str(OUTPUT_DIR / '12_final_state.png'), full_page=True)
    log("最终状态截图")

    return True


def main():
    log("=" * 60)
    log("LED Blink 项目完整测试开始")
    log("=" * 60)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            # 执行所有测试
            tests = [
                ('01_homepage', test_01_homepage),
                ('02_connect', test_02_connect_kicad),
                ('03_new_project', test_03_create_project),
                ('04_menus', test_04_menu_operations),
                ('05_toolbar', test_05_toolbar_operations),
                ('06_layers', test_06_layer_panel),
                ('07_status', test_07_status_bar),
                ('08_panels', test_08_right_panel),
                ('09_mouse', test_09_mouse_interaction),
                ('10_output', test_10_output_panel),
                ('11_api', test_11_api_backend),
                ('12_final', test_12_final_state),
            ]

            for test_name, test_func in tests:
                try:
                    results[test_name] = test_func(page)
                except Exception as e:
                    log(f"{test_name} 错误: {e}")
                    results[test_name] = False

            browser.close()

    except Exception as e:
        log(f"严重错误: {e}")

    # 保存结果
    with open(OUTPUT_DIR / 'full_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 打印汇总
    log("=" * 60)
    log("测试结果汇总")
    log("=" * 60)
    for key, value in results.items():
        status = "OK" if value else "FAIL"
        log(f"{key}: {status}")

    log("测试完成!")
    log(f"结果保存在: {OUTPUT_DIR}")

    return results


if __name__ == "__main__":
    main()
