"""
KiCad AI 完全自动化测试脚本
自动启动前后端服务，执行 Playwright 测试
"""

import asyncio
import subprocess
import sys
import time
import socket
import signal
import os
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ServiceManager:
    """服务管理器 - 自动启动/停止服务"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.web_dir = self.project_root / "kicad-ai-auto" / "web"
        self.agent_dir = self.project_root / "kicad-ai-auto" / "agent"
        self.processes = []

    def check_port(self, port: int) -> bool:
        """检查端口是否被占用"""
        for addr in ["127.0.0.1", "::1"]:
            try:
                sock = socket.socket(
                    socket.AF_INET if "." in addr else socket.AF_INET6,
                    socket.SOCK_STREAM,
                )
                sock.settimeout(1)
                result = sock.connect_ex((addr, port))
                sock.close()
                if result == 0:
                    return True
            except:
                pass
        return False

    async def wait_for_port(self, port: int, timeout: int = 30) -> bool:
        """等待端口就绪"""
        logger.info(f"等待端口 {port} 就绪...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_port(port):
                await asyncio.sleep(1)
                return True
            await asyncio.sleep(0.5)
        return False

    def start_backend(self):
        """启动后端服务"""
        if self.check_port(8000):
            logger.info("✓ 后端服务已在运行 (端口 8000)")
            return True

        logger.info("启动后端服务...")
        try:
            # 设置环境变量
            env = os.environ.copy()
            env["ALLOWED_ORIGINS"] = (
                "http://localhost:3000,http://localhost:3001,http://localhost:3002"
            )

            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=self.agent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if sys.platform == "win32"
                else 0,
            )
            self.processes.append(("backend", process))
            logger.info(f"✓ 后端服务进程已启动 (PID: {process.pid})")
            return True
        except Exception as e:
            logger.error(f"✗ 启动后端服务失败: {e}")
            return False

    def start_frontend(self):
        """启动前端服务"""
        # 查找可用端口
        frontend_port = None
        for port in [3000, 3001, 3002]:
            if not self.check_port(port):
                frontend_port = port
                break

        if not frontend_port:
            logger.error("无法找到可用端口 (3000-3002 都被占用)")
            return None

        logger.info(f"启动前端服务 (端口 {frontend_port})...")
        try:
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=self.web_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if sys.platform == "win32"
                else 0,
            )
            self.processes.append(("frontend", process))
            logger.info(f"✓ 前端服务进程已启动 (PID: {process.pid})")
            return frontend_port
        except Exception as e:
            logger.error(f"✗ 启动前端服务失败: {e}")
            return None

    def stop_all(self):
        """停止所有服务"""
        logger.info("\n停止所有服务...")
        for name, process in self.processes:
            try:
                if sys.platform == "win32":
                    process.terminate()
                else:
                    process.send_signal(signal.SIGTERM)

                try:
                    process.wait(timeout=5)
                    logger.info(f"✓ {name} 已停止")
                except:
                    process.kill()
                    logger.info(f"✓ {name} 已被强制停止")
            except Exception as e:
                logger.warning(f"⚠ 停止 {name} 时出错: {e}")


class AutomatedTester:
    """自动化测试器"""

    def __init__(self):
        self.service_manager = ServiceManager()
        self.screenshots_dir = Path("test_results")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.frontend_port = None

    async def setup_services(self):
        """设置并启动所有服务"""
        logger.info("=" * 70)
        logger.info("KiCad AI 完全自动化测试")
        logger.info("=" * 70)

        # 启动后端
        if not self.service_manager.start_backend():
            return False

        # 等待后端就绪
        if not await self.service_manager.wait_for_port(8000, timeout=30):
            logger.error("后端服务启动超时")
            return False
        logger.info("✓ 后端服务已就绪: http://localhost:8000")

        # 启动前端
        self.frontend_port = self.service_manager.start_frontend()
        if not self.frontend_port:
            return False

        # 等待前端就绪
        if not await self.service_manager.wait_for_port(self.frontend_port, timeout=30):
            logger.error("前端服务启动超时")
            return False
        logger.info(f"✓ 前端服务已就绪: http://localhost:{self.frontend_port}")

        # 额外等待确保服务完全初始化
        logger.info("等待服务完全初始化...")
        await asyncio.sleep(3)

        return True

    async def run_playwright_test(self):
        """运行 Playwright 测试"""
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
                ws.on("open", lambda: websocket_events.append(f"打开: {ws.url}"))
                ws.on("close", lambda: websocket_events.append(f"关闭: {ws.url}"))

            page.on("websocket", on_websocket)

            # 访问页面
            url = f"http://localhost:{self.frontend_port}"
            logger.info(f"访问: {url}")
            await page.goto(url, timeout=30000)
            logger.info("✓ 页面加载完成")

            # 等待 WebSocket 连接
            logger.info("等待 WebSocket 连接 (10秒)...")
            await asyncio.sleep(10)

            # 截图
            screenshot_path = self.screenshots_dir / "automated_test_result.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"✓ 截图已保存: {screenshot_path}")

            # 检查状态
            results = await self.check_page_status(page)

            # 输出日志
            logger.info("\n" + "-" * 70)
            logger.info("浏览器控制台日志")
            logger.info("-" * 70)
            for log in console_logs[-15:]:
                logger.info(log)

            if websocket_events:
                logger.info("\n" + "-" * 70)
                logger.info("WebSocket 事件")
                logger.info("-" * 70)
                for event in websocket_events:
                    logger.info(event)

            # 最终截图
            await page.screenshot(
                path=str(self.screenshots_dir / "final_state.png"), full_page=True
            )

            await browser.close()

            return results

    async def check_page_status(self, page) -> dict:
        """检查页面状态"""
        results = {
            "connection_ok": False,
            "canvas_ok": False,
            "status_text": "Unknown",
            "canvas_text": "Unknown",
        }

        # 检查连接状态
        try:
            status_elem = await page.query_selector('[data-testid="connection-status"]')
            if status_elem:
                results["status_text"] = await status_elem.inner_text()
                results["connection_ok"] = "已连接" in results["status_text"]
        except Exception as e:
            logger.error(f"检查连接状态时出错: {e}")

        # 检查画布
        try:
            canvas = await page.query_selector('[data-testid="canvas-container"]')
            if canvas:
                results["canvas_text"] = await canvas.inner_text()
                results["canvas_ok"] = "等待连接" not in results["canvas_text"]
        except Exception as e:
            logger.error(f"检查画布时出错: {e}")

        return results

    async def run(self):
        """运行完整测试流程"""
        try:
            # 启动服务
            if not await self.setup_services():
                logger.error("服务启动失败，测试中止")
                return False

            # 运行测试
            results = await self.run_playwright_test()

            # 输出结果
            logger.info("\n" + "=" * 70)
            logger.info("测试结果汇总")
            logger.info("=" * 70)
            logger.info(f"前端地址: http://localhost:{self.frontend_port}")
            logger.info(f"后端地址: http://localhost:8000")
            logger.info(
                f"连接状态: {'✅ 已连接' if results['connection_ok'] else '❌ 未连接'}"
            )
            logger.info(f"状态文本: {results['status_text']}")
            logger.info(
                f"画布显示: {'✅ 正常' if results['canvas_ok'] else '❌ 等待连接'}"
            )
            logger.info(f"画布内容: {results['canvas_text'][:50]}")
            logger.info(f"截图位置: {self.screenshots_dir.absolute()}")
            logger.info("=" * 70)

            # 诊断信息
            if not results["connection_ok"]:
                logger.warning("\n⚠️ WebSocket 连接失败")
                logger.info("可能原因:")
                logger.info("1. 后端 CORS 配置问题")
                logger.info("2. WebSocket 端口冲突")
                logger.info("3. 网络防火墙阻挡")

            if not results["canvas_ok"]:
                logger.info("\nℹ️ 画布显示'等待连接'是正常的")
                logger.info("Windows 本地环境无法捕获 KiCad 截图")
                logger.info("使用 Docker 环境可以看到 KiCad 实时画面")

            return results["connection_ok"]

        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            # 停止服务
            self.service_manager.stop_all()


async def main():
    """主函数"""
    tester = AutomatedTester()
    success = await tester.run()

    if success:
        logger.info("\n✅ 测试完成！WebSocket 连接正常")
    else:
        logger.warning("\n❌ 测试完成，但连接存在问题")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
