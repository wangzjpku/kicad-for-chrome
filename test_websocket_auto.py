"""
KiCad Web UI 自动化测试脚本 - 测试现有服务
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
    try:
        # 尝试 IPv4
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result == 0:
            return True
    except:
        pass

    try:
        # 尝试 IPv6
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("::1", port))
        sock.close()
        if result == 0:
            return True
    except:
        pass

    return False


async def test_websocket_connection():
    """测试 WebSocket 连接"""

    logger.info("=" * 60)
    logger.info("KiCad Web UI 自动化测试")
    logger.info("=" * 60)

    # 检查服务状态
    backend_ok = check_port(8000)

    # 检测前端端口 (3000 或 3001)
    frontend_port = None
    for port in [3000, 3001, 3002]:
        if check_port(port):
            frontend_port = port
            break

    frontend_ok = frontend_port is not None

    logger.info(f"后端服务 (8000): {'✓ 运行中' if backend_ok else '✗ 未启动'}")
    logger.info(
        f"前端服务 ({frontend_port or '未找到'}): {'✓ 运行中' if frontend_ok else '✗ 未启动'}"
    )

    if not backend_ok:
        logger.error("后端服务未启动，请先启动后端服务")
        return False

    if not frontend_ok:
        logger.error("前端服务未启动，请先启动前端服务")
        return False

    # 启动浏览器测试
    logger.info("\n--- 启动浏览器测试 ---")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"],
        )

        context = await browser.new_context(viewport={"width": 1920, "height": 1080})

        page = await context.new_page()

        # 收集所有日志
        console_logs = []
        websocket_events = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[Page Error] {err}"))

        # 监听 WebSocket
        def on_websocket(ws):
            websocket_events.append(f"WebSocket created: {ws.url}")
            ws.on(
                "open", lambda: websocket_events.append(f"WebSocket opened: {ws.url}")
            )
            ws.on(
                "close", lambda: websocket_events.append(f"WebSocket closed: {ws.url}")
            )
            ws.on(
                "error", lambda err: websocket_events.append(f"WebSocket error: {err}")
            )

        page.on("websocket", on_websocket)

        # 访问页面
        url = f"http://localhost:{frontend_port}"
        logger.info(f"访问: {url}")

        try:
            await page.goto(url, timeout=30000)
            logger.info("✓ 页面加载完成")
        except Exception as e:
            logger.error(f"页面加载失败: {e}")
            await browser.close()
            return False

        # 等待 WebSocket 连接尝试
        logger.info("等待 8 秒观察 WebSocket 连接...")
        await asyncio.sleep(8)

        # 截图
        screenshots_dir = Path("test_results")
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / "auto_test_result.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"✓ 截图已保存: {screenshot_path}")

        # 检查连接状态
        connection_status = False
        try:
            status_element = await page.query_selector(
                '[data-testid="connection-status"]'
            )
            if status_element:
                status_text = await status_element.inner_text()
                logger.info(f"连接状态指示器: {status_text}")
                connection_status = "已连接" in status_text
            else:
                logger.warning("未找到连接状态指示器")
        except Exception as e:
            logger.error(f"检查连接状态时出错: {e}")

        # 检查画布
        canvas_status = False
        try:
            canvas = await page.query_selector('[data-testid="canvas-container"]')
            if canvas:
                canvas_text = await canvas.inner_text()
                logger.info(f"画布内容: {canvas_text[:100]}")
                canvas_status = "等待连接" not in canvas_text
        except Exception as e:
            logger.error(f"检查画布状态时出错: {e}")

        # 诊断 WebSocket
        logger.info("\n--- WebSocket 诊断 ---")

        # 尝试手动连接 WebSocket
        ws_test = await page.evaluate("""
            async () => {
                return new Promise((resolve) => {
                    try {
                        const ws = new WebSocket('ws://localhost:8000/ws/control');
                        
                        ws.onopen = () => {
                            resolve({ success: true, message: 'WebSocket 连接成功' });
                            ws.close();
                        };
                        
                        ws.onerror = (error) => {
                            resolve({ success: false, message: 'WebSocket 错误' });
                        };
                        
                        ws.onclose = (event) => {
                            if (!event.wasClean) {
                                resolve({ 
                                    success: false, 
                                    message: `WebSocket 关闭: code=${event.code}`,
                                    code: event.code
                                });
                            }
                        };
                        
                        setTimeout(() => {
                            resolve({ success: false, message: '连接超时 (5秒)' });
                        }, 5000);
                    } catch (e) {
                        resolve({ success: false, message: '异常: ' + e.message });
                    }
                });
            }
        """)

        logger.info(f"手动 WebSocket 测试: {ws_test}")

        # 输出浏览器日志
        logger.info("\n--- 浏览器控制台日志 (最近20条) ---")
        for log in console_logs[-20:]:
            logger.info(log)

        # 输出 WebSocket 事件
        if websocket_events:
            logger.info("\n--- WebSocket 事件 ---")
            for event in websocket_events:
                logger.info(event)
        else:
            logger.info("\n--- 未捕获到 WebSocket 事件 ---")

        # 最终截图
        await page.screenshot(
            path=str(screenshots_dir / "final_state.png"), full_page=True
        )

        # 汇总结果
        logger.info("\n" + "=" * 60)
        logger.info("测试结果汇总")
        logger.info("=" * 60)
        logger.info(f"后端服务: {'✓ 正常' if backend_ok else '✗ 异常'}")
        logger.info(f"前端服务: {'✓ 正常' if frontend_ok else '✗ 异常'}")
        logger.info(
            f"WebSocket 连接状态: {'✓ 已连接' if connection_status else '✗ 未连接'}"
        )
        logger.info(f"画布显示: {'✓ 正常' if canvas_status else '✗ 显示等待连接'}")
        logger.info(
            f"手动 WebSocket 测试: {'✓ 成功' if ws_test.get('success') else '✗ 失败'}"
        )
        logger.info(f"截图位置: {screenshots_dir.absolute()}")
        logger.info("=" * 60)

        # 诊断建议
        if not connection_status:
            logger.warning("\n排查建议:")
            logger.warning("1. WebSocket 连接失败，可能是 CORS 配置问题")
            logger.warning("2. 检查后端日志是否有连接请求")
            logger.warning("3. 尝试重启前端服务: cd kicad-ai-auto/web && npm run dev")

            if ws_test.get("code") == 1006:
                logger.warning("4. 错误码 1006: 连接被异常关闭，可能是服务器拒绝了连接")

        if not canvas_status:
            logger.info("\n画布显示说明:")
            logger.info("- Windows 本地环境无法捕获 KiCad 截图")
            logger.info("- 需要使用 Docker 环境才能看到 KiCad 画面")

        # 保持浏览器打开供查看
        logger.info("\n浏览器将保持打开 15 秒供查看...")
        await asyncio.sleep(15)

        await browser.close()

        return connection_status


async def main():
    """主函数"""
    try:
        success = await test_websocket_connection()
        if success:
            logger.info("\n✓ 测试完成！WebSocket 连接正常")
        else:
            logger.warning("\n⚠ 测试完成，但 WebSocket 未连接")
    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
