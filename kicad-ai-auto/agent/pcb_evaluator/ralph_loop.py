"""
Ralph Loop 迭代优化器
- 最大迭代次数 20 次
- 每次迭代自动修复问题或记录进展
- 模拟手动设计改进过程
"""

import copy
import random
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

from .pcb_models import (
    PCBBoard,
    Issue,
    IssueType,
    Severity,
    Point2D,
    Track,
    Via,
    Component,
    EvaluationResult,
)
from .checkers import PCBChecker, DesignRules


@dataclass
class IterationResult:
    """单次迭代结果"""

    iteration: int
    board: PCBBoard
    issues_before: List[Issue]
    issues_after: List[Issue]
    fixed_issues: List[Issue]
    new_issues: List[Issue]
    unchanged_issues: List[Issue]
    scores_before: Dict[str, float]
    scores_after: Dict[str, float]
    action_taken: str
    success: bool


@dataclass
class RalphLoopResult:
    """Ralph Loop 迭代优化结果"""

    initial_issues: List[Issue]
    final_issues: List[Issue]
    iterations: List[IterationResult]
    total_iterations: int
    converged: bool
    max_iterations_reached: bool
    final_scores: Dict[str, float]
    improvement_summary: Dict[str, int]


class AutoFixer:
    """自动修复器 - 模拟手动设计改进"""

    def __init__(self, rules: DesignRules = None):
        self.rules = rules or DesignRules()

    def fix_issue(self, issue: Issue, board: PCBBoard) -> bool:
        """尝试修复单个问题"""
        fixers = {
            IssueType.TRACK_WIDTH_TOO_NARROW: self._fix_track_width,
            IssueType.TRACK_WIDTH_INSUFFICIENT_CURRENT: self._fix_track_width,
            IssueType.DECOUPLING_CAPACITOR_FAR: self._fix_decoupling_capacitor,
            IssueType.CRYSTAL_PLACEMENT_FAR: self._fix_crystal_placement,
            IssueType.THERMAL_CLEARANCE_INSUFFICIENT: self._fix_thermal_clearance,
            IssueType.CONNECTOR_NOT_EDGE: self._fix_connector_placement,
            IssueType.VIA_DRILL_TOO_SMALL: self._fix_via_drill,
            IssueType.VIA_PAD_TOO_SMALL: self._fix_via_pad,
            IssueType.COPPER_TO_EDGE_TOO_SMALL: self._fix_copper_to_edge,
            IssueType.ANNULAR_RING_TOO_SMALL: self._fix_annular_ring,
            IssueType.TRACK_SPACING_TOO_NARROW: self._fix_track_spacing,
            IssueType.DANGLING_TRACK: self._remove_dangling_track,
            IssueType.DIFFERENTIAL_LENGTH_MISMATCH: self._fix_differential_length,
            IssueType.ISOLATED_COPPER: self._remove_isolated_copper,
            IssueType.RF_TRACE_TOO_NARROW: self._fix_rf_trace_width,
            IssueType.ANTENNA_NEAR_METAL: self._fix_antenna_metal_distance,
        }

        fixer = fixers.get(issue.type)
        if fixer:
            return fixer(issue, board)

        return False

    def _fix_track_width(self, issue: Issue, board: PCBBoard) -> bool:
        """修复线宽问题"""
        track_id = issue.related_ids[0] if issue.related_ids else None
        if not track_id:
            return False

        for track in board.tracks:
            if track.id == track_id:
                # 根据问题类型设置合适的宽度
                net = board.get_net(track.net_id)
                if issue.type == IssueType.TRACK_WIDTH_INSUFFICIENT_CURRENT:
                    # 电源线需要更宽
                    track.width = max(track.width, self.rules.MIN_POWER_TRACK_WIDTH)
                elif net and net.is_power_supply:
                    # 电源网络使用电源线宽
                    track.width = max(track.width, self.rules.MIN_POWER_TRACK_WIDTH)
                else:
                    track.width = max(track.width, self.rules.MIN_TRACK_WIDTH)
                return True

        return False

    def _fix_decoupling_capacitor(self, issue: Issue, board: PCBBoard) -> bool:
        """修复去耦电容位置 - 移动到靠近 IC"""
        if len(issue.related_ids) >= 2:
            ic_id = issue.related_ids[0]
            cap_id = issue.related_ids[1]

            # 找到 IC 和电容
            ic = None
            cap = None
            for comp in board.components:
                if comp.id == ic_id:
                    ic = comp
                elif comp.id == cap_id:
                    cap = comp

            if not ic or not cap:
                return False

            # 计算当前距离
            current_dist = ic.position.distance_to(cap.position)

            # 目标距离 (去耦电容应在 IC 电源引脚 5mm 内)
            target_distance = 3.0

            if current_dist <= target_distance:
                return True  # 已经足够近

            # 移动电容到靠近 IC 的位置
            dx = ic.position.x - cap.position.x
            dy = ic.position.y - cap.position.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                # 移动到目标距离
                ratio = (distance - target_distance) / distance
                cap.position.x = ic.position.x - dx * ratio
                cap.position.y = ic.position.y - dy * ratio

                # 确保在板内
                cap.position.x = max(2, min(board.width - 2, cap.position.x))
                cap.position.y = max(2, min(board.height - 2, cap.position.y))
                return True

        return False

    def _fix_crystal_placement(self, issue: Issue, board: PCBBoard) -> bool:
        """修复晶振位置 - 移动到靠近 MCU"""
        if len(issue.related_ids) >= 1:
            # 获取晶振位置
            crystal = None
            for comp in board.components:
                if comp.id == issue.related_ids[0]:
                    crystal = comp
                    break

            if not crystal:
                return False

            # 找到 MCU 位置
            mcu = None
            for comp in board.components:
                if comp.is_mcu:
                    mcu = comp
                    break

            if not mcu:
                # 如果没有找到 MCU，向板中心移动
                crystal.position.x = board.width / 2
                crystal.position.y = board.height / 2
                return True

            # 移动晶振到靠近 MCU (向 MCU 方向移动)
            dx = mcu.position.x - crystal.position.x
            dy = mcu.position.y - crystal.position.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                # 移动到距离 MCU 10mm 的位置
                target_distance = 10.0
                ratio = target_distance / distance
                crystal.position.x = mcu.position.x - dx * ratio
                crystal.position.y = mcu.position.y - dy * ratio
                return True

        return False

    def _fix_thermal_clearance(self, issue: Issue, board: PCBBoard) -> bool:
        """修复发热元件间距"""
        if len(issue.related_ids) >= 2:
            # 移动第二个元件
            for comp in board.components:
                if comp.id == issue.related_ids[1]:
                    comp.position.x += 5
                    comp.position.y += 5
                    return True
        return False

    def _fix_connector_placement(self, issue: Issue, board: PCBBoard) -> bool:
        """修复接插件位置"""
        if issue.related_ids:
            for comp in board.components:
                if comp.id == issue.related_ids[0]:
                    # 移动到边缘
                    comp.position.x = board.width - 5
                    return True
        return False

    def _fix_via_drill(self, issue: Issue, board: PCBBoard) -> bool:
        """修复过孔孔径"""
        if issue.related_ids:
            for via in board.vias:
                if via.id == issue.related_ids[0]:
                    via.drill = self.rules.MIN_VIA_DRILL
                    return True
        return False

    def _fix_via_pad(self, issue: Issue, board: PCBBoard) -> bool:
        """修复过孔焊盘"""
        if issue.related_ids:
            for via in board.vias:
                if via.id == issue.related_ids[0]:
                    via.diameter = self.rules.MIN_VIA_PAD
                    return True
        return False

    def _fix_copper_to_edge(self, issue: Issue, board: PCBBoard) -> bool:
        """修复铜到边缘距离"""
        if issue.location:
            # 移动走线
            for track in board.tracks:
                for i, point in enumerate(track.points):
                    if (
                        abs(point.x - issue.location.x) < 1
                        and abs(point.y - issue.location.y) < 1
                    ):
                        # 移动到安全距离
                        if point.x < self.rules.MIN_COPPER_TO_EDGE:
                            point.x = self.rules.MIN_COPPER_TO_EDGE + 1
                        elif point.x > board.width - self.rules.MIN_COPPER_TO_EDGE:
                            point.x = board.width - self.rules.MIN_COPPER_TO_EDGE - 1
                        if point.y < self.rules.MIN_COPPER_TO_EDGE:
                            point.y = self.rules.MIN_COPPER_TO_EDGE + 1
                        elif point.y > board.height - self.rules.MIN_COPPER_TO_EDGE:
                            point.y = board.height - self.rules.MIN_COPPER_TO_EDGE - 1
                        return True
        return False

    def _fix_annular_ring(self, issue: Issue, board: PCBBoard) -> bool:
        """修复焊环问题"""
        if issue.related_ids:
            for via in board.vias:
                if via.id == issue.related_ids[0]:
                    # 增大过孔尺寸
                    new_drill = self.rules.MIN_VIA_DRILL
                    new_pad = new_drill + 2 * self.rules.MIN_ANNULAR_RING
                    via.drill = new_drill
                    via.diameter = new_pad
                    return True
        return False

    def _fix_track_spacing(self, issue: Issue, board: PCBBoard) -> bool:
        """修复走线间距"""
        # 简化：移动其中一条走线
        if len(issue.related_ids) >= 2:
            track_id = issue.related_ids[1]
            for track in board.tracks:
                if track.id == track_id:
                    # 偏移走线
                    for point in track.points:
                        point.y += 1  # 向外偏移
                    return True
        return False

    def _remove_dangling_track(self, issue: Issue, board: PCBBoard) -> bool:
        """删除悬空走线"""
        if issue.related_ids:
            track_id = issue.related_ids[0]
            board.tracks = [t for t in board.tracks if t.id != track_id]
            return True
        return False

    def _fix_differential_length(self, issue: Issue, board: PCBBoard) -> bool:
        """修复差分对长度 - 暂时禁用，因为会创建更多问题"""
        # 差分对长度补偿需要更复杂的算法，目前禁用
        # 因为添加蛇形走线会导致新的走线间距问题
        return False

    def _fix_rf_trace_width(self, issue: Issue, board: PCBBoard) -> bool:
        """修复 RF 走线宽度"""
        track_id = issue.related_ids[0] if issue.related_ids else None
        if not track_id:
            return False

        for track in board.tracks:
            if track.id == track_id:
                # RF 走线需要更宽以减少损耗
                MIN_RF_WIDTH = 0.2
                if track.width < MIN_RF_WIDTH:
                    track.width = MIN_RF_WIDTH
                    return True

        return False

    def _fix_antenna_metal_distance(self, issue: Issue, board: PCBBoard) -> bool:
        """修复天线与金属元件距离"""
        if len(issue.related_ids) >= 2:
            antenna_id = issue.related_ids[0]
            metal_id = issue.related_ids[1]

            antenna = None
            metal = None

            for comp in board.components:
                if comp.id == antenna_id:
                    antenna = comp
                elif comp.id == metal_id:
                    metal = comp

            if not antenna or not metal:
                return False

            # 目标距离
            MIN_ANTENNA_METAL_DISTANCE = 10.0

            # 计算当前距离
            current_dist = antenna.position.distance_to(metal.position)

            if current_dist >= MIN_ANTENNA_METAL_DISTANCE:
                return True  # 已经足够远

            # 移动天线到更远的位置
            dx = antenna.position.x - metal.position.x
            dy = antenna.position.y - metal.position.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                # 移动到目标距离
                ratio = MIN_ANTENNA_METAL_DISTANCE / distance
                antenna.position.x = metal.position.x + dx * ratio
                antenna.position.y = metal.position.y + dy * ratio

                # 确保在板内
                antenna.position.x = max(2, min(board.width - 2, antenna.position.x))
                antenna.position.y = max(2, min(board.height - 2, antenna.position.y))
                return True

        return False

    def _remove_isolated_copper(self, issue: Issue, board: PCBBoard) -> bool:
        """删除孤岛铜"""
        if issue.related_ids:
            zone_id = issue.related_ids[0]
            board.zones = [z for z in board.zones if z.id != zone_id]
            return True
        return False


