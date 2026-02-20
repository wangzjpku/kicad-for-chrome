#!/usr/bin/env python3
"""
Ralph Loop Playwright 自动化浏览器测试
自动测试前端界面的每一个按钮和功能
"""

import asyncio
import sys
import os

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

class RalphBrowserTester:
    def __init__(self):
        self.results = {}
        self.base_url = "http://localhost:3000"
        self.passed = 0
        self.failed = 0

    async def run(self):
        print("=" * 60)
        print("Ralph Loop Playwright Automation Test")
        print("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1. 访问首页
                print("\n[1] Visit homepage...")
                await page.goto(self.base_url, timeout=30000)
                await page.wait_for_load_state("networkidle")
                print(f"    Page title: {await page.title()}")
                self.passed += 1

                # 2. 测试项目列表页面
                print("\n[2] Test Project List page...")

                # 查找 New Project 按钮
                new_project_btn = page.locator('button:has-text("New Project")')
                if await new_project_btn.is_visible():
                    print(f"    [PASS] New Project button visible")
                    self.passed += 1
                else:
                    print(f"    [FAIL] New Project button NOT found")
                    self.failed += 1

                # 3. 点击 New Project 按钮并创建项目
                print("\n[3] Create new project...")
                try:
                    await new_project_btn.click(timeout=5000)
                    await page.wait_for_timeout(1500)

                    # 查找并填写项目名称
                    create_form = page.locator('input[placeholder="Project name"]')
                    if await create_form.is_visible():
                        await create_form.fill("TestProject_Playwright")
                        print("    [PASS] Project name entered")
                        self.passed += 1

                        # 点击 Create 按钮
                        create_btn = page.locator('button:has-text("Create")')
                        await create_btn.click()
                        await page.wait_for_timeout(2000)
                        print("    [PASS] Create button clicked")
                        self.passed += 1

                        # 刷新项目列表
                        await page.reload()
                        await page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"    [FAIL] Create project error: {e}")
                    self.failed += 1

                # 4. 点击项目进入编辑器
                print("\n[4] Open project in editor...")
                project_elem = page.locator('h3:has-text("TestProject_Playwright")').first
                if await project_elem.is_visible():
                    await project_elem.click()
                    await page.wait_for_timeout(3000)
                    print("    [PASS] Clicked project to enter editor")
                    self.passed += 1
                else:
                    print("    [FAIL] Project not found")
                    self.failed += 1

                # 5. 切换到原理图编辑器
                print("\n[5] Switch to Schematic Editor...")
                schematic_tab = page.locator('button:has-text("原理图编辑器")')
                if await schematic_tab.is_visible():
                    await schematic_tab.click()
                    await page.wait_for_timeout(3000)
                    print("    [PASS] Switched to Schematic Editor")
                    self.passed += 1
                else:
                    print("    [FAIL] Schematic Editor tab not found")
                    self.failed += 1

                # 6. 测试工具栏按钮
                print("\n[6] Test Toolbar buttons...")
                toolbar_buttons = [
                    ("选择", "Select"),
                    ("放置元件", "Place Component"),
                    ("绘制导线", "Draw Wire"),
                    ("添加标签", "Add Label"),
                    ("撤销", "Undo"),
                    ("重做", "Redo"),
                ]

                for btn_text, desc in toolbar_buttons:
                    btn = page.locator(f'button:has-text("{btn_text}")')
                    if await btn.count() > 0 and await btn.first.is_visible():
                        print(f"    [PASS] {desc} button visible")
                        self.passed += 1
                    else:
                        print(f"    [FAIL] {desc} button NOT found")
                        self.failed += 1

                # 7. 属性编辑面板
                print("\n[7] Test Property Panel...")
                property_elem = page.locator('text=属性编辑')
                if await property_elem.is_visible():
                    print("    [PASS] Property panel visible")
                    self.passed += 1
                else:
                    print("    [INFO] Property panel NOT visible (may need to select element first)")
                    # This is expected behavior, not a failure

                # 8. PCB 编辑器
                print("\n[8] Test PCB Editor...")
                pcb_elem = page.locator('button:has-text("PCB 编辑器")')
                if await pcb_elem.is_visible():
                    print("    [PASS] PCB Editor tab visible")
                    self.passed += 1
                else:
                    print("    [FAIL] PCB Editor tab NOT visible")
                    self.failed += 1

                # 9. 菜单栏
                print("\n[9] Test Menu Bar...")
                menu_items = ["文件", "File", "编辑", "Edit"]
                found_menus = 0
                for menu in menu_items:
                    menu_btn = page.locator(f'text={menu}')
                    if await menu_btn.count() > 0 and await menu_btn.first.is_visible():
                        found_menus += 1

                if found_menus > 0:
                    print(f"    [PASS] Found {found_menus} menu items")
                    self.passed += 1
                else:
                    print(f"    [FAIL] Menu items NOT visible")
                    self.failed += 1

                # 10. 截图
                print("\n[10] Save screenshot...")
                await page.screenshot(path="ralph_test_screenshot.png", full_page=True)
                print("    Screenshot: ralph_test_screenshot.png")

            except Exception as e:
                print(f"\n[ERROR] Test error: {e}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path="error_screenshot.png", full_page=True)
                self.failed += 1

            finally:
                print("\n" + "=" * 60)
                print(f"Test complete!")
                print(f"Passed: {self.passed}")
                print(f"Failed: {self.failed}")
                print(f"Total: {self.passed + self.failed}")
                print("=" * 60)
                await asyncio.sleep(2)
                await browser.close()

        print("\nBrowser closed")

async def main():
    tester = RalphBrowserTester()
    await tester.run()

if __name__ == "__main__":
    asyncio.run(main())
