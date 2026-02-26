"""
AI 设计循环模块
实现生成-验证-修复闭环
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class LoopState(Enum):
    """循环状态"""
    IDLE = "idle"
    GENERATING = "generating"
    VALIDATING = "validating"
    FIXING = "fixing"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class LoopConfig:
    """设计循环配置"""
    max_iterations: int = 3
    auto_fix: bool = True
    validate_after_generate: bool = True
    stop_on_first_success: bool = False


@dataclass
class LoopResult:
    """循环结果"""
    success: bool
    state: LoopState
    output_path: str
    iterations: int
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    erc_result: Optional[Dict[str, Any]]
    final_json: Optional[Dict[str, Any]]
    message: str


class AICircuitDesigner:
    """
    AI 电路设计师
    
    实现完整的生成-验证-修复闭环:
    1. 分析需求 → 生成初始电路
    2. 运行 ERC 验证
    3. 如果有错误 → LLM 修复
    4. 重复直到通过或达到最大迭代
    """
    
    def __init__(
        self,
        config: Optional[LoopConfig] = None,
        requirements_analyzer: Optional[Callable] = None,
        circuit_generator: Optional[Callable] = None,
        error_fixer: Optional[Callable] = None,
    ):
        """
        初始化 AI 设计师
        
        Args:
            config: 循环配置
            requirements_analyzer: 需求分析函数
            circuit_generator: 电路生成函数
            error_fixer: 错误修复函数
        """
        self.config = config or LoopConfig()
        self.requirements_analyzer = requirements_analyzer
        self.circuit_generator = circuit_generator
        self.error_fixer = error_fixer
        self._current_state = LoopState.IDLE
        self._current_iteration = 0
    
    @property
    def state(self) -> LoopState:
        """当前状态"""
        return self._current_state
    
    def design(
        self,
        requirements: str,
        output_path: str,
        **kwargs
    ) -> LoopResult:
        """
        完整的 AI 设计流程
        
        Args:
            requirements: 用户需求描述
            output_path: 输出文件路径
            **kwargs: 传递给生成器的额外参数
            
        Returns:
            LoopResult: 设计结果
        """
        # Step 1: 需求分析 → 生成电路 JSON
        self._current_state = LoopState.GENERATING
        self._current_iteration = 0
        
        circuit_json = self._analyze_requirements(requirements)
        
        if circuit_json is None:
            return LoopResult(
                success=False,
                state=LoopState.FAILED,
                output_path=output_path,
                iterations=0,
                errors=[{"type": "analysis_failed", "message": "需求分析失败"}],
                warnings=[],
                erc_result=None,
                final_json=None,
                message="需求分析阶段失败"
            )
        
        # Step 2: 迭代验证和修复
        for i in range(self.config.max_iterations):
            self._current_iteration = i + 1
            logger.info(f"=== 迭代 {self._current_iteration}/{self.config.max_iterations} ===")
            
            # 2.1 生成原理图
            self._current_state = LoopState.GENERATING
            generate_result = self._generate_circuit(circuit_json, output_path, **kwargs)
            
            if not generate_result.success:
                return LoopResult(
                    success=False,
                    state=LoopState.FAILED,
                    output_path=output_path,
                    iterations=i + 1,
                    errors=generate_result.errors,
                    warnings=generate_result.warnings,
                    erc_result=None,
                    final_json=circuit_json,
                    message=f"生成失败: {generate_result.errors}"
                )
            
            # 2.2 验证（可选）
            erc_result = None
            if self.config.validate_after_generate:
                self._current_state = LoopState.VALIDATING
                erc_result = self._validate_circuit(output_path)
                
                if not erc_result.get("has_errors", True):
                    # 验证通过！
                    self._current_state = LoopState.SUCCESS
                    return LoopResult(
                        success=True,
                        state=LoopState.SUCCESS,
                        output_path=output_path,
                        iterations=i + 1,
                        errors=[],
                        warnings=erc_result.get("warnings", []),
                        erc_result=erc_result,
                        final_json=circuit_json,
                        message=f"成功！ERC 通过 (迭代 {i + 1})"
                    )
            
            # 2.3 需要修复
            if self.config.auto_fix and self.error_fixer:
                self._current_state = LoopState.FIXING
                
                errors = erc_result.get("errors", []) if erc_result else []
                logger.info(f"发现 {len(errors)} 个错误，开始修复...")
                
                # 使用 LLM 修复
                fixed_json = self._fix_with_llm(circuit_json, errors)
                
                if fixed_json:
                    circuit_json = fixed_json
                    logger.info(f"修复完成，继续迭代...")
                else:
                    logger.warning("修复失败，继续当前方案")
            else:
                # 不自动修复，返回错误
                self._current_state = LoopState.FAILED
                return LoopResult(
                    success=False,
                    state=LoopState.FAILED,
                    output_path=output_path,
                    iterations=i + 1,
                    errors=errors if erc_result else [{"message": "验证失败"}],
                    warnings=erc_result.get("warnings", []) if erc_result else [],
                    erc_result=erc_result,
                    final_json=circuit_json,
                    message=f"验证失败，有 {len(errors)} 个错误"
                )
        
        # 达到最大迭代
        self._current_state = LoopState.MAX_ITERATIONS
        return LoopResult(
            success=False,
            state=LoopState.MAX_ITERATIONS,
            output_path=output_path,
            iterations=self.config.max_iterations,
            errors=[{"message": f"达到最大迭代次数 ({self.config.max_iterations})"}],
            warnings=[],
            erc_result=erc_result,
            final_json=circuit_json,
            message=f"达到最大迭代次数 ({self.config.max_iterations})，未能通过验证"
        )
    
    def _analyze_requirements(self, requirements: str) -> Optional[Dict[str, Any]]:
        """需求分析"""
        if self.requirements_analyzer:
            try:
                return self.requirements_analyzer(requirements)
            except Exception as e:
                logger.error(f"需求分析失败: {e}")
                return None
        
        # 默认: 返回空电路结构
        return {
            "title": "AI Circuit",
            "components": [],
            "wires": [],
            "nets": [],
            "powerSymbols": [],
            "labels": []
        }
    
    def _generate_circuit(
        self,
        circuit_json: Dict[str, Any],
        output_path: str,
        **kwargs
    ) -> "GenerateResult":
        """生成电路"""
        if self.circuit_generator:
            try:
                return self.circuit_generator(circuit_json, output_path, **kwargs)
            except Exception as e:
                logger.error(f"生成失败: {e}")
                return GenerateResult(success=False, errors=[str(e)])
        
        # 默认失败
        return GenerateResult(
            success=False,
            errors=["未配置电路生成器"]
        )
    
    def _validate_circuit(self, output_path: str) -> Dict[str, Any]:
        """验证电路"""
        from validators import validate_schematic
        try:
            return validate_schematic(output_path)
        except Exception as e:
            logger.error(f"验证失败: {e}")
            return {"has_errors": True, "errors": [{"message": str(e)}]}
    
    def _fix_with_llm(
        self,
        circuit_json: Dict[str, Any],
        errors: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """使用 LLM 修复错误"""
        if not self.error_fixer:
            return None
        
        try:
            return self.error_fixer(circuit_json, errors)
        except Exception as e:
            logger.error(f"LLM 修复失败: {e}")
            return None


@dataclass
class GenerateResult:
    """生成结果"""
    success: bool
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


def create_designer_with_glm(
    glm4_client,
    generator,
    config: Optional[LoopConfig] = None
) -> AICircuitDesigner:
    """
    创建配置好的 AI 设计师
    
    Args:
        glm4_client: GLM-4 客户端
        generator: 电路生成器
        config: 循环配置
        
    Returns:
        AICircuitDesigner: 配置好的设计师
    """
    
    def analyze_requirements(requirements: str) -> Dict[str, Any]:
        """使用 GLM 分析需求"""
        prompt = f"""
