#!/usr/bin/env python3
"""
Ralph Loop 自动化测试框架
用于持续执行测试→检查结果→失败则修复代码→再次测试 循环
"""

import sys
import io
# 设置UTF-8输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import subprocess
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 测试用例定义（从 ralph测试文档.txt 提取的 P0 优先测试用例）
TEST_CASES = {
    # 项目文件操作测试
    "F-001": {
        "name": "新建项目",
        "description": "点击'+ New Project'按钮创建新项目",
        "test_type": "frontend_api",
        "api_endpoint": "/api/v1/projects",
        "method": "POST",
        "data": {"name": "TestProject_Automated"},
        "expected_status": 200,
    },
    "F-002": {
        "name": "保存到本地",
        "description": "创建项目后保存到本地",
        "test_type": "frontend_api",
        "api_endpoint": "/api/v1/projects/{id}",
        "method": "GET",
        "expected_status": 200,
    },
    "F-006": {
        "name": "导出Gerber",
        "description": "导出Gerber文件",
        "test_type": "frontend_api",
        "api_endpoint": "/api/v1/projects/{id}/export/gerber",
        "method": "POST",
        "expected_status": 200,
    },
    "F-007": {
        "name": "导出BOM清单",
        "description": "导出BOM物料清单",
        "test_type": "frontend_api",
        "api_endpoint": "/api/v1/projects/{id}/export/bom",
        "method": "POST",
        "expected_status": 200,
    },
    # 原理图编辑器测试
    "S-001": {
        "name": "放置元件",
        "description": "在原理图编辑器中放置元件",
        "test_type": "store_action",
        "action": "addComponent",
        "expected_result": "component_added",
    },
    "S-008": {
        "name": "修改元件属性",
        "description": "双击元件修改属性",
        "test_type": "store_action",
        "action": "updateComponent",
        "expected_result": "component_updated",
    },
    "S-010": {
        "name": "删除元件",
        "description": "选中元件按Delete删除",
        "test_type": "store_action",
        "action": "removeSelectedElements",
        "expected_result": "element_removed",
    },
    "S-011": {
        "name": "撤销操作",
        "description": "删除后按Ctrl+Z撤销",
        "test_type": "store_action",
        "action": "undo",
        "expected_result": "undo_success",
    },
    # PCB编辑器测试
    "P-001": {
        "name": "导入网表",
        "description": "从原理图导入网表到PCB",
        "test_type": "frontend_api",
        "api_endpoint": "/api/v1/projects/{id}/pcb/design",
        "method": "GET",
        "expected_status": 200,
    },
    "P-003": {
        "name": "布线工具",
        "description": "使用布线工具连接焊盘",
        "test_type": "store_action",
        "action": "addTrack",
        "expected_result": "track_added",
    },
    "P-009": {
        "name": "DRC检查",
        "description": "运行设计规则检查",
        "test_type": "frontend_api",
        "api_endpoint": "/api/v1/projects/{id}/drc/run",
        "method": "POST",
        "expected_status": 200,
    },
}

