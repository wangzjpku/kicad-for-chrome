"""
Playwright AI Interface for KiCad
High-level API for AI agents to control KiCad
"""

from playwright.async_api import async_playwright, Page, Browser
from typing import Optional, Dict, List, Any, Tuple
import asyncio
import base64
import logging

logger = logging.getLogger(__name__)


class KiCadAIAgent:
    """
    KiCad AI Agent

    提供给 AI 程序的高级接口，用于控制 KiCad
    """

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def connect(self, headless: bool = False):
        """
        连接到 KiCad Web 界面

        Args:
            headless: 是否无头模式（调试用）
        """
        self.playwright = await async_playwright().start()

        # 启动浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=headless, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        # 创建新页面
        self.page = await self.browser.new_page(
            viewport={"width": 1920, "height": 1080}
        )

        # 访问 KiCad Web UI
        await self.page.goto(f"{self.server_url}/ui")

        # 等待页面加载完成
        await self.page.wait_for_selector('[data-testid="canvas-container"]')

        logger.info("Connected to KiCad Web UI")

    async def disconnect(self):
        """断开连接"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Disconnected from KiCad Web UI")

    # ========== 项目操作 ==========

    async def create_project(self, name: str):
        """创建新项目"""
        await self.click_menu("file", "new")
        await self.page.fill('[data-testid="project-name-input"]', name)
        await self.page.click('[data-testid="btn-create-project"]')
        await self.wait_for_load()

    async def open_project(self, project_path: str):
        """打开项目"""
        await self.click_menu("file", "open")
        await self.page.fill('[data-testid="file-input"]', project_path)
        await self.page.click('[data-testid="btn-open"]')
        await self.wait_for_load()

    async def save_project(self):
        """保存项目"""
        await self.click_menu("file", "save")
        await asyncio.sleep(0.5)

    # ========== 原理图编辑 ==========

    async def place_symbol(self, symbol: str, x: float, y: float, rotation: float = 0):
        """
        放置器件符号

        Args:
            symbol: 符号名称（如 'R', 'C', 'IC'）
            x, y: 放置位置（纳米单位）
            rotation: 旋转角度
        """
        # 激活放置工具
        await self.activate_tool("place_symbol")

        # 选择符号
        await self.page.fill('[data-testid="symbol-filter"]', symbol)
        await self.page.click(f'[data-testid="symbol-item-{symbol}"]')

        # 在画布上点击放置
        await self.click_canvas(x, y)

        # 旋转
        if rotation != 0:
            for _ in range(int(rotation / 90)):
                await self.press_key("r")

        # 完成放置
        await self.press_key("esc")

    async def draw_wire(self, start: Tuple[float, float], end: Tuple[float, float]):
        """
        绘制导线

        Args:
            start: 起点坐标 (x, y)
            end: 终点坐标 (x, y)
        """
        await self.activate_tool("draw_wire")
        await self.click_canvas(start[0], start[1])
        await self.click_canvas(end[0], end[1])
        await self.press_key("esc")

    async def place_power_symbol(self, symbol: str, x: float, y: float):
        """放置电源符号"""
        await self.click_menu("place", "power_symbol")
        await self.page.fill('[data-testid="power-symbol-filter"]', symbol)
        await self.page.click(f'[data-testid="power-symbol-{symbol}"]')
        await self.click_canvas(x, y)
        await self.press_key("esc")

    async def annotate_components(self):
        """标注器件"""
        await self.click_menu("tools", "annotate")
        await self.page.click('[data-testid="btn-annotate-all"]')
        await self.page.click('[data-testid="btn-confirm"]')

    async def run_erc(self) -> Dict[str, Any]:
        """运行 ERC 检查"""
        await self.click_menu("inspect", "erc")
        await self.page.click('[data-testid="btn-run-erc"]')
        await self.wait_for_element('[data-testid="erc-complete"]')

        # 获取 ERC 结果
        errors = await self.page.locator('[data-testid="erc-error"]').all()
        return {
            "error_count": len(errors),
            "errors": [await e.text_content() for e in errors],
        }

    # ========== PCB 编辑 ==========

    async def switch_to_pcb_editor(self):
        """切换到 PCB 编辑器"""
        await self.page.click('[data-testid="tab-pcb"]')
        await self.wait_for_load()

    async def update_pcb_from_schematic(self):
        """从原理图更新 PCB"""
        await self.click_menu("tools", "update_pcb_from_schematic")
        await self.page.click('[data-testid="btn-update-pcb"]')
        await self.wait_for_load()

    async def place_footprint(self, footprint: str, x: float, y: float):
        """
        放置封装

        Args:
            footprint: 封装名称（如 'R_0603', 'SOT-23'）
            x, y: 放置位置
        """
        await self.activate_tool("place_footprint")
        await self.page.fill('[data-testid="footprint-filter"]', footprint)
        await self.page.click(f'[data-testid="footprint-item-{footprint}"]')
        await self.click_canvas(x, y)
        await self.press_key("esc")

    async def route_track(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        layer: str = "F.Cu",
        width: float = 0.25,
    ):
        """
        布线

        Args:
            start: 起点
            end: 终点
            layer: 层名称
            width: 线宽（mm）
        """
        await self.activate_tool("route")
        await self.select_layer(layer)
        await self.set_track_width(width)
        await self.click_canvas(start[0], start[1])
        await self.click_canvas(end[0], end[1])
        await self.press_key("esc")

    async def add_via(
        self, x: float, y: float, top_layer: str = "F.Cu", bottom_layer: str = "B.Cu"
    ):
        """添加过孔"""
        await self.click_canvas(x, y)
        await self.press_key("v")

    async def fill_zone(self, net: str, layer: str):
        """铺铜"""
        await self.click_menu("place", "zone")
        await self.page.fill('[data-testid="zone-net"]', net)
        await self.select_layer(layer)
        # 绘制区域...
        await self.press_key("esc")

    async def auto_place_footprints(self):
        """自动布局"""
        await self.click_menu("tools", "auto_place")
        await self.page.click('[data-testid="btn-run-auto-place"]')
        await self.wait_for_load()

    async def auto_route(self):
        """自动布线"""
        await self.click_menu("route", "auto_route")
        await self.page.click('[data-testid="btn-run-auto-route"]')
        await self.wait_for_load()

    async def set_design_rules(self, rules: Dict[str, float]):
        """设置设计规则"""
        await self.click_menu("file", "board_setup")

        if "minTrackWidth" in rules:
            await self.page.fill(
                '[data-testid="rule-min-track-width"]', str(rules["minTrackWidth"])
            )

        if "minViaSize" in rules:
            await self.page.fill(
                '[data-testid="rule-min-via-size"]', str(rules["minViaSize"])
            )

        await self.page.click('[data-testid="btn-apply-rules"]')

    async def run_drc(self) -> Dict[str, Any]:
        """运行 DRC 检查"""
        await self.click_menu("inspect", "design_rules_check")
        await self.page.click('[data-testid="btn-run-drc"]')
        await self.wait_for_element('[data-testid="drc-complete"]')

        # 获取 DRC 结果
        report = await self.page.evaluate("""() => {
            const errors = Array.from(document.querySelectorAll('[data-testid="drc-error"]'))
                .map(e => ({
                    type: e.dataset.errorType,
                    description: e.textContent,
                    position: e.dataset.position
                }));
            return {
                error_count: errors.filter(e => e.type === 'error').length,
                warning_count: errors.filter(e => e.type === 'warning').length,
                unconnected: errors.filter(e => e.type === 'unconnected').length,
                errors: errors
            };
        }""")

        return report

    # ========== 文件导出 ==========

    async def export_gerber(self, output_dir: str) -> Dict[str, Any]:
        """导出 Gerber 文件"""
        await self.click_menu("file", "fabrication_outputs")
        await self.page.click('[data-testid="menu-gerbers"]')
        await self.page.fill('[data-testid="output-dir"]', output_dir)
        await self.page.click('[data-testid="btn-generate-gerbers"]')

        # 等待导出完成
        await self.wait_for_element('[data-testid="export-complete"]')

        # 获取导出文件列表
        files = await self.page.locator('[data-testid="exported-file"]').all()
        return {
            "success": True,
            "files": [await f.get_attribute("data-filename") for f in files],
        }

    async def export_drill(self, output_dir: str) -> Dict[str, Any]:
        """导出钻孔文件"""
        await self.click_menu("file", "fabrication_outputs")
        await self.page.click('[data-testid="menu-drill"]')
        await self.page.fill('[data-testid="output-dir"]', output_dir)
        await self.page.click('[data-testid="btn-generate-drill"]')
        await self.wait_for_element('[data-testid="export-complete"]')
        return {"success": True}

    async def export_bom(self, output_path: str) -> Dict[str, Any]:
        """导出 BOM"""
        await self.click_menu("file", "export")
        await self.page.click('[data-testid="export-bom"]')
        await self.page.fill('[data-testid="output-path"]', output_path)
        await self.page.click('[data-testid="btn-export"]')
        return {"success": True, "file": output_path}

    async def export_pickplace(self, output_dir: str) -> Dict[str, Any]:
        """导出 Pick & Place 文件"""
        await self.click_menu("file", "fabrication_outputs")
        await self.page.click('[data-testid="menu-pick-place"]')
        await self.page.fill('[data-testid="output-dir"]', output_dir)
        await self.page.click('[data-testid="btn-generate-pick-place"]')
        return {"success": True}

    async def export_all(self, output_dir: str) -> Dict[str, Any]:
        """导出所有生产文件"""
        results = {}

        results["gerber"] = await self.export_gerber(output_dir)
        results["drill"] = await self.export_drill(output_dir)
        results["bom"] = await self.export_bom(f"{output_dir}/bom.csv")
        results["pickplace"] = await self.export_pickplace(output_dir)

        return {
            "success": all(r.get("success", False) for r in results.values()),
            "results": results,
        }

    # ========== 状态查询 ==========

    async def get_screenshot(self) -> bytes:
        """获取截图"""
        return await self.page.screenshot()

    async def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        state = await self.page.evaluate("""() => {
            return {
                tool: document.querySelector('[data-testid="status-tool"]')?.textContent,
                coords: document.querySelector('[data-testid="status-coords"]')?.textContent,
                layer: document.querySelector('[data-testid="status-layer"]')?.textContent,
                zoom: document.querySelector('[data-testid="status-zoom"]')?.textContent
            };
        }""")
        return state

    async def get_logs(self) -> List[str]:
        """获取日志"""
        logs = await self.page.locator('[data-testid="log-entry"]').all()
        return [await log.text_content() for log in logs]

    async def get_errors(self) -> List[str]:
        """获取错误列表"""
        errors = await self.page.locator('[data-testid="error-item"]').all()
        return [await error.text_content() for error in errors]

    # ========== 低级操作 ==========

    async def click_menu(self, menu: str, item: Optional[str] = None):
        """点击菜单"""
        await self.page.click(f'[data-testid="menu-{menu}"]')
        if item:
            await self.page.click(f'[data-testid="{menu}-{item}"]')

    async def activate_tool(self, tool: str):
        """激活工具"""
        await self.page.click(f'[data-testid="tool-{tool}"]')

    async def click_canvas(self, x: float, y: float):
        """在画布上点击"""
        canvas = self.page.locator('[data-testid="canvas-overlay"]')
        await canvas.click(position={"x": x, "y": y})

    async def press_key(self, key: str):
        """发送按键"""
        await self.page.keyboard.press(key)

    async def type_text(self, text: str):
        """输入文本"""
        await self.page.keyboard.type(text)

    async def select_layer(self, layer: str):
        """选择层"""
        await self.page.click('[data-testid="layer-selector"]')
        await self.page.click(f'[data-testid="layer-{layer}"]')

    async def set_track_width(self, width: float):
        """设置线宽"""
        await self.page.fill('[data-testid="track-width"]', str(width))

    # ========== 等待方法 ==========

    async def wait_for_load(self, timeout: int = 10000):
        """等待加载完成"""
        await self.page.wait_for_load_state("networkidle", timeout=timeout)

    async def wait_for_element(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        await self.page.wait_for_selector(selector, timeout=timeout)

    async def wait_for_seconds(self, seconds: float):
        """等待指定秒数"""
        await asyncio.sleep(seconds)


# ========== 使用示例 ==========


async def example_usage():
    """使用示例"""
    agent = KiCadAIAgent()

    try:
        # 连接
        await agent.connect(headless=False)

        # 创建项目
        await agent.create_project("test-project")

        # 放置器件
        await agent.place_symbol("R", 50000000, 50000000)
        await agent.place_symbol("C", 60000000, 50000000)

        # 连线
        await agent.draw_wire((51000000, 50000000), (59000000, 50000000))

        # 标注
        await agent.annotate_components()

        # 保存
        await agent.save_project()

        # 截图
        screenshot = await agent.get_screenshot()
        with open("screenshot.png", "wb") as f:
            f.write(screenshot)

    finally:
        await agent.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())
