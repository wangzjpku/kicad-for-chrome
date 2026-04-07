"""
迭代优化过程可视化工具

提供实时分数曲线、学习记忆可视化、迭代过程追踪
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class IterationSnapshot:
    """迭代快照"""
    iteration: int
    timestamp: str
    total_score: float
    dimension_scores: Dict[str, float]
    action: str
    action_source: str  # exploration / exploitation
    success: bool
    improvement: float
    root_cause: str
    is_parameter_game: bool

    # 可选的详细信息
    drc_errors: int = 0
    routing_completion: float = 0.0
    component_count: int = 0


@dataclass
class VisualizationConfig:
    """可视化配置"""
    # 分数曲线配置
    show_target_line: bool = True
    target_score: float = 89.0
    show_dimension_lines: bool = True

    # 学习记忆显示配置
    show_success_rate: bool = True
    show_action_history: bool = True
    max_history_display: int = 20

    # 迭代追踪配置
    show_parameter_game_warning: bool = True
    show_convergence_indicator: bool = True
    convergence_window: int = 5  # 连续5次无改进视为收敛

    # 导出配置
    export_format: str = "html"  # html / json / markdown
    auto_export_interval: int = 5  # 每5次迭代自动导出


class IterationVisualizer:
    """迭代过程可视化器"""

    def __init__(self, config: VisualizationConfig = None):
        self.config = config or VisualizationConfig()
        self.snapshots: List[IterationSnapshot] = []
        self.start_time: str = datetime.now().isoformat()

    def record_iteration(self,
                        iteration: int,
                        total_score: float,
                        dimension_scores: Dict[str, float],
                        action: str,
                        action_source: str,
                        success: bool,
                        improvement: float,
                        root_cause: str,
                        is_parameter_game: bool,
                        extra_info: Dict[str, Any] = None):
        """记录一次迭代

        Args:
            iteration: 迭代次数
            total_score: 总分
            dimension_scores: 各维度分数
            action: 执行的动作
            action_source: 动作来源 (exploration/exploitation)
            success: 是否成功
            improvement: 提升分数
            root_cause: 根本原因
            is_parameter_game: 是否为参数游戏
            extra_info: 额外信息
        """
        extra_info = extra_info or {}

        snapshot = IterationSnapshot(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            total_score=total_score,
            dimension_scores=dimension_scores,
            action=action,
            action_source=action_source,
            success=success,
            improvement=improvement,
            root_cause=root_cause,
            is_parameter_game=is_parameter_game,
            drc_errors=extra_info.get("drc_errors", 0),
            routing_completion=extra_info.get("routing_completion", 0.0),
            component_count=extra_info.get("component_count", 0)
        )

        self.snapshots.append(snapshot)

    def generate_score_curve_data(self) -> Dict:
        """生成分数曲线数据

        Returns:
            Dict: 包含各条曲线数据的字典
        """
        iterations = [s.iteration for s in self.snapshots]
        total_scores = [s.total_score for s in self.snapshots]

        # 总分曲线
        data = {
            "iterations": iterations,
            "total_score": total_scores,
            "target_score": [self.config.target_score] * len(iterations),
        }

        # 各维度曲线
        if self.config.show_dimension_lines and self.snapshots:
            # 获取所有维度名称
            all_dimensions = set()
            for s in self.snapshots:
                all_dimensions.update(s.dimension_scores.keys())

            for dim in all_dimensions:
                data[f"dim_{dim}"] = [
                    s.dimension_scores.get(dim, 0) for s in self.snapshots
                ]

        return data

    def generate_learning_memory_display(self,
                                         learning_memory) -> Dict:
        """生成学习记忆显示数据

        Args:
            learning_memory: LearningMemory对象

        Returns:
            Dict: 学习记忆显示数据
        """
        display = {
            "successful_actions": {},
            "failed_actions": {},
            "action_success_rate": {},
            "root_cause_patterns": [],
            "cross_dimension_knowledge": [],
            "recent_history": []
        }

        # 成功动作统计
        for dim, actions in learning_memory.successful_actions.items():
            display["successful_actions"][dim] = sorted(
                actions.items(), key=lambda x: x[1], reverse=True
            )[:5]  # 每个维度最多显示5个

        # 失败动作
        for dim, actions in learning_memory.failed_actions.items():
            display["failed_actions"][dim] = list(actions)

        # 成功率
        for dim, rates in learning_memory.action_success_rate.items():
            display["action_success_rate"][dim] = sorted(
                rates.items(), key=lambda x: x[1], reverse=True
            )[:5]

        # 根因模式
        if hasattr(learning_memory, 'root_cause_patterns'):
            for pid, pattern in learning_memory.root_cause_patterns.items():
                display["root_cause_patterns"].append({
                    "pattern_id": pid,
                    "keywords": pattern.pattern_keywords,
                    "top_actions": sorted(
                        pattern.successful_actions.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:3]
                })

        # 跨维度知识
        if hasattr(learning_memory, 'cross_dimension_knowledge'):
            for (source, target), knowledge in learning_memory.cross_dimension_knowledge.items():
                display["cross_dimension_knowledge"].append({
                    "source": source,
                    "target": target,
                    "transferable_actions": knowledge.transferable_actions,
                    "success_rate": knowledge.success_rate
                })

        # 最近历史
        if hasattr(learning_memory, 'action_history'):
            display["recent_history"] = [
                {
                    "action": h.action,
                    "dimension": h.dimension,
                    "success": h.success,
                    "improvement": h.improvement,
                    "timestamp": h.timestamp
                }
                for h in learning_memory.action_history[-self.config.max_history_display:]
            ]

        return display

    def check_convergence(self) -> Dict:
        """检查收敛状态

        Returns:
            Dict: 收敛状态信息
        """
        if len(self.snapshots) < self.config.convergence_window:
            return {
                "converged": False,
                "reason": "insufficient_data",
                "iterations_without_improvement": 0
            }

        # 检查最近N次迭代是否有改进
        recent = self.snapshots[-self.config.convergence_window:]
        improvements = [s.improvement for s in recent if s.success]

        if not improvements or all(imp < 0.1 for imp in improvements):
            return {
                "converged": True,
                "reason": "no_significant_improvement",
                "iterations_without_improvement": self.config.convergence_window,
                "recent_avg_improvement": sum(improvements) / len(improvements) if improvements else 0
            }

        # 检查是否达到目标分数
        if self.snapshots[-1].total_score >= self.config.target_score:
            return {
                "converged": True,
                "reason": "target_reached",
                "final_score": self.snapshots[-1].total_score,
                "iterations_used": len(self.snapshots)
            }

        return {
            "converged": False,
            "reason": "still_improving",
            "iterations_without_improvement": 0
        }

    def detect_parameter_game_pattern(self) -> Dict:
        """检测参数游戏模式

        Returns:
            Dict: 参数游戏检测结果
        """
        parameter_game_count = sum(1 for s in self.snapshots if s.is_parameter_game)
        total_count = len(self.snapshots)

        # 检测连续参数游戏
        consecutive_pg = 0
        max_consecutive_pg = 0
        for s in self.snapshots:
            if s.is_parameter_game:
                consecutive_pg += 1
                max_consecutive_pg = max(max_consecutive_pg, consecutive_pg)
            else:
                consecutive_pg = 0

        return {
            "total_parameter_games": parameter_game_count,
            "parameter_game_rate": parameter_game_count / total_count if total_count > 0 else 0,
            "max_consecutive_parameter_games": max_consecutive_pg,
            "warning": max_consecutive_pg >= 3,
            "parameter_game_actions": [
                {"iteration": s.iteration, "action": s.action}
                for s in self.snapshots if s.is_parameter_game
            ]
        }

    def generate_progress_report(self) -> str:
        """生成进度报告

        Returns:
            str: Markdown格式的进度报告
        """
        if not self.snapshots:
            return "# 进度报告\n\n暂无迭代数据"

        first = self.snapshots[0]
        last = self.snapshots[-1]
        total_improvement = last.total_score - first.total_score

        # 统计
        success_count = sum(1 for s in self.snapshots if s.success)
        exploration_count = sum(1 for s in self.snapshots if s.action_source == "exploration")
        exploitation_count = sum(1 for s in self.snapshots if s.action_source == "exploitation")
        parameter_game_count = sum(1 for s in self.snapshots if s.is_parameter_game)

        report = f"""# 迭代优化进度报告

