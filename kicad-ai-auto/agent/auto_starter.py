"""
KiCad AI Auto - 智能启动管理器
自动完成 A/B/C 三个步骤：
A. 启动 KiCad 并启用 IPC Server
B. 安装 kicad-python 库
C. 启动前端界面
"""

import os
import sys
import time
import subprocess
import webbrowser
import logging
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import urllib.error

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoStarter:
    """自动启动管理器"""

    def __init__(self):
        self.project_dir = Path(__file__).parent.parent.parent
        self.backend_dir = self.project_dir / "kicad-ai-auto" / "agent"
        self.frontend_dir = self.project_dir / "kicad-ai-auto" / "web"
        self.kicad_dir = Path("E:/Program Files/KiCad/9.0")

        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.kicad_process: Optional[subprocess.Popen] = None

    def check_kicad_installed(self) -> bool:
        """检查 KiCad 是否已安装"""
        kicad_exe = self.kicad_dir / "bin" / "pcbnew.exe"
        if kicad_exe.exists():
            logger.info(f"✅ KiCad 9.0 已安装: {self.kicad_dir}")
            return True
        else:
            logger.error(f"❌ KiCad 未找到: {kicad_exe}")
            return False

    def install_dependencies(self) -> bool:
        """步骤 B: 安装 Python 依赖"""
        logger.info("=" * 50)
        logger.info("步骤 B: 安装 Python 依赖")
        logger.info("=" * 50)

        venv_python = self.backend_dir / "venv" / "Scripts" / "python.exe"
        venv_pip = self.backend_dir / "venv" / "Scripts" / "pip.exe"

        if not venv_python.exists():
            logger.error("❌ 虚拟环境未找到，请先创建虚拟环境")
            return False

        # 检查并安装 kicad-python
        logger.info("检查 kicad-python...")
        try:
            result = subprocess.run(
                [str(venv_python), "-c", "import kipy"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("✅ kicad-python 已安装")
            else:
                logger.info("正在安装 kicad-python...")
                subprocess.run(
                    [str(venv_pip), "install", "kicad-python", "-q"],
                    check=True
                )
                logger.info("✅ kicad-python 安装完成")
        except Exception as e:
            logger.warning(f"⚠️ kicad-python 安装失败: {e}")
            logger.info("将继续使用 PyAutoGUI 模式")

        # 检查并安装 pywin32
        logger.info("检查 pywin32...")
        try:
            result = subprocess.run(
                [str(venv_python), "-c", "import win32gui"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("✅ pywin32 已安装")
            else:
                logger.info("正在安装 pywin32...")
                subprocess.run(
                    [str(venv_pip), "install", "pywin32", "-q"],
                    check=True
                )
                logger.info("✅ pywin32 安装完成")
        except Exception as e:
            logger.warning(f"⚠️ pywin32 安装失败: {e}")

        return True

    def start_backend(self) -> bool:
        """启动后端服务"""
        logger.info("=" * 50)
        logger.info("启动后端服务")
        logger.info("=" * 50)

        venv_python = self.backend_dir / "venv" / "Scripts" / "python.exe"

        # 检查后端是否已在运行
        if self._is_port_open(8000):
            logger.info("✅ 后端已在运行 (端口 8000)")
            return True

        # 启动后端
        logger.info("正在启动后端...")
        try:
            self.backend_process = subprocess.Popen(
                [str(venv_python), "main.py"],
                cwd=str(self.backend_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # 等待后端启动
            logger.info("等待后端启动...")
            for i in range(30):  # 最多等待30秒
                time.sleep(1)
                if self._is_port_open(8000):
                    logger.info("✅ 后端已启动 (http://localhost:8000)")
                    return True

            logger.error("❌ 后端启动超时")
            return False

        except Exception as e:
            logger.error(f"❌ 启动后端失败: {e}")
            return False

    def start_kicad(self) -> bool:
        """步骤 A: 启动 KiCad"""
        logger.info("=" * 50)
        logger.info("步骤 A: 启动 KiCad")
        logger.info("=" * 50)

        pcbnew_exe = self.kicad_dir / "bin" / "pcbnew.exe"

        # 检查 KiCad 是否已在运行
        if self._is_process_running("pcbnew.exe"):
            logger.info("✅ KiCad 已在运行")
            return True

        # 启动 KiCad
        logger.info("正在启动 KiCad PCB Editor...")
        try:
            # 创建示例项目目录
            projects_dir = self.project_dir / "projects"
            projects_dir.mkdir(exist_ok=True)

            self.kicad_process = subprocess.Popen(
                [str(pcbnew_exe)],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            logger.info("✅ KiCad 已启动")
            logger.info("")
            logger.info("⚠️  重要提示：")
            logger.info("   请在 KiCad 中启用 IPC Server：")
            logger.info("   Tools → External Plugin → Start Server")
            logger.info("")

            # 等待用户确认
            input("按 Enter 键确认已启用 IPC Server（或跳过）...")

            return True

        except Exception as e:
            logger.error(f"❌ 启动 KiCad 失败: {e}")
            return False

    def connect_kicad_ipc(self) -> bool:
        """尝试连接 KiCad IPC"""
        logger.info("正在连接 KiCad IPC...")

        try:
            # 尝试通过 API 启动 IPC 连接
            req = urllib.request.Request(
                "http://localhost:8000/api/kicad-ipc/start",
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = response.read().decode()
                logger.info(f"IPC 启动结果: {result}")

            time.sleep(2)

            # 检查连接状态
            status_url = "http://localhost:8000/api/kicad-ipc/status"
            with urllib.request.urlopen(status_url, timeout=5) as response:
                status = response.read().decode()
                if '"connected":true' in status:
                    logger.info("✅ KiCad IPC 连接成功")
                    return True
                else:
                    logger.warning("⚠️ IPC 连接失败，将使用 PyAutoGUI 模式")
                    return False

        except Exception as e:
            logger.warning(f"⚠️ IPC 连接失败: {e}")
            logger.info("将使用 PyAutoGUI 模式")
            return False

    def start_frontend(self) -> bool:
        """步骤 C: 启动前端界面"""
        logger.info("=" * 50)
        logger.info("步骤 C: 启动前端界面")
        logger.info("=" * 50)

        npm_exe = "npm"

        # 检查 node_modules
        if not (self.frontend_dir / "node_modules").exists():
            logger.info("首次运行，安装前端依赖...")
            try:
                result = subprocess.run(
                    [npm_exe, "install"],
                    cwd=str(self.frontend_dir),
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"❌ npm install 失败: {result.stderr}")
                    return False
                logger.info("✅ 前端依赖安装完成")
            except Exception as e:
                logger.error(f"❌ 安装前端依赖失败: {e}")
                return False

        # 检查前端是否已在运行
        if self._is_port_open(3000) or self._is_port_open(5173):
            logger.info("✅ 前端已在运行")
            return True

        # 启动前端
        logger.info("正在启动前端...")
        try:
            self.frontend_process = subprocess.Popen(
                [npm_exe, "run", "dev"],
                cwd=str(self.frontend_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # 等待前端启动
            logger.info("等待前端启动...")
            for i in range(20):  # 最多等待20秒
                time.sleep(1)
                if self._is_port_open(3000) or self._is_port_open(5173):
                    port = 3000 if self._is_port_open(3000) else 5173
                    logger.info(f"✅ 前端已启动 (http://localhost:{port})")
                    return True

            logger.warning("⚠️ 前端启动超时，但可能仍在启动中")
            return True

        except Exception as e:
            logger.error(f"❌ 启动前端失败: {e}")
            return False

    def open_browser(self):
        """打开浏览器"""
        logger.info("正在打开浏览器...")

        # 确定前端端口
        port = 3000 if self._is_port_open(3000) else 5173
        url = f"http://localhost:{port}"

        try:
            webbrowser.open(url)
            logger.info(f"✅ 已打开浏览器: {url}")
        except Exception as e:
            logger.warning(f"⚠️ 打开浏览器失败: {e}")
            logger.info(f"   请手动访问: {url}")

    def _is_port_open(self, port: int) -> bool:
        """检查端口是否开放"""
        import socket
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except:
            return False

    def _is_process_running(self, process_name: str) -> bool:
        """检查进程是否正在运行"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                capture_output=True,
                text=True
            )
            return process_name in result.stdout
        except:
            return False

    def print_summary(self):
        """打印启动摘要"""
        logger.info("")
        logger.info("=" * 50)
        logger.info("启动完成摘要")
        logger.info("=" * 50)

        # 检查各项状态
        backend_ok = self._is_port_open(8000)
        frontend_port = 3000 if self._is_port_open(3000) else (5173 if self._is_port_open(5173) else None)
        kicad_ok = self._is_process_running("pcbnew.exe")

        logger.info(f"后端服务:     {'✅ 运行中' if backend_ok else '❌ 未运行'} (http://localhost:8000)")
        logger.info(f"前端界面:     {'✅ 运行中' if frontend_port else '❌ 未运行'} (http://localhost:{frontend_port})" if frontend_port else "前端界面:     ❌ 未运行")
        logger.info(f"KiCad:        {'✅ 运行中' if kicad_ok else '❌ 未运行'}")

        logger.info("")
        logger.info("访问地址:")
        logger.info(f"  - 前端界面:  http://localhost:{frontend_port or '3000/5173'}")
        logger.info(f"  - API 文档:  http://localhost:8000/docs")
        logger.info(f"  - 健康检查:  http://localhost:8000/api/health")
        logger.info(f"  - KiCad IPC: http://localhost:8000/api/kicad-ipc/status")
        logger.info("")
        logger.info("=" * 50)

    def run(self):
        """运行完整的自动启动流程"""
        logger.info("\n" + "=" * 50)
        logger.info("KiCad AI Auto - 全自动启动")
        logger.info("=" * 50 + "\n")

        try:
            # 步骤 0: 检查 KiCad 安装
            if not self.check_kicad_installed():
                return False

            # 步骤 B: 安装依赖
            if not self.install_dependencies():
                return False

            # 启动后端
            if not self.start_backend():
                return False

            # 步骤 A: 启动 KiCad
            if not self.start_kicad():
                return False

            # 尝试连接 IPC
            self.connect_kicad_ipc()

            # 步骤 C: 启动前端
            if not self.start_frontend():
                return False

            # 打开浏览器
            self.open_browser()

            # 打印摘要
            self.print_summary()

            logger.info("\n✅ 所有服务启动完成！")
            logger.info("按 Ctrl+C 停止此脚本（服务将继续运行）\n")

            # 保持脚本运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n\n收到停止信号，正在关闭...")
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        logger.info("正在关闭服务...")

        if self.backend_process:
            self.backend_process.terminate()
            logger.info("后端已关闭")

        if self.frontend_process:
            self.frontend_process.terminate()
            logger.info("前端已关闭")

        # 注意：不关闭 KiCad，让用户自己决定

        logger.info("清理完成")


def main():
    """主入口"""
    starter = AutoStarter()
    starter.run()


if __name__ == "__main__":
    main()
