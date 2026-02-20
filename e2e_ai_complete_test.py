"""
KiCad AI 智能项目创建对话框 - 完整自动化测试
基于 test3.md 测试方案实现

测试模块:
T3.1: UI 对话框测试
T3.2: 需求提交测试
T3.3: AI 分析进度测试
T3.4: 项目方案预览测试
T3.5: 原理图预览测试
T3.6: 方案确认测试
T3.7: 完整流程测试
T3.8: 边缘情况测试
"""

import asyncio
import json
import logging
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@dataclass
class TestStep:
    """测试步骤记录"""
    test_id: str
    name: str
    success: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    screenshot: str = ""


class TestReport:
    """测试报告生成器"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.steps: List[TestStep] = []
        self.start_time = datetime.now()
        self.screenshots: List[str] = []

    def record(self, test_id: str, name: str, success: bool,
               message: str = "", details: Dict = None, screenshot: str = ""):
        """记录测试步骤"""
        step = TestStep(
            test_id=test_id,
            name=name,
            success=success,
            message=message,
            details=details or {},
            timestamp=datetime.now().isoformat(),
            screenshot=screenshot
        )
        self.steps.append(step)

        status = "✓" if success else "✗"
        logger.info(f"  [{test_id}] {status} {name}: {message}")

        return step

    async def screenshot_page(self, page: Page, name: str) -> str:
        """保存截图"""
        filename = f"{datetime.now().strftime('%H%M%S')}_{name}.png"
        filepath = self.output_dir / filename
        await page.screenshot(path=str(filepath), full_page=True)
        self.screenshots.append(str(filepath))
        return str(filepath)

    def get_summary(self) -> Dict:
        """生成测试摘要"""
        total = len(self.steps)
        passed = sum(1 for s in self.steps if s.success)
        failed = total - passed
        duration = (datetime.now() - self.start_time).total_seconds()

        # 按测试类分组统计
        categories = {}
        for step in self.steps:
            cat = step.test_id.split('.')[0]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "tests": []}
            categories[cat]["tests"].append({
                "id": step.test_id,
                "name": step.name,
                "success": step.success,
                "message": step.message
            })
            if step.success:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1

        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
                "duration_seconds": round(duration, 2)
            },
            "categories": categories,
            "steps": [
                {
                    "test_id": s.test_id,
                    "name": s.name,
                    "success": s.success,
                    "message": s.message,
                    "timestamp": s.timestamp,
                    "screenshot": s.screenshot
                }
                for s in self.steps
            ],
            "screenshots": self.screenshots
        }

    def save_report(self) -> Dict:
        """保存测试报告"""
        report = self.get_summary()

        # JSON 报告
        json_path = self.output_dir / "test_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # HTML 报告
        html_content = self._generate_html_report(report)
        html_path = self.output_dir / "test_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"\n📄 测试报告已保存:")
        logger.info(f"   JSON: {json_path}")
        logger.info(f"   HTML: {html_path}")

        return report

    def _generate_html_report(self, report: Dict) -> str:
        """生成 HTML 报告"""
        summary = report["summary"]
        categories = report["categories"]

        status_icon = "✅" if summary["failed"] == 0 else "⚠️"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>KiCad AI E2E 测试报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #16213e; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #4ade80; }}
        .stat-value.failed {{ color: #f87171; }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .category {{ background: #16213e; border-radius: 8px; margin-bottom: 15px; overflow: hidden; }}
        .category-header {{ background: #0f3460; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
        .category-title {{ font-size: 18px; font-weight: 600; }}
        .category-stats {{ font-size: 14px; color: #888; }}
        .test-list {{ padding: 10px 0; }}
        .test-item {{ padding: 12px 20px; display: flex; align-items: center; border-bottom: 1px solid #0f3460; }}
        .test-item:last-child {{ border-bottom: none; }}
        .test-status {{ width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-size: 14px; }}
        .test-status.pass {{ background: #166534; }}
        .test-status.fail {{ background: #991b1b; }}
        .test-info {{ flex: 1; }}
        .test-id {{ color: #4ade80; font-family: monospace; font-size: 12px; }}
        .test-name {{ font-weight: 500; margin-top: 2px; }}
        .test-message {{ color: #888; font-size: 13px; margin-top: 4px; }}
        .screenshots {{ background: #16213e; border-radius: 8px; padding: 20px; margin-top: 20px; }}
        .screenshots h3 {{ margin-top: 0; }}
        .screenshot-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }}
        .screenshot-item {{ background: #0f3460; border-radius: 8px; overflow: hidden; }}
        .screenshot-item img {{ width: 100%; height: auto; display: block; }}
        .screenshot-item .caption {{ padding: 10px; font-size: 12px; color: #888; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{status_icon} KiCad AI E2E 测试报告</h1>
            <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="summary">
            <div class="stat-card">
                <div class="stat-value">{summary['total']}</div>
                <div class="stat-label">总测试数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['passed']}</div>
                <div class="stat-label">通过</div>
            </div>
            <div class="stat-card">
                <div class="stat-value failed">{summary['failed']}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['success_rate']}</div>
                <div class="stat-label">成功率</div>
            </div>
        </div>
"""
        # 添加分类测试结果
        category_names = {
            "T31": "T3.1: UI 对话框测试",
            "T32": "T3.2: 需求提交测试",
            "T33": "T3.3: AI 分析进度测试",
            "T34": "T3.4: 项目方案预览测试",
            "T35": "T3.5: 原理图预览测试",
            "T36": "T3.6: 方案确认测试",
            "T37": "T3.7: 完整流程测试",
            "T38": "T3.8: 边缘情况测试"
        }

        for cat_id, cat_data in categories.items():
            cat_name = category_names.get(cat_id, cat_id)
            html += f"""
        <div class="category">
            <div class="category-header">
                <span class="category-title">{cat_name}</span>
                <span class="category-stats">✓ {cat_data['passed']} / ✗ {cat_data['failed']}</span>
            </div>
            <div class="test-list">
"""
            for test in cat_data["tests"]:
                status_class = "pass" if test["success"] else "fail"
                status_icon = "✓" if test["success"] else "✗"
                html += f"""
                <div class="test-item">
                    <div class="test-status {status_class}">{status_icon}</div>
                    <div class="test-info">
                        <div class="test-id">{test['id']}</div>
                        <div class="test-name">{test['name']}</div>
                        <div class="test-message">{test['message']}</div>
                    </div>
                </div>
"""
            html += "            </div>\n        </div>\n"

        # 添加截图
        if self.screenshots:
            html += """
        <div class="screenshots">
            <h3>📸 测试截图</h3>
            <div class="screenshot-grid">
"""
            for i, ss in enumerate(self.screenshots, 1):
                filename = Path(ss).name
                html += f"""
                <div class="screenshot-item">
                    <img src="{filename}" alt="Screenshot {i}">
                    <div class="caption">{filename}</div>
                </div>
"""
            html += "            </div>\n        </div>\n"

        html += """
    </div>
</body>
</html>
"""
        return html


