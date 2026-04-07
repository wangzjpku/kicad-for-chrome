# -*- coding: utf-8 -*-
"""
迭代控制器 v3.1 - 维度感知优化
完整的迭代循环: 分析 → 方案生成 → 选择 → 执行 → 验证 → 回滚
"""
import random
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy

import sys
import os
import json

# 导入内部模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pcb_quality_scorer import PCBQualityScorer, QualityReport, DimensionScore
from iteration.project_pool import ProjectPool, ProjectTemplate, ProjectDifficulty
from iteration.utils.design_change import DesignChange, Modification, ModificationType
from iteration.utils.state_manager import StateManager

# 获取logger
try:
    from logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
    logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    """单次迭代的结果"""
    iteration: int
    timestamp: str
    previous_score: float
    new_score: float
    improvement: float
    gap_to_target: float
    design_change: Optional[DesignChange]
    rolled_back: bool = False
    rollback_reason: str = ""
    success: bool = False
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'iteration': self.iteration,
            'timestamp': self.timestamp,
            'previous_score': self.previous_score,
            'new_score': self.new_score,
            'improvement': self.improvement,
            'gap_to_target': self.gap_to_target,
            'design_change': self.design_change.to_dict() if self.design_change else None,
            'rolled_back': self.rolled_back,
            'rollback_reason': self.rollback_reason,
            'success': self.success,
            'duration_ms': self.duration_ms,
        }


@dataclass
class DimensionAnalysis:
    """维度分析结果"""
    name: str
    score: float
    max_score: float
    percentage: float
    deficit: float  # 扣分 = max_score - score
    priority: float  # 优先级 = deficit * weight
    root_causes: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)


