#!/usr/bin/env python3
"""
Ralph Loop AI Dialog Playwright 测试
测试 AI 智能项目创建对话框的所有功能
"""

import asyncio
import sys
import os
import json

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

class AIAutomationTester:
    def __init__(self):
        self.base_url = "http://localhost:3001"
        self.passed = 0
        self.failed = 0
        self.results = []

    async def run(self):
        print("=" * 60)
        print("Ralph Loop AI Dialog Playwright Test")
        print("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1. 访问项目列表页面
                print("\n[T3.1.1] 测试对话框打开...")
                await page.goto(self.base_url, timeout=30000)
                await page.wait_for_load_state("networkidle")
                print(f"    页面标题: {await page.title()}")
                self.record_result("T3.1.1", True, "页面加载成功")

                # 2. 点击 AI 创建按钮
                print("\n[T3.1.1] 点击 AI 创建按钮...")
                ai_create_btn = page.locator('button:has-text("AI 创建")')
                if await ai_create_btn.is_visible():
                    await ai_create_btn.click()
                    await page.wait_for_timeout(1000)
                    print("    [PASS] 点击 AI 创建按钮")
                    self.record_result("T3.1.1_click", True, "AI 创建按钮点击成功")
                else:
                    print("    [FAIL] AI 创建按钮未找到")
                    self.record_result("T3.1.1_click", False, "AI 创建按钮未找到")
                    return

                # 3. 验证对话框打开
                print("\n[T3.1.1] 验证对话框...")
                dialog = page.locator('.dialog-overlay')
                if await dialog.is_visible():
                    print("    [PASS] 对话框已打开")
                    self.record_result("T3.1.1_dialog", True, "对话框打开成功")
                else:
                    print("    [FAIL] 对话框未打开")
                    self.record_result("T3.1.1_dialog", False, "对话框未打开")

                # 4. 验证标题
                dialog_title = page.locator('.dialog-header h2')
                title_text = await dialog_title.text_content()
                if "AI 智能创建项目" in title_text:
                    print(f"    [PASS] 标题正确: {title_text}")
                    self.record_result("T3.1.1_title", True, f"标题正确: {title_text}")
                else:
                    print(f"    [FAIL] 标题错误: {title_text}")
                    self.record_result("T3.1.1_title", False, f"标题错误: {title_text}")

                # T3.1.3: 测试输入区域
                print("\n[T3.1.3] 测试输入区域...")
                input_area = page.locator('textarea#requirements')
                if await input_area.is_visible():
                    await input_area.fill("设计一个5V稳压电源，输入220V交流")
                    print("    [PASS] 输入区域可用，可以输入文本")
                    self.record_result("T3.1.3_input", True, "输入区域正常")
                else:
                    print("    [FAIL] 输入区域未找到")
                    self.record_result("T3.1.3_input", False, "输入区域未找到")

                # T3.1.4: 测试提交按钮状态
                print("\n[T3.1.4] 测试提交按钮状态...")
                submit_btn = page.locator('button:has-text("开始分析")')
                if await submit_btn.is_enabled():
                    print("    [PASS] 提交按钮已启用")
                    self.record_result("T3.1.4_button", True, "提交按钮已启用")
                else:
                    print("    [FAIL] 提交按钮未启用")
                    self.record_result("T3.1.4_button", False, "提交按钮未启用")

                # T3.2.2: 提交需求测试
                print("\n[T3.2.2] 提交需求...")
                await submit_btn.click()
                print("    点击提交按钮")

                # 等待分析完成
                print("    等待 AI 分析...")
                await page.wait_for_timeout(3000)

                # 检查是否进入预览模式
                preview_section = page.locator('.step-preview')
                if await preview_section.is_visible():
                    print("    [PASS] 进入预览模式")
                    self.record_result("T3.2.2_preview", True, "成功进入预览模式")
                else:
                    # 检查是否还在分析中
                    analyzing = page.locator('.step-analyzing')
                    if await analyzing.is_visible():
                        await page.wait_for_timeout(5000)
                        if await preview_section.is_visible():
                            print("    [PASS] 分析完成，进入预览模式")
                            self.record_result("T3.2.2_preview", True, "成功进入预览模式")
                        else:
                            print("    [WARN] 仍在分析中，跳过预览测试")
                            self.record_result("T3.2.2_preview", False, "未能进入预览模式")
                    else:
                        print("    [FAIL] 未进入预览模式")
                        self.record_result("T3.2.2_preview", False, "未能进入预览模式")

                # T3.4.1: 方案内容显示测试
                print("\n[T3.4.1] 测试方案内容显示...")
                spec_section = page.locator('.spec-section')
                if await spec_section.is_visible():
                    # 检查项目名称
                    project_name = await spec_section.locator('h4').text_content()
                    print(f"    项目名称: {project_name}")
                    self.record_result("T3.4.1_name", True, f"项目名称: {project_name}")

                    # 检查器件表格
                    components_table = spec_section.locator('.components-table')
                    if await components_table.is_visible():
                        rows = await components_table.locator('tbody tr').count()
                        print(f"    器件数量: {rows}")
                        self.record_result("T3.4.1_components", True, f"器件数量: {rows}")
                    else:
                        print("    [WARN] 器件表格未找到")
                        self.record_result("T3.4.1_components", False, "器件表格未找到")
                else:
                    print("    [FAIL] 方案区域未找到")
                    self.record_result("T3.4.1_content", False, "方案区域未找到")

                # T3.5.1: 原理图预览测试
                print("\n[T3.5.1] 测试原理图预览...")
                schematic_section = page.locator('.schematic-section')
                if await schematic_section.is_visible():
                    print("    [PASS] 原理图预览区域可见")
                    self.record_result("T3.5.1_schematic", True, "原理图预览区域可见")
                else:
                    print("    [WARN] 原理图预览区域未找到")
                    self.record_result("T3.5.1_schematic", False, "原理图预览区域未找到")

                # T3.6.1: 确认创建项目测试
                print("\n[T3.6.1] 测试确认创建...")
                confirm_btn = page.locator('button:has-text("确认创建")')
                if await confirm_btn.is_visible():
                    await confirm_btn.click()
                    await page.wait_for_timeout(2000)
                    print("    [PASS] 点击确认创建按钮")
                    self.record_result("T3.6.1_confirm", True, "确认创建按钮点击成功")

                    # 验证项目是否创建成功
                    await page.wait_for_timeout(1000)
                    # 检查对话框是否关闭
                    dialog_closed = not await page.locator('.dialog-overlay').is_visible()
                    if dialog_closed:
                        print("    [PASS] 对话框已关闭，项目可能已创建")
                        self.record_result("T3.6.1_created", True, "项目创建成功")
                    else:
                        print("    [WARN] 对话框未关闭")
                        self.record_result("T3.6.1_created", False, "项目创建失败")
                else:
                    print("    [FAIL] 确认创建按钮未找到")
                    self.record_result("T3.6.1_confirm", False, "确认创建按钮未找到")

                # 保存截图
                print("\n[T3.10] 保存测试截图...")
                await page.screenshot(path="ai_dialog_test.png", full_page=True)
                print("    截图: ai_dialog_test.png")
                self.record_result("T3.10_screenshot", True, "截图保存成功")

            except Exception as e:
                print(f"\n[错误] 测试异常: {e}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path="ai_dialog_error.png", full_page=True)
                self.record_result("ERROR", False, str(e))
                self.failed += 1

            finally:
                await browser.close()

        # 打印测试结果
        self.print_results()

    def record_result(self, test_id: str, passed: bool, message: str):
        """记录测试结果"""
        status = "PASS" if passed else "FAIL"
        if passed:
            self.passed += 1
        else:
            self.failed += 1

        self.results.append({
            "id": test_id,
            "status": status,
            "message": message
        })

    def print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        for result in self.results:
            status_symbol = "✓" if result["status"] == "PASS" else "✗"
            print(f"  {status_symbol} {result['id']}: {result['message']}")

        print("-" * 60)
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"总计: {self.passed + self.failed}")
        print(f"通过率: {self.passed * 100 / (self.passed + self.failed) if (self.passed + self.failed) > 0 else 0:.1f}%")
        print("=" * 60)


async def main():
    tester = AIAutomationTester()
    await tester.run()

if __name__ == "__main__":
    asyncio.run(main())
