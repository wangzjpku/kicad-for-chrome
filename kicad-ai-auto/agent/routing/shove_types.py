# -*- coding: utf-8 -*-
"""
Push-and-Shove 路由器数据结构

定义推挤布线算法所需的全部数据类型，包括：
- 碰撞检测与表示
- 推挤方向与策略
- 成本函数参数
- 推挤结果与统计
"""

import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set


class ShoveDirection(Enum):
    """推挤方向"""
    UP = "up"          # +Y 方向
    DOWN = "down"      # -Y 方向
    LEFT = "left"      # -X 方向
    RIGHT = "right"    # +X 方向
    CUSTOM = "custom"  # 自定义角度方向


class ConflictType(Enum):
    """碰撞类型"""
    PARALLEL = "parallel"          # 平行走线碰撞（侧向推挤）
    ENDPOINT = "endpoint"          # 端点碰撞
    T_JUNCTION = "t_junction"      # T型交叉
    CROSSING = "crossing"          # 正交穿越
    CORNER = "corner"              # 拐角处碰撞
    PAD_COLLISION = "pad_collision"  # 焊盘碰撞


class ShoveStrategy(Enum):
    """推挤策略"""
    SHOVE = "shove"              # 推挤现有走线
    WALKAROUND = "walkaround"    # 绕行避开
    RIPUP = "ripup"              # 拆除重布
    VIAS = "vias"                # 换层（加过孔）
    GIVE_UP = "give_up"          # 放弃


@dataclass
class ShoveConflict:
    """
    碰撞事件

    记录一条正在布的走线与一条已有走线之间的碰撞信息。
    """
    # 碰撞的主动线段（正在布的线）
    active_segment_start: Tuple[float, float]
    active_segment_end: Tuple[float, float]

    # 被碰撞的障碍线段
    obstacle_start: Tuple[float, float]
    obstacle_end: Tuple[float, float]
    obstacle_net: str = ""
    obstacle_priority: int = 0

    # 碰撞位置
    collision_point: Tuple[float, float] = (0.0, 0.0)

    # 碰撞类型
    conflict_type: ConflictType = ConflictType.PARALLEL

    # 推挤所需最小距离（mm）
    required_clearance: float = 0.2

    # 估算推挤距离（mm）
    shove_distance: float = 0.0

    @property
    def is_fixed(self) -> bool:
        """障碍物是否固定不可推挤"""
        return self.obstacle_priority >= 100

    @property
    def is_high_priority(self) -> bool:
        """障碍物是否高优先级（难以推挤）"""
        return self.obstacle_priority >= 50


@dataclass
class ShoveOptions:
    """
    推挤参数配置

    控制推挤行为的具体参数。
    """
    # 最大递归推挤深度（A推B，B推C...最多几层）
    max_shove_depth: int = 8

    # 最大推挤距离（mm），超过此距离放弃推挤
    max_shove_distance: float = 5.0

    # 最小推挤步进（mm）
    min_shove_step: float = 0.1

    # 推挤后最小间距（mm）
    post_shove_clearance: float = 0.2

    # 是否允许推挤不同网络的走线
    allow_cross_net_shove: bool = True

    # 是否允许级联推挤（推挤被推挤影响的走线）
    allow_cascade: bool = True

    # 推挤失败后是否尝试绕行
    fallback_to_walkaround: bool = True

    # 绕行失败后是否尝试拆除重布
    fallback_to_ripup: bool = False

    # 推挤后的线段是否保持正交（水平/垂直）
    force_orthogonal: bool = True

    # 推挤成本权重
    cost_per_mm: float = 1.0          # 每mm推挤距离成本
    cost_per_cascade: float = 5.0     # 每层级联成本
    cost_per_via: float = 10.0        # 每个过孔成本
    cost_per_cross_net: float = 3.0   # 跨网络推挤成本
    cost_drc_violation: float = 50.0  # DRC违规成本


