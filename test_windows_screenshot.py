"""
Windows 截图功能测试脚本
"""

import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_windows_screenshot():
    """测试 Windows 窗口截图"""

    logger.info("=" * 70)
    logger.info("Windows 窗口截图功能测试")
    logger.info("=" * 70)

    screenshots_dir = Path("test_results")
    screenshots_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"],
        )

        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # 访问页面
        url = "http://localhost:3000"
        logger.info(f"访问: {url}")
        await page.goto(url, timeout=30000)
        logger.info("✓ 页面加载完成")

        # 等待连接
        logger.info("等待 WebSocket 连接 (10秒)...")
        await asyncio.sleep(10)

        # 截图
        screenshot = screenshots_dir / "windows_test.png"
        await page.screenshot(path=str(screenshot), full_page=True)
        logger.info(f"✓ 截图已保存: {screenshot}")

        # 检查状态
        try:
            status_elem = await page.query_selector('[data-testid="connection-status"]')
            if status_elem:
                status = await status_elem.inner_text()
                logger.info(f"连接状态: {status}")
        except:
            pass

        try:
            canvas = await page.query_selector('[data-testid="canvas-container"]')
            if canvas:
                text = await canvas.inner_text()
                logger.info(f"画布内容: {text[:100]}")
        except:
            pass

        # 保持浏览器打开
        logger.info("\n浏览器保持打开 15 秒，请查看截图结果...")
        await asyncio.sleep(15)

        await browser.close()

    logger.info("\n测试完成！")
    logger.info(f"请查看截图: {screenshot}")


if __name__ == "__main__":
    asyncio.run(test_windows_screenshot())