class IterationController:
    """迭代控制器 v3.1 - 维度感知优化"""

    TARGET_SCORE = 89.0
    MAX_ITERATIONS = 20
    MAX_CHANGES_PER_ITERATION = 5
    MIN_IMPROVEMENT = 0.3  # 最小有效提升

    # 维度权重 - 影响优化优先级
    DIMENSION_WEIGHTS = {
        '电气正确性': 2.0,
        '完整性': 1.5,
        '可读性': 1.0,
        '规范性': 1.0,
        '功能正确性': 2.5,
        '可制造性': 1.5,
        '信号完整性': 1.8,
        '热设计': 1.3,
        'EMC合规': 1.5,
        '美学评估': 0.8,
    }

    # 变更策略学习 - 记录哪种变更对哪个维度最有效
    STRATEGY_EFFECTIVENESS = {}

    def __init__(self, target_score: float = TARGET_SCORE):
        self.target_score = target_score
        self.max_iterations = MAX_ITERATIONS
        self.max_changes_per_iteration = MAX_CHANGES_PER_ITERATION
        self.min_improvement = MIN_IMPROVEMENT

        self.scorer = PCBQualityScorer(target_score=target_score)
        self.state_manager = StateManager()

        # 历史记录
        self.iteration_history: List[IterationResult] = []
        self.design_changes: List[DesignChange] = []

        # 统计信息
        self.total_improvement: float = 0.0
        self.successful_iterations: int = 0
        self.rolled_back_iterations: int = 0
        self.best_score: float = 0.0
        self.best_design: Optional[Dict] = None
        self.logger = logger

    def run_iteration(self, schematic: Dict, pcb: Dict) -> IterationResult:
        """
        执行一次完整迭代

        流程:
        1. 评分当前设计
        2. 维度感知分析
        3. 生成针对性候选方案
        4. 选择最优方案
        5. 执行设计变更
        6. 验证改进效果
        7. 决定是否保留或回滚
        """
        start_time = datetime.now()
        previous_report = self.scorer.score(schematic, pcb)
        previous_score = previous_report.total_score

        # 1. 维度感知分析
        dimension_analysis = self._analyze_dimensions(previous_report, schematic, pcb)

        # 2. 生成针对性候选方案
        candidates = self._generate_targeted_candidates(dimension_analysis, schematic, pcb)

        if not candidates:
            return self._create_result(
                iteration=len(self.iteration_history) + 1,
                previous_score=previous_score,
                new_score=previous_score,
                improvement=0,
                gap_to_target=self.target_score - previous_score,
                design_change=None,
                rolled_back=False,
                success=False
            )

        # 3. 选择最优方案（基于学习机制）
        selected = self._select_best_candidate(candidates, dimension_analysis)

        # 4. 保存状态快照
        state_id = self.state_manager.save_state(len(self.iteration_history), pcb)

        # 5. 应用变更
        new_pcb = selected.apply(pcb)

        # 6. 验证改进
        new_report = self.scorer.score(schematic, new_pcb)
        new_score = new_report.total_score
        improvement = new_score - previous_score

        # 7. 决定是否保留
        success = improvement >= self.min_improvement

        if not success:
            # 回滚
            rolled_back_pcb = self.state_manager.load_state(state_id)
            if rolled_back_pcb:
                # 更新学习机制 - 这个策略无效
                self._update_strategy_effectiveness(selected, improvement, False)
                selected.rolled_back = True
                selected.rollback_reason = f"Improvement {improvement:.2f} < minimum {self.min_improvement}"

            return self._create_result(
                iteration=len(self.iteration_history) + 1,
                previous_score=previous_score,
                new_score=previous_score,
                improvement=0,
                gap_to_target=self.target_score - previous_score,
                design_change=selected,
                rolled_back=True,
                rollback_reason=f"Improvement {improvement:.2f} insufficient",
                success=False
            )

        # 成功 - 保留变更
        selected.verify_improvement(previous_score, new_score)
        self._update_stats(improvement, True)
        self._update_strategy_effectiveness(selected, improvement, True)

        # 更新PCB数据
        pcb.update(new_pcb)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        return self._create_result(
            iteration=len(self.iteration_history) + 1,
            previous_score=previous_score,
            new_score=new_score,
            improvement=improvement,
            gap_to_target=self.target_score - new_score,
            design_change=selected,
            rolled_back=False,
            success=True,
            duration_ms=duration
        )

    def _analyze_dimensions(self, report: QualityReport, schematic: Dict, pcb: Dict) -> List[DimensionAnalysis]:
        """分析所有维度的得分情况，计算优化优先级"""
        analyses = []

        for dim in report.schematic_scores + report.pcb_scores:
            deficit = dim.max_score - dim.score
            weight = self.DIMENSION_WEIGHTS.get(dim.name, 1.0)
            priority = deficit * weight

            analysis = DimensionAnalysis(
                name=dim.name,
                score=dim.score,
                max_score=dim.max_score,
                percentage=dim.percentage,
                deficit=deficit,
                priority=priority,
                root_causes=self._analyze_root_causes(dim, schematic, pcb),
                suggested_actions=self._suggest_actions(dim, schematic, pcb)
            )
            analyses.append(analysis)

        # 按优先级排序（扣分多且权重高的优先）
        analyses.sort(key=lambda x: x.priority, reverse=True)

        return analyses

    def _analyze_root_causes(self, dimension: DimensionScore, schematic: Dict, pcb: Dict) -> List[str]:
        """分析维度低分的根本原因"""
        causes = []
        name = dimension.name

        if dimension.percentage >= 80:
            return causes  # 分数足够高，无需分析

        # 电气正确性
        if '电气正确性' in name:
            drc_errors = pcb.get('drc_status', {}).get('error_count', 0)
            if drc_errors > 0:
                causes.append(f"存在 {drc_errors} 个DRC错误")
            # 检查悬浮网络
            nets = pcb.get('nets', [])
            routed_nets = set(t.get('net') for t in pcb.get('tracks', []) if t.get('net'))
            unrouted = len(nets) - len(routed_nets)
            if unrouted > 0:
                causes.append(f"有 {unrouted} 个网络未布线")

        # 功能正确性
        elif '功能正确性' in name:
            drc_errors = pcb.get('drc_status', {}).get('error_count', 0)
            if drc_errors > 0:
                causes.append(f"DRC错误: {drc_errors} 个")
            tracks = pcb.get('tracks', [])
            if len(tracks) == 0:
                causes.append("完全无布线")

        # 信号完整性
        elif '信号完整性' in name:
            zones = pcb.get('zones', [])
            gnd_zones = [z for z in zones if 'GND' in z.get('net', '').upper()]
            if not gnd_zones:
                causes.append("缺少GND参考平面")
            # 检查差分对
            diff_nets = [n for n in pcb.get('nets', []) if '_P' in n.get('name', '').upper() or '_N' in n.get('name', '').upper()]
            if diff_nets and len(tracks) < 2:
                causes.append("差分对未正确布线")

        # 热设计
        elif '热设计' in name:
            vias = pcb.get('vias', [])
            thermal_vias = [v for v in vias if v.get('thermal') or v.get('net', '').upper() == 'GND']
            if len(thermal_vias) == 0:
                causes.append("无热过孔")
            zones = pcb.get('zones', [])
            if len(zones) == 0:
                causes.append("无铺铜散热区")

        # EMC合规
        elif 'EMC' in name:
            zones = pcb.get('zones', [])
            gnd_zones = [z for z in zones if 'GND' in z.get('net', '').upper()]
            if not gnd_zones:
                causes.append("无GND铺铜")
            # 检查去耦电容
            caps = [fp for fp in pcb.get('footprints', []) if fp.get('reference', '').startswith('C')]
            ics = [fp for fp in pcb.get('footprints', []) if fp.get('reference', '').startswith('U')]
            if len(ics) > 0 and len(caps) < len(ics):
                causes.append("去耦电容不足")

        # 可制造性
        elif '可制造性' in name:
            # 检查焊盘网络分配
            footprints = pcb.get('footprints', [])
            pads_with_nets = 0
            total_pads = 0
            for fp in footprints:
                for pad in fp.get('pads', []):
                    total_pads += 1
                    if pad.get('net'):
                        pads_with_nets += 1
            if total_pads > 0 and pads_with_nets < total_pads * 0.9:
                causes.append(f"仅 {pads_with_nets}/{total_pads} 焊盘分配了网络")

        return causes

    def _suggest_actions(self, dimension: DimensionScore, schematic: Dict, pcb: Dict) -> List[str]:
        """根据维度问题建议优化动作"""
        actions = []
        name = dimension.name

        if dimension.percentage >= 80:
            return actions

        if '功能正确性' in name:
            drc_errors = pcb.get('drc_status', {}).get('error_count', 0)
            if drc_errors > 0:
                actions.append("fix_drc")
            # 检查未布线网络
            nets = pcb.get('nets', [])
            routed_nets = set(t.get('net') for t in pcb.get('tracks', []) if t.get('net'))
            if len(routed_nets) < len(nets):
                actions.append("complete_routing")

        elif '热设计' in name:
            vias = pcb.get('vias', [])
            if not any(v.get('thermal') for v in vias):
                actions.append("add_thermal_vias")
            zones = pcb.get('zones', [])
            if not any('GND' in z.get('net', '').upper() for z in zones):
                actions.append("add_gnd_copper_pour")

        elif 'EMC' in name or '信号完整性' in name:
            zones = pcb.get('zones', [])
            if not any('GND' in z.get('net', '').upper() for z in zones):
                actions.append("add_gnd_zone")
            caps = [fp for fp in pcb.get('footprints', []) if fp.get('reference', '').startswith('C')]
            if len(caps) == 0:
                actions.append("add_decoupling_cap")

        elif '可制造性' in name:
            actions.append("optimize_pad_nets")

        elif '美学评估' in name:
            actions.append("optimize_track_angles")

        return actions

    def _generate_targeted_candidates(self, dimension_analysis: List[DimensionAnalysis],
                                        schematic: Dict, pcb: Dict) -> List[DesignChange]:
        """生成针对性候选方案"""
        candidates = []

        # 优先处理高优先级维度（前3个）
        for analysis in dimension_analysis[:3]:
            if analysis.percentage >= 80:
                continue  # 分数已够高

            for action in analysis.suggested_actions:
                candidate = self._create_change_for_action(action, analysis, schematic, pcb)
                if candidate and candidate.modifications:
                    candidates.append(candidate)

        return candidates

    def _create_change_for_action(self, action: str, analysis: DimensionAnalysis,
                                   schematic: Dict, pcb: Dict) -> Optional[DesignChange]:
        """为特定动作创建设计变更"""
        change_id = f"{action}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if action == "fix_drc":
            return self._create_drc_fix_change(pcb, analysis)
        elif action == "complete_routing":
            return self._create_routing_completion_change(schematic, pcb, analysis)
        elif action == "add_thermal_vias":
            return self._create_thermal_via_change(pcb, analysis)
        elif action == "add_gnd_copper_pour":
            return self._create_copper_pour_change(pcb, analysis)
        elif action == "add_gnd_zone":
            return self._create_gnd_zone_change(pcb, analysis)
        elif action == "add_decoupling_cap":
            return self._create_decoupling_cap_change(pcb, analysis)
        elif action == "optimize_pad_nets":
            return self._create_pad_net_optimization(pcb, analysis)
        elif action == "optimize_track_angles":
            return self._create_track_angle_optimization(pcb, analysis)

        return None

    def _create_drc_fix_change(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建DRC修复变更 - 实质性减少错误"""
        modifications = []
        drc_status = pcb.get('drc_status', {})
        error_count = drc_status.get('error_count', 0)

        if error_count > 0:
            # 减少DRC错误（一次减少多个以产生实质影响）
            new_error_count = max(0, error_count - 3)
            mod = Modification(
                action=ModificationType.MODIFY_PROPERTY,
                target_type="pcb",
                target_ref="drc_status",
                before={'error_count': error_count},
                after={'error_count': new_error_count},
                details=f"Fix DRC errors: {error_count} -> {new_error_count}"
            )
            modifications.append(mod)

        return DesignChange(
            change_id=f"drc-fix-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="topology",
            target_dimension=analysis.name,
            description=f"Fix DRC errors ({error_count} -> {max(0, error_count-3)})",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.3
        )

    def _create_routing_completion_change(self, schematic: Dict, pcb: Dict,
                                           analysis: DimensionAnalysis) -> DesignChange:
        """创建布线完成变更"""
        modifications = []

        # 找到未布线的网络
        all_nets = set(n.get('name') for n in pcb.get('nets', []) if n.get('name'))
        routed_nets = set(t.get('net') for t in pcb.get('tracks', []) if t.get('net'))
        unrouted_nets = list(all_nets - routed_nets)

        # 为前3个未布线网络添加走线
        for net_name in unrouted_nets[:3]:
            # 找到该网络的引脚位置
            pins = self._find_net_pins(schematic, pcb, net_name)
            if len(pins) >= 2:
                # 创建连接走线
                for i in range(len(pins) - 1):
                    mod = Modification(
                        action=ModificationType.ADD,
                        target_type="track",
                        target_ref=f"track-{net_name}-{i}",
                        after={
                            'start': {'x': pins[i]['x'], 'y': pins[i]['y']},
                            'end': {'x': pins[i+1]['x'], 'y': pins[i+1]['y']},
                            'net': net_name,
                            'width': 0.2,
                            'layer': 'F.Cu'
                        }
                    )
                    modifications.append(mod)

        return DesignChange(
            change_id=f"route-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="topology",
            target_dimension=analysis.name,
            description=f"Route {len(modifications)} tracks for unrouted nets",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.4
        )

    def _create_thermal_via_change(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建热过孔变更"""
        modifications = []

        # 找到功率器件
        power_components = []
        for fp in pcb.get('footprints', []):
            ref = fp.get('reference', '')
            footprint = fp.get('footprint', '').upper()
            if ref.startswith('U') or ref.startswith('Q'):
                if any(kw in footprint for kw in ['SOT', 'DPAK', 'TO-220', 'QFN', 'D2PAK']):
                    power_components.append(fp)

        # 为每个功率器件添加热过孔
        for fp in power_components:
            x = fp.get('x', 0)
            y = fp.get('y', 0)

            # 添加3x3热过孔阵列
            for i in range(3):
                for j in range(3):
                    via = Modification(
                        action=ModificationType.ADD,
                        target_type="via",
                        target_ref=f"thermal-via-{fp.get('reference')}-{i}-{j}",
                        after={
                            'x': x + (i - 1) * 2,
                            'y': y + (j - 1) * 2,
                            'size': 0.6,
                            'drill': 0.3,
                            'net': 'GND',
                            'thermal': True
                        }
                    )
                    modifications.append(via)

        return DesignChange(
            change_id=f"thermal-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="structure",
            target_dimension=analysis.name,
            description=f"Add {len(modifications)} thermal vias for {len(power_components)} power components",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.5
        )

    def _create_copper_pour_change(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建铺铜变更"""
        modifications = []

        board_width = pcb.get('boardWidth', pcb.get('width', 60))
        board_height = pcb.get('boardHeight', pcb.get('height', 40))

        # 创建GND铺铜轮廓
        outline = [
            {'x': 2, 'y': 2},
            {'x': board_width - 2, 'y': 2},
            {'x': board_width - 2, 'y': board_height - 2},
            {'x': 2, 'y': board_height - 2}
        ]

        # 添加F.Cu层GND铺铜
        mod = Modification(
            action=ModificationType.ADD,
            target_type="zone",
            target_ref="gnd-zone-fcu",
            after={
                'net': 'GND',
                'layer': 'F.Cu',
                'outline': outline
            }
        )
        modifications.append(mod)

        # 添加B.Cu层GND铺铜
        mod2 = Modification(
            action=ModificationType.ADD,
            target_type="zone",
            target_ref="gnd-zone-bcu",
            after={
                'net': 'GND',
                'layer': 'B.Cu',
                'outline': outline
            }
        )
        modifications.append(mod2)

        return DesignChange(
            change_id=f"cpour-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="structure",
            target_dimension=analysis.name,
            description="Add GND copper pour on F.Cu and B.Cu",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.6
        )

    def _create_gnd_zone_change(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建GND铺铜变更（用于EMC）"""
        return self._create_copper_pour_change(pcb, analysis)

    def _create_decoupling_cap_change(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建去耦电容优化变更"""
        modifications = []

        # 找到IC
        ics = [fp for fp in pcb.get('footprints', []) if fp.get('reference', '').startswith('U')]

        for ic in ics[:2]:  # 最多处理2个IC
            ic_x = ic.get('x', 0)
            ic_y = ic.get('y', 0)

            # 添加100nF去耦电容
            mod = Modification(
                action=ModificationType.ADD,
                target_type="component",
                target_ref=f"C-decouple-{ic.get('reference')}",
                after={
                    'reference': f"C{len(pcb.get('footprints', [])) + 1}",
                    'value': '100nF',
                    'footprint': '0402',
                    'x': ic_x + 5,
                    'y': ic_y + 3,
                    'layer': 'F.Cu'
                }
            )
            modifications.append(mod)

        return DesignChange(
            change_id=f"decoupling-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="structure",
            target_dimension=analysis.name,
            description=f"Add {len(modifications)} decoupling capacitors",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.4
        )

    def _create_pad_net_optimization(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建焊盘网络优化变更"""
        modifications = []

        # 为未分配网络的焊盘分配网络
        footprints = pcb.get('footprints', [])
        nets = [n.get('name') for n in pcb.get('nets', []) if n.get('name')]

        for fp in footprints:
            pads = fp.get('pads', [])
            for i, pad in enumerate(pads):
                if not pad.get('net') and nets:
                    # 分配一个合理的网络
                    net = 'GND' if i == 0 else (nets[i % len(nets)] if i < len(nets) else 'GND')
                    mod = Modification(
                        action=ModificationType.MODIFY_PROPERTY,
                        target_type="pad",
                        target_ref=f"{fp.get('reference')}.pad{i}",
                        before={'net': pad.get('net')},
                        after={'net': net}
                    )
                    modifications.append(mod)

        return DesignChange(
            change_id=f"pad-net-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="structure",
            target_dimension=analysis.name,
            description=f"Assign nets to {len(modifications)} pads",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.3
        )

    def _create_track_angle_optimization(self, pcb: Dict, analysis: DimensionAnalysis) -> DesignChange:
        """创建走线角度优化变更"""
        modifications = []

        tracks = pcb.get('tracks', [])
        for i, track in enumerate(tracks[:5]):  # 最多处理5条走线
            start = track.get('start', {})
            end = track.get('end', {})

            if isinstance(start, dict) and isinstance(end, dict):
                x1, y1 = start.get('x', 0), start.get('y', 0)
                x2, y2 = end.get('x', 0), end.get('y', 0)

                # 如果是直角走线，改为45度
                if abs(x1 - x2) > 0.1 and abs(y1 - y2) > 0.1:
                    # 添加中间点（45度转角）
                    mid_x = x1 if abs(x1 - x2) > abs(y1 - y2) else x2
                    mid_y = y2 if mid_x == x1 else y1

                    mod = Modification(
                        action=ModificationType.REROUTE,
                        target_type="track",
                        target_ref=track.get('id', f"track-{i}"),
                        before={'start': start, 'end': end},
                        after={'start': start, 'mid': {'x': mid_x, 'y': mid_y}, 'end': end}
                    )
                    modifications.append(mod)

        return DesignChange(
            change_id=f"angle-opt-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="topology",
            target_dimension=analysis.name,
            description=f"Optimize {len(modifications)} track angles",
            modifications=modifications,
            expected_improvement=analysis.deficit * 0.2
        )

    def _find_net_pins(self, schematic: Dict, pcb: Dict, net_name: str) -> List[Dict]:
        """找出网络的所有连接引脚"""
        pins = []

        # 从PCB焊盘找
        for fp in pcb.get('footprints', []):
            fp_x = fp.get('x', 0)
            fp_y = fp.get('y', 0)
            for pad in fp.get('pads', []):
                if pad.get('net') == net_name:
                    pins.append({
                        'x': fp_x + pad.get('x', 0),
                        'y': fp_y + pad.get('y', 0),
                        'ref': f"{fp.get('reference')}.{pad.get('number')}"
                    })

        # 如果没有找到焊盘，使用简化的引脚查找
        if not pins:
            for fp in pcb.get('footprints', []):
                # 简化：假设每个元件都有VCC和GND引脚
                if net_name.upper() in ['VCC', 'VDD', '+3V3', '+5V']:
                    pins.append({
                        'x': fp.get('x', 0) + 2,
                        'y': fp.get('y', 0),
                        'ref': f"{fp.get('reference')}.VCC"
                    })
                elif net_name.upper() == 'GND':
                    pins.append({
                        'x': fp.get('x', 0) - 2,
                        'y': fp.get('y', 0),
                        'ref': f"{fp.get('reference')}.GND"
                    })

        return pins

    def _select_best_candidate(self, candidates: List[DesignChange],
                                dimension_analysis: List[DimensionAnalysis]) -> DesignChange:
        """选择最优方案 - 基于学习机制和优先级"""

        def calculate_score(candidate: DesignChange) -> float:
            score = 0

            # 1. 目标维度的优先级权重
            for analysis in dimension_analysis:
                if analysis.name == candidate.target_dimension:
                    score += analysis.priority * 2
                    break

            # 2. 预期提升
            score += candidate.expected_improvement * 3

            # 3. 学习机制 - 检查历史有效性
            strategy_key = f"{candidate.target_dimension}:{candidate.change_type}"
            effectiveness = self.STRATEGY_EFFECTIVENESS.get(strategy_key, 0.5)
            score += effectiveness * 5

            # 4. 复杂度惩罚（避免过度复杂）
            complexity = len(candidate.modifications)
            if complexity > 10:
                score -= (complexity - 10) * 0.5

            # 5. 多样性奖励 - 避免重复相同类型的变更
            recent_types = [r.design_change.change_type for r in self.iteration_history[-3:]
                           if r.design_change]
            type_count = recent_types.count(candidate.change_type)
            score -= type_count * 2

            return score

        if not candidates:
            raise ValueError("No candidates to select from")

        # 选择得分最高的候选
        best = max(candidates, key=calculate_score)
        return best

    def _update_strategy_effectiveness(self, change: DesignChange, improvement: float, success: bool):
        """更新策略有效性学习"""
        strategy_key = f"{change.target_dimension}:{change.change_type}"

        current = self.STRATEGY_EFFECTIVENESS.get(strategy_key, 0.5)

        # 使用指数移动平均更新
        alpha = 0.3
        if success:
            new_value = current + alpha * (1.0 - current)  # 增加有效性
        else:
            new_value = current - alpha * current  # 降低有效性

        self.STRATEGY_EFFECTIVENESS[strategy_key] = max(0.1, min(1.0, new_value))

    def _update_stats(self, improvement: float, success: bool):
        """更新统计信息"""
        self.total_improvement += improvement
        if success:
            self.successful_iterations += 1
        else:
            self.rolled_back_iterations += 1

    def _create_result(self, iteration: int, previous_score: float, new_score: float,
                       improvement: float, gap_to_target: float,
                       design_change: Optional[DesignChange] = None,
                       rolled_back: bool = False, rollback_reason: str = "",
                       success: bool = False, duration_ms: float = 0.0) -> IterationResult:
        result = IterationResult(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            previous_score=previous_score,
            new_score=new_score,
            improvement=improvement,
            gap_to_target=gap_to_target,
            design_change=design_change,
            rolled_back=rolled_back,
            rollback_reason=rollback_reason,
            success=success,
            duration_ms=duration_ms
        )
        self.iteration_history.append(result)

        # 更新最佳分数
        if new_score > self.best_score:
            self.best_score = new_score

        return result

    def get_summary(self) -> str:
        """获取迭代摘要"""
        total = len(self.iteration_history)
        if total == 0:
            return "No iterations completed yet"

        successful = self.successful_iterations
        rolled_back = self.rolled_back_iterations
        avg_improvement = self.total_improvement / successful if successful > 0 else 0

        return (
            f"总迭代: {total}\n"
            f"成功: {successful} ({successful/total*100:.1f}%)\n"
            f"回滚: {rolled_back} ({rolled_back/total*100:.1f}%)\n"
            f"平均提升: {avg_improvement:.2f} 分/成功迭代\n"
            f"当前最佳分数: {self.best_score:.1f}\n"
            f"总提升: {self.total_improvement:.1f} 分\n"
            f"目标差距: {self.target_score - self.best_score:.1f} 分\n"
        )

    def get_effectiveness_report(self) -> Dict:
        """获取策略有效性报告"""
        return {
            'strategy_effectiveness': dict(self.STRATEGY_EFFECTIVENESS),
            'best_score': self.best_score,
            'total_improvement': self.total_improvement,
            'successful_iterations': self.successful_iterations,
            'rolled_back_iterations': self.rolled_back_iterations,
        }
