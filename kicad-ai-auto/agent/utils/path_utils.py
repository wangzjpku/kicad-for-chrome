"""
路径工具函数
处理项目中的路径相关操作
"""

import os
import sys
from pathlib import Path
from typing import Optional, List


def get_project_root() -> Path:
    """获取项目根目录"""
    # 从当前文件向上查找 setup.py, pyproject.toml 或项目标识
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (
            (parent / "pyproject.toml").exists()
            or (parent / "setup.py").exists()
            or (parent / "kicad-ai-auto").exists()
        ):
            return parent
    return current.parent


def ensure_dir(path: str) -> str:
    """确保目录存在

    Args:
        path: 目录路径

    Returns:
        规范化后的路径
    """
    os.makedirs(path, exist_ok=True)
    return os.path.normpath(path)


def find_file_in_parents(
    filename: str, start_path: Optional[str] = None
) -> Optional[str]:
    """在父目录中查找文件

    Args:
        filename: 要查找的文件名
        start_path: 起始路径，默认为当前工作目录

    Returns:
        文件的完整路径，如果未找到返回 None
    """
    if start_path is None:
        start_path = os.getcwd()

    current = Path(start_path).resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / filename
        if candidate.exists():
            return str(candidate)

    return None


def get_kicad_default_paths() -> List[str]:
    """获取系统默认 KiCad 安装路径

    Returns:
        可能的 KiCad 可执行文件路径列表
    """
    paths = []

    if sys.platform == "win32":
        # Windows 路径
        paths.extend(
            [
                r"E:\Program Files\KiCad\9.0\bin\kicad.exe",
                r"E:\Program Files\KiCad\8.0\bin\kicad.exe",
                r"C:\Program Files\KiCad\9.0\bin\kicad.exe",
                r"C:\Program Files\KiCad\8.0\bin\kicad.exe",
                r"C:\Program Files (x86)\KiCad\9.0\bin\kicad.exe",
            ]
        )
    elif sys.platform == "darwin":
        # macOS 路径
        paths.extend(
            [
                "/Applications/KiCad.app/Contents/MacOS/kicad",
                "/Applications/KiCad9.app/Contents/MacOS/kicad",
            ]
        )
    else:
        # Linux 路径
        paths.extend(
            [
                "/usr/bin/kicad",
                "/usr/local/bin/kicad",
                "/opt/kicad/bin/kicad",
            ]
        )

    return paths


def find_kicad_executable() -> Optional[str]:
    """查找系统中的 KiCad 可执行文件

    Returns:
        KiCad 可执行文件路径，如果未找到返回 None
    """
    # 1. 检查环境变量
    for env_var in ["KICAD_PATH", "KICAD_BIN", "KICAD"]:
        path = os.environ.get(env_var)
        if path and os.path.exists(path):
            return path

    # 2. 检查默认路径
    for path in get_kicad_default_paths():
        if os.path.exists(path):
            return path

    # 3. 尝试从 PATH 查找
    import shutil

    return shutil.which("kicad") or shutil.which("kicad.exe")


def get_config_dir() -> Path:
    """获取配置目录

    优先级: 用户配置目录 > 项目配置 > 默认
    """
    # 用户配置目录
    if sys.platform == "win32":
        config_home = Path(os.environ.get("APPDATA", "")) / "KiCad-AI"
    elif sys.platform == "darwin":
        config_home = Path.home() / "Library/Application Support/KiCad-AI"
    else:
        config_home = Path.home() / ".config/kicad-ai"

    # 项目配置
    project_config = get_project_root() / "config"

    return config_home if config_home.exists() else project_config
