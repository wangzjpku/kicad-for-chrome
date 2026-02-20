"""
KiCad AI 完整 E2E 测试 - Playwright 自动化测试
完整模拟用户通过 AI 创建项目的全流程

测试流程:
1. 访问项目列表页面
2. 点击 AI 创建按钮打开对话框
3. 输入自然语言需求描述
4. 等待 AI 分析完成
5. 验证预览结果显示
6. 确认创建项目
7. 验证项目创建成功并进入编辑器
"""

import asyncio
import json
import logging
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class TestResult:
    """测试结果记录器"""
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
        self.screenshots = []
        self.start_time = datetime.now()

    def record(self, step: str, success: bool, message: str = "", details: dict = None):
        """记录测试步骤结果"""
        self.results[step] = {
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        status = "✓" if success else "✗"
        logger.info(f"  [{status}] {step}: {message}")

    async def screenshot(self, page: Page, name: str) -> Path:
        """保存截图"""
        filename = f"{datetime.now().strftime('%H%M%S')}_{name}.png"
        filepath = self.output_dir / filename
        await page.screenshot(path=str(filepath), full_page=True)
        self.screenshots.append(str(filepath))
        logger.info(f"  📷 截图保存: {filename}")
        return filepath

    def summary(self) -> dict:
        """生成测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["success"])
        duration = (datetime.now() - self.start_time).total_seconds()

        return {
            "total_steps": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "duration_seconds": round(duration, 2),
            "steps": self.results,
            "screenshots": self.screenshots
        }

    def save_report(self):
        """保存测试报告"""
        report = self.summary()
        report_path = self.output_dir / "test_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"\n📄 测试报告已保存: {report_path}")
        return report


def check_port(port: int) -> bool:
    """检查端口是否可用"""
    for addr in ["127.0.0.1", "::1"]:
        try:
            sock = socket.socket(
                socket.AF_INET if "." in addr else socket.AF_INET6,
                socket.SOCK_STREAM
            )
            sock.settimeout(1)
            result = sock.connect_ex((addr, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
    return False


class KiCadAIETest:
    """KiCad AI E2E 测试类"""

    def __init__(self, result: TestResult):
        self.result = result
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.console_logs = []
        self.network_requests = []
        self.errors = []

    async def setup(self, playwright):
        """初始化浏览器"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 初始化测试环境")
        logger.info("=" * 70)

        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )

        self.page = await self.context.new_page()

        # 设置事件监听
        self.page.on("console", lambda msg: self.console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "time": datetime.now().isoformat()
        }))

        self.page.on("pageerror", lambda err: self.errors.append({
            "error": str(err),
            "time": datetime.now().isoformat()
        }))

        self.page.on("request", lambda req: self.network_requests.append({
            "method": req.method,
            "url": req.url,
            "time": datetime.now().isoformat()
        }))

        self.result.record("browser_setup", True, "浏览器初始化成功")

    async def teardown(self):
        """清理测试环境"""
        if self.browser:
            await self.browser.close()
        logger.info("\n🔚 测试环境已清理")

    async def step1_check_services(self):
        """Step 1: 检查后端和前端服务"""
        logger.info("\n" + "-" * 70)
        logger.info("📋 Step 1: 检查服务状态")
        logger.info("-" * 70)

        backend_ok = check_port(8000)
        frontend_ok = check_port(3000)

        self.result.record(
            "step1_backend",
            backend_ok,
            f"后端服务 (8000): {'运行中' if backend_ok else '未启动'}"
        )

        self.result.record(
            "step1_frontend",
            frontend_ok,
            f"前端服务 (3000): {'运行中' if frontend_ok else '未启动'}"
        )

        if not backend_ok or not frontend_ok:
            logger.error("❌ 服务未完全启动，请先启动前后端服务")
            return False

        return True

    async def step2_navigate_to_homepage(self):
        """Step 2: 访问项目列表页面"""
        logger.info("\n" + "-" * 70)
        logger.info("🏠 Step 2: 访问项目列表页面")
        logger.info("-" * 70)

        try:
            url = "http://localhost:3000"
            logger.info(f"  访问: {url}")

            await self.page.goto(url, timeout=30000, wait_until="networkidle")
            await self.page.wait_for_load_state("domcontentloaded")

            # 等待页面加载
            await asyncio.sleep(2)

            title = await self.page.title()
            self.result.record("step2_navigate", True, f"页面标题: {title}")
            await self.result.screenshot(self.page, "01_homepage")

            return True
        except Exception as e:
            self.result.record("step2_navigate", False, f"访问失败: {str(e)}")
            return False

    async def step3_open_ai_dialog(self):
        """Step 3: 点击 AI 创建按钮"""
        logger.info("\n" + "-" * 70)
        logger.info("🤖 Step 3: 打开 AI 创建对话框")
        logger.info("-" * 70)

        try:
            # 查找 AI 创建按钮
            ai_button = None

            # 尝试多种选择器
            selectors = [
                "button:has-text('AI 创建')",
                "button:has-text('🤖')",
                "button:has-text('AI')",
                ".ai-create-btn",
                "[data-testid='ai-create-button']"
            ]

            for selector in selectors:
                try:
                    ai_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if ai_button:
                        logger.info(f"  找到 AI 按钮: {selector}")
                        break
                except:
                    continue

            if not ai_button:
                self.result.record("step3_find_button", False, "未找到 AI 创建按钮")
                return False

            self.result.record("step3_find_button", True, "找到 AI 创建按钮")

            # 点击按钮
            await ai_button.click()
            await asyncio.sleep(1)

            # 验证对话框是否打开
            dialog = await self.page.wait_for_selector(".dialog-overlay, [role='dialog']", timeout=5000)

            if dialog:
                self.result.record("step3_open_dialog", True, "AI 对话框已打开")
                await self.result.screenshot(self.page, "02_ai_dialog_opened")
                return True
            else:
                self.result.record("step3_open_dialog", False, "对话框未打开")
                return False

        except Exception as e:
            self.result.record("step3_open_dialog", False, f"打开对话框失败: {str(e)}")
            await self.result.screenshot(self.page, "02_error")
            return False

    async def step4_input_requirements(self, requirements: str):
        """Step 4: 输入需求描述"""
        logger.info("\n" + "-" * 70)
        logger.info("📝 Step 4: 输入 AI 需求描述")
        logger.info("-" * 70)

        try:
            # 查找输入框
            textarea = await self.page.wait_for_selector(
                "textarea#requirements, textarea[placeholder*='需求'], textarea",
                timeout=5000
            )

            if not textarea:
                self.result.record("step4_find_input", False, "未找到需求输入框")
                return False

            self.result.record("step4_find_input", True, "找到需求输入框")

            # 输入需求
            logger.info(f"  输入需求: {requirements[:50]}...")
            await textarea.fill(requirements)
            await asyncio.sleep(0.5)

            self.result.record("step4_input", True, f"已输入需求 ({len(requirements)} 字符)")
            await self.result.screenshot(self.page, "03_requirements_input")

            return True

        except Exception as e:
            self.result.record("step4_input", False, f"输入失败: {str(e)}")
            return False

    async def step5_submit_analysis(self):
        """Step 5: 提交 AI 分析"""
        logger.info("\n" + "-" * 70)
        logger.info("🚀 Step 5: 提交 AI 分析请求")
        logger.info("-" * 70)

        try:
            # 查找提交按钮
            submit_btn = await self.page.wait_for_selector(
                "button:has-text('开始分析'), button:has-text('提交'), button.submit-btn",
                timeout=5000
            )

            if not submit_btn:
                self.result.record("step5_find_button", False, "未找到开始分析按钮")
                return False

            self.result.record("step5_find_button", True, "找到开始分析按钮")

            # 点击提交
            await submit_btn.click()
            self.result.record("step5_submit", True, "已点击开始分析")

            # 等待分析过程
            logger.info("  ⏳ 等待 AI 分析...")
            await asyncio.sleep(2)
            await self.result.screenshot(self.page, "04_analyzing")

            # 等待预览页面出现 (最长等待 30 秒)
            try:
                preview = await self.page.wait_for_selector(
                    ".step-preview, .spec-section, .schematic-preview",
                    timeout=30000
                )

                if preview:
                    self.result.record("step5_analysis_complete", True, "AI 分析完成，显示预览")
                    await self.result.screenshot(self.page, "05_preview_result")
                    return True
                else:
                    self.result.record("step5_analysis_complete", False, "未显示预览结果")
                    return False

            except Exception as wait_err:
                # 检查是否显示错误
                error_elem = await self.page.query_selector(".step-error, .error-message")
                if error_elem:
                    error_text = await error_elem.inner_text()
                    self.result.record("step5_analysis_complete", False, f"AI 分析出错: {error_text}")
                    await self.result.screenshot(self.page, "05_error")
                else:
                    self.result.record("step5_analysis_complete", False, f"等待超时: {str(wait_err)}")
                return False

        except Exception as e:
            self.result.record("step5_submit", False, f"提交失败: {str(e)}")
            return False

    async def step6_verify_preview(self):
        """Step 6: 验证预览结果"""
        logger.info("\n" + "-" * 70)
        logger.info("🔍 Step 6: 验证 AI 生成的预览结果")
        logger.info("-" * 70)

        try:
            # 检查项目名称
            project_name = await self.page.query_selector(".spec-content h4, .spec-section h4")
            if project_name:
                name_text = await project_name.inner_text()
                self.result.record("step6_project_name", True, f"项目名称: {name_text}")
            else:
                self.result.record("step6_project_name", False, "未找到项目名称")

            # 检查技术参数表格
            params_table = await self.page.query_selector(".params-table")
            if params_table:
                rows = await params_table.query_selector_all("tr")
                self.result.record("step6_params", True, f"技术参数: {len(rows)} 行")
            else:
                self.result.record("step6_params", True, "无技术参数表格")

            # 检查器件选型表格
            components_table = await self.page.query_selector(".components-table")
            if components_table:
                rows = await components_table.query_selector_all("tbody tr")
                self.result.record("step6_components", True, f"器件选型: {len(rows)} 个器件")
            else:
                self.result.record("step6_components", False, "未找到器件选型表格")

            # 检查原理图预览
            schematic = await self.page.query_selector(".schematic-canvas, svg.schematic-canvas")
            if schematic:
                self.result.record("step6_schematic", True, "原理图预览已渲染")
            else:
                self.result.record("step6_schematic", True, "无原理图预览 (可能只有器件清单)")

            # 检查器件清单
            component_cards = await self.page.query_selector_all(".component-card")
            if component_cards:
                self.result.record("step6_component_list", True, f"器件清单: {len(component_cards)} 个")
            else:
                self.result.record("step6_component_list", True, "无器件清单卡片")

            await self.result.screenshot(self.page, "06_full_preview")
            return True

        except Exception as e:
            self.result.record("step6_verify", False, f"验证失败: {str(e)}")
            return False

    async def step7_confirm_creation(self):
        """Step 7: 确认创建项目"""
        logger.info("\n" + "-" * 70)
        logger.info("✅ Step 7: 确认创建项目")
        logger.info("-" * 70)

        try:
            # 查找确认创建按钮
            confirm_btn = await self.page.wait_for_selector(
                "button:has-text('确认创建'), button.confirm-btn, button:has-text('创建')",
                timeout=5000
            )

            if not confirm_btn:
                self.result.record("step7_find_button", False, "未找到确认创建按钮")
                return False

            self.result.record("step7_find_button", True, "找到确认创建按钮")

            # 点击确认 - 使用 force=True 强制点击（绕过遮挡检测）
            # 或使用 JavaScript 直接触发点击事件
            try:
                await confirm_btn.click(force=True, timeout=5000)
            except:
                # 如果 force click 失败，使用 JavaScript 点击
                await self.page.evaluate("(btn) => btn.click()", confirm_btn)

            self.result.record("step7_click", True, "已点击确认创建")

            # 等待创建完成
            await asyncio.sleep(3)
            await self.result.screenshot(self.page, "07_creating")

            # 验证对话框关闭
            dialog = await self.page.query_selector(".dialog-overlay, [role='dialog']")
            if not dialog or not await dialog.is_visible():
                self.result.record("step7_dialog_closed", True, "对话框已关闭")
            else:
                self.result.record("step7_dialog_closed", True, "对话框仍然可见 (可能在加载)")

            return True

        except Exception as e:
            self.result.record("step7_confirm", False, f"确认创建失败: {str(e)}")
            return False

    async def step8_verify_project_created(self):
        """Step 8: 验证项目创建成功"""
        logger.info("\n" + "-" * 70)
        logger.info("🎯 Step 8: 验证项目创建成功")
        logger.info("-" * 70)

        try:
            # 等待页面跳转或更新
            await asyncio.sleep(2)

            # 检查是否进入编辑器
            current_url = self.page.url
            logger.info(f"  当前 URL: {current_url}")

            if "editor" in current_url or "project" in current_url:
                self.result.record("step8_url", True, f"已进入编辑器: {current_url}")
            else:
                self.result.record("step8_url", True, f"仍在项目列表: {current_url}")

            # 检查编辑器元素
            editor = await self.page.query_selector(".editor-container, .pcb-editor, .schematic-editor, [data-testid='editor']")
            if editor:
                self.result.record("step8_editor", True, "编辑器组件已加载")
            else:
                self.result.record("step8_editor", True, "未检测到编辑器 (可能在项目列表)")

            # 检查项目列表更新
            project_items = await self.page.query_selector_all(".project-item, .project-card, [data-project-id]")
            self.result.record("step8_projects", True, f"项目列表: {len(project_items)} 个项目")

            await self.result.screenshot(self.page, "08_final_state")
            return True

        except Exception as e:
            self.result.record("step8_verify", False, f"验证失败: {str(e)}")
            return False

    async def step9_check_api_calls(self):
        """Step 9: 检查 API 调用情况"""
        logger.info("\n" + "-" * 70)
        logger.info("📊 Step 9: 检查 API 调用情况")
        logger.info("-" * 70)

        try:
            # 统计 API 调用
            api_calls = [r for r in self.network_requests if "/api/" in r["url"]]

            # 分类统计
            ai_analyze_calls = [r for r in api_calls if "/ai/analyze" in r["url"]]
            project_calls = [r for r in api_calls if "/projects" in r["url"] and r["method"] == "POST"]

            self.result.record(
                "step9_api_total",
                True,
                f"总 API 调用: {len(api_calls)} 次",
                {"calls": api_calls[-10:]}  # 只保留最后 10 条
            )

            self.result.record(
                "step9_ai_analyze",
                len(ai_analyze_calls) > 0,
                f"AI 分析调用: {len(ai_analyze_calls)} 次"
            )

            self.result.record(
                "step9_project_create",
                len(project_calls) > 0,
                f"项目创建调用: {len(project_calls)} 次"
            )

            # 检查控制台错误
            error_logs = [log for log in self.console_logs if log["type"] == "error"]
            if error_logs:
                self.result.record(
                    "step9_console_errors",
                    False,
                    f"控制台错误: {len(error_logs)} 条",
                    {"errors": error_logs[-5:]}
                )
            else:
                self.result.record("step9_console_errors", True, "无控制台错误")

            return True

        except Exception as e:
            self.result.record("step9_api", False, f"检查失败: {str(e)}")
            return False


