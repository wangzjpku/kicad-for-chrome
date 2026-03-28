"""
SPICE Simulator 100% Coverage Tests

基于实际 simulator/spice_simulator.py 模块结构
"""
import pytest
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.spice_simulator import (
    SpiceSimulator, SimulationResult, AnalysisType,
    get_simulator, run_simulation
)


class TestSpiceSimulator:
    """SPICE仿真器测试"""

    @pytest.fixture
    def simulator(self):
        """创建仿真器"""
        return SpiceSimulator()

    def test_simulator_initialization(self, simulator):
        """测试仿真器初始化"""
        assert simulator is not None
        assert hasattr(simulator, 'ngspice_path')

    def test_simulate_dc_op(self, simulator):
        """测试直流工作点分析"""
        schematic = {
            "components": [
                {"ref": "R1", "type": "resistor", "value": "1k", "pins": ["N1", "N2"]}
            ],
            "nets": [
                {"name": "NET1", "nodes": ["R1.1", "R1.2"]}
            ]
        }

        result = simulator.simulate(schematic, "dc_op")

        assert isinstance(result, SimulationResult)

    def test_simulate_ac(self, simulator):
        """测试交流分析"""
        schematic = {
            "components": [
                {"ref": "R1", "type": "resistor", "value": "1k", "pins": ["IN", "OUT"]}
            ],
            "nets": []
        }

        result = simulator.simulate(schematic, "ac")

        assert isinstance(result, SimulationResult)
        assert result.analysis_type == "ac"

    def test_simulate_tran(self, simulator):
        """测试瞬态分析"""
        schematic = {
            "components": [
                {"ref": "C1", "type": "capacitor", "value": "100n", "pins": ["P", "N"]}
            ],
            "nets": []
        }

        result = simulator.simulate(schematic, "tran", {"tstop": 1})

        assert isinstance(result, SimulationResult)

    def test_simulate_with_parameters(self, simulator):
        """测试带参数的仿真"""
        schematic = {
            "components": [
                {"ref": "R1", "type": "resistor", "value": "1k", "pins": ["A", "B"]}
            ],
            "nets": []
        }

        params = {"tstop": 0.001, "tstep": 0.0001}

        result = simulator.simulate(schematic, "tran", params)

        assert isinstance(result, SimulationResult)

    def test_has_ngspice(self, simulator):
        """测试检查ngspice是否可用"""
        has_ngspice = simulator._has_ngspice()

        assert isinstance(has_ngspice, bool)

    def test_mock_simulation(self, simulator):
        """测试模拟仿真"""
        schematic = {
            "components": [
                {"ref": "R1", "type": "resistor", "value": "1k", "pins": ["A", "B"]}
            ],
            "nets": []
        }

        result = simulator._mock_simulation(schematic, "dc_op")

        assert isinstance(result, SimulationResult)
        assert result.success is True


class TestAnalysisType:
    """分析类型枚举测试"""

    def test_dc_op_value(self):
        """测试DC_OP值"""
        assert AnalysisType.DC_OP.value == "dc_op"

    def test_ac_value(self):
        """测试AC值"""
        assert AnalysisType.AC.value == "ac"

    def test_tran_value(self):
        """测试TRAN值"""
        assert AnalysisType.TRAN.value == "tran"

    def test_dc_sweep_value(self):
        """测试DC_SWEEP值"""
        assert AnalysisType.DC_SWEEP.value == "dc_sweep"


class TestSimulationResult:
    """仿真结果测试"""

    def test_result_success(self):
        """测试成功结果"""
        result = SimulationResult(
            success=True,
            analysis_type="dc_op",
            data={"V1": [5.0], "V2": [0.0]},
            parameters={"tolerance": 0.001}
        )

        assert result.success is True
        assert result.analysis_type == "dc_op"
        assert len(result.data) > 0

    def test_result_failure(self):
        """测试失败结果"""
        result = SimulationResult(
            success=False,
            analysis_type="dc_op",
            data={},
            parameters={},
            error_message="Singular matrix"
        )

        assert result.success is False
        assert result.error_message == "Singular matrix"


class TestModuleFunctions:
    """模块级函数测试"""

    def test_get_simulator(self):
        """测试获取仿真器单例"""
        sim1 = get_simulator()
        sim2 = get_simulator()

        assert sim1 is sim2

    def test_run_simulation_function(self):
        """测试run_simulation函数"""
        schematic = {
            "components": [
                {"ref": "R1", "type": "resistor", "value": "1k", "pins": ["A", "B"]}
            ],
            "nets": []
        }

        result = run_simulation(schematic, "dc_op")

        assert isinstance(result, SimulationResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
