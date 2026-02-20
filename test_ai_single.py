"""
测试 AI 分析功能 - 单次测试版本
"""

import os
import sys
import subprocess
import time
import requests
import json

BASE_URL = "http://localhost:8000"

# 设置环境变量
os.environ["ZHIPU_API_KEY"] = "c762f2f90a2944cc9ccceaedee969a33.I6x5IhWw7IWcublJ"


def start_backend():
    """启动后端服务"""
    print("Starting backend server...")
    env = os.environ.copy()
    env["ZHIPU_API_KEY"] = "c762f2f90a2944cc9ccceaedee969a33.I6x5IhWw7IWcublJ"

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd="kicad-ai-auto/agent",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print("Waiting for server to start...")
    time.sleep(8)

    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"Server started: {response.status_code == 200}")
    except:
        print("Warning: Server may not be ready")

    return proc


def test_single(requirements, test_name):
    """测试单个需求"""
    print(f"\n{'=' * 60}")
    print(f"Test: {test_name}")
    print(f"Requirements: {requirements}")
    print("=" * 60)

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/analyze",
            json={"requirements": requirements},
            timeout=180,  # 增加到180秒超时
        )

        if response.status_code == 200:
            data = response.json()
            print(f"\n[SUCCESS]")
            print(f"Project Name: {data.get('spec', {}).get('name', 'N/A')}")
            desc = data.get("spec", {}).get("description", "N/A")
            print(
                f"Description: {desc[:100]}..."
                if len(desc) > 100
                else f"Description: {desc}"
            )

            components = data.get("spec", {}).get("components", [])
            print(f"Component Count: {len(components)}")

            if components:
                print("\nComponents:")
                for j, comp in enumerate(components[:5], 1):
                    print(
                        f"  {j}. {comp.get('name', 'N/A')} - {comp.get('model', 'N/A')} ({comp.get('package', 'N/A')})"
                    )
                if len(components) > 5:
                    print(f"  ... and {len(components) - 5} more components")

            schematic = data.get("schematic", {})
            print(
                f"\nSchematic: {len(schematic.get('components', []))} components, {len(schematic.get('wires', []))} wires"
            )
            return True
        else:
            print(f"\n[FAILED] HTTP Status: {response.status_code}")
            print(f"Error: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        print(f"\n[TIMEOUT] Request timed out after 180 seconds")
        return False
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    proc = start_backend()

    # 测试1: 5V稳压电源
    test_single(
        "Design a 5V regulated power supply, input 220V AC, output 5V DC, 1A current",
        "5V Power Supply",
    )

    # 等待一下
    time.sleep(2)

    # 测试2: WiFi控制器
    test_single(
        "Design a WiFi smart controller based on ESP32, support 4-channel relay remote control",
        "WiFi Controller",
    )

    # 等待一下
    time.sleep(2)

    # 测试3: 超声波测距
    test_single(
        "Design an ultrasonic distance module using HC-SR04 sensor, display distance on OLED screen",
        "Ultrasonic Module",
    )

    print("\n" + "=" * 60)
    print("All Tests Complete")
    print("=" * 60)

    proc.terminate()
    proc.wait()
    print("Backend stopped")
