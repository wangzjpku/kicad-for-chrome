# -*- coding: utf-8 -*-
"""
PCB迭代优化模块 v3.0
"""

from .iteration_optimizer import IterationOptimizer, OptimizationConfig
from .project_pool import ProjectPool, ProjectTemplate, ProjectDifficulty
from .core.iteration_controller import IterationController
from .utils.design_change import DesignChange, Modification, ModificationType
from .utils.state_manager import StateManager
from .engines.topology_changer import TopologyChanger
from .engines.structure_changer import StructureChanger
from .engines.global_re_router import GlobalReRouter
from ..pcb_quality_scorer import PCBQualityScorer, QualityReport

__all__ = [
    'IterationOptimizer',
    'OptimizationConfig',
    'ProjectPool',
    'ProjectTemplate',
    'ProjectDifficulty',
    'IterationController',
    'DesignChange',
    'Modification',
    'ModificationType',
    'StateManager',
    'TopologyChanger',
    'StructureChanger',
    'GlobalReRouter',
    'PCBQualityScorer',
    'QualityReport',
]
