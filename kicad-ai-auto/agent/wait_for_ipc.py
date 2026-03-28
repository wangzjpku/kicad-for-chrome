"""
KiCad IPC 连接监控器
当用户启动IPC服务后自动检测并连接
"""
import os
import time
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# KiCad API 基础URL
API_BASE = "http://localhost:8000"
IPC_STATUS_URL = f"{API_BASE}/api/kicad-ipc/status"
IPC_START_URL = f"{API_BASE}/api/kicad-ipc/start"

# 检查socket文件
def check_socket():
    temp = os.environ.get('TEMP') or os.environ.get('TMP')
    socket_path = os.path.join(temp, 'kicad', 'api.sock')
    return os.path.exists(socket_path)


def check_api_connection():
    """通过API检查连接状态"""
    try:
        response = requests.get(IPC_STATUS_URL, timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get('connected', False)
    except Exception as e:
        logger.debug(f"API连接检查失败: {e}")
    return False


def try_start_ipc():
    """尝试通过API启动IPC"""
    try:
        response = requests.post(IPC_START_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('connected', False)
    except Exception as e:
        logger.debug(f"Start IPC failed: {e}")
    return False


def wait_for_connection(max_wait=60, check_interval=2):
    """
    等待IPC连接

    Args:
        max_wait: 最大等待时间（秒）
        check_interval: 检查间隔（秒）
    """
    logger.info("=" * 60)
    logger.info("Waiting for KiCad IPC connection...")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Please start the IPC service in KiCad:")
    logger.info("  1. Open PCB Editor in KiCad")
    logger.info("  2. Click: Tools → External Plugin → Start Server")
    logger.info("")
    logger.info("Waiting for connection...")
    logger.info("")

    start_time = time.time()
    connected = False

    while time.time() - start_time < max_wait:
        # 检查socket文件
        if check_socket():
            logger.info("Socket file detected! Attempting to connect...")

        # 尝试通过API检查/启动
        if check_api_connection():
            connected = True
            break

        # 尝试启动IPC
        if try_start_ipc():
            if check_api_connection():
                connected = True
                break

        time.sleep(check_interval)

        # 显示等待状态
        elapsed = int(time.time() - start_time)
        print(f"\r  Waiting... {elapsed}s / {max_wait}s", end="", flush=True)

    print()  # 换行

    if connected:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ SUCCESS: Connected to KiCad IPC!")
        logger.info("=" * 60)
        return True
    else:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✗ TIMEOUT: Could not connect to KiCad IPC")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Please ensure:")
        logger.info("  1. KiCad PCB Editor is open")
        logger.info("  2. IPC service is started: Tools → External Plugin → Start Server")
        return False


if __name__ == "__main__":
    import sys

    max_wait = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    wait_for_connection(max_wait)
