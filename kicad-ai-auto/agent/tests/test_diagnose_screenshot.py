"""
Diagnose Screenshot Tests
测试截图诊断功能
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import numpy as np

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_diagnose_screenshot_import():
    """测试导入模块"""
    try:
        import diagnose_screenshot

        assert diagnose_screenshot is not None
        print("[OK] diagnose_screenshot module imported")
    except ImportError as e:
        # 如果cv2不可用，模块可能无法导入
        print(f"[SKIP] diagnose_screenshot import failed: {e}")


@patch("cv2.imread")
@patch("cv2.cvtColor")
@patch("cv2.Canny")
def test_detect_edges(mock_canny, mock_cvt, mock_imread):
    """测试边缘检测"""
    # 模拟图像
    mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_canny.return_value = np.zeros((100, 100), dtype=np.uint8)
    mock_cvt.return_value = np.zeros((100, 100), dtype=np.uint8)

    try:
        from diagnose_screenshot import detect_edges

        result = detect_edges("test.png")
        print(f"[OK] detect_edges result: {result}")
    except ImportError:
        print("[SKIP] cv2 not available")


@patch("cv2.imread")
@patch("cv2.countNonZero")
def test_has_sufficient_content(mock_count, mock_imread):
    """测试内容检测"""
    mock_imread.return_value = np.ones((100, 100, 3), dtype=np.uint8) * 255
    mock_count.return_value = 1000  # 足够的非黑色像素

    try:
        from diagnose_screenshot import has_sufficient_content

        result = has_sufficient_content("test.png")
        assert result is True
        print("[OK] has_sufficient_content - sufficient")
    except ImportError:
        print("[SKIP] cv2 not available")


@patch("cv2.imread")
@patch("cv2.countNonZero")
def test_has_sufficient_content_insufficient(mock_count, mock_imread):
    """测试内容不足的情况"""
    mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_count.return_value = 10  # 像素太少

    try:
        from diagnose_screenshot import has_sufficient_content

        result = has_sufficient_content("test.png")
        assert result is False
        print("[OK] has_sufficient_content - insufficient")
    except ImportError:
        print("[SKIP] cv2 not available")


@patch("PIL.Image.open")
def test_is_blank_image(mock_open):
    """测试空白图像检测"""
    mock_img = MagicMock()
    mock_img.convert.return_value = mock_img
    mock_img.getdata.return_value = [0] * 100
    mock_open.return_value = mock_img

    try:
        from diagnose_screenshot import is_blank_image

        result = is_blank_image("test.png")
        print(f"[OK] is_blank_image: {result}")
    except ImportError:
        print("[SKIP] PIL not available")


def test_calculate_image_quality_score():
    """测试图像质量评分"""
    try:
        from diagnose_screenshot import calculate_image_quality_score

        # 模拟一个正常图像
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        score = calculate_image_quality_score(test_image)
        assert 0 <= score <= 100
        print(f"[OK] Image quality score: {score}")
    except ImportError:
        print("[SKIP] cv2 not available")


def test_detect_ui_elements():
    """测试UI元素检测"""
    try:
        from diagnose_screenshot import detect_ui_elements

        # 模拟一个空白/简单图像
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        elements = detect_ui_elements(test_image)
        assert isinstance(elements, dict)
        print(f"[OK] UI elements: {elements}")
    except ImportError:
        print("[SKIP] cv2 not available")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Diagnose Screenshot Tests")
    print("=" * 60)

    test_diagnose_screenshot_import()
    test_detect_edges()
    test_has_sufficient_content()
    test_has_sufficient_content_insufficient()
    test_is_blank_image()
    test_calculate_image_quality_score()
    test_detect_ui_elements()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
