"""简化版 E2E 测试"""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("打开浏览器...")
        await page.goto("http://localhost:3000")
        await page.wait_for_load_state("networkidle")

        # 等待用户操作
        print("请在浏览器中手动操作:")
        print("1. 登录(如果需要)")
        print("2. 点击新建项目")
        print("3. 输入需求: ne555 led blink")
        print("4. 等待生成完成")

        # 等待用户手动操作一段时间
        await page.wait_for_timeout(120000)  # 等待2分钟

        # 截图
        await page.screenshot(path="e2e/manual_test.png", full_page=True)
        print("截图保存: e2e/manual_test.png")

        await browser.close()

if __name__ == "__main__":
    import os
    os.makedirs("e2e", exist_ok=True)
    asyncio.run(test())