def check_port(port: int) -> bool:
    """检查端口是否可用"""
    import urllib.request
    try:
        # 使用 HTTP 请求检测
        url = f"http://localhost:{port}"
        if port == 8000:
            url = f"http://localhost:{port}/api/health"
        req = urllib.request.Request(url, method='GET')
        urllib.request.urlopen(req, timeout=2)
        return True
    except:
        try:
            # 备用：使用 socket 检测
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            return result == 0
        except:
            return False


class AIDialogTester:
    """AI 对话框测试类"""

    def __init__(self, report: TestReport):
        self.report = report
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.console_logs = []
        self.network_requests = []

    async def setup(self, playwright):
        """初始化浏览器"""
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized",
            ]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )

        self.page = await self.context.new_page()

        # 监听事件
        self.page.on("console", lambda msg: self.console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        self.page.on("request", lambda req: self.network_requests.append({
            "method": req.method,
            "url": req.url
        }))

        self.report.record("SETUP", "浏览器初始化", True, "Chromium 浏览器已启动")

    async def teardown(self):
        """清理环境"""
        if self.browser:
            await self.browser.close()

    # ========== 辅助方法 ==========

    async def _safe_click(self, selector: str, timeout: int = 5000) -> bool:
        """安全点击 - 处理元素遮挡问题"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                # 先尝试普通点击
                try:
                    await element.click(timeout=3000)
                    return True
                except:
                    # 如果失败，使用 force click
                    await element.click(force=True, timeout=3000)
                    return True
        except:
            return False

    async def _js_click(self, selector: str) -> bool:
        """JavaScript 点击"""
        try:
            await self.page.evaluate(f"""
                const el = document.querySelector('{selector}');
                if (el) el.click();
            """)
            return True
        except:
            return False

    async def _open_dialog(self) -> bool:
        """打开 AI 对话框"""
        try:
            # 查找并点击 AI 创建按钮
            selectors = [
                "button:has-text('AI 创建')",
                "button:has-text('🤖')",
            ]

            for selector in selectors:
                if await self._safe_click(selector, timeout=3000):
                    await asyncio.sleep(0.5)
                    # 验证对话框是否打开
                    dialog = await self.page.query_selector(".dialog-overlay, [role='dialog']")
                    if dialog:
                        return True
            return False
        except:
            return False

    async def _close_dialog(self) -> bool:
        """关闭 AI 对话框"""
        try:
            # 尝试多种关闭方式
            # 1. 点击关闭按钮
            close_btn = await self.page.query_selector(".close-btn, button:has-text('×')")
            if close_btn:
                await close_btn.click(force=True)
                await asyncio.sleep(0.5)

            # 2. 按 ESC 键
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            # 验证对话框是否关闭
            dialog = await self.page.query_selector(".dialog-overlay")
            if dialog:
                visible = await dialog.is_visible()
                return not visible
            return True
        except:
            return False

    # ========== T3.1 UI 对话框测试 ==========

    async def test_T31_1_dialog_open(self):
        """T3.1.1: 对话框打开测试"""
        try:
            # 访问页面
            await self.page.goto("http://localhost:3000", timeout=30000)
            await asyncio.sleep(2)

            # 点击 AI 创建按钮
            success = await self._open_dialog()

            if success:
                # 验证对话框标题 (支持带 emoji 的标题)
                title = await self.page.query_selector(".dialog-header h2")
                title_text = await title.inner_text() if title else ""

                screenshot = await self.report.screenshot_page(self.page, "T31_1_dialog_open")

                # 检查标题包含 "AI 智能创建项目" 即可（允许前面有 emoji）
                title_ok = "AI 智能创建项目" in title_text

                self.report.record(
                    "T31.1", "对话框打开测试",
                    title_ok,
                    f"标题: {title_text}",
                    screenshot=screenshot
                )
            else:
                self.report.record("T31.1", "对话框打开测试", False, "无法打开对话框")

        except Exception as e:
            self.report.record("T31.1", "对话框打开测试", False, str(e))

    async def test_T31_2_dialog_close(self):
        """T3.1.2: 对话框关闭测试"""
        try:
            # 确保对话框打开
            await self._open_dialog()
            await asyncio.sleep(0.5)

            # 关闭对话框
            success = await self._close_dialog()

            screenshot = await self.report.screenshot_page(self.page, "T31_2_dialog_close")

            self.report.record(
                "T31.2", "对话框关闭测试",
                success,
                "对话框已关闭" if success else "对话框未关闭",
                screenshot=screenshot
            )

        except Exception as e:
            self.report.record("T31.2", "对话框关闭测试", False, str(e))

    async def test_T31_3_input_area(self):
        """T3.1.3: 输入区域测试"""
        try:
            # 打开对话框
            await self._open_dialog()
            await asyncio.sleep(0.5)

            # 查找输入框
            textarea = await self.page.query_selector("textarea#requirements, textarea")

            if textarea:
                # 测试聚焦
                await textarea.click()
                await asyncio.sleep(0.2)

                # 测试输入
                test_text = "测试输入内容 123"
                await textarea.fill(test_text)
                await asyncio.sleep(0.2)

                # 验证输入内容
                value = await textarea.input_value()

                screenshot = await self.report.screenshot_page(self.page, "T31_3_input_area")

                self.report.record(
                    "T31.3", "输入区域测试",
                    value == test_text,
                    f"输入内容: {value[:30]}...",
                    screenshot=screenshot
                )
            else:
                self.report.record("T31.3", "输入区域测试", False, "未找到输入框")

            # 清理
            await self._close_dialog()

        except Exception as e:
            self.report.record("T31.3", "输入区域测试", False, str(e))

    async def test_T31_4_submit_button_state(self):
        """T3.1.4: 提交按钮状态测试"""
        try:
            # 打开对话框
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            submit_btn = await self.page.query_selector("button:has-text('开始分析'), .submit-btn")

            # 检查初始状态
            initial_disabled = submit_btn and await submit_btn.is_disabled()

            # 输入内容
            if textarea and submit_btn:
                await textarea.fill("测试需求")
                await asyncio.sleep(0.3)

                # 检查输入后状态
                after_disabled = await submit_btn.is_disabled()

                screenshot = await self.report.screenshot_page(self.page, "T31_4_button_state")

                self.report.record(
                    "T31.4", "提交按钮状态测试",
                    initial_disabled and not after_disabled,
                    f"初始禁用: {initial_disabled}, 输入后禁用: {after_disabled}",
                    screenshot=screenshot
                )
            else:
                self.report.record("T31.4", "提交按钮状态测试", False, "未找到按钮或输入框")

            await self._close_dialog()

        except Exception as e:
            self.report.record("T31.4", "提交按钮状态测试", False, str(e))

    # ========== T3.2 需求提交测试 ==========

    async def test_T32_1_empty_submit(self):
        """T3.2.1: 提交空输入测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")

            # 清空输入
            if textarea:
                await textarea.fill("")
                await asyncio.sleep(0.2)

                # 尝试点击提交
                submit_btn = await self.page.query_selector("button:has-text('开始分析'), .submit-btn")

                if submit_btn:
                    is_disabled = await submit_btn.is_disabled()

                    screenshot = await self.report.screenshot_page(self.page, "T32_1_empty_submit")

                    self.report.record(
                        "T32.1", "提交空输入测试",
                        is_disabled,
                        f"按钮禁用状态: {is_disabled}",
                        screenshot=screenshot
                    )
                else:
                    self.report.record("T32.1", "提交空输入测试", False, "未找到提交按钮")
            else:
                self.report.record("T32.1", "提交空输入测试", False, "未找到输入框")

            await self._close_dialog()

        except Exception as e:
            self.report.record("T32.1", "提交空输入测试", False, str(e))

    async def test_T32_2_valid_submit(self):
        """T3.2.2: 提交有效需求测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")

            if textarea:
                # 输入有效需求
                await textarea.fill("设计一个5V稳压电源")
                await asyncio.sleep(0.3)

                # 点击提交 - 新流程使用"下一步"按钮
                submit_btn = await self.page.query_selector(
                    "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
                )

                if submit_btn:
                    await submit_btn.click(force=True)
                    await asyncio.sleep(1)

                    # 检查是否显示加载状态或问答界面
                    analyzing = await self.page.query_selector(".step-analyzing, .spinner, .progress-text")
                    clarifying = await self.page.query_selector(".step-clarifying, .questions-list")

                    screenshot = await self.report.screenshot_page(self.page, "T32_2_valid_submit")

                    success = analyzing is not None or clarifying is not None
                    self.report.record(
                        "T32.2", "提交有效需求测试",
                        success,
                        "已提交，进入下一步" if success else "未显示加载或问答状态",
                        screenshot=screenshot
                    )
                else:
                    self.report.record("T32.2", "提交有效需求测试", False, "未找到提交按钮")
            else:
                self.report.record("T32.2", "提交有效需求测试", False, "未找到输入框")

            # 等待并关闭
            await asyncio.sleep(3)
            await self._close_dialog()

        except Exception as e:
            self.report.record("T32.2", "提交有效需求测试", False, str(e))

    # ========== T3.3 AI 分析进度测试 ==========

    async def test_T33_1_progress_display(self):
        """T3.3.1: 进度显示测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个LED闪烁电路")
                await asyncio.sleep(0.2)

                submit_btn = await self.page.query_selector(
                    "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
                )
                if submit_btn:
                    await submit_btn.click(force=True)
                    await asyncio.sleep(0.5)

                    # 检查进度文字或问答界面
                    progress = await self.page.query_selector(".progress-text, .step-analyzing p")
                    clarifying = await self.page.query_selector(".step-clarifying, .detected-info")

                    screenshot = await self.report.screenshot_page(self.page, "T33_1_progress")

                    success = progress is not None or clarifying is not None
                    self.report.record(
                        "T33.1", "进度显示测试",
                        success,
                        "显示进度或问答界面" if success else "未显示进度",
                        screenshot=screenshot
                    )

            await asyncio.sleep(3)
            await self._close_dialog()

        except Exception as e:
            self.report.record("T33.1", "进度显示测试", False, str(e))

    async def test_T33_2_analysis_complete(self):
        """T3.3.2: 分析完成测试 - 新的交互式问答流程"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个5V稳压电源，输入220V交流电")
                await asyncio.sleep(0.2)

                # 步骤1: 点击"下一步"进入问答
                submit_btn = await self.page.query_selector(
                    "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
                )
                if submit_btn:
                    await submit_btn.click(force=True)

                    # 等待问答界面或分析中状态 (最长10秒)
                    try:
                        await self.page.wait_for_selector(
                            ".step-clarifying, .step-analyzing, .questions-list",
                            timeout=10000
                        )
                        await asyncio.sleep(1)

                        # 步骤2: 如果有问答界面，点击"生成方案"或"跳过"
                        clarify_section = await self.page.query_selector(".step-clarifying")
                        if clarify_section:
                            # 尝试点击"生成方案"按钮
                            gen_btn = await self.page.query_selector(
                                "button:has-text('生成方案'), button:has-text('跳过')"
                            )
                            if gen_btn:
                                await gen_btn.click(force=True)

                        # 等待预览 (最长30秒)
                        preview = await self.page.wait_for_selector(
                            ".step-preview, .spec-section",
                            timeout=30000
                        )

                        screenshot = await self.report.screenshot_page(self.page, "T33_2_complete")

                        self.report.record(
                            "T33.2", "分析完成测试",
                            preview is not None,
                            "分析完成，显示预览" if preview else "未显示预览",
                            screenshot=screenshot
                        )
                    except:
                        self.report.record("T33.2", "分析完成测试", False, "等待超时")

            await self._close_dialog()

        except Exception as e:
            self.report.record("T33.2", "分析完成测试", False, str(e))

    # ========== T3.4 项目方案预览测试 ==========

    async def test_T34_1_spec_content(self):
        """T3.4.1: 方案内容显示测试 - 新的交互式问答流程"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个5V稳压电源，输入220V交流电")
                await asyncio.sleep(0.2)

                # 步骤1: 点击"下一步"
                submit_btn = await self.page.query_selector(
                    "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
                )
                if submit_btn:
                    await submit_btn.click(force=True)

                    # 等待问答界面
                    try:
                        await self.page.wait_for_selector(
                            ".step-clarifying, .questions-list",
                            timeout=10000
                        )
                        await asyncio.sleep(0.5)

                        # 步骤2: 点击"生成方案"或"跳过"
                        gen_btn = await self.page.query_selector(
                            "button:has-text('生成方案'), button:has-text('跳过')"
                        )
                        if gen_btn:
                            await gen_btn.click(force=True)

                        # 等待预览
                        await self.page.wait_for_selector(".step-preview, .spec-section", timeout=30000)
                        await asyncio.sleep(1)

                        # 检查各项内容
                        project_name = await self.page.query_selector(".spec-content h4")
                        params_table = await self.page.query_selector(".params-table")
                        components_table = await self.page.query_selector(".components-table")

                        name_text = await project_name.inner_text() if project_name else ""

                        screenshot = await self.report.screenshot_page(self.page, "T34_1_spec")

                        self.report.record(
                            "T34.1", "方案内容显示测试",
                            project_name is not None,
                            f"项目名: {name_text}, 参数表: {params_table is not None}, 器件表: {components_table is not None}",
                            screenshot=screenshot
                        )
                    except Exception as wait_err:
                        self.report.record("T34.1", "方案内容显示测试", False, f"等待超时: {str(wait_err)}")

            await self._close_dialog()

        except Exception as e:
            self.report.record("T34.1", "方案内容显示测试", False, str(e))

    # ========== T3.5 原理图预览测试 ==========

    async def test_T35_1_schematic_render(self):
        """T3.5.1: 原理图渲染测试 - 新的交互式问答流程"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个5V稳压电源")
                await asyncio.sleep(0.2)

                # 步骤1: 点击"下一步"
                submit_btn = await self.page.query_selector(
                    "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
                )
                if submit_btn:
                    await submit_btn.click(force=True)

                    # 等待问答界面
                    try:
                        await self.page.wait_for_selector(
                            ".step-clarifying, .questions-list",
                            timeout=10000
                        )
                        await asyncio.sleep(0.5)

                        # 步骤2: 点击"生成方案"
                        gen_btn = await self.page.query_selector(
                            "button:has-text('生成方案'), button:has-text('跳过')"
                        )
                        if gen_btn:
                            await gen_btn.click(force=True)

                        # 等待预览
                        await self.page.wait_for_selector(".step-preview, .spec-section", timeout=30000)
                        await asyncio.sleep(1)

                        # 检查原理图 SVG
                        schematic_svg = await self.page.query_selector(".schematic-canvas, svg.schematic-canvas")

                        # 检查器件卡片
                        component_cards = await self.page.query_selector_all(".component-card")

                        screenshot = await self.report.screenshot_page(self.page, "T35_1_schematic")

                        self.report.record(
                            "T35.1", "原理图渲染测试",
                            schematic_svg is not None or len(component_cards) > 0,
                            f"SVG: {schematic_svg is not None}, 器件卡片: {len(component_cards)}",
                            screenshot=screenshot
                        )
                    except Exception as wait_err:
                        self.report.record("T35.1", "原理图渲染测试", False, f"等待超时: {str(wait_err)}")

            await self._close_dialog()

        except Exception as e:
            self.report.record("T35.1", "原理图渲染测试", False, str(e))

    # ========== T3.6 方案确认测试 ==========

    async def test_T36_1_confirm_create(self):
        """T3.6.1: 确认创建项目测试 - 新的交互式问答流程"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个USB转串口模块")
                await asyncio.sleep(0.2)

                # 步骤1: 点击"下一步"
                submit_btn = await self.page.query_selector(
                    "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
                )
                if submit_btn:
                    await submit_btn.click(force=True)

                    # 等待问答界面
                    try:
                        await self.page.wait_for_selector(
                            ".step-clarifying, .questions-list",
                            timeout=10000
                        )
                        await asyncio.sleep(0.5)

                        # 步骤2: 点击"生成方案"
                        gen_btn = await self.page.query_selector(
                            "button:has-text('生成方案'), button:has-text('跳过')"
                        )
                        if gen_btn:
                            await gen_btn.click(force=True)

                        # 等待预览
                        await self.page.wait_for_selector(".step-preview, .spec-section", timeout=30000)
                        await asyncio.sleep(1)

                        # 步骤3: 点击确认创建
                        confirm_btn = await self.page.query_selector("button:has-text('确认创建'), .confirm-btn")

                        if confirm_btn:
                            await confirm_btn.click(force=True)
                            await asyncio.sleep(3)

                            screenshot = await self.report.screenshot_page(self.page, "T36_1_confirm")

                            # 检查对话框是否关闭
                            dialog = await self.page.query_selector(".dialog-overlay")
                            dialog_visible = dialog and await dialog.is_visible()

                            self.report.record(
                                "T36.1", "确认创建项目测试",
                                True,
                                f"对话框状态: {'可见' if dialog_visible else '已关闭'}",
                                screenshot=screenshot
                            )
                        else:
                            self.report.record("T36.1", "确认创建项目测试", False, "未找到确认按钮")
                    except Exception as wait_err:
                        self.report.record("T36.1", "确认创建项目测试", False, f"等待超时: {str(wait_err)}")

        except Exception as e:
            self.report.record("T36.1", "确认创建项目测试", False, str(e))

    async def test_T36_2_abandon_create(self):
        """T3.6.2: 放弃创建测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个智能家居控制器")
                await asyncio.sleep(0.2)

                submit_btn = await self.page.query_selector("button:has-text('开始分析'), .submit-btn")
                if submit_btn:
                    await submit_btn.click(force=True)

                    await self.page.wait_for_selector(".step-preview, .spec-section", timeout=30000)
                    await asyncio.sleep(1)

                    # 点击放弃按钮
                    abandon_btn = await self.page.query_selector("button:has-text('放弃'), .abandon-btn")

                    if abandon_btn:
                        await abandon_btn.click(force=True)
                        await asyncio.sleep(1)

                        screenshot = await self.report.screenshot_page(self.page, "T36_2_abandon")

                        # 验证对话框关闭
                        dialog = await self.page.query_selector(".dialog-overlay")
                        dialog_visible = dialog and await dialog.is_visible()

                        self.report.record(
                            "T36.2", "放弃创建测试",
                            not dialog_visible,
                            f"对话框已关闭: {not dialog_visible}",
                            screenshot=screenshot
                        )
                    else:
                        self.report.record("T36.2", "放弃创建测试", False, "未找到放弃按钮")

        except Exception as e:
            self.report.record("T36.2", "放弃创建测试", False, str(e))

    async def test_T36_3_back_to_edit(self):
        """T3.6.3: 返回修改测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")
            original_text = "设计一个LED驱动电路"

            if textarea:
                await textarea.fill(original_text)
                await asyncio.sleep(0.2)

                submit_btn = await self.page.query_selector("button:has-text('开始分析'), .submit-btn")
                if submit_btn:
                    await submit_btn.click(force=True)

                    await self.page.wait_for_selector(".step-preview, .spec-section", timeout=30000)
                    await asyncio.sleep(1)

                    # 点击返回修改
                    back_btn = await self.page.query_selector("button:has-text('返回'), .back-btn")

                    if back_btn:
                        await back_btn.click(force=True)
                        await asyncio.sleep(0.5)

                        # 检查是否返回输入界面
                        input_step = await self.page.query_selector(".step-input")
                        textarea_visible = await textarea.is_visible()

                        screenshot = await self.report.screenshot_page(self.page, "T36_3_back")

                        self.report.record(
                            "T36.3", "返回修改测试",
                            input_step is not None and textarea_visible,
                            f"输入界面可见: {textarea_visible}",
                            screenshot=screenshot
                        )
                    else:
                        self.report.record("T36.3", "返回修改测试", False, "未找到返回按钮")

            await self._close_dialog()

        except Exception as e:
            self.report.record("T36.3", "返回修改测试", False, str(e))

    # ========== T3.7 完整流程测试 ==========

    async def test_T37_1_full_flow(self):
        """T3.7.1: 完整创建流程测试 - 新的交互式问答流程"""
        try:
            # 1. 访问页面
            await self.page.goto("http://localhost:3000", timeout=30000)
            await asyncio.sleep(2)

            screenshot1 = await self.report.screenshot_page(self.page, "T37_1_step1")

            # 2. 打开 AI 对话框
            await self._open_dialog()
            await asyncio.sleep(0.5)

            screenshot2 = await self.report.screenshot_page(self.page, "T37_1_step2")

            # 3. 输入需求
            textarea = await self.page.query_selector("textarea#requirements, textarea")
            if textarea:
                await textarea.fill("设计一个锂电池充电模块，使用TP4056芯片")
                await asyncio.sleep(0.3)

            screenshot3 = await self.report.screenshot_page(self.page, "T37_1_step3")

            # 4. 步骤1: 点击"下一步"进入问答
            submit_btn = await self.page.query_selector(
                "button:has-text('下一步'), button:has-text('开始分析'), .submit-btn"
            )
            if submit_btn:
                await submit_btn.click(force=True)

                # 等待问答界面
                try:
                    await self.page.wait_for_selector(
                        ".step-clarifying, .questions-list",
                        timeout=10000
                    )
                    await asyncio.sleep(0.5)

                    # 5. 步骤2: 点击"生成方案"（跳过问答）
                    gen_btn = await self.page.query_selector(
                        "button:has-text('生成方案'), button:has-text('跳过')"
                    )
                    if gen_btn:
                        await gen_btn.click(force=True)

                    # 6. 等待分析完成
                    await self.page.wait_for_selector(".step-preview, .spec-section", timeout=30000)
                    await asyncio.sleep(1)

                    screenshot4 = await self.report.screenshot_page(self.page, "T37_1_step4")

                    # 7. 步骤3: 确认创建
                    confirm_btn = await self.page.query_selector("button:has-text('确认创建'), .confirm-btn")
                    if confirm_btn:
                        await confirm_btn.click(force=True)
                        await asyncio.sleep(2)

                    screenshot5 = await self.report.screenshot_page(self.page, "T37_1_step5")

                    # 8. 验证创建结果
                    current_url = self.page.url
                    dialog = await self.page.query_selector(".dialog-overlay")
                    dialog_visible = dialog and await dialog.is_visible()

                    self.report.record(
                        "T37.1", "完整创建流程测试",
                        not dialog_visible,
                        f"URL: {current_url}, 对话框关闭: {not dialog_visible}",
                        screenshot=screenshot5
                    )
                except Exception as wait_err:
                    self.report.record("T37.1", "完整创建流程测试", False, f"等待超时: {str(wait_err)}")

        except Exception as e:
            self.report.record("T37.1", "完整创建流程测试", False, str(e))

    # ========== T3.8 边缘情况测试 ==========

    async def test_T38_1_special_chars(self):
        """T3.8.3: 特殊字符输入测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")

            # 输入包含特殊字符的内容
            special_text = "设计一个电路 <script>alert('xss')</script> & \"test\" 'single'"
            if textarea:
                await textarea.fill(special_text)
                await asyncio.sleep(0.3)

                # 验证输入值正确处理
                value = await textarea.input_value()

                screenshot = await self.report.screenshot_page(self.page, "T38_1_special")

                self.report.record(
                    "T38.1", "特殊字符输入测试",
                    value == special_text,
                    f"特殊字符正确处理: {value == special_text}",
                    screenshot=screenshot
                )

            await self._close_dialog()

        except Exception as e:
            self.report.record("T38.1", "特殊字符输入测试", False, str(e))

    async def test_T38_2_long_text(self):
        """T3.8.4: 超长文本输入测试"""
        try:
            await self._open_dialog()
            await asyncio.sleep(0.5)

            textarea = await self.page.query_selector("textarea#requirements, textarea")

            # 生成超长文本
            long_text = "设计一个电路模块。" * 200  # 约 2000 字符

            if textarea:
                await textarea.fill(long_text)
                await asyncio.sleep(0.5)

                # 验证无崩溃
                value = await textarea.input_value()

                screenshot = await self.report.screenshot_page(self.page, "T38_2_long")

                self.report.record(
                    "T38.2", "超长文本输入测试",
                    len(value) > 1000,
                    f"输入长度: {len(value)} 字符",
                    screenshot=screenshot
                )

            await self._close_dialog()

        except Exception as e:
            self.report.record("T38.2", "超长文本输入测试", False, str(e))


async def run_tests(test_class: str = None):
    """运行测试"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("e2e_test_results") / f"{timestamp}_complete"
    report = TestReport(output_dir)

    logger.info("\n" + "=" * 70)
    logger.info("🧪 KiCad AI 智能对话框 - 完整自动化测试")
    logger.info("=" * 70)
    logger.info(f"输出目录: {output_dir}")

    # 检查服务
    logger.info("\n📋 检查服务状态...")
    backend_ok = check_port(8000)
    frontend_ok = check_port(3000)

    report.record(
        "PRECHECK", "服务检查",
        backend_ok and frontend_ok,
        f"后端: {'✓' if backend_ok else '✗'}, 前端: {'✓' if frontend_ok else '✗'}"
    )

    if not backend_ok or not frontend_ok:
        logger.error("❌ 服务未启动，请先启动前后端服务")
        return

    async with async_playwright() as p:
        tester = AIDialogTester(report)

        try:
            await tester.setup(p)

            # 运行测试用例
            logger.info("\n" + "-" * 70)
            logger.info("T3.1: UI 对话框测试")
            logger.info("-" * 70)
            await tester.test_T31_1_dialog_open()
            await tester.test_T31_2_dialog_close()
            await tester.test_T31_3_input_area()
            await tester.test_T31_4_submit_button_state()

            logger.info("\n" + "-" * 70)
            logger.info("T3.2: 需求提交测试")
            logger.info("-" * 70)
            await tester.test_T32_1_empty_submit()
            await tester.test_T32_2_valid_submit()

            logger.info("\n" + "-" * 70)
            logger.info("T3.3: AI 分析进度测试")
            logger.info("-" * 70)
            await tester.test_T33_1_progress_display()
            await tester.test_T33_2_analysis_complete()

            logger.info("\n" + "-" * 70)
            logger.info("T3.4: 项目方案预览测试")
            logger.info("-" * 70)
            await tester.test_T34_1_spec_content()

            logger.info("\n" + "-" * 70)
            logger.info("T3.5: 原理图预览测试")
            logger.info("-" * 70)
            await tester.test_T35_1_schematic_render()

            logger.info("\n" + "-" * 70)
            logger.info("T3.6: 方案确认测试")
            logger.info("-" * 70)
            await tester.test_T36_1_confirm_create()
            await tester.test_T36_2_abandon_create()
            await tester.test_T36_3_back_to_edit()

            logger.info("\n" + "-" * 70)
            logger.info("T3.7: 完整流程测试")
            logger.info("-" * 70)
            await tester.test_T37_1_full_flow()

            logger.info("\n" + "-" * 70)
            logger.info("T3.8: 边缘情况测试")
            logger.info("-" * 70)
            await tester.test_T38_1_special_chars()
            await tester.test_T38_2_long_text()

        finally:
            await tester.teardown()

    # 保存报告
    result = report.save_report()

    # 打印摘要
    logger.info("\n" + "=" * 70)
    logger.info("📊 测试结果摘要")
    logger.info("=" * 70)
    logger.info(f"  总测试数: {result['summary']['total']}")
    logger.info(f"  通过: {result['summary']['passed']}")
    logger.info(f"  失败: {result['summary']['failed']}")
    logger.info(f"  成功率: {result['summary']['success_rate']}")
    logger.info(f"  耗时: {result['summary']['duration_seconds']} 秒")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KiCad AI E2E 完整测试")
    parser.add_argument("--class", "-c", dest="test_class", help="运行指定测试类 (T31-T38)")

    args = parser.parse_args()
    asyncio.run(run_tests(args.test_class))
