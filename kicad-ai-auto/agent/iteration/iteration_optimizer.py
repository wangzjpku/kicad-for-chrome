# -*- coding: utf-8 -*-
"""
PCB迭代优化器 v3.0
主入口 - 整合所有组件实现完整的迭代优化流程
"""
import random
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb_quality_scorer import PCBQualityScorer, QualityReport
from .project_pool import ProjectPool, ProjectTemplate, ProjectDifficulty
from .core.iteration_controller import IterationController, IterationResult
from .utils.design_change import DesignChange
from ..logger import get_logger
from ..config import settings

logger = get_logger(__name__)


@dataclass
class OptimizationConfig:
    """优化配置"""
    target_score: float = 89.0
    max_iterations: int = 20
    max_changes_per_iteration: int = 5
    min_improvement: float = 0.5
    enable_rollback: bool = True
    parallel_attempts: int = 3
    learning_rate: float = 0.1
    difficulty_advancement_threshold: float = 2.0
    adaptive_learning: bool = True
    strategy_weights: Optional[Dict[str, float]] = None
    def __post_init__(self):
        if self.strategy_weights is None:
            self.strategy_weights = {
                'topology': 0.3,
                'structure': 0.3,
                'global': 0.4
            }


class IterationOptimizer:
    """PCB迭代优化器 v3.0"""
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.target_score = config.target_score
        self.max_iterations = config.max_iterations
        self.max_changes_per_iteration = config.max_changes_per_iteration
        self.min_improvement = config.min_improvement
        self.adaptive_learning = config.adaptive_learning
        self.strategy_weights = config.strategy_weights
        self.logger = logger
        self.project_pool = ProjectPool(target_score=self.target_score)
        self.iteration_controller = IterationController(target_score=self.target_score)
        self.current_project: Optional[str] = None
        self.current_difficulty = ProjectDifficulty.LEVEL_1
        # 统计信息
        self.total_iterations = 0
        self.successful_projects = 0
        self.total_improvement = 0.0
        self.best_score = 0.0
        self.optimization_history: List[Dict] = []
    def run_optimization(self, project_name: Optional[str] = None) -> Dict:
        """运行完整优化流程"""
        self.logger.info("=" * 60)
        self.logger.info("PCB迭代优化器 v3.0")
        self.logger.info("=" * 60)
        # 1. 选择或生成项目
        if project_name:
            template = self.project_pool.get_template_by_name(project_name)
        else:
            template = self.project_pool.get_random_project()
        if not template:
            self.logger.error("No project template available")
            return {'error': 'No project available'}
        self.current_project = template.name
        self.logger.info(f"\n项目: {template.name}")
        self.logger.info(f"难度: {template.difficulty.name}")
        self.logger.info(f"类别: {template.category}")
        # 2. 生成初始设计
        self.logger.info("\n[步骤1] 生成初始设计...")
        schematic, pcb = self.project_pool.generate_initial_design(template)
        self._save_checkpoint('initial_design', {'schematic': schematic, 'pcb': pcb})
        # 3. 初始评分
        initial_report = self.project_pool.scorer.score(schematic, pcb)
        self.logger.info(f"\n[步骤2] 初始评分...")
        self.logger.info(f"  总分: {initial_report.total_score} ({initial_report.grade})")
        self.logger.info(f"  与目标差距: {self.target_score - initial_report.total_score:.1f} 分")
        # 4. 迭代优化
        self.logger.info("\n[步骤3] 开始迭代优化...")
        self.logger.info(f"  目标分数: {self.target_score}")
        self.logger.info(f"  最大迭代: {self.max_iterations}")
        for i in range(1, self.max_iterations + 1):
            self.logger.info(f"\n{'=' * 50}")
            self.logger.info(f"迭代 {i}/{self.max_iterations}")
            # 执行迭代
            result = self.iteration_controller.run_iteration(schematic, pcb)
            # 更新统计
            self.total_iterations += 1
            if result.success:
                self.total_improvement += result.improvement
            if result.new_score > self.best_score:
                self.best_score = result.new_score
            # 记录历史
            self.optimization_history.append({
                'iteration': i,
                'result': result.to_dict(),
                'timestamp': datetime.now().isoformat()
            })
            # 输出结果
            status = "SUCCESS" if result.success else "ROLLED BACK" if result.rolled_back else "NO IMPROVEMENT"
            self.logger.info(f"  {status}")
            self.logger.info(f"  分数: {result.previous_score:.1f} -> {result.new_score:.1f}")
            self.logger.info(f"  提升: {result.improvement:+.1f} 分")
            self.logger.info(f"  方案: {result.design_change.description if result.design_change else 'None'}")
            if result.rolled_back:
                self.logger.info(f"  回滚原因: {result.rollback_reason}")
            # 检查是否达到目标
            if result.new_score >= self.target_score:
                self.logger.info(f"\n  达到目标分数 {self.target_score}!")
                # 检查是否需要提升难度
                if self._should_advance_difficulty():
                    self._advance_difficulty()
                    self.logger.info(f"\n  提升难度到 {self.current_difficulty.name}")
                    # 重新生成项目
                    template = self.project_pool.get_project_by_difficulty(self.current_difficulty)
                    if template:
                        schematic, pcb = self.project_pool.generate_initial_design(template)
                        self.current_project = template.name
                        self.logger.info(f"\n  新项目: {template.name}")
        # 5. 生成最终报告
        return self._generate_final_report()
    def _should_advance_difficulty(self) -> bool:
        """判断是否应该提升难度"""
        if not self.adaptive_learning:
            return False
        recent_results = [r for r in self.optimization_history[-5:]]
        if not recent_results:
            return False
        success_rate = sum(1 for r in recent_results if r['result']['success']) / len(recent_results)
        threshold = self.config.difficulty_advancement_threshold
        return success_rate >= threshold
    def _advance_difficulty(self):
        """提升难度等级"""
        current_level = self.current_difficulty.value
        if current_level < 4:
            new_level = current_level + 1
            self.current_difficulty = ProjectDifficulty(new_level)
            self.logger.info(f"Difficulty advanced to Level {new_level}")
    def _generate_final_report(self) -> Dict:
        """生成最终报告"""
        final_iteration = self.optimization_history[-1] if self.optimization_history else {}
        report = {
            'project_name': self.current_project,
            'target_score': self.target_score,
            'max_iterations': self.max_iterations,
            'total_iterations': self.total_iterations,
            'final_score': final_iteration['result']['new_score'],
            'success': final_iteration['result']['new_score'] >= self.target_score,
            'total_improvement': self.total_improvement,
            'successful_iterations': self.successful_projects,
            'history': self.optimization_history,
        }
        # 保存报告
        report_path = f"iteration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.logger.info(f"\n报告已保存到: {report_path}")
        return report
    def get_progress(self) -> Dict:
        """获取当前进度"""
        return {
            'current_project': self.current_project,
            'current_difficulty': self.current_difficulty.name,
            'total_iterations': self.total_iterations,
            'max_iterations': self.max_iterations,
            'total_improvement': self.total_improvement,
            'best_score': self.best_score,
        }
    def _save_checkpoint(self, phase: str, data: Dict):
        """保存检查点"""
        checkpoint_dir = "checkpoints"
        os.makedirs(checkpoint_dir, exist_ok=True)
        filename = f"{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(os.path.join(checkpoint_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    def load_checkpoint(self, phase: str) -> Optional[Dict]:
        """加载检查点"""
        checkpoint_dir = "checkpoints"
        filename = f"{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(checkpoint_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    def set_strategy_weights(self, weights: Dict[str, float]):
        """设置策略权重"""
        self.strategy_weights = weights
        self.logger.info(f"Strategy weights updated: {weights}")
def main():
    """主函数 - 用于命令行运行"""
    import argparse
    parser = argparse.ArgumentParser(description='PCB迭代优化器')
    parser.add_argument('--project', '-p', help='项目名称')
    parser.add_argument('--target', '-t', type=float, default=89.0, help='目标分数')
    parser.add_argument('--iterations', '-i', type=int, default=20, help='最大迭代次数')
    args = parser.parse_args()
    config = OptimizationConfig(
        target_score=args.target,
        max_iterations=args.iterations
    )
    optimizer = IterationOptimizer(config)
    optimizer.run_optimization(args.project)
if __name__ == '__main__':
    main()