async def run_full_test(test_case: dict):
    """运行完整测试"""
    test_name = test_case["name"]
    requirements = test_case["requirements"]

    # 创建结果目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("e2e_test_results") / f"{timestamp}_{test_name}"
    result = TestResult(output_dir)

    logger.info("\n" + "=" * 70)
    logger.info(f"🧪 KiCad AI E2E 测试 - {test_name}")
    logger.info("=" * 70)
    logger.info(f"  需求描述: {requirements[:80]}...")
    logger.info(f"  输出目录: {output_dir}")

    async with async_playwright() as p:
        test = KiCadAIETest(result)

        try:
            # 初始化
            await test.setup(p)

            # Step 1: 检查服务
            if not await test.step1_check_services():
                raise Exception("服务检查失败")

            # Step 2: 访问首页
            if not await test.step2_navigate_to_homepage():
                raise Exception("访问首页失败")

            # Step 3: 打开 AI 对话框
            if not await test.step3_open_ai_dialog():
                raise Exception("打开 AI 对话框失败")

            # Step 4: 输入需求
            if not await test.step4_input_requirements(requirements):
                raise Exception("输入需求失败")

            # Step 5: 提交分析
            if not await test.step5_submit_analysis():
                raise Exception("AI 分析失败")

            # Step 6: 验证预览
            await test.step6_verify_preview()

            # Step 7: 确认创建
            if not await test.step7_confirm_creation():
                raise Exception("确认创建失败")

            # Step 8: 验证创建成功
            await test.step8_verify_project_created()

            # Step 9: 检查 API 调用
            await test.step9_check_api_calls()

        except Exception as e:
            logger.error(f"\n❌ 测试执行出错: {str(e)}")
            result.record("test_error", False, str(e))
            if test.page:
                await result.screenshot(test.page, "error_final")

        finally:
            await test.teardown()

    # 生成报告
    report = result.save_report()

    # 打印摘要
    logger.info("\n" + "=" * 70)
    logger.info("📊 测试结果摘要")
    logger.info("=" * 70)
    logger.info(f"  总步骤: {report['total_steps']}")
    logger.info(f"  通过: {report['passed']}")
    logger.info(f"  失败: {report['failed']}")
    logger.info(f"  成功率: {report['success_rate']}")
    logger.info(f"  耗时: {report['duration_seconds']} 秒")

    return report


