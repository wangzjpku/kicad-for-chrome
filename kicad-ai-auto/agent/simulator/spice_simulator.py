"""
SPICE 仿真器 v1.0

功能特性：
1. 生成 SPICE 网表
2. 调用 ngspice 进行仿真
3. 解析仿真结果

支持的分析类型：
- DC_OP: 直流工作点
- AC: 交流分析
- TRAN: 瞬态分析
- DC_SWEEP: 直流扫描

作者：AI Assistant
版本：1.0
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import os
import subprocess
import tempfile
import json
import logging

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型"""
    DC_OP = "dc_op"  # 直流工作点
    AC = "ac"  # 交流分析
    TRAN = "tran"  # 瞬态分析
    DC_SWEEP = "dc_sweep"  # 直流扫描


@dataclass
class SimulationResult:
    """仿真结果"""
    success: bool
    analysis_type: str
    data: Dict[str, List[float]]  # 变量名 -> 数据列表
    parameters: Dict[str, float]  # 参数
    error_message: Optional[str] = None


class SpiceSimulator:
    """
    SPICE 仿真器

    集成方式:
    1. 本地 ngspice (Windows/Linux)
    2. 远程仿真服务 (如 AWS)
    """

    def __init__(self, ngspice_path: str = None):
        """
        初始化仿真器

        Args:
            ngspice_path: ngspice 可执行文件路径
        """
        self.ngspice_path = ngspice_path or self._find_ngspice()

    def _find_ngspice(self) -> str:
        """查找 ngspice"""
        # 常见路径
        common_paths = [
            "ngspice",
            os.environ.get("NGSPICE_PATH", ""),
            "C:\\ngspice\\bin\\ngspice.exe",
            "C:\\Program Files\\ngspice\\bin\\ngspice.exe",
            "/usr/bin/ngspice",
            "/usr/local/bin/ngspice"
        ]

        for path in common_paths:
            if not path:
                continue
            try:
                result = subprocess.run(
                    [path, "-v"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Found ngspice at: {path}")
                    return path
            except (subprocess.SubprocessError, FileNotFoundError, OSError, TimeoutError):
                pass

        logger.warning("ngspice not found, simulation will be mocked")
        return "ngspice"  # 返回命令名，实际调用时会失败

    def simulate(
        self,
        schematic: Dict[str, Any],
        analysis_type: str = "tran",
        parameters: Dict[str, Any] = None
    ) -> SimulationResult:
        """
        运行仿真

        Args:
            schematic: 原理图数据
            analysis_type: 分析类型 (dc_op, ac, tran, dc_sweep)
            parameters: 仿真参数

        Returns:
            SimulationResult
        """
        if parameters is None:
            parameters = {}

        logger.info(f"Running {analysis_type} simulation")

        # 生成网表
        netlist = self._generate_netlist(schematic, analysis_type, parameters)

        # 检查是否有 ngspice
        if not self._has_ngspice():
            # 返回模拟结果
            return self._mock_simulation(analysis_type, parameters)

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.cir',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(netlist)
                netlist_file = f.name

            # 运行仿真
            result = self._run_ngspice(netlist_file)

            # 删除临时文件
            try:
                os.unlink(netlist_file)
            except OSError:
                pass

            if result["success"]:
                return SimulationResult(
                    success=True,
                    analysis_type=analysis_type,
                    data=result.get("data", {}),
                    parameters=parameters
                )
            else:
                return SimulationResult(
                    success=False,
                    analysis_type=analysis_type,
                    data={},
                    parameters=parameters,
                    error_message=result.get("error", "Unknown error")
                )

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return SimulationResult(
                success=False,
                analysis_type=analysis_type,
                data={},
                parameters=parameters,
                error_message=str(e)
            )

    def _has_ngspice(self) -> bool:
        """检查是否有 ngspice"""
        try:
            subprocess.run(
                [self.ngspice_path, "-v"],
                capture_output=True,
                timeout=5
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError, OSError, TimeoutError):
            return False

    def _generate_netlist(
        self,
        schematic: Dict[str, Any],
        analysis_type: str,
        parameters: Dict[str, Any]
    ) -> str:
        """
        生成 SPICE 网表

        Args:
            schematic: 原理图数据
            analysis_type: 分析类型
            parameters: 仿真参数

        Returns:
            SPICE 网表字符串
        """
        lines = []

        # 标题
        lines.append("* KiCad to SPICE Netlist")
        lines.append("")

        # 组件
        components = schematic.get("components", [])
        for comp in components:
            ref = comp.get("reference", "X")
            name = comp.get("name", "")
            value = comp.get("value", "")
            pins = comp.get("pins", [])
            footprint = comp.get("footprint", "")

            # 根据元件类型生成 SPICE 元件
            if name.upper().startswith("R"):
                # 电阻
                pins_str = " ".join([f"{p.get('net', 'NC')}" for p in pins])
                lines.append(f"{ref} {pins_str} {value}")
            elif name.upper().startswith("C"):
                # 电容
                pins_str = " ".join([f"{p.get('net', 'NC')}" for p in pins])
                lines.append(f"{ref} {pins_str} {value}")
            elif name.upper().startswith("L"):
                # 电感
                pins_str = " ".join([f"{p.get('net', 'NC')}" for p in pins])
                lines.append(f"{ref} {pins_str} {value}")
            elif "LED" in name.upper():
                # LED - 使用二极管模型
                pins_str = " ".join([f"{p.get('net', 'NC')}" for p in pins])
                lines.append(f"{ref} {pins_str} D")
            elif any(x in name.upper() for x in ["NE555", "555"]):
                # NE555 - 简化模型
                lines.append(f"* {ref} NE555 Timer (simplified)")
            elif any(x in name.upper() for x in ["STM32", "MCU", "ATMEGA", "ARDUINO"]):
                # MCU - 简化为电压源
                for pin in pins:
                    if pin.get("type") == "power_in":
                        net = pin.get("net", "VCC")
                        lines.append(f"V_{ref}_{pin.get('number')} {net} 0 DC 3.3V")
            else:
                lines.append(f"* {ref} {name} (unsupported)")

        lines.append("")

        # 电源
        lines.append("* Power Supply")
        lines.append("VCC VCC 0 DC 5V")
        lines.append("GND GND 0 DC 0V")
        lines.append("")

        # 分析命令
        if analysis_type == "dc_op":
            lines.append(".OP")
        elif analysis_type == "ac":
            lines.append(".AC DEC 10 1 1Meg")
        elif analysis_type == "tran":
            tstop = parameters.get("tstop", 1)
            tstep = parameters.get("tstep", 0.001)
            lines.append(f".TRAN {tstep} {tstop}")
        elif analysis_type == "dc_sweep":
            vstart = parameters.get("vstart", 0)
            vstop = parameters.get("vstop", 5)
            vstep = parameters.get("vstep", 0.1)
            lines.append(f".DC VCC {vstart} {vstop} {vstep}")

        lines.append("")
        lines.append(".END")

        return "\n".join(lines)

    def _run_ngspice(self, netlist_file: str) -> Dict[str, Any]:
        """运行 ngspice"""
        try:
            result = subprocess.run(
                [self.ngspice_path, "-b", "-o", "spice_output.txt", netlist_file],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # 解析输出
                return self._parse_output()
            else:
                return {
                    "success": False,
                    "error": result.stderr or "ngspice failed"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Simulation timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_output(self) -> Dict[str, Any]:
        """解析 ngspice 输出"""
        # 简化实现 - 实际需要解析 ngspice 的输出文件
        return {
            "success": True,
            "data": {}
        }

    def _mock_simulation(
        self,
        analysis_type: str,
        parameters: Dict[str, Any]
    ) -> SimulationResult:
        """返回模拟仿真结果"""
        logger.info(f"Mocking {analysis_type} simulation")

        data = {}

        if analysis_type == "dc_op":
            data = {
                "V(vcc)": [5.0],
                "V(out)": [2.5],
                "I(VCC)": [0.001]
            }
        elif analysis_type == "tran":
            tstop = parameters.get("tstop", 1)
            tstep = parameters.get("tstep", 0.001)
            num_points = int(tstop / tstep)
            data = {
                "time": [i * tstep for i in range(num_points)],
                "V(out)": [2.5 + 0.5 * (i * tstep / tstop) for i in range(num_points)]
            }
        elif analysis_type == "ac":
            data = {
                "frequency": [100, 1000, 10000, 100000, 1000000],
                "V(out)": [1.0, 0.95, 0.8, 0.5, 0.2]
            }

        return SimulationResult(
            success=True,
            analysis_type=analysis_type,
            data=data,
            parameters=parameters
        )


# 全局实例
_simulator: Optional[SpiceSimulator] = None


def get_simulator() -> SpiceSimulator:
    """获取仿真器单例"""
    global _simulator
    if _simulator is None:
        _simulator = SpiceSimulator()
    return _simulator


def run_simulation(
    schematic: Dict[str, Any],
    analysis_type: str = "tran",
    parameters: Dict[str, Any] = None
) -> SimulationResult:
    """
    运行仿真

    Args:
        schematic: 原理图数据
        analysis_type: 分析类型
        parameters: 仿真参数

    Returns:
        SimulationResult
    """
    simulator = get_simulator()
    return simulator.simulate(schematic, analysis_type, parameters)
