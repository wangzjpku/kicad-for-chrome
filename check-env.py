"""
KiCad IPC 环境验证脚本
v0.2.0 - Phase 0 Task 0.1

功能:
1. 检测KiCad 9.0+安装
2. 验证kicad-python库安装
3. 测试IPC连接
4. 生成环境报告
"""

import sys
import subprocess
import os
from pathlib import Path


# 颜色输出
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_status(message, status="info"):
    """打印带颜色的状态信息"""
    # Windows兼容: 使用ASCII字符
    if sys.platform == "win32":
        if status == "success":
            print(f"[OK] {message}")
        elif status == "error":
            print(f"[ERR] {message}")
        elif status == "warning":
            print(f"[WARN] {message}")
        else:
            print(f"[INFO] {message}")
    else:
        if status == "success":
            print(f"{Colors.GREEN}✓{Colors.END} {message}")
        elif status == "error":
            print(f"{Colors.RED}✗{Colors.END} {message}")
        elif status == "warning":
            print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
        else:
            print(f"{Colors.BLUE}ℹ{Colors.END} {message}")


def check_kicad_installation():
    """检查KiCad安装"""
    print("\n" + "=" * 60)
    print("检查KiCad安装")
    print("=" * 60)

    # Windows默认路径
    kicad_paths = [
        r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
        r"E:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        r"E:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
    ]

    kicad_cli = None
    for path in kicad_paths:
        if os.path.exists(path):
            kicad_cli = path
            print_status(f"找到KiCad: {path}", "success")
            break

    if not kicad_cli:
        print_status("未找到KiCad安装", "error")
        print("  请安装KiCad 9.0+ 或手动指定路径")
        return None

    # 检查版本
    try:
        result = subprocess.run(
            [kicad_cli, "--version"], capture_output=True, text=True
        )
        version = result.stdout.strip()
        print_status(f"KiCad版本: {version}", "success")

        # 检查版本号
        if "9." in version or "8." in version:
            print_status("版本符合要求 (>= 8.0)", "success")
        else:
            print_status("版本可能过低，建议升级到9.0+", "warning")

        return kicad_cli
    except Exception as e:
        print_status(f"无法获取版本: {e}", "error")
        return kicad_cli


def check_kicad_python():
    """检查kicad-python库"""
    print("\n" + "=" * 60)
    print("检查kicad-python库")
    print("=" * 60)

    try:
        import kipy

        print_status("kicad-python (kipy) 已安装", "success")

        # 尝试获取版本
        try:
            version = kipy.__version__
            print_status(f"kipy版本: {version}", "success")
        except:
            print_status("已安装kipy但无法获取版本", "warning")

        return True
    except ImportError:
        print_status("kicad-python (kipy) 未安装", "error")
        print("  安装命令: pip install kicad-python")
        return False


def test_ipc_connection():
    """测试IPC连接"""
    print("\n" + "=" * 60)
    print("测试IPC连接")
    print("=" * 60)

    print_status("注意: 此测试需要KiCad GUI正在运行", "info")
    print("  1. 打开KiCad PCB Editor")
    print("  2. 点击菜单: Tools → External Plugin → Start Server")
    print("  3. 然后按Enter继续测试...")

    # 不自动测试，因为需要GUI
    print_status("IPC连接测试需要手动进行", "warning")
    print("\n  手动测试步骤:")
    print("  1. 启动KiCad PCB Editor")
    print("  2. 启动IPC Server")
    print(
        '  3. 运行: python -c "import kipy; c = kipy.Client(); print(c.get_version())"'
    )

    return None


def check_environment():
    """检查环境变量"""
    print("\n" + "=" * 60)
    print("检查环境变量")
    print("=" * 60)

    # 检查Python版本
    python_version = sys.version_info
    print_status(
        f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}",
        "success" if python_version >= (3, 11) else "warning",
    )

    if python_version < (3, 11):
        print("  建议升级到Python 3.11+")

    # 检查PATH
    path = os.environ.get("PATH", "")
    if "KiCad" in path:
        print_status("PATH中包含KiCad路径", "success")
    else:
        print_status("PATH中未找到KiCad路径", "warning")

    return True


def generate_report(kicad_cli, has_kipy):
    """生成环境报告"""
    print("\n" + "=" * 60)
    print("环境验证报告")
    print("=" * 60)

    all_good = True

    if kicad_cli:
        print_status("KiCad安装: OK", "success")
    else:
        print_status("KiCad安装: MISSING", "error")
        all_good = False

    if has_kipy:
        print_status("kicad-python: OK", "success")
    else:
        print_status("kicad-python: MISSING", "error")
        all_good = False

    print("\n" + "-" * 60)
    if all_good:
        print_status("环境验证通过!可以开始开发", "success")
        print("\n下一步:")
        print("  1. 启动KiCad PCB Editor")
        print("  2. 启动IPC Server")
        print("  3. 运行后端服务: cd kicad-ai-auto/backend && python main.py")
    else:
        print_status("环境验证未通过,请修复上述问题", "error")
        print("\n需要安装:")
        if not kicad_cli:
            print("  - KiCad 9.0+: https://www.kicad.org/download/")
        if not has_kipy:
            print("  - kicad-python: pip install kicad-python")

    return all_good


def main():
    """主函数"""
    print("=" * 60)
    print("KiCad Web Editor - 环境验证工具")
    print("版本: v0.2.0")
    print("=" * 60)

    # 检查各项
    kicad_cli = check_kicad_installation()
    has_kipy = check_kicad_python()
    check_environment()
    test_ipc_connection()

    # 生成报告
    success = generate_report(kicad_cli, has_kipy)

    # 保存配置
    if kicad_cli:
        config_path = Path("kicad-ai-auto/backend/.env")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_content = f"""# KiCad Web Editor - Environment Config
# Auto-generated by v0.2.0

# KiCad Configuration
KICAD_CLI_PATH={kicad_cli}
KICAD_SHARE_PATH={os.path.dirname(os.path.dirname(kicad_cli))}\\share\\kicad

# Database Configuration (SQLite for local deployment)
DATABASE_URL=sqlite+aiosqlite:///./kicad_editor.db

# 项目路径 (Windows)
PROJECTS_DIR=C:\\KiCadWebEditor\\projects
OUTPUT_DIR=C:\\KiCadWebEditor\\output
TEMP_DIR=C:\\KiCadWebEditor\\temp

# 服务器配置
HOST=127.0.0.1
PORT=8000
DEBUG=true

# 安全
SECRET_KEY=your-secret-key-change-in-production
"""

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        print(f"\n[OK] 配置文件已生成: {config_path}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