你是一个电路设计专家。请根据用户需求设计电路。

需求：{requirements}

请生成 JSON 格式的电路描述。
"""
        response = glm4_client.chat(prompt)
        # 解析 JSON...
        return _parse_json_response(response)
    
    def fix_with_llm(
        circuit_json: Dict[str, Any],
        errors: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """使用 GLM 修复错误"""
        errors_text = "\n".join([
            f"- {e.get('type', 'unknown')}: {e.get('message', '')}"
            for e in errors
        ])
        
        prompt = f"""
当前电路存在以下 ERC 错误：

{errors_text}

当前电路 JSON：
{json.dumps(circuit_json, indent=2)}

请修复这些错误并返回修复后的 JSON。
"""
        response = glm4_client.chat(prompt)
        return _parse_json_response(response)
    
    return AICircuitDesigner(
        config=config,
        requirements_analyzer=analyze_requirements,
        circuit_generator=generator.generate,
        error_fixer=fix_with_llm
    )


def _parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """解析 JSON 响应"""
    import re
    import json
    
    # 尝试从 markdown 代码块中提取
    match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # 尝试直接解析
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    return None


import json  # For default usage

__all__ = [
    "AICircuitDesigner",
    "LoopConfig", 
    "LoopResult",
    "LoopState",
    "create_designer_with_glm",
]
