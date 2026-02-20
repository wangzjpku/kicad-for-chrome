"""
KiCad AI Playwright 自动化测试 - 使用现有服务
"""

import asyncio
import socket
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_port(port: int) -> bool:
    """检查端口是否被占用"""
    for addr in ["127.0.0.1", "::1"]:
        try:
            sock = socket.socket(
                socket.AF_INET if "." in addr else socket.AF_INET6, socket.SOCK_STREAM
            )
            sock.settimeout(1)
            result = sock.connect_ex((addr, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
    return False


async def run_automated_test():
    """运行自动化测试"""
    logger.info("=" * 70)
    logger.info("KiCad AI Playwright 自动化测试")
    logger.info("=" * 70)

    # 检查服务
    backend_ok = check_port(8000)
    frontend_ok = check_port(3000)

    logger.info(f"后端服务 (8000): {'✓ 运行中' if backend_ok else '✗ 未启动'}")
    logger.info(f"前端服务 (3000): {'✓ 运行中' if frontend_ok else '✗ 未启动'}")

    if not backend_ok:
        logger.error("后端服务未启动，请先启动后端")
        return False

    if not frontend_ok:
        logger.error("前端服务未启动，请先启动前端 (npm run dev)")
        return False

    # 创建截图目录
    screenshots_dir = Path("test_results")
    screenshots_dir.mkdir(exist_ok=True)

    # 启动 Playwright
    logger.info("\n" + "-" * 70)
    logger.info("启动浏览器测试")
    logger.info("-" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"],
        )

        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # 收集日志
        console_logs = []
        websocket_events = []
        errors = []

        page.on("console", lambda msg: console_logs.append((msg.type, msg.text)))
        page.on("pageerror", lambda err: errors.append(str(err)))

        def on_websocket(ws):
            url = ws.url
            websocket_events.append(("created", url))
            ws.on("open", lambda: websocket_events.append(("opened", url)))
            ws.on("close", lambda: websocket_events.append(("closed", url)))

        page.on("websocket", on_websocket)

        # 访问页面
        url = "http://localhost:3000"
        logger.info(f"访问: {url}")
        await page.goto(url, timeout=30000)
        logger.info("✓ 页面加载完成")

        # 等待 WebSocket 连接
        logger.info("等待 WebSocket 连接 (8秒)...")
        await asyncio.sleep(8)

        # 截图
        screenshot1 = screenshots_dir / "test_step1.png"
        await page.screenshot(path=str(screenshot1), full_page=True)
        logger.info(f"✓ 截图已保存: {screenshot1}")

        # 检查状态
        logger.info("\n" + "-" * 70)
        logger.info("检查页面状态")
        logger.info("-" * 70)

        connection_status = "Unknown"
        connection_ok = False
        try:
            status_elem = await page.query_selector('[data-testid="connection-status"]')
            if status_elem:
                connection_status = await status_elem.inner_text()
                connection_ok = "已连接" in connection_status
                logger.info(f"连接状态: {connection_status}")
            else:
                logger.warning("未找到连接状态指示器")
        except Exception as e:
            logger.error(f"检查连接状态时出错: {e}")

        canvas_text = "Unknown"
        canvas_ok = False
        try:
            canvas = await page.query_selector('[data-testid="canvas-container"]')
            if canvas:
                canvas_text = await canvas.inner_text()
                canvas_ok = "等待连接" not in canvas_text
                logger.info(f"画布内容: {canvas_text[:100]}")
            else:
                logger.warning("未找到画布容器")
        except Exception as e:
            logger.error(f"检查画布时出错: {e}")

        # 输出日志
        logger.info("\n" + "-" * 70)
        logger.info("浏览器控制台日志 (最近10条)")
        logger.info("-" * 70)
        for log_type, log_text in console_logs[-10:]:
            logger.info(f"[{log_type}] {log_text[:100]}")

        if websocket_events:
            logger.info("\n" + "-" * 70)
            logger.info("WebSocket 事件")
            logger.info("-" * 70)
            for event_type, event_url in websocket_events[-5:]:
                logger.info(f"{event_type}: {event_url}")

        if errors:
            logger.info("\n" + "-" * 70)
            logger.info("页面错误")
            logger.info("-" * 70)
            for error in errors[-5:]:
                logger.error(error[:100])

        # 最终截图
        screenshot2 = screenshots_dir / "test_final.png"
        await page.screenshot(path=str(screenshot2), full_page=True)

        await browser.close()

        # 输出结果
        logger.info("\n" + "=" * 70)
        logger.info("测试结果汇总")
        logger.info("=" * 70)
        logger.info(f"前端地址: http://localhost:3000")
        logger.info(f"后端地址: http://localhost:8000")
        logger.info(f"WebSocket 连接: {'✅ 已连接' if connection_ok else '❌ 未连接'}")
        logger.info(f"连接状态文本: {connection_status}")
        logger.info(f"画布显示: {'✅ 正常' if canvas_ok else '❌ 等待连接'}")
        logger.info(f"截图1: {screenshot1}")
        logger.info(f"截图2: {screenshot2}")
        logger.info("=" * 70)

        # 结论
        logger.info("\n" + "=" * 70)
        if connection_ok:
            logger.info("✅ 测试成功！WebSocket 连接正常")
            logger.info("\n说明:")
            logger.info("- 右上角和底部都显示'已连接'")
            logger.info("- 中间显示'等待连接'是正常的（Windows 无法截图）")
            logger.info("- 使用 Docker 可以看到 KiCad 实时画面")
        else:
            logger.info("❌ WebSocket 连接失败")
            logger.info("\n可能原因:")
            logger.info("1. CORS 配置问题（需要重启后端）")
            logger.info("2. 端口冲突")
            logger.info("3. 防火墙阻挡")
        logger.info("=" * 70)

        return connection_ok


async def main():
    """主函数"""
    try:
        success = await run_automated_test()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