## 基本信息
- 开始时间: {self.start_time}
- 当前时间: {datetime.now().isoformat()}
- 总迭代次数: {len(self.snapshots)}

## 分数变化
- 初始分数: {first.total_score:.1f}
- 当前分数: {last.total_score:.1f}
- 总提升: +{total_improvement:.1f}
- 目标分数: {self.config.target_score}
- 差距: {self.config.target_score - last.total_score:.1f}

## 迭代统计
- 成功迭代: {success_count}/{len(self.snapshots)} ({success_count/len(self.snapshots)*100:.1f}%)
- 探索迭代: {exploration_count}
- 利用迭代: {exploitation_count}
- 参数游戏次数: {parameter_game_count} ({parameter_game_count/len(self.snapshots)*100:.1f}%)

## 各维度分数
"""
        # 各维度分数
        for dim, score in last.dimension_scores.items():
            first_score = first.dimension_scores.get(dim, 0)
            change = score - first_score
            report += f"- {dim}: {score:.1f} ({change:+.1f})\n"

        # 收敛状态
        convergence = self.check_convergence()
        report += f"\n## 收敛状态\n"
        report += f"- 状态: {'已收敛' if convergence['converged'] else '继续优化中'}\n"
        report += f"- 原因: {convergence['reason']}\n"

        # 参数游戏警告
        pg_detection = self.detect_parameter_game_pattern()
        if pg_detection['warning']:
            report += f"\n## 警告: 检测到参数游戏模式\n"
            report += f"- 参数游戏比例: {pg_detection['parameter_game_rate']*100:.1f}%\n"
            report += f"- 最大连续次数: {pg_detection['max_consecutive_parameter_games']}\n"

        return report

    def export_to_html(self, filepath: str, learning_memory=None):
        """导出为HTML可视化页面

        Args:
            filepath: 文件路径
            learning_memory: 可选的学习记忆对象
        """
        score_data = self.generate_score_curve_data()
        convergence = self.check_convergence()
        pg_detection = self.detect_parameter_game_pattern()

        # 准备学习记忆数据
        memory_display = {}
        if learning_memory:
            memory_display = self.generate_learning_memory_display(learning_memory)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCB迭代优化可视化</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            margin-top: 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
        }}
        .action-list {{
            max-height: 300px;
            overflow-y: auto;
        }}
        .action-item {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .action-success {{
            color: #28a745;
        }}
        .action-fail {{
            color: #dc3545;
        }}
        .parameter-game {{
            background: #fff3cd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PCB迭代优化可视化</h1>

        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">{self.snapshots[-1].total_score if self.snapshots else 0:.1f}</div>
                <div class="stat-label">当前分数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{len(self.snapshots)}</div>
                <div class="stat-label">迭代次数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{sum(1 for s in self.snapshots if s.success)}/{len(self.snapshots)}</div>
                <div class="stat-label">成功迭代</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{pg_detection['parameter_game_rate']*100:.0f}%</div>
                <div class="stat-label">参数游戏比例</div>
            </div>
        </div>

        {"<div class='success'>已达到目标分数!</div>" if convergence['converged'] and convergence['reason'] == 'target_reached' else ""}
        {"<div class='warning'>警告: 检测到连续参数游戏模式</div>" if pg_detection['warning'] else ""}

        <div class="card">
            <h2>分数曲线</h2>
            <div class="chart-container">
                <canvas id="scoreChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>迭代历史</h2>
            <div class="action-list">
                {self._generate_action_history_html()}
            </div>
        </div>

        {self._generate_learning_memory_html(memory_display) if memory_display else ""}
    </div>

    <script>
        const ctx = document.getElementById('scoreChart').getContext('2d');
        const scoreData = {json.dumps(score_data)};

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: scoreData.iterations,
                datasets: [{{
                    label: '总分',
                    data: scoreData.total_score,
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    fill: true,
                    tension: 0.1
                }}, {{
                    label: '目标',
                    data: scoreData.target_score,
                    borderColor: '#FF5722',
                    borderDash: [5, 5],
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: false,
                        min: 50,
                        max: 100
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: '迭代优化分数曲线'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _generate_action_history_html(self) -> str:
        """生成动作历史HTML"""
        html = ""
        for s in reversed(self.snapshots[-20:]):
            status_class = "action-success" if s.success else "action-fail"
            pg_class = "parameter-game" if s.is_parameter_game else ""
            source_badge = "探索" if s.action_source == "exploration" else "利用"

            html += f"""
            <div class="action-item {pg_class}">
                <strong>#{s.iteration}</strong>
                <span class="{status_class}">{"+" if s.success else "-"}{s.improvement:.1f}</span>
                <span>{s.action}</span>
                <small>[{source_badge}]</small>
                <small>{s.total_score:.1f}分</small>
                {'<small style="color:#ffc107">参数游戏</small>' if s.is_parameter_game else ''}
            </div>
            """
        return html

    def _generate_learning_memory_html(self, memory_display: Dict) -> str:
        """生成学习记忆HTML"""
        if not memory_display:
            return ""

        html = """
        <div class="card">
            <h2>学习记忆</h2>
            <div class="stats-grid">
        """

        # 成功动作
        html += "<div class='stat-item'><h3>成功动作</h3><ul>"
        for dim, actions in memory_display.get('successful_actions', {}).items():
            for action, count in actions[:3]:
                html += f"<li>{dim}: {action} ({count}次)</li>"
        html += "</ul></div>"

        # 成功率
        html += "<div class='stat-item'><h3>动作成功率</h3><ul>"
        for dim, rates in memory_display.get('action_success_rate', {}).items():
            for action, rate in rates[:3]:
                html += f"<li>{action}: {rate*100:.0f}%</li>"
        html += "</ul></div>"

        # 跨维度知识
        cross_dim = memory_display.get('cross_dimension_knowledge', [])
        if cross_dim:
            html += "<div class='stat-item'><h3>跨维度迁移</h3><ul>"
            for kd in cross_dim[:5]:
                html += f"<li>{kd['source']} → {kd['target']}: {len(kd['transferable_actions'])}个动作</li>"
            html += "</ul></div>"

        html += """
            </div>
        </div>
        """
        return html

    def export_to_json(self, filepath: str):
        """导出为JSON格式

        Args:
            filepath: 文件路径
        """
        data = {
            "start_time": self.start_time,
            "config": {
                "target_score": self.config.target_score,
                "convergence_window": self.config.convergence_window,
            },
            "snapshots": [
                {
                    "iteration": s.iteration,
                    "timestamp": s.timestamp,
                    "total_score": s.total_score,
                    "dimension_scores": s.dimension_scores,
                    "action": s.action,
                    "action_source": s.action_source,
                    "success": s.success,
                    "improvement": s.improvement,
                    "root_cause": s.root_cause,
                    "is_parameter_game": s.is_parameter_game,
                }
                for s in self.snapshots
            ],
            "score_curve": self.generate_score_curve_data(),
            "convergence": self.check_convergence(),
            "parameter_game_detection": self.detect_parameter_game_pattern(),
        }

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# 便捷函数
def create_visualizer(config: VisualizationConfig = None) -> IterationVisualizer:
    """创建可视化器"""
    return IterationVisualizer(config)
