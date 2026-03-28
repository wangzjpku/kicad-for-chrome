"""
自动布线功能测试
测试KiCad自动布线的API接口
"""

import pytest
import requests
import time
import json

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/kicad-ipc"


class TestAutoRoute:
    """自动布线功能测试"""

    def __init__(self):
        """初始化"""
        self.results = []

    def test_kicad_status(self):
        """测试1: KiCad连接状态"""
        print("\n=== 测试1: KiCad连接状态 ===")
        response = requests.get(f"{API_BASE}/status")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "KiCad连接状态",
            "status_code": response.status_code,
            "connected": data.get("connected", False),
            "passed": response.status_code == 200
        })

        return data.get("connected", False)

    def test_kicad_start(self):
        """测试2: 启动KiCad"""
        print("\n=== 测试2: 启动KiCad ===")

        # 检查是否有KiCad
        import os
        kicad_path = os.environ.get("KICAD_CLI_PATH", "E:/Program Files/KiCad/9.0/bin/kicad.exe")
        if not os.path.exists(kicad_path):
            print(f"KiCad not found at {kicad_path}")
            self.results.append({
                "test": "启动KiCad",
                "passed": False,
                "error": "KiCad not found"
            })
            return False

        # 尝试启动KiCad
        response = requests.post(f"{API_BASE}/start")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "启动KiCad",
            "status_code": response.status_code,
            "success": data.get("success", False),
            "passed": response.status_code == 200 and data.get("success", False)
        })

        return data.get("connected", False)

    def test_get_routing_rules(self):
        """测试3: 获取布线规则"""
        print("\n=== 测试3: 获取布线规则 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "获取布线规则",
                "passed": False,
                "error": "KiCad not connected"
            })
            return None

        response = requests.get(f"{API_BASE}/routing-rules")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "获取布线规则",
            "status_code": response.status_code,
            "has_rules": "rules" in data,
            "passed": response.status_code == 200 and "rules" in data
        })

        return data.get("rules")

    def test_set_routing_rules(self):
        """测试4: 设置布线规则"""
        print("\n=== 测试4: 设置布线规则 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "设置布线规则",
                "passed": False,
                "error": "KiCad not connected"
            })
            return False

        rules = {
            "name": "Test Rule",
            "description": "Test routing rule",
            "min_trace_width": 0.15,
            "max_trace_width": 1.0,
            "default_trace_width": 0.25,
            "min_clearance": 0.15,
            "via_diameter": 0.6,
            "via_drill": 0.3,
            "impedance_controlled": False
        }

        response = requests.post(f"{API_BASE}/routing-rules", json=rules)
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "设置布线规则",
            "status_code": response.status_code,
            "success": data.get("success", False),
            "passed": response.status_code == 200
        })

        return data.get("success", False)

    def test_get_ratsnest(self):
        """测试5: 获取鼠线信息"""
        print("\n=== 测试5: 获取鼠线信息 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "获取鼠线信息",
                "passed": False,
                "error": "KiCad not connected"
            })
            return None

        response = requests.get(f"{API_BASE}/ratsnest")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "获取鼠线信息",
            "status_code": response.status_code,
            "success": data.get("success", False),
            "passed": response.status_code == 200
        })

        return data.get("ratsnest")

    def test_show_ratsnest(self):
        """测试6: 显示/隐藏鼠线"""
        print("\n=== 测试6: 显示鼠线 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "显示鼠线",
                "passed": False,
                "error": "KiCad not connected"
            })
            return False

        response = requests.post(f"{API_BASE}/show-ratsnest?show=true")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "显示鼠线",
            "status_code": response.status_code,
            "success": data.get("success", False),
            "passed": response.status_code == 200
        })

        return data.get("success", False)

    def test_auto_route(self):
        """测试7: 执行自动布线"""
        print("\n=== 测试7: 执行自动布线 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "执行自动布线",
                "passed": False,
                "error": "KiCad not connected"
            })
            return None

        route_params = {
            "net_class": "default",
            "ripup_days": False,
            "stability": 50,
            "max_iterations": 100
        }

        response = requests.post(f"{API_BASE}/auto-route", json=route_params)
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "执行自动布线",
            "status_code": response.status_code,
            "success": data.get("success", False),
            "passed": response.status_code == 200
        })

        return data.get("result")

    def test_clear_tracks(self):
        """测试8: 清除所有走线"""
        print("\n=== 测试8: 清除所有走线 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "清除所有走线",
                "passed": False,
                "error": "KiCad not connected"
            })
            return False

        response = requests.post(f"{API_BASE}/clear-tracks")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "清除所有走线",
            "status_code": response.status_code,
            "success": data.get("success", False),
            "passed": response.status_code == 200
        })

        return data.get("success", False)

    def test_get_statistics(self):
        """测试9: 获取PCB统计信息"""
        print("\n=== 测试9: 获取PCB统计信息 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "获取PCB统计信息",
                "passed": False,
                "error": "KiCad not connected"
            })
            return None

        response = requests.get(f"{API_BASE}/statistics")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "获取PCB统计信息",
            "status_code": response.status_code,
            "passed": response.status_code == 200
        })

        return data

    def test_get_items(self):
        """测试10: 获取PCB项目列表"""
        print("\n=== 测试10: 获取PCB项目列表 ===")

        # 先检查连接状态
        status_resp = requests.get(f"{API_BASE}/status")
        if not status_resp.json().get("connected"):
            print("KiCad未连接，跳过此测试")
            self.results.append({
                "test": "获取PCB项目列表",
                "passed": False,
                "error": "KiCad not connected"
            })
            return None

        response = requests.get(f"{API_BASE}/items")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        data = response.json()
        self.results.append({
            "test": "获取PCB项目列表",
            "status_code": response.status_code,
            "count": data.get("count", 0),
            "passed": response.status_code == 200
        })

        return data.get("items", [])

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*50)
        print("测试结果总结")
        print("="*50)

        passed = 0
        failed = 0

        for result in self.results:
            status = "✅ 通过" if result.get("passed", False) else "❌ 失败"
            print(f"{result.get('test', 'Unknown')}: {status}")
            if result.get("passed", False):
                passed += 1
            else:
                failed += 1

        print("="*50)
        print(f"总计: {passed} 通过, {failed} 失败")
        print(f"通过率: {passed*100/(passed+failed) if (passed+failed) > 0 else 0:.1f}%")
        print("="*50)

        return passed, failed


if __name__ == "__main__":
    # 手动运行测试
    tester = TestAutoRoute()

    # 测试1: 连接状态
    connected = tester.test_kicad_status()

    if not connected:
        # 测试2: 启动KiCad
        connected = tester.test_kicad_start()
        if connected:
            time.sleep(2)  # 等待KiCad完全启动

    # 如果连接了，继续测试其他功能
    if connected:
        # 测试3-10
        tester.test_get_routing_rules()
        tester.test_set_routing_rules()
        tester.test_get_ratsnest()
        tester.test_show_ratsnest()
        tester.test_auto_route()
        tester.test_clear_tracks()
        tester.test_get_statistics()
        tester.test_get_items()
    else:
        print("\nKiCad未连接，无法继续测试")
        # 即使未连接也测试API响应
        tester.test_get_routing_rules()
        tester.test_set_routing_rules()
        tester.test_get_ratsnest()
        tester.test_show_ratsnest()
        tester.test_auto_route()
        tester.test_clear_tracks()
        tester.test_get_statistics()
        tester.test_get_items()

    # 打印总结
    tester.print_summary()
