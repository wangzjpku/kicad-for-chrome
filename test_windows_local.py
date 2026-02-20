"""
KiCad AI 闭环测试脚本 - Windows 本地环境版

此脚本用于测试 Windows 本地 KiCad 的 AI 自动化：
1. 连接本地 KiCad Web UI
2. 截图验证（使用本地 KiCad 窗口）
3. 发送命令控制 KiCad

前置条件:
    1. KiCad 已启动并运行
    2. 前端开发服务器已启动: npm run dev
    3. 后端 API 已启动 (如果使用 HTTP 模式)

使用方法:
    python test_windows_local.py
"""

import asyncio
import base64
from playwright.async_api import async_playwright
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KiCadWindowsLocalTest:
    """Windows 本地 KiCad 测试类"""

    def __init__(self, frontend_url: str = "http://localhost:3001"):
        self.frontend_url = frontend_url
        self.browser = None
        self.page = None
        self.playwright = None
        self.screenshots_dir = Path("test_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)

    async def setup(self, headless: bool = False):
        """初始化浏览器"""
        logger.info("启动浏览器...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"],
        )
        self.page = await self.browser.new_page(
            viewport={"width": 1920, "height": 1080}
        )
        logger.info("✓ 浏览器已启动")

    async def teardown(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("✓ 浏览器已关闭")

    async def navigate_to_ui(self):
        """导航到 Web UI"""
        logger.info(f"访问 KiCad Web UI: {self.frontend_url}")
        await self.page.goto(self.frontend_url)

        # 等待页面加载 - 等待画布容器或连接状态指示器
        try:
            await self.page.wait_for_selector(
                '[data-testid="canvas-container"]', timeout=10000
            )
            logger.info("✓ Web UI 加载完成")
        except:
            logger.warning("⚠ 画布容器未找到，但页面可能已加载")

    async def take_screenshot(self, name: str):
        """截图保存"""
        screenshot_path = self.screenshots_dir / f"{name}.png"
        await self.page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"✓ 截图已保存: {screenshot_path}")
        return screenshot_path

    async def check_connection_status(self):
        """检查连接状态"""
        logger.info("检查连接状态...")

        # 检查右上角的连接状态指示器
        try:
            # 等待连接成功或失败
            await asyncio.sleep(2)  # 给 WebSocket 连接一点时间

            # 截图看当前状态
            await self.take_screenshot("connection_check")

            # 获取连接状态文本
            status_element = await self.page.query_selector(
                '[data-testid="connection-status"]'
            )
            if status_element:
                status_text = await status_element.inner_text()
                logger.info(f"连接状态指示器: {status_text}")

                if "已连接" in status_text:
                    logger.info("✓ WebSocket 连接成功")
                    return True
                else:
                    logger.warning(f"⚠ 连接状态: {status_text}")
                    return False
            else:
                logger.warning("⚠ 未找到连接状态指示器")
                return False

        except Exception as e:
            logger.error(f"检查连接状态时出错: {e}")
            return False

    async def check_canvas_display(self):
        """检查画布显示"""
        logger.info("检查画布显示...")

        # 截图看画布状态
        await self.take_screenshot("canvas_check")

        # 检查画布内容
        canvas = await self.page.query_selector('[data-testid="canvas-container"]')
        if canvas:
            # 检查是否有截图显示
            img = await self.page.query_selector('[data-testid="canvas-image"]')
            if img:
                src = await img.get_attribute("src")
                if src and src.startswith("data:image"):
                    logger.info("✓ 画布显示 KiCad 截图")
                    return True
                else:
                    logger.info(f"画布图片 src: {src[:50] if src else 'None'}...")
                    return False
            else:
                # 检查是否显示"等待连接"
                text = await canvas.inner_text()
                if "等待连接" in text:
                    logger.warning("⚠ 画布显示'等待连接'")
                    return False
                else:
                    logger.info(f"画布内容: {text[:100]}")
                    return True
        else:
            logger.warning("⚠ 未找到画布容器")
            return False

    async def test_basic_workflow(self):
        """测试基本工作流程"""
        logger.info("=" * 60)
        logger.info("开始 KiCad Windows 本地环境测试")
        logger.info("=" * 60)

        try:
            await self.setup(headless=False)
            await self.navigate_to_ui()

            # 步骤 1: 检查初始状态
            logger.info("\n--- 步骤 1: 检查连接状态 ---")
            connected = await self.check_connection_status()

            # 步骤 2: 检查画布
            logger.info("\n--- 步骤 2: 检查画布显示 ---")
            canvas_ok = await self.check_canvas_display()

            # 步骤 3: 检查底部状态栏
            logger.info("\n--- 步骤 3: 检查状态栏 ---")
            try:
                status_bar = await self.page.query_selector('[data-testid="statusbar"]')
                if status_bar:
                    status_text = await status_bar.inner_text()
                    logger.info(f"状态栏内容: {status_text[:200]}")
                    await self.take_screenshot("statusbar")
                else:
                    logger.warning("⚠ 未找到状态栏")
            except Exception as e:
                logger.error(f"检查状态栏时出错: {e}")

            # 步骤 4: 检查日志面板
            logger.info("\n--- 步骤 4: 检查日志面板 ---")
            try:
                output_panel = await self.page.query_selector(
                    '[data-testid="output-panel"]'
                )
                if output_panel:
                    logs_text = await output_panel.inner_text()
                    logger.info(f"日志面板内容:\n{logs_text[:500]}")
                    await self.take_screenshot("logs")
                else:
                    logger.warning("⚠ 未找到日志面板")
            except Exception as e:
                logger.error(f"检查日志面板时出错: {e}")

            # 最终截图
            await self.take_screenshot("final_state")

            # 汇总结果
            logger.info("\n" + "=" * 60)
            logger.info("测试结果汇总")
            logger.info("=" * 60)
            logger.info(f"WebSocket 连接: {'✓ 成功' if connected else '✗ 失败'}")
            logger.info(f"画布显示: {'✓ 正常' if canvas_ok else '✗ 异常'}")
            logger.info(f"截图保存在: {self.screenshots_dir.absolute()}")
            logger.info("=" * 60)

            if connected and canvas_ok:
                logger.info("✓ 所有检查通过！系统运行正常")
            else:
                logger.warning("⚠ 部分检查未通过，请查看截图和日志")

                if not connected:
                    logger.info("\n排查建议:")
                    logger.info(
                        "1. 检查后端服务是否运行: http://localhost:8000/api/health"
                    )
                    logger.info("2. 检查 WebSocket 端口是否可访问")
                    logger.info("3. 查看浏览器控制台的网络请求")

                if not canvas_ok:
                    logger.info("\n画布显示排查:")
                    logger.info("1. 当前是 Windows 本地环境，截图功能需要 Docker 环境")
                    logger.info("2. 或者需要实现 Windows 窗口捕获功能")

            # 保持浏览器打开一段时间，方便查看
            logger.info("\n浏览器将保持打开 30 秒，方便查看...")
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"测试失败: {e}")
            await self.take_screenshot("error_state")
            raise
        finally:
            await self.teardown()


async def main():
    """主函数"""
    test = KiCadWindowsLocalTest()
    await test.test_basic_workflow()


if __name__ == "__main__":
    asyncio.run(main())
