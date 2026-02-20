"""
测试 AI 分析功能
测试3个不同的需求描述，验证是否能正确调用GLM-4并生成不同方案
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

# 测试需求描述
TEST_CASES = [
    {
        "name": "Test 1: 5V Power Supply",
        "requirements": "Design a 5V regulated power supply, input 220V AC, output 5V DC, 1A current",
    },
    {
        "name": "Test 2: WiFi Smart Controller",
        "requirements": "Design a WiFi smart controller based on ESP32, support 4-channel relay remote control",
    },
    {
        "name": "Test 3: Ultrasonic Distance Module",
        "requirements": "Design an ultrasonic distance module using HC-SR04 sensor, display distance on OLED screen",
    },
]


def start_backend():
    """启动后端服务"""
    print("Starting backend server...")
    # 使用 subprocess 启动后端
    env = os.environ.copy()
    env["ZHIPU_API_KEY"] = "c762f2f90a2944cc9ccceaedee969a33.I6x5IhWw7IWcublJ"

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd="kicad-ai-auto/agent",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 等待服务启动
    print("Waiting for server to start...")
    time.sleep(8)

    # 检查服务是否启动
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"Server started: {response.status_code == 200}")
    except:
        print("Warning: Server may not be ready")

    return proc


def test_ai_analyze():
    """测试AI分析接口"""

    # 启动后端
    proc = start_backend()

    print("\n" + "=" * 60)
    print("Starting AI Analysis Tests")
    print("=" * 60)

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 60}")
        print(f"Test {i}: {test_case['name']}")
        print(f"Requirements: {test_case['requirements']}")
        print("=" * 60)

        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/ai/analyze",
                json={"requirements": test_case["requirements"]},
                timeout=120,
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

                # 检查原理图
                schematic = data.get("schematic", {})
                print(
                    f"\nSchematic: {len(schematic.get('components', []))} components, {len(schematic.get('wires', []))} wires"
                )

            else:
                print(f"\n[FAILED] HTTP Status: {response.status_code}")
                print(f"Error: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print(f"\n[FAILED] Connection failed! Backend not running")
            break
        except Exception as e:
            print(f"\n[ERROR] {str(e)}")

    print("\n" + "=" * 60)
    print("Tests Complete")
    print("=" * 60)

    # 关闭后端
    proc.terminate()
    proc.wait()
    print("Backend stopped")


if __name__ == "__main__":
    test_ai_analyze()
