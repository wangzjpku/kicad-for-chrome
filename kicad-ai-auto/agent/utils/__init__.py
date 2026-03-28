"""
工具函数模块
提供项目中常用的工具函数
"""

import time
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


# 默认等待时间配置
DEFAULT_WAIT_SHORT = 0.1  # 短等待 (100ms)
DEFAULT_WAIT_MEDIUM = 0.2  # 中等待 (200ms)
DEFAULT_WAIT_LONG = 0.5  # 长等待 (500ms)
DEFAULT_WAIT_STARTUP = 3  # 启动等待 (3s)


def wait_short():
    """短等待 - 100ms"""
    time.sleep(DEFAULT_WAIT_SHORT)


def wait_medium():
    """中等待 - 200ms"""
    time.sleep(DEFAULT_WAIT_MEDIUM)


def wait_long():
    """长等待 - 500ms"""
    time.sleep(DEFAULT_WAIT_LONG)


def wait_startup():
    """启动等待 - 3秒"""
    time.sleep(DEFAULT_WAIT_STARTUP)


def wait_with_retry(
    condition: Callable[[], bool],
    max_attempts: int = 3,
    delay: float = 1.0,
    timeout: float = 30.0,
) -> bool:
    """条件等待函数

    Args:
        condition: 返回bool的条件函数
        max_attempts: 最大重试次数
        delay: 每次重试间隔(秒)
        timeout: 超时时间(秒)

    Returns:
        bool: 条件是否满足
    """
    start_time = time.time()
    attempts = 0

    while attempts < max_attempts:
        if condition():
            return True

        if time.time() - start_time > timeout:
            logger.warning(f"wait_with_retry timeout after {timeout}s")
            return False

        time.sleep(delay)
        attempts += 1

    return False


def wait_until(
    condition: Callable[[], bool],
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    error_message: str = "Condition timeout",
) -> bool:
    """等待条件满足

    Args:
        condition: 条件函数
        timeout: 超时时间(秒)
        poll_interval: 轮询间隔(秒)
        error_message: 超时时错误消息

    Returns:
        bool: 是否在超时前满足条件

    Raises:
        TimeoutError: 超时且条件未满足
    """
    start_time = time.time()

    while not condition():
        if time.time() - start_time > timeout:
            raise TimeoutError(error_message)
        time.sleep(poll_interval)

    return True


class RetryContext:
    """重试上下文管理器"""

    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay
        self.attempt = 0
        self.last_error: Optional[Exception] = None

    def __enter__(self):
        self.attempt += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.last_error = exc_val
            if self.attempt < self.max_retries:
                logger.warning(
                    f"Attempt {self.attempt} failed, retrying in {self.delay}s..."
                )
                time.sleep(self.delay)
                return True  # 抑制异常，继续重试
        return False

    @property
    def succeeded(self) -> bool:
        return self.last_error is None
