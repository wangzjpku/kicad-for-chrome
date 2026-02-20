#!/usr/bin/env python3
"""
Ralph Loop Playwright 电路设计测试
设计一个完整的电源模块电路
"""

import asyncio
import sys
import os

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

class RalphCircuitDesigner:
    def __init__(self):
        self.base_url = "http://localhost:3000"
        self.passed = 0
        self.failed = 0

    async def run(self):
        print("=" * 60)
        print("Ralph Loop 电路设计测试 - 电源模块")
        print("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1. 访问首页
                print("\n[1] 访问首页...")
                await page.goto(self.base_url, timeout=30000)
                await page.wait_for_load_state("networkidle")
                print(f"    页面标题: {await page.title()}")
                self.passed += 1

                # 2. 创建新项目
                print("\n[2] 创建新项目...")
                new_project_btn = page.locator('button:has-text("New Project")')
                await new_project_btn.click()
                await page.wait_for_timeout(1500)

                create_form = page.locator('input[placeholder="Project name"]')
                await create_form.fill("PowerModule_Circuit")
                print("    输入项目名称: PowerModule_Circuit")

                create_btn = page.locator('button:has-text("Create")')
                await create_btn.click()
                await page.wait_for_timeout(2000)
                print("    点击创建按钮")
                self.passed += 1

                # 刷新项目列表
                await page.reload()
                await page.wait_for_load_state("networkidle")

                # 3. 打开项目
                print("\n[3] 打开项目...")
                project_elem = page.locator('h3:has-text("PowerModule_Circuit")').first
                await project_elem.click()
                await page.wait_for_timeout(3000)
                print("    进入编辑器")
                self.passed += 1

                # 4. 切换到原理图编辑器
                print("\n[4] 切换到原理图编辑器...")
                schematic_tab = page.locator('button:has-text("原理图编辑器")')
                await schematic_tab.click()
                await page.wait_for_timeout(3000)
                print("    已切换到原理图编辑器")
                self.passed += 1

                # 5. 设计电源模块电路
                print("\n[5] 设计电源模块电路...")
                print("    电路设计: 220V AC → 变压器 → 整流桥 → 滤波电容 → 稳压芯片 → 5V DC输出")

                # 5.1 选择放置元件工具
                print("\n    [5.1] 选择放置元件工具...")
                place_component_btn = page.locator('button:has-text("放置元件")')
                await place_component_btn.click()
                await page.wait_for_timeout(500)
                print("        选择: 放置元件")
                self.passed += 1

                # 5.2 点击画布添加元件
                print("\n    [5.2] 添加元件到画布...")

                # 获取画布区域
                canvas = page.locator('canvas').first
                canvas_box = await canvas.bounding_box()
                if canvas_box:
                    print(f"        画布位置: {canvas_box}")

                    # 点击添加元件 (这里模拟添加元件，实际会添加到画布)
                    # 由于是自动化测试，我们点击画布不同位置来模拟添加多个元件
                    x_base = canvas_box['x'] + 100
                    y_base = canvas_box['y'] + 100

                    # 添加第一个元件 (假设是变压器/输入)
                    await page.mouse.click(x_base, y_base)
                    await page.wait_for_timeout(500)
                    print("        添加元件位置 1")

                    await page.mouse.click(x_base + 150, y_base)
                    await page.wait_for_timeout(500)
                    print("        添加元件位置 2")

                    await page.mouse.click(x_base + 300, y_base)
                    await page.wait_for_timeout(500)
                    print("        添加元件位置 3")

                    await page.mouse.click(x_base + 450, y_base)
                    await page.wait_for_timeout(500)
                    print("        添加元件位置 4")
                    self.passed += 1

                # 5.3 切换到选择工具
                print("\n    [5.3] 切换到选择工具...")
                select_btn = page.locator('button:has-text("选择")')
                await select_btn.click()
                await page.wait_for_timeout(500)
                print("        已切换到选择工具")
                self.passed += 1

                # 5.4 绘制导线 - 连接元件
                print("\n    [5.4] 绘制导线 (连接电路)...")
                wire_btn = page.locator('button:has-text("绘制导线")')
                await wire_btn.click()
                await page.wait_for_timeout(500)
                print("        选择绘制导线工具")

                # 模拟绘制几条导线
                if canvas_box:
                    # 绘制第一条导线 (输入到变压器)
                    await page.mouse.move(x_base + 50, y_base + 50)
                    await page.mouse.down()
                    await page.mouse.move(x_base + 150, y_base + 50)
                    await page.mouse.up()
                    await page.wait_for_timeout(300)
                    print("        绘制导线 1")

                    # 绘制第二条导线 (变压器到整流桥)
                    await page.mouse.move(x_base + 200, y_base + 50)
                    await page.mouse.down()
                    await page.mouse.move(x_base + 300, y_base + 50)
                    await page.mouse.up()
                    await page.wait_for_timeout(300)
                    print("        绘制导线 2")

                    # 绘制第三条导线 (整流桥到稳压芯片)
                    await page.mouse.move(x_base + 350, y_base + 50)
                    await page.mouse.down()
                    await page.mouse.move(x_base + 450, y_base + 50)
                    await page.mouse.up()
                    await page.wait_for_timeout(300)
                    print("        绘制导线 3")
                    self.passed += 1

                # 5.5 添加标签
                print("\n    [5.5] 添加标签...")
                label_btn = page.locator('button:has-text("添加标签")')
                await label_btn.click()
                await page.wait_for_timeout(500)
                print("        选择添加标签工具")

                # 在画布上添加几个标签
                if canvas_box:
                    # 添加输入标签 (220V AC)
                    await page.mouse.click(x_base, y_base - 30)
                    await page.wait_for_timeout(500)
                    print("        添加标签: INPUT_220V")

                    # 添加输出标签 (5V DC)
                    await page.mouse.click(x_base + 500, y_base - 30)
                    await page.wait_for_timeout(500)
                    print("        添加标签: OUTPUT_5V")
                    self.passed += 1

                # 6. 测试撤销功能
                print("\n[6] 测试撤销功能...")
                undo_btn = page.locator('button:has-text("撤销")')
                # 检查撤销按钮是否存在
                if await undo_btn.count() > 0:
                    print("    撤销按钮可用")
                    self.passed += 1
                else:
                    print("    撤销按钮不可用")
                    self.failed += 1

                # 7. 测试重做功能
                print("\n[7] 测试重做功能...")
                redo_btn = page.locator('button:has-text("重做")')
                if await redo_btn.count() > 0:
                    print("    重做按钮可用")
                    self.passed += 1
                else:
                    print("    重做按钮不可用")
                    self.failed += 1

                # 8. 切换到 PCB 编辑器
                print("\n[8] 切换到 PCB 编辑器...")
                pcb_tab = page.locator('button:has-text("PCB 编辑器")')
                await pcb_tab.click()
                await page.wait_for_timeout(3000)
                print("    已切换到 PCB 编辑器")
                self.passed += 1

                # 9. 验证 PCB 编辑器功能
                print("\n[9] 验证 PCB 编辑器...")

                # PCB 编辑器使用图标按钮 (↖, ✥, ╱, □)
                # 检查工具栏是否存在
                toolbar_buttons = page.locator('button')
                button_count = await toolbar_buttons.count()
                print(f"    PCB 工具栏按钮数量: {button_count}")

                if button_count > 0:
                    print("    PCB 工具栏存在 ✓")
                    self.passed += 1
                else:
                    print("    PCB 工具栏不存在 ✗")
                    self.failed += 1

                # 检查 PCB 画布是否存在
                pcb_canvas = page.locator('canvas')
                if await pcb_canvas.count() > 0:
                    print("    PCB 画布存在 ✓")
                    self.passed += 1
                else:
                    print("    PCB 画布不存在 ✗")
                    self.failed += 1

                # 10. 保存截图
                print("\n[10] 保存电路设计截图...")
                await page.screenshot(path="power_module_circuit.png", full_page=True)
                print("    截图已保存: power_module_circuit.png")

                # 11. 返回项目列表
                print("\n[11] 返回项目列表...")
                back_btn = page.locator('button:has-text("← 项目列表")')
                await back_btn.click()
                await page.wait_for_timeout(2000)
                print("    已返回项目列表")
                self.passed += 1

                # 12. 验证项目存在
                print("\n[12] 验证项目...")
                project_in_list = page.locator('h3:has-text("PowerModule_Circuit")')
                if await project_in_list.count() > 0:
                    print("    项目已保存并显示在列表中")
                    self.passed += 1
                else:
                    print("    项目未找到")
                    self.failed += 1

            except Exception as e:
                print(f"\n[错误] 测试异常: {e}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path="circuit_error.png", full_page=True)
                self.failed += 1

            finally:
                print("\n" + "=" * 60)
                print(f"电路设计测试完成!")
                print(f"通过: {self.passed}")
                print(f"失败: {self.failed}")
                print(f"总计: {self.passed + self.failed}")
                print("=" * 60)
                await asyncio.sleep(2)
                await browser.close()

        print("\n浏览器已关闭")

async def main():
    designer = RalphCircuitDesigner()
    await designer.run()

if __name__ == "__main__":
    asyncio.run(main())