class RalphTestFramework:
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.project_id = None

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 使用ASCII字符避免编码问题
        status_icons = {"INFO": "[i]", "ERROR": "[x]", "PASS": "[+]", "FAIL": "[!]"}
        icon = status_icons.get(level, "[*]")
        print(f"[{timestamp}] {icon} {message}")

    def check_services(self) -> bool:
        """检查后端和前端服务是否运行"""
        self.log("检查服务状态...")
        try:
            # 检查后端
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{self.backend_url}/api/health"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip() != "200":
                self.log("后端服务未运行", "ERROR")
                return False

            # 检查前端
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", self.frontend_url],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip() != "200":
                self.log("前端服务未运行", "ERROR")
                return False

            self.log("所有服务运行正常")
            return True
        except Exception as e:
            self.log(f"服务检查失败: {e}", "ERROR")
            return False

    def run_api_test(self, test_case: Dict) -> Tuple[bool, str]:
        """执行API测试"""
        endpoint = test_case["api_endpoint"]
        method = test_case["method"]

        # 如果需要project_id但没有，则先创建一个
        if "{id}" in endpoint and not self.project_id:
            success, msg = self.create_test_project()
            if not success:
                return False, msg

        endpoint = endpoint.replace("{id}", self.project_id) if self.project_id else endpoint
        url = f"{self.backend_url}{endpoint}"

        try:
            if method == "GET":
                result = subprocess.run(
                    ["curl", "-s", "-w", "\\n%{http_code}", url],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout
                status_code = output.strip().split("\n")[-1]
                response_body = "\n".join(output.strip().split("\n")[:-1])
            elif method == "POST":
                data = json.dumps(test_case.get("data", {}))
                result = subprocess.run(
                    ["curl", "-s", "-w", "\\n%{http_code}", "-X", "POST", "-H", "Content-Type: application/json", "-d", data, url],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout
                status_code = output.strip().split("\n")[-1]
                response_body = "\n".join(output.strip().split("\n")[:-1])

            expected_status = str(test_case["expected_status"])
            success = status_code == expected_status

            if success:
                return True, f"API返回状态码 {status_code}"
            else:
                return False, f"期望 {expected_status}, 实际 {status_code}, 响应: {response_body[:200]}"

        except Exception as e:
            return False, f"API请求失败: {e}"

    def create_test_project(self) -> Tuple[bool, str]:
        """创建测试项目"""
        self.log("创建测试项目...")
        url = f"{self.backend_url}/api/v1/projects"
        data = json.dumps({"name": f"TestProject_{int(time.time())}"})

        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json", "-d", data, url],
                capture_output=True,
                text=True,
                timeout=10
            )
            response = result.stdout

            try:
                project_data = json.loads(response)
                if "id" in project_data:
                    self.project_id = project_data["id"]
                    self.log(f"测试项目创建成功: {self.project_id}")
                    return True, self.project_id
            except json.JSONDecodeError:
                pass

            return False, f"无法解析项目创建响应: {response[:200]}"
        except Exception as e:
            return False, f"创建项目失败: {e}"

    def run_frontend_test(self, test_case: Dict) -> Tuple[bool, str]:
        """执行前端测试"""
        # 检查前端页面是否正常加载
        try:
            result = subprocess.run(
                ["curl", "-s", self.frontend_url],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "kicad" in result.stdout.lower() or "KiCad" in result.stdout:
                return True, "前端页面加载正常"
            else:
                return False, "前端页面内容异常"
        except Exception as e:
            return False, f"前端测试失败: {e}"

    def run_test(self, test_id: str) -> Tuple[bool, str]:
        """运行单个测试用例"""
        test_case = TEST_CASES.get(test_id)
        if not test_case:
            return False, f"测试用例 {test_id} 不存在"

        self.log(f"执行测试: {test_id} - {test_case['name']}")

        test_type = test_case.get("test_type", "frontend_api")

        if test_type == "frontend_api":
            return self.run_api_test(test_case)
        elif test_type == "frontend":
            return self.run_frontend_test(test_case)
        elif test_type == "store_action":
            # Store测试需要更复杂的设置，这里暂时返回跳过
            return False, "Store action 测试需要前端运行环境"
        else:
            return False, f"未知的测试类型: {test_type}"

    def run_all_tests(self) -> Dict[str, Dict]:
        """运行所有测试用例"""
        self.log("=" * 60)
        self.log("开始执行 Ralph Loop 自动化测试")
        self.log("=" * 60)

        # 首先检查服务
        if not self.check_services():
            self.log("服务检查失败，请确保后端和前端正在运行", "ERROR")
            self.log("启动命令:")
            self.log("  后端: cd kicad-ai-auto/agent && python main.py")
            self.log("  前端: cd kicad-ai-auto/web && npm run dev")
            return {}

        # 按优先级执行测试
        priority_order = ["F-001", "F-002", "S-008", "S-010", "S-011", "F-006", "F-007", "P-001", "P-003", "P-009"]

        for test_id in priority_order:
            if test_id not in TEST_CASES:
                continue

            success, message = self.run_test(test_id)

            self.results[test_id] = {
                "name": TEST_CASES[test_id]["name"],
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }

            status = "✅ PASS" if success else "❌ FAIL"
            self.log(f"{test_id}: {status} - {message}")

        self.log("=" * 60)
        self.log("测试执行完成")
        self.log("=" * 60)

        # 统计结果
        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)
        self.log(f"通过: {passed}/{total}")

        return self.results

    def generate_report(self) -> str:
        """生成测试报告"""
        report = ["# Ralph Loop 测试报告\n"]
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)
        report.append(f"**通过率: {passed}/{total} ({passed*100//total}%)**\n\n")

        report.append("## 测试结果详情\n")
        report.append("| 编号 | 测试项 | 状态 | 说明 |\n")
        report.append("|------|--------|------|------|\n")

        for test_id, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report.append(f"| {test_id} | {result['name']} | {status} | {result['message']} |\n")

        return "".join(report)

def main():
    framework = RalphTestFramework()
    results = framework.run_all_tests()

    if results:
        report = framework.generate_report()
        print("\n" + report)

        # 保存报告
        with open("RALPH_TEST_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report)

        print("\n报告已保存到 RALPH_TEST_REPORT.md")

        # 返回退出码
        passed = sum(1 for r in results.values() if r["success"])
        sys.exit(0 if passed == len(results) else 1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
