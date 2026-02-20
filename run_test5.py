# -*- coding: utf-8 -*-
"""
Test5 LED Blink 项目完整测试脚本
测试 LED_Blink_v1 项目的所有功能
"""

import os
import sys
import time
import json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

# 配置
BACKEND_URL = 'http://localhost:8000'
FRONTEND_URL = 'http://localhost:3000'
PROJECT_NAME = 'LED_Blink_v1'

output_dir = Path("test5_results")
output_dir.mkdir(exist_ok=True)

results = {}


def log(msg):
    """日志输出"""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def test_backend_api():
    """测试后端 API"""
    log("=" * 50)
    log("Phase 1: 后端 API 测试")
    log("=" * 50)

    # 健康检查
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        data = resp.json()
        log(f"后端状态: {data.get('status')}")
        log(f"KiCad 运行: {data.get('kicad_running')}")
        results['backend_health'] = True
    except Exception as e:
        log(f"后端 API 错误: {e}")
        results['backend_health'] = False


def test_kicad_connection():
    """测试 KiCad 连接"""
    log("=" * 50)
    log("Phase 2: KiCad 连接测试")
    log("=" * 50)

    # 尝试启动 KiCad
    try:
        resp = requests.post(f"{BACKEND_URL}/api/kicad-ipc/start", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                log("KiCad 启动成功")
                results['kicad_start'] = True
            else:
                log(f"KiCad 启动失败: {data}")
                results['kicad_start'] = False
        else:
            log(f"KiCad 启动失败: {resp.status_code}")
            results['kicad_start'] = False
    except Exception as e:
        log(f"KiCad 启动错误: {e}")
        results['kicad_start'] = False

    # 检查状态
    try:
        resp = requests.get(f"{BACKEND_URL}/api/kicad-ipc/status", timeout=5)
        status = resp.json()
        log(f"KiCad 连接状态: {status}")
    except:
        pass


def test_frontend():
    """测试前端界面"""
    log("=" * 50)
    log("Phase 3: 前端界面测试")
    log("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        # 访问前端
        page.goto(FRONTEND_URL)
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        # 截图
        page.screenshot(path=str(output_dir / '01_homepage.png'), full_page=True)
        log("首页截图已保存")

        # 检查菜单
        menus = ['File', 'Edit', 'View', 'Place', 'Tools', 'Help']
        found_menus = []
        for menu in menus:
            try:
                if page.locator(f'text={menu}').first.is_visible(timeout=1000):
                    found_menus.append(menu)
            except:
                pass

        log(f"找到菜单: {found_menus}")
        results['frontend_menus'] = len(found_menus) >= 4

        # 检查工具栏
        try:
            # 截图查看工具栏
            page.screenshot(path=str(output_dir / '02_toolbar.png'), full_page=True)
            log("工具栏截图已保存")
        except:
            pass

        browser.close()


def test_project_creation():
    """测试项目创建"""
    log("=" * 50)
    log("Phase 4: 项目创建测试")
    log("=" * 50)

    # 尝试通过 API 创建项目
    try:
        # 检查项目 API
        resp = requests.get(f"{BACKEND_URL}/api/project", timeout=5)
        log(f"项目列表 API 状态: {resp.status_code}")

        # 如果有项目，列出
        if resp.status_code == 200:
            projects = resp.json()
            log(f"现有项目: {projects}")

        results['project_api'] = True
    except Exception as e:
        log(f"项目 API 错误: {e}")
        results['project_api'] = False


def test_pcb_operations():
    """测试 PCB 操作 API"""
    log("=" * 50)
    log("Phase 5: PCB 操作测试")
    log("=" * 50)

    # 测试 IPC API 端点
    endpoints = [
        "/api/kicad-ipc/status",
        "/api/kicad-ipc/items",
        "/api/kicad-ipc/selection",
    ]

    for endpoint in endpoints:
        try:
            resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            log(f"{endpoint}: {resp.status_code}")
        except Exception as e:
            log(f"{endpoint}: 错误 - {str(e)[:50]}")


def test_export_functions():
    """测试导出功能"""
    log("=" * 50)
    log("Phase 6: 导出功能测试")
    log("=" * 50)

    # 检查导出 API
    try:
        # 获取导出格式
        resp = requests.get(f"{BACKEND_URL}/api/export/formats", timeout=5)
        if resp.status_code == 200:
            formats = resp.json()
            log(f"支持的格式: {formats}")
            results['export_formats'] = True
        else:
            log(f"导出格式 API: {resp.status_code}")
            results['export_formats'] = False
    except Exception as e:
        log(f"导出 API 错误: {e}")
        results['export_formats'] = False


def test_drc():
    """测试 DRC 功能"""
    log("=" * 50)
    log("Phase 7: DRC 测试")
    log("=" * 50)

    try:
        resp = requests.post(f"{BACKEND_URL}/api/drc/run", timeout=30)
        log(f"DRC 状态: {resp.status_code}")
        if resp.status_code == 200:
            results['drc'] = True
        else:
            results['drc'] = False
    except Exception as e:
        log(f"DRC 错误: {e}")
        results['drc'] = False


def save_results():
    """保存测试结果"""
    log("=" * 50)
    log("保存测试结果")
    log("=" * 50)

    # 保存到文件
    with open(output_dir / 'test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 保存详细日志
    with open(output_dir / 'test_log.txt', 'w', encoding='utf-8') as f:
        f.write("LED Blink 项目测试结果\n")
        f.write("=" * 50 + "\n")
        for key, value in results.items():
            f.write(f"{key}: {value}\n")

    log(f"结果已保存到 {output_dir}/")


def main():
    """主测试函数"""
    print("=" * 60)
    print("LED Blink 项目完整测试")
    print("=" * 60)

    # Phase 1: 后端 API
    test_backend_api()

    # Phase 2: KiCad 连接
    test_kicad_connection()

    # Phase 3: 前端
    test_frontend()

    # Phase 4: 项目创建
    test_project_creation()

    # Phase 5: PCB 操作
    test_pcb_operations()

    # Phase 6: 导出
    test_export_functions()

    # Phase 7: DRC
    test_drc()

    # 保存结果
    save_results()

    # 输出汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for key, value in results.items():
        status = "✓" if value else "✗"
        print(f"{status} {key}: {value}")

    print("\n测试完成！")
    return results


if __name__ == "__main__":
    main()
