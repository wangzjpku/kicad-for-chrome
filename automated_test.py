"""
KiCad AI 完全自动化测试脚本 - 使用构建后的前端
"""

import asyncio
import subprocess
import sys
import time
import socket
import os
import http.server
import socketserver
import threading
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


async def wait_for_port(port: int, timeout: int = 30) -> bool:
    """等待端口就绪"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_port(port):
            await asyncio.sleep(1)
            return True
        await asyncio.sleep(0.5)
    return False


class SimpleHTTPServer:
    """简单的 HTTP 服务器用于提供前端"""

    def __init__(self, directory: Path, port: int):
        self.directory = directory
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """启动服务器"""
        os.chdir(self.directory)

        handler = http.server.SimpleHTTPRequestHandler
        self.server = socketserver.TCPServer(("", self.port), handler)

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"✓ HTTP 服务器已启动: http://localhost:{self.port}")

    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("✓ HTTP 服务器已停止")


async def run_test():
    """运行自动化测试"""
    logger.info("=" * 70)
    logger.info("KiCad AI 完全自动化测试")
    logger.info("=" * 70)

    project_root = Path(__file__).parent
    dist_dir = project_root / "kicad-ai-auto" / "web" / "dist"
    agent_dir = project_root / "kicad-ai-auto" / "agent"
    screenshots_dir = project_root / "test_results"
    screenshots_dir.mkdir(exist_ok=True)

    backend_process = None
    http_server = None
    frontend_port = 3002  # 使用固定端口

    try:
        # 检查后端是否已运行
        if not check_port(8000):
            logger.info("启动后端服务...")
            env = os.environ.copy()
            env["ALLOWED_ORIGINS"] = (
                f"http://localhost:{frontend_port},http://localhost:3000,http://localhost:3001"
            )

            backend_process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=agent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            logger.info(f"✓ 后端进程已启动 (PID: {backend_process.pid})")

            if not await wait_for_port(8000, timeout=30):
                logger.error("✗ 后端服务启动超时")
                return False
        else:
            logger.info("✓ 后端服务已在运行")

        logger.info("✓ 后端服务已就绪: http://localhost:8000")

        # 启动前端 HTTP 服务器
        if dist_dir.exists():
            logger.info(f"启动前端 HTTP 服务器 (端口 {frontend_port})...")
            http_server = SimpleHTTPServer(dist_dir, frontend_port)
            http_server.start()

            if not await wait_for_port(frontend_port, timeout=10):
                logger.error("✗ 前端服务启动超时")
                return False

            logger.info(f"✓ 前端服务已就绪: http://localhost:{frontend_port}")
        else:
            logger.warning(f"⚠ 前端构建目录不存在: {dist_dir}")
            logger.info("使用已有的前端服务...")
            for port in [3000, 3001]:
                if check_port(port):
                    frontend_port = port
                    logger.info(f"✓ 使用现有前端服务: http://localhost:{frontend_port}")
                    break
            else:
                logger.error("✗ 未找到可用的前端服务")
                return False

        # 等待服务稳定
        await asyncio.sleep(2)

        # 启动 Playwright 测试
        logger.info("\n" + "-" * 70)
        logger.info("启动 Playwright 浏览器测试")
        logger.info("-" * 70)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"],
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            # 收集日志
            console_logs = []
            websocket_events = []

            page.on(
                "console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}")
            )
            page.on("pageerror", lambda err: console_logs.append(f"[Error] {err}"))

            def on_websocket(ws):
                websocket_events.append(f"创建: {ws.url}")
                ws.on("open", lambda: websocket_events.append(f"✓ 打开: {ws.url}"))
                ws.on("close", lambda: websocket_events.append(f"✗ 关闭: {ws.url}"))

            page.on("websocket", on_websocket)

            # 访问页面
            url = f"http://localhost:{frontend_port}"
            logger.info(f"访问: {url}")

            try:
                await page.goto(url, timeout=30000)
                logger.info("✓ 页面加载完成")
            except Exception as e:
                logger.error(f"✗ 页面加载失败: {e}")
                await browser.close()
                return False

            # 等待 WebSocket 连接
            logger.info("等待 WebSocket 连接 (10秒)...")
            await asyncio.sleep(10)

            # 截图
            screenshot_path = screenshots_dir / "automated_test.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"✓ 截图已保存: {screenshot_path}")

            # 检查状态
            connection_ok = False
            canvas_ok = False

            try:
                status_elem = await page.query_selector(
                    '[data-testid="connection-status"]'
                )
                if status_elem:
                    status_text = await status_elem.inner_text()
                    connection_ok = "已连接" in status_text
                    logger.info(f"连接状态: {status_text}")
            except Exception as e:
                logger.error(f"检查连接状态时出错: {e}")

            try:
                canvas = await page.query_selector('[data-testid="canvas-container"]')
                if canvas:
                    canvas_text = await canvas.inner_text()
                    canvas_ok = "等待连接" not in canvas_text
                    logger.info(f"画布内容: {canvas_text[:100]}")
            except Exception as e:
                logger.error(f"检查画布时出错: {e}")

            # 输出日志
            logger.info("\n" + "-" * 70)
            logger.info("浏览器控制台日志 (最近15条)")
            logger.info("-" * 70)
            for log in console_logs[-15:]:
                logger.info(log)

            if websocket_events:
                logger.info("\n" + "-" * 70)
                logger.info("WebSocket 事件")
                logger.info("-" * 70)
                for event in websocket_events[-10:]:
                    logger.info(event)

            # 最终截图
            await page.screenshot(
                path=str(screenshots_dir / "final.png"), full_page=True
            )

            await browser.close()

            # 输出结果
            logger.info("\n" + "=" * 70)
            logger.info("测试结果汇总")
            logger.info("=" * 70)
            logger.info(f"前端地址: http://localhost:{frontend_port}")
            logger.info(f"后端地址: http://localhost:8000")
            logger.info(f"WebSocket 连接: {'✅ 成功' if connection_ok else '❌ 失败'}")
            logger.info(f"画布显示: {'✅ 正常' if canvas_ok else '❌ 等待连接'}")
            logger.info(f"截图位置: {screenshots_dir.absolute()}")
            logger.info("=" * 70)

            return connection_ok

    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 清理资源
        logger.info("\n清理资源...")
        if http_server:
            http_server.stop()
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except:
                backend_process.kill()
            logger.info("✓ 后端服务已停止")


async def main():
    """主函数"""
    success = await run_test()

    if success:
        logger.info("\n✅ 测试成功！WebSocket 连接正常")
    else:
        logger.warning("\n❌ 测试失败，请检查日志")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
