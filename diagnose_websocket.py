"""
WebSocket 连接诊断脚本
"""

import asyncio
from playwright.async_api import async_playwright


async def diagnose_websocket():
    """诊断 WebSocket 连接问题"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # 设置控制台日志监听
        page = await context.new_page()

        # 监听 console 消息
        page.on("console", lambda msg: print(f"[Console {msg.type}]: {msg.text}"))

        # 监听页面错误
        page.on("pageerror", lambda err: print(f"[Page Error]: {err}"))

        # 监听 WebSocket
        page.on("websocket", lambda ws: print(f"[WebSocket] 创建: {ws.url}"))

        print("=" * 60)
        print("WebSocket 诊断")
        print("=" * 60)

        # 访问页面
        print("\n1. 访问 http://localhost:3001")
        await page.goto("http://localhost:3001")
        await asyncio.sleep(3)

        # 执行 JavaScript 检查 WebSocket 状态
        print("\n2. 检查 WebSocket 状态...")
        ws_status = await page.evaluate("""
            () => {
                // 获取 WebSocket 状态（如果页面暴露了这个信息）
                const logs = [];
                
                // 捕获网络请求
                if (window.performance && window.performance.getEntries) {
                    const entries = window.performance.getEntries();
                    entries.forEach(entry => {
                        if (entry.name && entry.name.includes('ws://')) {
                            logs.push(`WebSocket 请求: ${entry.name} - 状态: ${entry.responseStatus || 'unknown'}`);
                        }
                    });
                }
                
                return logs;
            }
        """)

        if ws_status:
            print("WebSocket 请求日志:")
            for log in ws_status:
                print(f"  {log}")
        else:
            print("未找到 WebSocket 请求日志")

        # 等待一段时间看 WebSocket 连接尝试
        print("\n3. 等待 5 秒观察 WebSocket 连接...")
        await asyncio.sleep(5)

        # 截图
        await page.screenshot(path="websocket_diagnose.png", full_page=True)
        print("\n4. 截图已保存: websocket_diagnose.png")

        # 尝试手动连接 WebSocket
        print("\n5. 尝试手动连接 WebSocket...")
        ws_result = await page.evaluate("""
            async () => {
                return new Promise((resolve) => {
                    try {
                        const ws = new WebSocket('ws://localhost:8000/ws/control');
                        
                        ws.onopen = () => {
                            resolve({ success: true, message: 'WebSocket 连接成功' });
                            ws.close();
                        };
                        
                        ws.onerror = (error) => {
                            resolve({ success: false, message: 'WebSocket 错误: ' + error.type });
                        };
                        
                        ws.onclose = (event) => {
                            if (!event.wasClean) {
                                resolve({ 
                                    success: false, 
                                    message: `WebSocket 关闭: code=${event.code}, reason=${event.reason || 'unknown'}` 
                                });
                            }
                        };
                        
                        // 3 秒超时
                        setTimeout(() => {
                            resolve({ success: false, message: '连接超时' });
                        }, 3000);
                    } catch (e) {
                        resolve({ success: false, message: '异常: ' + e.message });
                    }
                });
            }
        """)

        print(f"手动连接结果: {ws_result}")

        print("\n" + "=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(diagnose_websocket())
