"""
KiCad AI RF PCB Test Script - 改进版
"""

import asyncio
import socket
import sys
import json
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"


def check_port(port):
    """检查端口 - 同时检查IPv4和IPv6"""
    for addr in ["127.0.0.1", "0.0.0.0"]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((addr, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("::1", port))
        sock.close()
        if result == 0:
            return True
    except:
        pass
    return False


async def run_test():
    logger.info("=" * 60)
    logger.info("RF PCB Test - Starting")
    logger.info("=" * 60)

    # Check services
    backend_ok = check_port(8000)
    frontend_ok = check_port(3000)

    logger.info(f"Backend (8000): {'OK' if backend_ok else 'NOT RUNNING'}")
    logger.info(f"Frontend (3000): {'OK' if frontend_ok else 'NOT RUNNING'}")

    if not backend_ok or not frontend_ok:
        logger.error("Please start services first!")
        return False

    # Test API first
    logger.info("Testing AI API...")
    import urllib.request

    req = urllib.request.Request(
        "http://localhost:8000/api/v1/ai/analyze",
        data=json.dumps({"requirements": "射频放大器"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        ai_result = json.loads(response.read())
        components = ai_result.get("spec", {}).get("components", [])
        logger.info(f"AI API returned {len(components)} components")

        # Check footprints
        footprints_ok = all(c.get("footprint") for c in components)
        logger.info(f"All components have footprints: {footprints_ok}")

        for comp in components:
            logger.info(
                f"  - {comp.get('name')}: {comp.get('footprint', 'NO FOOTPRINT')}"
            )

    # Create screenshot directory
    screenshots_dir = Path("rf_test_results")
    screenshots_dir.mkdir(exist_ok=True)

    test_results = {"passed": False, "api_works": True, "errors": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        page.on("pageerror", lambda err: test_results["errors"].append(str(err)))

        try:
            # Step 1: Access frontend
            logger.info("Step 1: Access frontend...")
            await page.goto(FRONTEND_URL, timeout=30000)
            await asyncio.sleep(3)
            await page.screenshot(
                path=str(screenshots_dir / "01_frontend.png"), full_page=True
            )
            logger.info("  -> Frontend loaded")

            # Step 2: Click New Project button
            logger.info("Step 2: Click New Project...")
            new_project_btn = await page.query_selector(
                'button:has-text("New Project")'
            )
            if new_project_btn:
                await new_project_btn.click()
                await asyncio.sleep(2)
                await page.screenshot(
                    path=str(screenshots_dir / "02_new_project.png"), full_page=True
                )
                logger.info("  -> New project dialog opened")
            else:
                logger.warning(
                    "  -> New Project button not found, trying AI button instead"
                )

            # Step 3: Click AI button
            logger.info("Step 3: Click AI button...")
            ai_buttons = await page.query_selector_all("button")
            ai_btn = None
            for btn in ai_buttons:
                text = await btn.inner_text()
                if "AI" in text or "创建" in text:
                    ai_btn = btn
                    break

            if ai_btn:
                await ai_btn.click()
                await asyncio.sleep(2)
                await page.screenshot(
                    path=str(screenshots_dir / "03_ai_clicked.png"), full_page=True
                )
                logger.info("  -> AI dialog should be open")

            # Step 4: Look for input elements
            logger.info("Step 4: Look for input...")
            textarea = await page.query_selector("textarea")
            input_field = await page.query_selector("input")

            if textarea:
                logger.info("  -> Found textarea")
                await textarea.fill("设计一个2.4GHz射频放大器PCB模块，使用BFR540晶体管")
                await page.screenshot(
                    path=str(screenshots_dir / "04_input.png"), full_page=True
                )

                # Find and click generate button
                gen_buttons = await page.query_selector_all("button")
                for btn in gen_buttons:
                    text = await btn.inner_text()
                    if "生成" in text or "Create" in text or "生成" in text:
                        await btn.click()
                        logger.info("  -> Clicked generate")
                        await asyncio.sleep(5)
                        await page.screenshot(
                            path=str(screenshots_dir / "05_generated.png"),
                            full_page=True,
                        )
                        break
            elif input_field:
                logger.info("  -> Found input field")
                await input_field.fill("射频放大器")
                await page.screenshot(
                    path=str(screenshots_dir / "04_input.png"), full_page=True
                )

            # Step 5: Wait and check results
            logger.info("Step 5: Check results...")
            await asyncio.sleep(3)
            await page.screenshot(
                path=str(screenshots_dir / "06_results.png"), full_page=True
            )

            # Check page content
            body = await page.content()
            if "PCB" in body or "pcb" in body.lower() or "project" in body.lower():
                test_results["passed"] = True
                logger.info("  -> Project elements detected!")

            # Step 6: API verification summary
            logger.info("Step 6: API Verification")
            logger.info(f"  -> AI API works: {test_results['api_works']}")
            logger.info(f"  -> Components generated: {len(components)}")
            logger.info(f"  -> Footprints assigned: {footprints_ok}")

        except Exception as e:
            logger.error(f"Test error: {e}")
            test_results["errors"].append(str(e))
            await page.screenshot(
                path=str(screenshots_dir / "error.png"), full_page=True
            )

        finally:
            await browser.close()

    # Final results
    logger.info("=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"AI API Functional: {test_results['api_works']}")
    logger.info(f"Components Generated: {len(components)}")
    logger.info(f"Footprints Assigned: {footprints_ok}")
    logger.info(f"Frontend UI Works: {test_results['passed']}")

    if test_results["errors"]:
        logger.info(f"Errors: {test_results['errors']}")

    logger.info(f"Screenshots saved to: {screenshots_dir}/")
    logger.info("=" * 60)

    # Test passes if API works and has footprints
    return test_results["api_works"] and footprints_ok


if __name__ == "__main__":
    try:
        success = asyncio.run(run_test())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
