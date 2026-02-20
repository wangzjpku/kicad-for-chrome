"""
Ralph Loop Iter 2: 前端交互测试
测试前端UI和用户交互
"""

import asyncio
import socket
import sys
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"


def check_port(port):
    for addr in ["127.0.0.1", "::1"]:
        try:
            sock = socket.socket(
                socket.AF_INET if ":" not in addr else socket.AF_INET6,
                socket.SOCK_STREAM,
            )
            sock.settimeout(1)
            result = sock.connect_ex((addr if ":" not in addr else "::1", port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
    return False


async def test_frontend_interaction():
    logger.info("=" * 60)
    logger.info("Iter 2: Frontend Interaction Test")
    logger.info("=" * 60)

    # Check services
    if not check_port(8000):
        logger.error("Backend not running!")
        return False
    if not check_port(3000):
        logger.error("Frontend not running!")
        return False

    screenshots_dir = Path("test_results_iter2")
    screenshots_dir.mkdir(exist_ok=True)

    results = {
        "page_load": False,
        "new_project_button": False,
        "ai_button": False,
        "input_works": False,
        "backend_status_visible": False,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        try:
            # Test UI01: Page load
            logger.info("Test UI01: Page load...")
            await page.goto(FRONTEND_URL, timeout=30000)
            await asyncio.sleep(3)
            await page.screenshot(
                path=str(screenshots_dir / "01_page_load.png"), full_page=True
            )

            # Check for key elements
            page_content = await page.content()
            if "Auto-GPT" in page_content or "Projects" in page_content:
                results["page_load"] = True
                logger.info("  -> Page loaded successfully")

            # Check backend status
            if "已连接" in page_content or "Connected" in page_content:
                results["backend_status_visible"] = True
                logger.info("  -> Backend status visible")

            # Test UI02: New Project button
            logger.info("Test UI02: New Project button...")
            new_proj_btn = await page.query_selector('button:has-text("New Project")')
            if new_proj_btn:
                results["new_project_button"] = True
                logger.info("  -> New Project button found")
                await new_proj_btn.click()
                await asyncio.sleep(1)
                await page.screenshot(
                    path=str(screenshots_dir / "02_new_project.png"), full_page=True
                )

            # Test UI03: AI button
            logger.info("Test UI03: AI button...")
            ai_buttons = await page.query_selector_all("button")
            for btn in ai_buttons:
                text = await btn.inner_text()
                if "AI" in text or "创建" in text:
                    results["ai_button"] = True
                    logger.info(f"  -> AI button found: {text}")
                    await btn.click()
                    await asyncio.sleep(1)
                    await page.screenshot(
                        path=str(screenshots_dir / "03_ai_dialog.png"), full_page=True
                    )
                    break

            # Test UI04: Input field
            logger.info("Test UI04: Input field...")
            textarea = await page.query_selector("textarea")
            if textarea:
                results["input_works"] = True
                logger.info("  -> Textarea found")
                await textarea.fill("测试LED电路")
                await asyncio.sleep(0.5)
                await page.screenshot(
                    path=str(screenshots_dir / "04_input_filled.png"), full_page=True
                )

            # Test UI05: Check for dialog overlay issue
            logger.info("Test UI05: Dialog overlay check...")
            overlay = await page.query_selector('.dialog-overlay, [class*="overlay"]')
            if overlay:
                logger.warning("  -> Dialog overlay detected (may block clicks)")

        except Exception as e:
            logger.error(f"Test error: {e}")
        finally:
            await browser.close()

    # Summary
    logger.info("=" * 60)
    logger.info("Iter 2 Results:")
    logger.info("=" * 60)
    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        logger.info(f"  {k}: {status}")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    logger.info(f"Total: {passed}/{total} passed")

    return passed >= 3  # At least 3/5 should pass


if __name__ == "__main__":
    try:
        success = asyncio.run(test_frontend_interaction())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)