class RalphLoopOptimizer:
    """Ralph Loop 迭代优化器"""

    def __init__(
        self,
        max_iterations: int = 20,
        rules: DesignRules = None,
        checker: PCBChecker = None,
    ):
        self.max_iterations = max_iterations
        self.rules = rules or DesignRules()
        self.checker = checker or PCBChecker(self.rules)
        self.auto_fixer = AutoFixer(self.rules)

    def optimize(
        self,
        board: PCBBoard,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> RalphLoopResult:
        """
        执行 Ralph Loop 迭代优化

        Args:
            board: PCB 板
            progress_callback: 进度回调 (current, total, message)

        Returns:
            RalphLoopResult: 迭代优化结果
        """
        # 深拷贝原始板
        working_board = copy.deepcopy(board)

        # 初始评估
        initial_result = self.checker.evaluate(working_board)
        initial_issues = initial_result.issues

        print(f"\n{'=' * 60}")
        print(f"Ralph Loop 迭代优化开始")
        print(f"{'=' * 60}")
        print(
            f"初始问题数: {len(initial_issues)} (错误: {initial_result.error_count}, 警告: {initial_result.warning_count})"
        )
        print(f"最大迭代次数: {self.max_iterations}")
        print(f"{'=' * 60}\n")

        iterations = []
        current_issues = initial_issues
        converged = False
        max_reached = False

        for iteration in range(1, self.max_iterations + 1):
            # 记录本次迭代前的问题
            issues_before = current_issues.copy()

            # 评估当前状态
            result_before = self.checker.evaluate(working_board)
            scores_before = result_before.scores

            # 尝试修复问题
            fixed_issues = []
            failed_fixes = []

            # 按严重程度排序，先修复错误，再修复警告
            sorted_issues = sorted(
                issues_before,
                key=lambda x: (0 if x.severity == Severity.ERROR else 1, x.type.value),
            )

            # 尝试修复每个问题
            for issue in sorted_issues:
                if issue.auto_fixable:
                    # 尝试修复
                    fixed = self.auto_fixer.fix_issue(issue, working_board)
                    if fixed:
                        fixed_issues.append(issue)

            # 重新评估
            result_after = self.checker.evaluate(working_board)
            issues_after = result_after.issues
            scores_after = result_after.scores

            # 分析本次迭代的变化
            before_ids = set(i.type.value + i.message[:30] for i in issues_before)
            after_ids = set(i.type.value + i.message[:30] for i in issues_after)

            new_ids = after_ids - before_ids
            fixed_ids = before_ids - after_ids

            new_issues = [
                i for i in issues_after if i.type.value + i.message[:30] in new_ids
            ]
            unchanged_issues = [
                i
                for i in issues_after
                if i.type.value + i.message[:30] in after_ids
                and i.type.value + i.message[:30] not in fixed_ids
            ]

            # 记录迭代结果
            iteration_result = IterationResult(
                iteration=iteration,
                board=copy.deepcopy(working_board),
                issues_before=issues_before,
                issues_after=issues_after,
                fixed_issues=fixed_issues,
                new_issues=new_issues,
                unchanged_issues=unchanged_issues,
                scores_before=scores_before,
                scores_after=scores_after,
                action_taken=f"修复了 {len(fixed_issues)} 个问题",
                success=len(fixed_issues) > 0,
            )
            iterations.append(iteration_result)

            # 打印迭代信息
            print(f"[迭代 {iteration:02d}/{self.max_iterations}]")
            print(f"  修复: {len(fixed_issues)} 个问题")
            print(f"  新增: {len(new_issues)} 个问题")
            print(
                f"  剩余: {len(issues_after)} 个问题 (错误: {result_after.error_count}, 警告: {result_after.warning_count})"
            )
            print(f"  评分: {scores_after.get('总体', 0):.1f}")
            print()

            # 调用进度回调
            if progress_callback:
                progress_callback(
                    iteration,
                    self.max_iterations,
                    f"迭代 {iteration}: 修复 {len(fixed_issues)} 个问题",
                )

            # 更新当前问题列表
            current_issues = issues_after

            # 检查是否收敛 (没有新问题，且没有可修复的问题)
            if len(new_issues) == 0 and len(fixed_issues) == 0:
                print(f"\n[OK] Converged! No new issues and no fixable issues\n")
                converged = True
                break

            # 检查是否完全无问题
            if len(issues_after) == 0:
                print(f"\n[OK] All issues fixed!\n")
                converged = True
                break

        # 检查是否达到最大迭代次数
        if len(iterations) >= self.max_iterations:
            max_reached = True
            print(f"\n[WARN] Reached max iterations {self.max_iterations}\n")

        # 生成改进摘要
        improvement = self._generate_improvement_summary(initial_issues, current_issues)

        # 最终评估
        final_result = self.checker.evaluate(working_board)

        return RalphLoopResult(
            initial_issues=initial_issues,
            final_issues=current_issues,
            iterations=iterations,
            total_iterations=len(iterations),
            converged=converged,
            max_iterations_reached=max_reached,
            final_scores=final_result.scores,
            improvement_summary=improvement,
        )

    def _generate_improvement_summary(
        self, initial_issues: List[Issue], final_issues: List[Issue]
    ) -> Dict[str, int]:
        """生成改进摘要"""
        initial_by_type = {}
        final_by_type = {}

        for issue in initial_issues:
            key = issue.category
            initial_by_type[key] = initial_by_type.get(key, 0) + 1

        for issue in final_issues:
            key = issue.category
            final_by_type[key] = final_by_type.get(key, 0) + 1

        summary = {}
        for category in set(list(initial_by_type.keys()) + list(final_by_type.keys())):
            initial_count = initial_by_type.get(category, 0)
            final_count = final_by_type.get(category, 0)
            summary[category] = initial_count - final_count

        return summary

    def print_result(self, result: RalphLoopResult):
        """打印结果"""
        print(f"\n{'=' * 60}")
        print(f"Ralph Loop 迭代优化完成")
        print(f"{'=' * 60}")
        print(f"总迭代次数: {result.total_iterations}")
        print(f"收敛: {'是' if result.converged else '否'}")
        print(f"达到最大迭代: {'是' if result.max_iterations_reached else '否'}")
        print(f"\n初始问题: {len(result.initial_issues)}")
        print(f"最终问题: {len(result.final_issues)}")

        if result.improvement_summary:
            print(f"\n改进摘要:")
            for category, count in result.improvement_summary.items():
                if count > 0:
                    print(f"  {category}: +{count}")
                elif count < 0:
                    print(f"  {category}: {count}")

        print(f"\n最终评分:")
        for key, value in result.final_scores.items():
            print(f"  {key}: {value:.1f}")

        if result.final_issues:
            print(f"\n剩余问题 ({len(result.final_issues)} 个):")
            for issue in result.final_issues[:10]:  # 只显示前10个
                print(f"  [{issue.severity.value.upper()}] {issue.message}")
            if len(result.final_issues) > 10:
                print(f"  ... 还有 {len(result.final_issues) - 10} 个问题")

        print(f"\n{'=' * 60}\n")
