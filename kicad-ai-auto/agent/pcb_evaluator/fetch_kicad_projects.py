"""
从 GitHub 获取真实 KiCad 项目
用于测试 Ralph Loop 优化器
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import hashlib


# 已知包含 KiCad 项目的 GitHub 仓库列表
KNOWN_KICAD_REPOS = [
    # 开发板
    "devnithw/stm32-devboard",
    "mihirscsharma/STM32-RF-PCB",
    "nwasr/Stamp-Board-of-AD8232",
    "Liam-Craig/Sonata-PCB-KiCAD",
    "Ikarthikmb/Circuit-Designesigns",
    "Diodes-Delight/Piunora-Hardware",
    "danb35/myDewControllerPro-PCB",
    # 更多项目
    "myklemykle/pocketintegrator-kicad",
    "dwhitters/KiCad-HealthHub",
    # 电源相关
    "circuitdigest/ESP32-Battery-Manager",
    # 传感器
    "Protocentral/Protocentral_MAX30003",
    # USB相关
    "futureless/USB-PD-Kicad",
    # 蓝牙/WiFi
    "tiny_modules/tm-esp32-c3",
]


class KiCadProjectFetcher:
    """从 GitHub 获取 KiCad 项目"""

    def __init__(self, cache_dir: str = "./kicad_projects_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_projects(self, num_projects: int = 20) -> List[str]:
        """获取多个 KiCad 项目"""
        projects = []

        # 使用 GitHub API 搜索 KiCad 项目
        search_results = self._search_kicad_projects(num_projects * 2)

        for repo in search_results:
            if len(projects) >= num_projects:
                break

            try:
                project_path = self._clone_project(repo)
                if project_path:
                    projects.append(project_path)
                    print(f"✓ 获取项目: {repo}")
            except Exception as e:
                print(f"✗ 获取失败: {repo} - {e}")

        return projects

    def _search_kicad_projects(self, limit: int = 40) -> List[str]:
        """搜索 GitHub 上的 KiCad 项目"""
        repos = []

        # 方法1: 使用 gh 命令搜索
        try:
            result = subprocess.run(
                [
                    "gh",
                    "search",
                    "repos",
                    "kicad_pcb",
                    "--limit",
                    str(limit),
                    "--json",
                    "fullName",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                repos = [item["fullName"] for item in data]
        except Exception as e:
            print(f"gh search failed: {e}")

        # 方法2: 使用已知项目列表
        if not repos:
            repos = KNOWN_KICAD_REPOS[:limit]

        return repos[:limit]

    def _clone_project(self, repo: str) -> Optional[str]:
        """克隆项目到本地"""
        # 计算缓存路径
        repo_hash = hashlib.md5(repo.encode()).hexdigest()[:8]
        project_dir = self.cache_dir / repo.replace("/", "_") / repo_hash

        if project_dir.exists():
            # 检查是否已经有 .kicad_pcb 文件
            pcb_files = list(project_dir.glob("*.kicad_pcb"))
            if pcb_files:
                return str(project_dir)

        # 克隆仓库
        try:
            project_dir.parent.mkdir(parents=True, exist_ok=True)

            # 使用 git clone
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    f"https://github.com/{repo}.git",
                    str(project_dir),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return None

            # 检查是否有 KiCad 文件
            kicad_files = list(project_dir.glob("**/*.kicad_pcb"))
            if not kicad_files:
                # 可能整个仓库被下载了，但没有 .kicad_pcb
                return None

            return str(project_dir)

        except Exception as e:
            print(f"Clone error: {e}")
            return None

    def list_local_projects(self) -> List[str]:
        """列出本地缓存的项目"""
        projects = []
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                pcb_files = list(item.glob("**/*.kicad_pcb"))
                for pcb in pcb_files:
                    projects.append(str(pcb.parent))
        return projects


def get_real_kicad_projects(num: int = 20) -> List[str]:
    """获取真实 KiCad 项目的便捷函数"""
    fetcher = KiCadProjectFetcher()
    return fetcher.fetch_projects(num)


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("GitHub KiCad 项目获取器")
    print("=" * 60)

    fetcher = KiCadProjectFetcher()

    print("\n搜索 GitHub 上的 KiCad 项目...")
    repos = fetcher._search_kicad_projects(20)

    print(f"找到 {len(repos)} 个项目:")
    for repo in repos[:10]:
        print(f"  - {repo}")

    print("\n尝试获取项目...")
    projects = fetcher.fetch_projects(5)
    print(f"\n成功获取 {len(projects)} 个项目")