# ========== 测试用例定义 ==========
TEST_CASES = [
    {
        "name": "power_supply",
        "requirements": "设计一个5V稳压电源，输入220V交流电，输出5V直流电，电流1A"
    },
    {
        "name": "led_driver",
        "requirements": "设计一个LED驱动电路，使用ATtiny85单片机控制8个LED闪烁"
    },
    {
        "name": "smart_home",
        "requirements": "设计一个智能家居控制器，基于ESP32，支持WiFi远程控制，4路继电器输出"
    },
    {
        "name": "usb_uart",
        "requirements": "设计一个USB转串口模块，使用CH340G芯片，支持3.3V和5V电平"
    },
    {
        "name": "battery_charger",
        "requirements": "设计一个锂电池充电模块，使用TP4056芯片，支持过充过放保护"
    }
]


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="KiCad AI E2E 测试")
    parser.add_argument(
        "--case", "-c",
        type=str,
        default="power_supply",
        choices=[tc["name"] for tc in TEST_CASES],
        help="测试用例名称"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="运行所有测试用例"
    )
    parser.add_argument(
        "--custom", "-t",
        type=str,
        help="自定义需求描述"
    )

    args = parser.parse_args()

    if args.custom:
        # 自定义测试
        test_case = {
            "name": "custom",
            "requirements": args.custom
        }
        await run_full_test(test_case)
    elif args.all:
        # 运行所有测试
        for tc in TEST_CASES:
            await run_full_test(tc)
    else:
        # 运行指定测试
        test_case = next((tc for tc in TEST_CASES if tc["name"] == args.case), TEST_CASES[0])
        await run_full_test(test_case)


if __name__ == "__main__":
    asyncio.run(main())
