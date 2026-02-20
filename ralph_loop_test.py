"""
Ralph Loop 迭代测试脚本
模拟人工手动操作，测试 KiCad for Chrome 应用的各项功能

Ralph Loop 方法：
1. Record - 记录测试步骤
2. Analyze - 分析测试结果
3. Plan - 规划下一步
4. Execute - 执行测试
5. Loop - 迭代直到全部通过
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# ========== 配置 ==========
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
API_BASE = f"{BACKEND_URL}/api/v1"


# 测试结果类
class TestResult:
    def __init__(
        self,
        iteration: int,
        test_name: str,
        passed: bool,
        details: str,
        error: Optional[str] = None,
        fix_applied: Optional[str] = None,
    ):
        self.iteration = iteration
        self.test_name = test_name
        self.passed = passed
        self.details = details
        self.error = error
        self.fix_applied = fix_applied


# 测试记录
test_history: List[TestResult] = []


def log_test(result: TestResult):
    """记录测试结果"""
    test_history.append(result)
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"[Iteration {result.iteration}] {result.test_name}")
    print(f"Status: {status}")
    print(f"Details: {result.details}")
    if result.error:
        print(f"Error: {result.error}")
    if result.fix_applied:
        print(f"Fix: {result.fix_applied}")
    print("=" * 60)


def test_backend_health() -> TestResult:
    """测试1: 后端健康检查"""
    iteration = 1
    test_name = "后端健康检查"

    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if response.status_code == 200:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details="后端服务正常运行，API文档可访问",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"后端返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="无法连接到后端服务",
            error=str(e),
        )


def test_frontend_health() -> TestResult:
    """测试2: 前端健康检查"""
    iteration = 2
    test_name = "前端健康检查"

    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details="前端服务正常运行",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"前端返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="无法连接到前端服务",
            error=str(e),
        )


def test_ai_footprint_search_resistor() -> TestResult:
    """测试3: 封装搜索 - 电阻"""
    iteration = 3
    test_name = "封装搜索 - 电阻"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search",
            params={"keyword": "resistor"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个电阻封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_capacitor() -> TestResult:
    """测试4: 封装搜索 - 电容"""
    iteration = 4
    test_name = "封装搜索 - 电容"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search",
            params={"keyword": "capacitor"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个电容封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_ic() -> TestResult:
    """测试5: 封装搜索 - 集成电路"""
    iteration = 5
    test_name = "封装搜索 - IC"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search", params={"keyword": "ic"}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个IC封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_atmega() -> TestResult:
    """测试6: 封装搜索 - ATmega328"""
    iteration = 6
    test_name = "封装搜索 - ATmega328"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search",
            params={"keyword": "ATmega328"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个ATmega封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_empty() -> TestResult:
    """测试7: 封装搜索 - 空关键词"""
    iteration = 7
    test_name = "封装搜索 - 空关键词"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search", params={"keyword": ""}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            # 空关键词应该返回适当的错误或空结果，而不是默认项目
            if data.get("success") == False or not data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details="空关键词正确处理（返回错误或空结果）",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="空关键词返回了结果，应该返回错误",
                    error="空关键词未正确处理",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装搜索API调用失败",
            error=str(e),
        )


def test_project_list() -> TestResult:
    """测试8: 项目列表API"""
    iteration = 8
    test_name = "项目列表API"

    try:
        response = requests.get(f"{API_BASE}/project/list", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details=f"项目列表API正常，返回 {len(data.get('projects', []))} 个项目",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="项目列表API调用失败",
            error=str(e),
        )


def test_kicad_status() -> TestResult:
    """测试9: KiCad状态检查"""
    iteration = 9
    test_name = "KiCad状态检查"

    try:
        response = requests.get(f"{API_BASE}/kicad/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details=f"KiCad状态: {data.get('status', 'unknown')}",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="KiCad状态API调用失败",
            error=str(e),
        )


def test_screenshot_api() -> TestResult:
    """测试10: 截图API"""
    iteration = 10
    test_name = "截图API"

    try:
        response = requests.get(f"{API_BASE}/kicad/screenshot", timeout=10)
        if response.status_code == 200:
            # 截图API应该返回图片或JSON
            content_type = response.headers.get("content-type", "")
            if "image" in content_type or "json" in content_type:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"截图API正常，Content-Type: {content_type}",
                )
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details="截图API正常返回",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="截图API调用失败",
            error=str(e),
        )


def test_ai_analyze_requirements_valid() -> TestResult:
    """测试11: AI分析有效需求"""
    iteration = 11
    test_name = "AI分析 - 有效需求"

    try:
        response = requests.post(
            f"{API_BASE}/ai/analyze",
            json={"requirements": "设计一个5V稳压电源，使用LM7805"},
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"AI分析成功: {data.get('message', 'OK')}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details=f"AI分析失败: {data.get('message', 'Unknown error')}",
                    error=data.get("message", "Unknown error"),
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="AI分析API调用失败",
            error=str(e),
        )


def test_ai_analyze_empty() -> TestResult:
    """测试12: AI分析空需求"""
    iteration = 12
    test_name = "AI分析 - 空需求"

    try:
        response = requests.post(
            f"{API_BASE}/ai/analyze", json={"requirements": ""}, timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            # 空需求应该返回错误
            if data.get("success") == False:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details="空需求正确返回错误",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="空需求应该返回错误，但返回了成功",
                    error="空需求未正确处理",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="AI分析API调用失败",
            error=str(e),
        )


def test_ai_footprint_recommend() -> TestResult:
    """测试13: 封装推荐API"""
    iteration = 13
    test_name = "封装推荐API"

    try:
        response = requests.post(
            f"{API_BASE}/ai/footprint/recommend",
            json={"component_name": "ATmega328P", "package": "DIP-28"},
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("recommended_footprint"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"推荐封装: {data['recommended_footprint']}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="封装推荐返回空结果",
                    error="推荐失败",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装推荐API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_led() -> TestResult:
    """测试14: 封装搜索 - LED"""
    iteration = 14
    test_name = "封装搜索 - LED"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search", params={"keyword": "led"}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个LED封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="LED封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="LED封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_usb() -> TestResult:
    """测试15: 封装搜索 - USB连接器"""
    iteration = 15
    test_name = "封装搜索 - USB"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search", params={"keyword": "usb"}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个USB封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="USB封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="USB封装搜索API调用失败",
            error=str(e),
        )


def test_menu_click_api() -> TestResult:
    """测试16: 菜单点击API"""
    iteration = 16
    test_name = "菜单点击API"

    try:
        response = requests.post(
            f"{API_BASE}/kicad/menu/click", json={"menu_path": "File"}, timeout=10
        )
        if response.status_code == 200:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details="菜单点击API正常",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="菜单点击API调用失败",
            error=str(e),
        )


def test_tool_activate_api() -> TestResult:
    """测试17: 工具激活API"""
    iteration = 17
    test_name = "工具激活API"

    try:
        response = requests.post(
            f"{API_BASE}/kicad/tool/activate", json={"tool": "Select"}, timeout=10
        )
        if response.status_code == 200:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details="工具激活API正常",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="工具激活API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_mosfet() -> TestResult:
    """测试18: 封装搜索 - MOS管"""
    iteration = 18
    test_name = "封装搜索 - MOS管"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search", params={"keyword": "mosfet"}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个MOS封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="MOS封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="MOS封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_crystal() -> TestResult:
    """测试19: 封装搜索 - 晶振"""
    iteration = 19
    test_name = "封装搜索 - 晶振"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search", params={"keyword": "crystal"}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=True,
                    details=f"找到 {len(data['results'])} 个晶振封装: {data['results'][:3]}",
                )
            else:
                return TestResult(
                    iteration=iteration,
                    test_name=test_name,
                    passed=False,
                    details="晶振封装搜索返回空结果",
                    error="搜索返回 success=false 或空结果",
                )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="晶振封装搜索API调用失败",
            error=str(e),
        )


def test_ai_footprint_search_unknown() -> TestResult:
    """测试20: 封装搜索 - 未知关键词"""
    iteration = 20
    test_name = "封装搜索 - 未知关键词"

    try:
        response = requests.get(
            f"{API_BASE}/ai/footprint/search",
            params={"keyword": "xyz123unknown"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            # 未知关键词可能返回空结果或默认封装
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=True,
                details=f"未知关键词处理: success={data.get('success')}, results={len(data.get('results', []))}",
            )
        else:
            return TestResult(
                iteration=iteration,
                test_name=test_name,
                passed=False,
                details=f"API返回状态码 {response.status_code}",
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return TestResult(
            iteration=iteration,
            test_name=test_name,
            passed=False,
            details="封装搜索API调用失败",
            error=str(e),
        )


# 所有测试函数列表
ALL_TESTS = [
    test_backend_health,
    test_frontend_health,
    test_ai_footprint_search_resistor,
    test_ai_footprint_search_capacitor,
    test_ai_footprint_search_ic,
    test_ai_footprint_search_atmega,
    test_ai_footprint_search_empty,
    test_project_list,
    test_kicad_status,
    test_screenshot_api,
    test_ai_analyze_requirements_valid,
    test_ai_analyze_empty,
    test_ai_footprint_recommend,
    test_ai_footprint_search_led,
    test_ai_footprint_search_usb,
    test_menu_click_api,
    test_tool_activate_api,
    test_ai_footprint_search_mosfet,
    test_ai_footprint_search_crystal,
    test_ai_footprint_search_unknown,
]


def run_all_tests() -> List[TestResult]:
    """运行所有测试"""
    results = []

    print("\n" + "=" * 60)
    print("开始 Ralph Loop 迭代测试")
    print("=" * 60)

    for test_func in ALL_TESTS:
        result = test_func()
        log_test(result)
        results.append(result)

        # 每次测试后短暂等待
        time.sleep(0.5)

    return results


def print_summary(results: List[TestResult]):
    """打印测试摘要"""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"总计: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"通过率: {passed / total * 100:.1f}%")
    print("=" * 60)

    if failed > 0:
        print("\n失败测试详情:")
        for r in results:
            if not r.passed:
                print(f"  - 迭代{r.iteration}: {r.test_name}")
                print(f"    错误: {r.error}")
                print(f"    详情: {r.details}")


if __name__ == "__main__":
    results = run_all_tests()
    print_summary(results)

    # 保存结果到文件
    with open("ralph_loop_test_results.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "iteration": r.iteration,
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "details": r.details,
                    "error": r.error,
                    "fix_applied": r.fix_applied,
                }
                for r in results
            ],
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n结果已保存到 ralph_loop_test_results.json")

    # 返回退出码
    sys.exit(0 if all(r.passed for r in results) else 1)