@dataclass
class ShoveAction:
    """
    单个推挤动作

    记录对一条线段执行的具体推挤操作。
    """
    # 被推挤的原始线段
    original_start: Tuple[float, float]
    original_end: Tuple[float, float]
    original_layer: str = "F.Cu"
    original_net: str = ""

    # 推挤后的新位置
    new_start: Tuple[float, float] = (0.0, 0.0)
    new_end: Tuple[float, float] = (0.0, 0.0)

    # 推挤方向
    direction: ShoveDirection = ShoveDirection.CUSTOM

    # 推挤距离
    distance: float = 0.0

    # 推挤成本
    cost: float = 0.0

    # 是否导致DRC违规
    causes_drc: bool = False

    @property
    def displacement_x(self) -> float:
        """X方向位移"""
        return self.new_start[0] - self.original_start[0]

    @property
    def displacement_y(self) -> float:
        """Y方向位移"""
        return self.new_start[1] - self.original_start[1]


@dataclass
class CascadeEntry:
    """
    级联推挤记录

    记录一级推挤引发的连锁反应。
    """
    depth: int                          # 级联深度（1=直接碰撞，2=被推后碰撞...）
    trigger_action: ShoveAction         # 触发此级联的动作
    resulting_actions: List[ShoveAction] = field(default_factory=list)  # 此级联产生的动作
    total_cost: float = 0.0


@dataclass
class ShoveResult:
    """
    推挤操作的总结果

    包含完整的推挤执行结果和统计信息。
    """
    success: bool
    strategy_used: ShoveStrategy = ShoveStrategy.SHOVE

    # 直接推挤的动作
    actions: List[ShoveAction] = field(default_factory=list)

    # 级联推挤记录
    cascades: List[CascadeEntry] = field(default_factory=list)

    # 布线结果
    routed_segments: List[Dict] = field(default_factory=list)

    # 统计信息
    total_shoved_tracks: int = 0       # 被推挤的总走线数
    total_shove_distance: float = 0.0  # 总推挤距离
    max_cascade_depth: int = 0         # 最大级联深度
    total_cost: float = 0.0            # 总推挤成本
    drc_violations: int = 0            # 推挤后DRC违规数

    # 消息
    message: str = ""

    @property
    def has_cascades(self) -> bool:
        return len(self.cascades) > 0

    @property
    def cost_per_track(self) -> float:
        if self.total_shoved_tracks == 0:
            return 0.0
        return self.total_cost / self.total_shoved_tracks


@dataclass
class CostBreakdown:
    """
    成本分解

    详细展示推挤成本的组成部分，用于决策和调试。
    """
    distance_cost: float = 0.0         # 距离成本
    cascade_cost: float = 0.0          # 级联成本
    via_cost: float = 0.0              # 过孔成本
    cross_net_cost: float = 0.0        # 跨网络成本
    drc_penalty: float = 0.0           # DRC惩罚
    ortho_penalty: float = 0.0         # 非正交惩罚

    @property
    def total(self) -> float:
        return (self.distance_cost + self.cascade_cost +
                self.via_cost + self.cross_net_cost +
                self.drc_penalty + self.ortho_penalty)


@dataclass
class WalkaroundCandidate:
    """
    绕行候选方案

    当推挤不可行时，提供的绕行路径选项。
    """
    # 绕行路径点
    path_points: List[Tuple[float, float]] = field(default_factory=list)

    # 绕行额外长度
    extra_length: float = 0.0

    # 绕行需要的过孔数
    vias_needed: int = 0

    # 绕行成本
    cost: float = 0.0

    # 绕行后是否产生DRC问题
    has_drc_risk: bool = False

    @property
    def is_better_than_shove(self) -> bool:
        """判断绕行是否比推挤更划算（需要在上下文中比较）"""
        return not self.has_drc_risk and self.vias_needed <= 1


@dataclass
class ShoveStatistics:
    """
    推挤布线统计信息

    用于性能监控和算法调优。
    """
    total_routes_attempted: int = 0
    shove_successes: int = 0
    walkaround_successes: int = 0
    ripup_successes: int = 0
    failures: int = 0

    total_tracks_shoved: int = 0
    total_cascade_depth: int = 0
    total_shove_distance: float = 0.0

    avg_shove_cost: float = 0.0
    max_shove_depth_seen: int = 0

    @property
    def shove_rate(self) -> float:
        """推挤成功率"""
        if self.total_routes_attempted == 0:
            return 0.0
        return self.shove_successes / self.total_routes_attempted

    @property
    def total_success_rate(self) -> float:
        """总成功率（推挤+绕行+拆除重布）"""
        if self.total_routes_attempted == 0:
            return 0.0
        successes = self.shove_successes + self.walkaround_successes + self.ripup_successes
        return successes / self.total_routes_attempted
