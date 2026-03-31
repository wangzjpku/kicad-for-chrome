# -*- coding: utf-8 -*-
"""
Rip-up & Retry 路由器

当标准布线（A* + 推挤）无法完成所有网络时，
尝试拆除已布网络并重新布线，以提高总布通率。

策略：
1. 先用标准方法布所有网络
2. 收集失败的网络
3. 找到阻碍失败网络的已布网络
4. 拆除阻碍网络
5. 先布失败网络，再重新布拆除的网络
6. 最多重试 N 轮
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set

from routing.push_router import PushRouter, Segment, Point, Obstacle, RouteStatus
from routing.shove_types import ShoveOptions, ShoveStatistics

logger = logging.getLogger(__name__)


@dataclass
class NetRoute:
    """一条网络的布线信息"""
    net_name: str
    start: Tuple[float, float]
    end: Tuple[float, float]
    layer: str = "F.Cu"
    segments: List[Segment] = field(default_factory=list)
    success: bool = False
    priority: int = 0  # 布线优先级（低的先布）


@dataclass
class RipupResult:
    """Rip-up & Retry 总结果"""
    success: bool
    routed_nets: Dict[str, List[Segment]] = field(default_factory=dict)
    failed_nets: List[str] = field(default_factory=list)
    total_attempts: int = 0
    ripup_count: int = 0
    statistics: ShoveStatistics = field(default_factory=ShoveStatistics)
    message: str = ""


class RipupRouter:
    """
    拆除重布路由器

    使用 PushRouter 进行实际布线，并在失败时
    尝试拆除已布网络来提高布通率。
    """

    def __init__(
        self,
        grid_size: float = 0.25,
        trace_width: float = 0.25,
        clearance: float = 0.2,
        max_ripup_rounds: int = 3,
        shove_options: Optional[ShoveOptions] = None,
    ):
        self.grid_size = grid_size
        self.trace_width = trace_width
        self.clearance = clearance
        self.max_ripup_rounds = max_ripup_rounds
        self.shove_options = shove_options or ShoveOptions()

    def route_all(
        self,
        nets: List[NetRoute],
        existing_obstacles: Optional[List[Segment]] = None,
    ) -> RipupResult:
        """
        布线所有网络，失败时执行rip-up & retry。

        Args:
            nets: 待布线网络列表
            existing_obstacles: 已有的固定障碍（如焊盘、板框等）

        Returns:
            RipupResult: 完整布线结果
        """
        stats = ShoveStatistics()
        stats.total_routes_attempted = len(nets)

        # 初始化路由器
        router = self._create_router(existing_obstacles)

        # 第1轮：标准布线
        routed, failed = self._route_round(router, nets, stats)
        logger.info(f"第1轮: 布通 {len(routed)}/{len(nets)}, 失败 {len(failed)}")

        if not failed:
            return RipupResult(
                success=True,
                routed_nets={name: segs for name, segs in routed.items()},
                failed_nets=[],
                total_attempts=len(nets),
                statistics=stats,
                message=f"全部 {len(nets)} 条网络布线成功",
            )

        # 第2~N轮：rip-up & retry
        total_ripups = 0
        for round_num in range(2, self.max_ripup_rounds + 2):
            if not failed:
                break

            # 找到阻碍失败网络的已布网络
            blocking = self._find_blocking_nets(router, failed, routed)

            if not blocking:
                logger.info(f"无法找到可拆除的网络，停止重试")
                break

            # 拆除阻碍网络（按优先级从高到低拆，最多拆3条）
            to_ripup = sorted(blocking, key=lambda n: routed[n][0].width if routed[n] else 0, reverse=True)
            to_ripup = to_ripup[:3]

            ripped_nets = []
            for net_name in to_ripup:
                if net_name in routed:
                    # 移除已布线段
                    for seg in routed[net_name]:
                        router.obstacles = [
                            obs for obs in router.obstacles
                            if not self._same_segment(obs.segment, seg)
                        ]
                    ripped_nets.append(net_name)
                    del routed[net_name]
                    total_ripups += 1
                    logger.debug(f"拆除网络: {net_name}")

            # 重新布线：先布失败网络，再布被拆除的网络
            retry_nets = failed + [
                NetRoute(
                    net_name=name,
                    start=(routed.get(name, [Segment(Point(0, 0), Point(0, 0))])[0].start.x,
                           routed.get(name, [Segment(Point(0, 0), Point(0, 0))])[0].start.y),
                    end=(routed.get(name, [Segment(Point(0, 0), Point(0, 0))])[0].end.x,
                         routed.get(name, [Segment(Point(0, 0), Point(0, 0))])[0].end.y),
                )
                for name in ripped_nets
            ]

            # 这里需要原始net数据来重建
            net_lookup = {n.net_name: n for n in nets}
            retry_net_objects = []
            for net_name in failed:
                if net_name in net_lookup:
                    retry_net_objects.append(net_lookup[net_name])
            for net_name in ripped_nets:
                if net_name in net_lookup:
                    retry_net_objects.append(net_lookup[net_name])

            new_routed, new_failed = self._route_round(router, retry_net_objects, stats)
            routed.update(new_routed)
            failed = new_failed + [
                n for n in ripped_nets if n not in new_routed and n not in new_failed
            ]

            logger.info(f"第{round_num}轮: 布通 +{len(new_routed)}, 仍失败 {len(failed)}, 拆除 {len(ripped_nets)}")

        # 计算统计
        stats.ripup_successes = len(routed) - (len(nets) - len(failed) - stats.total_routes_attempted)
        stats.failures = len(failed)

        return RipupResult(
            success=len(failed) == 0,
            routed_nets={name: segs for name, segs in routed.items()},
            failed_nets=failed,
            total_attempts=len(nets),
            ripup_count=total_ripups,
            statistics=stats,
            message=f"布通 {len(routed)}/{len(nets)}，拆除 {total_ripups} 条网络",
        )

    def _create_router(
        self,
        existing_obstacles: Optional[List[Segment]] = None,
    ) -> PushRouter:
        """创建新的PushRouter实例"""
        router = PushRouter(
            grid_size=self.grid_size,
            trace_width=self.trace_width,
            clearance=self.clearance,
        )

        if existing_obstacles:
            for seg in existing_obstacles:
                router.add_obstacle(Obstacle(segment=seg, priority=100))

        return router

    def _route_round(
        self,
        router: PushRouter,
        nets: List[NetRoute],
        stats: ShoveStatistics,
    ) -> Tuple[Dict[str, List[Segment]], List[str]]:
        """
        执行一轮布线。

        Returns:
            (布通的网络{名字: 线段}, 失败的网络名字列表)
        """
        routed: Dict[str, List[Segment]] = {}
        failed: List[str] = []

        # 按优先级排序（电源和高速优先）
        sorted_nets = sorted(nets, key=lambda n: n.priority)

        for net in sorted_nets:
            result = router.route(
                start=net.start,
                end=net.end,
                start_layer=net.layer,
                end_layer=net.layer,
                net_name=net.net_name,
                shove_options=self.shove_options,
            )

            if result.success:
                routed[net.net_name] = result.routed_segments
                stats.shove_successes += 1
            else:
                failed.append(net.net_name)
                stats.failures += 1

        return routed, failed

    def _find_blocking_nets(
        self,
        router: PushRouter,
        failed_net_names: List[str],
        routed: Dict[str, List[Segment]],
    ) -> List[str]:
        """
        找到阻碍失败网络的已布网络。

        策略：对每条失败网络，找到与A*理想路径相交的已布网络。
        """
        blocking: Set[str] = set()

        # 检查路由器中非固定障碍的来源
        for obs in router.obstacles:
            if obs.priority >= 100:
                continue

            # 尝试匹配到已布网络
            for net_name, segments in routed.items():
                for seg in segments:
                    if self._same_segment(obs.segment, seg):
                        blocking.add(net_name)
                        break

        # 简化：返回所有非固定已布网络作为候选
        return list(blocking)

    def _same_segment(self, seg1: Segment, seg2: Segment) -> bool:
        """判断两条线段是否相同（考虑方向无关）"""
        tol = 0.01
        return (
            abs(seg1.start.x - seg2.start.x) < tol
            and abs(seg1.start.y - seg2.start.y) < tol
            and abs(seg1.end.x - seg2.end.x) < tol
            and abs(seg1.end.y - seg2.end.y) < tol
        ) or (
            abs(seg1.start.x - seg2.end.x) < tol
            and abs(seg1.start.y - seg2.end.y) < tol
            and abs(seg1.end.x - seg2.start.x) < tol
            and abs(seg1.end.y - seg2.start.y) < tol
        )
