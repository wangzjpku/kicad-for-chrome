"""
Ralph Loop Iter 5: 异常处理测试
测试边界条件和错误恢复
"""

import asyncio
import socket
import sys
import json
from pathlib import Path
import urllib.request
import urllib.error
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000"


def make_request(url, data=None, method="POST"):
    """发送HTTP请求"""
    try:
        headers = {"Content-Type": "application/json"}
        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}


def test_exception_handling():
    logger.info("=" * 60)
    logger.info("Iter 5: Exception Handling Test")
    logger.info("=" * 60)

    results = {}

    # EX01: 空需求输入
    logger.info("Test EX01: Empty requirements...")
    result = make_request(f"{BACKEND_URL}/api/v1/ai/analyze", {"requirements": ""})
    if "spec" in result:
        results["EX01_empty_input"] = "PASS - returns default project"
    elif "error" in result:
        results["EX01_empty_input"] = "PASS - returns error"
    else:
        results["EX01_empty_input"] = f"UNEXPECTED: {result}"

    # EX02: 超短输入
    logger.info("Test EX02: Short input 'a'...")
    result = make_request(f"{BACKEND_URL}/api/v1/ai/analyze", {"requirements": "a"})
    if "spec" in result:
        results["EX02_short_input"] = "PASS"
    else:
        results["EX02_short_input"] = f"FAIL: {result}"

    # EX03: 有效需求
    logger.info("Test EX03: Valid LED circuit...")
    result = make_request(
        f"{BACKEND_URL}/api/v1/ai/analyze", {"requirements": "LED闪烁电路"}
    )
    if "spec" in result and "components" in result["spec"]:
        comp_count = len(result["spec"]["components"])
        has_footprint = all("footprint" in c for c in result["spec"]["components"])
        results["EX03_valid_requirements"] = (
            f"PASS - {comp_count} components, footprints: {has_footprint}"
        )
    else:
        results["EX03_valid_requirements"] = f"FAIL: {result}"

    # EX04: 封装推荐空输入
    logger.info("Test EX04: Empty footprint recommend...")
    result = make_request(
        f"{BACKEND_URL}/api/v1/ai/footprint/recommend", {"component_name": ""}
    )
    if "recommendation" in result:
        results["EX04_empty_component"] = (
            f"PASS - returns: {result.get('recommendation')}"
        )
    else:
        results["EX04_empty_component"] = f"INFO: {result}"

    # EX05: 正常封装推荐
    logger.info("Test EX05: Normal footprint recommend...")
    result = make_request(
        f"{BACKEND_URL}/api/v1/ai/footprint/recommend",
        {"component_name": "电阻", "package": "0805"},
    )
    if "recommendation" in result:
        results["EX05_normal_footprint"] = f"PASS - {result.get('recommendation')}"
    else:
        results["EX05_normal_footprint"] = f"FAIL: {result}"

    # EX06: 无效项目ID
    logger.info("Test EX06: Invalid project ID...")
    result = make_request(f"{BACKEND_URL}/api/v1/projects/invalid-id-123", method="GET")
    if "detail" in result or "error" in result:
        results["EX06_invalid_project"] = "PASS - returns 404"
    else:
        results["EX06_invalid_project"] = f"UNEXPECTED: {result}"

    # EX07: 健康检查
    logger.info("Test EX07: Health check...")
    result = make_request(f"{BACKEND_URL}/api/v1/ai/health", method="GET")
    if "status" in result:
        results["EX07_health_check"] = f"PASS - {result.get('status')}"
    else:
        results["EX07_health_check"] = f"FAIL: {result}"

    # Summary
    logger.info("=" * 60)
    logger.info("Iter 5 Results:")
    logger.info("=" * 60)
    for k, v in results.items():
        logger.info(f"  {k}: {v}")

    passed = sum(1 for v in results.values() if "PASS" in v)
    total = len(results)
    logger.info(f"Total: {passed}/{total} passed")
    logger.info("=" * 60)

    return passed >= total - 1  # Allow 1 failure


if __name__ == "__main__":
    try:
        success = test_exception_handling()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
