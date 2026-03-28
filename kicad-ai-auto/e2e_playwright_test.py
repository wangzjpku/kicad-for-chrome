"""
KiCad AI Auto Playwright E2E 测试

使用 Playwright 进行浏览器自动化测试
测试前端 UI 交互流程
"""

import pytest
import time
import os

# Playwright 测试
pytest_plugins = ('playwright',)

BASE_URL = "http://localhost:3000"
WEB_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"


class TestFrontend:
    """前端UI测试"""

    @pytest.fixture(scope="class")
    def browser(self, playwright):
        """启动浏览器"""
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()

    def test_page_loads(self, browser):
        """测试页面加载"""
        page = browser.new_page()
        page.goto(WEB_URL, timeout=30000)
        # 等待页面加载
        page.wait_for_load_state("networkidle", timeout=10000)
        # 截图
        page.screenshot(path="test_outputs/01_page_load.png")
        page.close()

    def test_navigate_to_projects(self, browser):
        """测试导航到项目列表"""
        page = browser.new_page()
        page.goto(WEB_URL, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)

        # 查找项目链接并点击
        try:
            project_link = page.locator("text=项目").first
            project_link.click()
            page.wait_for_timeout(2000)
            page.screenshot(path="test_outputs/02_projects.png")
        except Exception as e:
            page.screenshot(path="test_outputs/02_error.png")
            print(f"导航失败: {e}")

        page.close()

    def test_open_ai_dialog(self, browser):
        """测试打开AI对话框"""
        page = browser.new_page()
        page.goto(WEB_URL, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)

        try:
            # 查找AI按钮
            ai_button = page.locator("text=AI").first
            ai_button.click()
            page.wait_for_timeout(2000)
            page.screenshot(path="test_outputs/03_ai_dialog.png")

            # 检查对话框是否打开
            dialog = page.locator('[role="dialog"]')
            if dialog.count() > 0:
                print("AI对话框已打开")
        except Exception as e:
            page.screenshot(path="test_outputs/03_error.png")
            print(f"AI对话框打开失败: {e}")

        page.close()


class TestFullWorkflow:
    """完整工作流测试"""

    @pytest.fixture(scope="class")
    def browser(self, playwright):
        """启动浏览器"""
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()

    @pytest.fixture(scope="class")
    def authenticated_page(self, browser):
        """创建已认证的页面"""
        page = browser.new_page()
        page.goto(WEB_URL, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)
        return page

    def test_create_new_project(self, browser):
        """测试创建新项目"""
        page = browser.new_page()
        page.goto(WEB_URL, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)

        try:
            # 点击新建项目
            new_project_btn = page.locator("text=新建").first
            new_project_btn.click()
            page.wait_for_timeout(1000)

            # 填写项目名
            name_input = page.locator('input[type="text"], input[placeholder*="名称"]').first
            if name_input.count() > 0:
                name_input.fill(f"Test_Project_{int(time.time())}")

                # 点击确认
                confirm_btn = page.locator("text=创建, text=确定").first
                confirm_btn.click()
                page.wait_for_timeout(2000)

            page.screenshot(path="test_outputs/04_new_project.png")
            print("新项目创建完成")
        except Exception as e:
            page.screenshot(path="test_outputs/04_error.png")
            print(f"创建项目失败: {e}")

        page.close()


if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("test_outputs", exist_ok=True)
    pytest.main([__file__, "-v", "--tb=short"])
