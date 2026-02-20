"""
KiCad AI 闭环测试脚本

此脚本用于测试完整的 KiCad AI 自动化闭环：
1. 创建新项目
2. 打开原理图编辑器
3. 放置器件符号
4. 绘制导线
5. 切换到 PCB 编辑器
6. 放置封装
7. 布线
8. 截图验证

使用方法:
    1. 确保 Docker 服务已启动: start-docker.bat
    2. 运行此脚本: python test_closed_loop.py
"""

import asyncio
import base64
from playwright.async_api import async_playwright
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KiCadClosedLoopTest:
    """KiCad 闭环测试类"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
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
            headless=headless, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self.page = await self.browser.new_page(
            viewport={"width": 1920, "height": 1080}
        )
        logger.info("浏览器已启动")

    async def teardown(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭")

    async def navigate_to_ui(self):
        """导航到 Web UI"""
        logger.info("访问 KiCad Web UI...")
        await self.page.goto(f"{self.server_url}/ui")
        await self.page.wait_for_selector(
            '[data-testid="canvas-container"]', timeout=30000
        )
        logger.info("Web UI 加载完成")

    async def take_screenshot(self, name: str):
        """截图保存"""
        screenshot_path = self.screenshots_dir / f"{name}.png"
        await self.page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"截图已保存: {screenshot_path}")
        return screenshot_path

    async def check_connection_status(self):
        """检查连接状态"""
        logger.info("检查连接状态...")
        # 等待连接状态变为已连接
        await self.page.wait_for_selector(
            '[data-testid="connection-status"]:has-text("已连接")', timeout=30000
        )
        logger.info("✓ 连接状态: 已连接")

    async def create_project(self, name: str = "TestProject"):
        """创建新项目"""
        logger.info(f"创建新项目: {name}")
        # 点击 File 菜单
        await self.page.click('[data-testid="menu-file"]')
        await asyncio.sleep(0.5)
        # 点击 New
        await self.page.click('[data-testid="menu-file-new"]')
        await asyncio.sleep(0.5)
        # 填写项目名称
        await self.page.fill('[data-testid="project-name-input"]', name)
        await asyncio.sleep(0.5)
        # 点击创建
        await self.page.click('[data-testid="btn-create-project"]')
        await asyncio.sleep(3)  # 等待项目创建
        logger.info(f"✓ 项目已创建: {name}")

    async def open_schematic_editor(self):
        """打开原理图编辑器"""
        logger.info("打开原理图编辑器...")
        await self.page.click('[data-testid="btn-schematic-editor"]')
        await asyncio.sleep(3)
        logger.info("✓ 原理图编辑器已打开")

    async def place_symbol(self, symbol: str, x: int, y: int):
        """放置器件符号"""
        logger.info(f"放置器件: {symbol} 在位置 ({x}, {y})")
        # 激活放置工具
        await self.page.click('[data-testid="tool-place-symbol"]')
        await asyncio.sleep(0.5)
        # 选择符号
        await self.page.fill('[data-testid="symbol-filter"]', symbol)
        await asyncio.sleep(0.5)
        await self.page.click(f'[data-testid="symbol-item-{symbol}"]')
        await asyncio.sleep(0.5)
        # 点击画布放置
        canvas = await self.page.query_selector('[data-testid="canvas-container"]')
        box = await canvas.bounding_box()
        screen_x = box["x"] + (x / 1920) * box["width"]
        screen_y = box["y"] + (y / 1080) * box["height"]
        await self.page.mouse.click(screen_x, screen_y)
        await asyncio.sleep(1)
        logger.info(f"✓ 器件已放置: {symbol}")

    async def draw_wire(self, start: tuple, end: tuple):
        """绘制导线"""
        logger.info(f"绘制导线: {start} -> {end}")
        # 激活导线工具
        await self.page.click('[data-testid="tool-draw-wire"]')
        await asyncio.sleep(0.5)
        # 在画布上绘制
        canvas = await self.page.query_selector('[data-testid="canvas-container"]')
        box = await canvas.bounding_box()
        start_x = box["x"] + (start[0] / 1920) * box["width"]
        start_y = box["y"] + (start[1] / 1080) * box["height"]
        end_x = box["x"] + (end[0] / 1920) * box["width"]
        end_y = box["y"] + (end[1] / 1080) * box["height"]
        # 拖动绘制
        await self.page.mouse.move(start_x, start_y)
        await self.page.mouse.down()
        await asyncio.sleep(0.2)
        await self.page.mouse.move(end_x, end_y)
        await self.page.mouse.up()
        await asyncio.sleep(1)
        logger.info("✓ 导线已绘制")

    async def switch_to_pcb_editor(self):
        """切换到 PCB 编辑器"""
        logger.info("切换到 PCB 编辑器...")
        await self.page.click('[data-testid="btn-pcb-editor"]')
        await asyncio.sleep(3)
        logger.info("✓ PCB 编辑器已打开")

    async def place_footprint(self, footprint: str, x: int, y: int):
        """放置封装"""
        logger.info(f"放置封装: {footprint} 在位置 ({x}, {y})")
        await self.page.click('[data-testid="tool-place-footprint"]')
        await asyncio.sleep(0.5)
        await self.page.fill('[data-testid="footprint-filter"]', footprint)
        await asyncio.sleep(0.5)
        await self.page.click(f'[data-testid="footprint-item-{footprint}"]')
        await asyncio.sleep(0.5)
        canvas = await self.page.query_selector('[data-testid="canvas-container"]')
        box = await canvas.bounding_box()
        screen_x = box["x"] + (x / 1920) * box["width"]
        screen_y = box["y"] + (y / 1080) * box["height"]
        await self.page.mouse.click(screen_x, screen_y)
        await asyncio.sleep(1)
        logger.info(f"✓ 封装已放置: {footprint}")

    async def route_track(self, start: tuple, end: tuple):
        """布线"""
        logger.info(f"布线: {start} -> {end}")
        await self.page.click('[data-testid="tool-route-track"]')
        await asyncio.sleep(0.5)
        canvas = await self.page.query_selector('[data-testid="canvas-container"]')
        box = await canvas.bounding_box()
        start_x = box["x"] + (start[0] / 1920) * box["width"]
        start_y = box["y"] + (start[1] / 1080) * box["height"]
        end_x = box["x"] + (end[0] / 1920) * box["width"]
        end_y = box["y"] + (end[1] / 1080) * box["height"]
        await self.page.mouse.move(start_x, start_y)
        await self.page.mouse.down()
        await asyncio.sleep(0.2)
        await self.page.mouse.move(end_x, end_y)
        await self.page.mouse.up()
        await asyncio.sleep(1)
        logger.info("✓ 布线完成")

    async def run_test(self):
        """运行完整测试"""
        logger.info("=" * 60)
        logger.info("开始 KiCad AI 闭环测试")
        logger.info("=" * 60)

        try:
            await self.setup(headless=False)  # 设置为 True 可无头运行
            await self.navigate_to_ui()
            await self.take_screenshot("01_initial_load")

            # 检查连接
            await self.check_connection_status()
            await self.take_screenshot("02_connected")

            # 测试 1: 创建项目
            await self.create_project("ClosedLoopTest")
            await self.take_screenshot("03_project_created")

            # 测试 2: 原理图编辑
            await self.open_schematic_editor()
            await self.take_screenshot("04_schematic_editor")

            await self.place_symbol("R", 400, 300)
            await self.take_screenshot("05_symbol_placed")

            await self.place_symbol("C", 600, 300)
            await self.take_screenshot("06_capacitor_placed")

            await self.draw_wire((400, 300), (600, 300))
            await self.take_screenshot("07_wire_drawn")

            # 测试 3: PCB 编辑
            await self.switch_to_pcb_editor()
            await self.take_screenshot("08_pcb_editor")

            await self.place_footprint("R_0603", 400, 400)
            await self.take_screenshot("09_footprint_placed")

            await self.route_track((400, 400), (600, 400))
            await self.take_screenshot("10_track_routed")

            logger.info("=" * 60)
            logger.info("✓ 所有测试完成！")
            logger.info(f"✓ 截图保存在: {self.screenshots_dir.absolute()}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"测试失败: {e}")
            await self.take_screenshot("error_state")
            raise
        finally:
            await self.teardown()


async def main():
    """主函数"""
    test = KiCadClosedLoopTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
