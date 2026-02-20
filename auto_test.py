"""
KiCad Web UI 自动化测试脚本
自动检测服务状态，重启服务，测试 WebSocket 连接
"""

import asyncio
import subprocess
import sys
import time
import socket
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ServiceManager:
    """服务管理器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.web_dir = self.project_root / "kicad-ai-auto" / "web"
        self.agent_dir = self.project_root / "kicad-ai-auto" / "agent"

    def check_port(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            return result == 0
        except:
            return False

    async def wait_for_port(self, port: int, timeout: int = 30) -> bool:
        """等待端口就绪"""
        logger.info(f"等待端口 {port} 就绪...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_port(port):
                await asyncio.sleep(1)  # 等待服务完全启动
                return True
            await asyncio.sleep(0.5)
        return False


class KiCadAutomatedTest:
    """KiCad 自动化测试"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.screenshots_dir = self.project_root / "test_results"
        self.screenshots_dir.mkdir(exist_ok=True)
        self.service_manager = ServiceManager()
        self.frontend_port = None

    async def setup(self):
        """设置测试环境"""
        logger.info("=" * 60)
        logger.info("KiCad Web UI 自动化测试")
        logger.info("=" * 60)

        # 检查后端服务
        await self.check_and_restart_backend()

        # 启动前端服务
        await self.start_frontend()

    async def check_and_restart_backend(self):
        """检查并确保后端服务运行"""
        if self.service_manager.check_port(8000):
            logger.info("✓ 后端服务已在端口 8000 运行")
        else:
            logger.error("✗ 后端服务未运行")
            logger.info("请手动启动后端服务:")
            logger.info("  cd kicad-ai-auto/agent")
            logger.info("  python main.py")
            raise RuntimeError("后端服务未启动")

    async def start_frontend(self):
        """启动前端服务"""
        logger.info("\n--- 启动前端服务 ---")

        # 查找可用端口
        base_port = 3000
        for port in range(3000, 3010):
            if not self.service_manager.check_port(port):
                self.frontend_port = port
                break

        if not self.frontend_port:
            logger.error("无法找到可用端口")
            raise RuntimeError("无可用端口")

        logger.info(f"使用端口: {self.frontend_port}")

        # 启动前端开发服务器
        logger.info("启动前端开发服务器...")
        try:
            self.frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=self.service_manager.web_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )

            # 等待服务启动
            logger.info("等待前端服务启动...")
            await asyncio.sleep(5)

            # 等待端口就绪
            if not await self.service_manager.wait_for_port(
                self.frontend_port, timeout=30
            ):
                logger.error("前端服务启动超时")
                self.frontend_process.terminate()
                raise RuntimeError("前端服务启动失败")

            logger.info(f"✓ 前端服务已启动: http://localhost:{self.frontend_port}")

        except Exception as e:
            logger.error(f"启动前端服务失败: {e}")
            raise

    async def run_browser_test(self):
        """运行浏览器测试"""
        logger.info("\n--- 启动浏览器测试 ---")

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
            page.on(
                "console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}")
            )
            page.on("pageerror", lambda err: console_logs.append(f"[Error] {err}"))

            # 访问页面
            url = f"http://localhost:{self.frontend_port}"
            logger.info(f"访问: {url}")

            try:
                await page.goto(url, timeout=30000)
                logger.info("✓ 页面加载完成")
            except Exception as e:
                logger.error(f"页面加载失败: {e}")
                await browser.close()
                raise

            # 等待 WebSocket 连接尝试
            logger.info("等待 WebSocket 连接...")
            await asyncio.sleep(5)

            # 截图检查状态
            screenshot_path = self.screenshots_dir / "test_result.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"✓ 截图已保存: {screenshot_path}")

            # 检查连接状态
            connection_status = await self.check_connection_status(page)

            # 检查画布状态
            canvas_status = await self.check_canvas_status(page)

            # 输出日志
            logger.info("\n--- 浏览器控制台日志 ---")
            for log in console_logs[-20:]:  # 显示最后20条
                logger.info(log)

            # 汇总结果
            logger.info("\n" + "=" * 60)
            logger.info("测试结果汇总")
            logger.info("=" * 60)
            logger.info(f"前端端口: {self.frontend_port}")
            logger.info(f"后端端口: 8000")
            logger.info(
                f"WebSocket 连接: {'✓ 成功' if connection_status else '✗ 失败'}"
            )
            logger.info(f"画布显示: {'✓ 正常' if canvas_status else '✗ 异常'}")
            logger.info(f"截图位置: {screenshot_path}")
            logger.info("=" * 60)

            # 如果连接失败，尝试诊断
            if not connection_status:
                await self.diagnose_websocket(page)

            # 保持浏览器打开一段时间供查看
            logger.info("\n浏览器将保持打开 10 秒供查看...")
            await asyncio.sleep(10)

            await browser.close()

            return connection_status and canvas_status

    async def check_connection_status(self, page) -> bool:
        """检查连接状态"""
        try:
            # 查找连接状态指示器
            status_element = await page.query_selector(
                '[data-testid="connection-status"]'
            )
            if status_element:
                status_text = await status_element.inner_text()
                logger.info(f"连接状态: {status_text}")
                return "已连接" in status_text
            else:
                logger.warning("未找到连接状态指示器")
                return False
        except Exception as e:
            logger.error(f"检查连接状态时出错: {e}")
            return False

    async def check_canvas_status(self, page) -> bool:
        """检查画布状态"""
        try:
            canvas = await page.query_selector('[data-testid="canvas-container"]')
            if canvas:
                canvas_text = await canvas.inner_text()
                if "等待连接" in canvas_text:
                    logger.warning("画布显示'等待连接'")
                    return False
                else:
                    logger.info("画布内容已更新")
                    return True
            else:
                logger.warning("未找到画布容器")
                return False
        except Exception as e:
            logger.error(f"检查画布状态时出错: {e}")
            return False

    async def diagnose_websocket(self, page):
        """诊断 WebSocket 问题"""
        logger.info("\n--- WebSocket 诊断 ---")

        # 尝试手动连接 WebSocket
        result = await page.evaluate("""
            async () => {
                return new Promise((resolve) => {
                    try {
                        const ws = new WebSocket('ws://localhost:8000/ws/control');
                        
                        ws.onopen = () => {
                            resolve({ success: true, message: 'WebSocket 连接成功' });
                            ws.close();
                        };
                        
                        ws.onerror = (error) => {
                            resolve({ success: false, message: 'WebSocket 错误', error: error.type });
                        };
                        
                        ws.onclose = (event) => {
                            if (!event.wasClean) {
                                resolve({ 
                                    success: false, 
                                    message: `WebSocket 关闭`,
                                    code: event.code,
                                    reason: event.reason
                                });
                            }
                        };
                        
                        setTimeout(() => {
                            resolve({ success: false, message: '连接超时' });
                        }, 5000);
                    } catch (e) {
                        resolve({ success: false, message: '异常', error: e.message });
                    }
                });
            }
        """)

        logger.info(f"手动 WebSocket 测试结果: {result}")

    async def cleanup(self):
        """清理资源"""
        if hasattr(self, "frontend_process"):
            logger.info("停止前端服务...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except:
                self.frontend_process.kill()

    async def run(self):
        """运行完整测试"""
        try:
            await self.setup()
            success = await self.run_browser_test()

            if success:
                logger.info("\n✓ 测试通过！系统运行正常")
            else:
                logger.warning("\n⚠ 测试未完全通过，请查看截图和日志")

        finally:
            await self.cleanup()


async def main():
    """主函数"""
    test = KiCadAutomatedTest()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
