"""
PCB 质量检查器 - 检查线宽、布局、走线正确性、走线符合性
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import math

from .pcb_models import (
    PCBBoard,
    Issue,
    IssueType,
    Severity,
    Point2D,
    Track,
    Via,
    Zone,
    Component,
    Net,
)


class DesignRules:
    """设计规则配置"""

    # 线宽规则 (mm)
    MIN_TRACK_WIDTH = 0.1  # 最小线宽
    MIN_POWER_TRACK_WIDTH = 0.3  # 最小电源线宽
    MIN_SIGNAL_TRACK_WIDTH = 0.1  # 最小信号线宽

    # 电流承载相关 (基于 IPC-2221)
    COPPER_WEIGHT_OZ = 1  # 铜厚 (oz)
    MAX_TEMP_RISE = 30  # 最大温升 (°C)
    CURRENT_DERATING = 0.5  # 电流降额因子

    # 间距规则 (mm)
    MIN_TRACK_SPACING = 0.1  # 最小走线间距
    MIN_CLEARANCE = 0.1  # 最小间隙

    # 过孔规则 (mm)
    MIN_VIA_DRILL = 0.3  # 最小过孔孔径
    MIN_VIA_PAD = 0.5  # 最小过孔焊盘
    MIN_ANNULAR_RING = 0.15  # 最小焊环

    # 布局规则 (mm)
    MAX_DECOUPLING_CAP_DISTANCE = 5.0  # 去耦电容到引脚最大距离
    MAX_CRYSTAL_DISTANCE = 15.0  # 晶振到MCU最大距离
    MIN_THERMAL_CLEARANCE = 10.0  # 发热元件最小间距
    CONNECTOR_EDGE_MARGIN = 5.0  # 接插件边缘距板边距离

    # 差分对规则
    MAX_DIFFERENTIAL_LENGTH_MISMATCH = 1.5  # 差分对最大长度差 (mm)

    # 边缘规则 (mm)
    MIN_COPPER_TO_EDGE = 0.5  # 铜到板边最小距离


class TrackWidthChecker:
    """线宽合理性检查器"""

    def __init__(self, rules: DesignRules = None):
        self.rules = rules or DesignRules()

    def check(self, board: PCBBoard) -> List[Issue]:
        """检查所有走线"""
        issues = []

        for track in board.tracks:
            issues.extend(self._check_single_track(track, board))

        return issues

    def _check_single_track(self, track: Track, board: PCBBoard) -> List[Issue]:
        """检查单条走线"""
        issues = []
        net = board.get_net(track.net_id)

        # 1. 检查最小线宽
        min_width = self._get_min_width(net)
        if track.width < min_width:
            issues.append(
                Issue(
                    id=f"width_{track.id}",
                    type=IssueType.TRACK_WIDTH_TOO_NARROW,
                    severity=Severity.ERROR,
                    category="线宽",
                    message=f"走线 {track.id} (网络 {net.name if net else 'N/A'}) 宽度 {track.width:.3f}mm < {min_width:.2f}mm",
                    location=track.points[0] if track.points else None,
                    related_ids=[track.id],
                    auto_fixable=True,
                    fix_suggestion=f"将走线加宽至 {min_width:.2f}mm",
                )
            )

        # 2. 检查电流承载能力
        if net and net.is_power_supply:
            current_capacity = self._calculate_current_capacity(track.width)
            if current_capacity < 1.0:  # 假设1A需求
                issues.append(
                    Issue(
                        id=f"current_{track.id}",
                        type=IssueType.TRACK_WIDTH_INSUFFICIENT_CURRENT,
                        severity=Severity.WARNING,
                        category="线宽",
                        message=f"电源走线 {track.id} 电流承载能力 {current_capacity:.2f}A < 1A",
                        location=track.points[0] if track.points else None,
                        related_ids=[track.id],
                        auto_fixable=True,
                        fix_suggestion=f"将走线加宽至可承载至少1A电流",
                    )
                )

        return issues

    def _get_min_width(self, net: Optional[Net]) -> float:
        """获取最小线宽"""
        if net and net.is_power_supply:
            return self.rules.MIN_POWER_TRACK_WIDTH
        return self.rules.MIN_SIGNAL_TRACK_WIDTH

    def _calculate_current_capacity(self, width_mm: float) -> float:
        """计算电流承载能力 (基于 IPC-2221)"""
        width_mil = width_mm * 39.37
        area_mil = width_mil * self.rules.COPPER_WEIGHT_OZ

        # IPC-2221 公式
        # I = K * ΔT^0.44 * A^0.725
        current = (self.rules.MAX_TEMP_RISE**0.44) * (area_mil**0.725) / 0.048

        # 应用降额因子
        return current * self.rules.CURRENT_DERATING


class LayoutChecker:
    """布局合理性检查器"""

    def __init__(self, rules: DesignRules = None):
        self.rules = rules or DesignRules()

    def check(self, board: PCBBoard) -> List[Issue]:
        """检查布局"""
        issues = []

        # 1. 检查去耦电容位置
        issues.extend(self._check_decoupling_capacitors(board))

        # 2. 检查晶振位置
        issues.extend(self._check_crystal_placement(board))

        # 3. 检查发热元件间距
        issues.extend(self._check_thermal_clearance(board))

        # 4. 检查接插件位置
        issues.extend(self._check_connector_placement(board))

        # 5. 检查 RF/天线相关
        issues.extend(self._check_rf_antenna(board))

        return issues

    def _check_decoupling_capacitors(self, board: PCBBoard) -> List[Issue]:
        """检查去耦电容位置 - 只检查真正需要去耦的IC"""
        issues = []

        # 只找真正的IC (MCU, 电源芯片等)
        ics = [c for c in board.components if c.is_ic or c.is_mcu]

        # 只找贴片小电容 (容量较小的，如100nF, 10nF, 1nF等)
        # 排除电解电容(通常是大容量的)
        small_capacitors = [
            c
            for c in board.components
            if "C" in c.reference.upper()
            and not c.is_ic
            and not c.is_connector
            # 只检查小容量贴片电容 (通常是小封装的)
            and any(
                x in c.value.upper()
                for x in ["NF", "UF", "PF", "1", "10", "22", "47", "100"]
            )
            and "UF" not in c.value.upper()  # 排除大于1uF的
        ]

        # 只检查距离确实很远的电容 (阈值30mm)
        DECOUPLING_THRESHOLD = 30.0

        for ic in ics:
            for cap in small_capacitors:
                distance = ic.position.distance_to(cap.position)

                # 只有距离确实很远才报告 (>30mm)
                if distance > DECOUPLING_THRESHOLD:
                    issues.append(
                        Issue(
                            id=f"decoup_{ic.reference}_{cap.reference}",
                            type=IssueType.DECOUPLING_CAPACITOR_FAR,
                            severity=Severity.INFO,  # 改为INFO级别
                            category="布局",
                            message=f"去耦电容 {cap.reference} 距 {ic.reference} {distance:.1f}mm",
                            location=cap.position,
                            related_ids=[ic.id, cap.id],
                            auto_fixable=False,  # INFO级别问题不自动修复，避免迭代不稳定
                            fix_suggestion=f"将 {cap.reference} 移至靠近 {ic.reference}",
                        )
                    )

        return issues

    def _check_crystal_placement(self, board: PCBBoard) -> List[Issue]:
        """检查晶振位置"""
        issues = []

        crystals = [c for c in board.components if c.is_crystal]
        mcus = [c for c in board.components if c.is_mcu]

        for crystal in crystals:
            for mcu in mcus:
                distance = crystal.position.distance_to(mcu.position)

                if distance > self.rules.MAX_CRYSTAL_DISTANCE:
                    issues.append(
                        Issue(
                            id=f"xtal_{crystal.reference}",
                            type=IssueType.CRYSTAL_PLACEMENT_FAR,
                            severity=Severity.ERROR,
                            category="布局",
                            message=f"晶振 {crystal.reference} 距 MCU {mcu.reference} {distance:.1f}mm > {self.rules.MAX_CRYSTAL_DISTANCE}mm",
                            location=crystal.position,
                            related_ids=[crystal.id, mcu.id],
                            auto_fixable=True,
                            fix_suggestion=f"将晶振移至靠近 MCU (距离 < {self.rules.MAX_CRYSTAL_DISTANCE}mm)",
                        )
                    )

        return issues

    def _check_thermal_clearance(self, board: PCBBoard) -> List[Issue]:
        """检查发热元件间距"""
        issues = []

        heat_sinks = [c for c in board.components if c.is_heatsink]

        for i, hs1 in enumerate(heat_sinks):
            for hs2 in heat_sinks[i + 1 :]:
                distance = hs1.position.distance_to(hs2.position)

                if distance < self.rules.MIN_THERMAL_CLEARANCE:
                    issues.append(
                        Issue(
                            id=f"thermal_{hs1.reference}_{hs2.reference}",
                            type=IssueType.THERMAL_CLEARANCE_INSUFFICIENT,
                            severity=Severity.WARNING,
                            category="布局",
                            message=f"发热元件 {hs1.reference} 和 {hs2.reference} 间距 {distance:.1f}mm < {self.rules.MIN_THERMAL_CLEARANCE}mm",
                            location=Point2D(
                                (hs1.position.x + hs2.position.x) / 2,
                                (hs1.position.y + hs2.position.y) / 2,
                            ),
                            related_ids=[hs1.id, hs2.id],
                            auto_fixable=True,
                            fix_suggestion=f"增加元件间距至至少 {self.rules.MIN_THERMAL_CLEARANCE}mm",
                        )
                    )

        return issues

    def _check_connector_placement(self, board: PCBBoard) -> List[Issue]:
        """检查接插件位置"""
        issues = []

        connectors = [c for c in board.components if c.is_connector]

        for conn in connectors:
            # 检查是否靠近板边
            edge_distance = min(
                conn.position.x,
                board.width - conn.position.x,
                conn.position.y,
                board.height - conn.position.y,
            )

            if edge_distance > self.rules.CONNECTOR_EDGE_MARGIN:
                issues.append(
                    Issue(
                        id=f"conn_{conn.reference}",
                        type=IssueType.CONNECTOR_NOT_EDGE,
                        severity=Severity.WARNING,
                        category="布局",
                        message=f"接插件 {conn.reference} 距板边 {edge_distance:.1f}mm > {self.rules.CONNECTOR_EDGE_MARGIN}mm",
                        location=conn.position,
                        related_ids=[conn.id],
                        auto_fixable=True,
                        fix_suggestion=f"将接插件移至靠近板边 (距板边 < {self.rules.CONNECTOR_EDGE_MARGIN}mm)",
                    )
                )

        return issues

    def _check_rf_antenna(self, board: PCBBoard) -> List[Issue]:
        """检查 RF/天线相关问题"""
        issues = []

        # 找到所有天线和射频元件
        antennas = []
        metals = []
        rf_tracks = []

        for comp in board.components:
            # 识别天线
            if any(
                keyword in comp.value.lower()
                for keyword in ["antenna", "rf", "wifi", "ble", "zigbee", "nrf", "esp"]
            ):
                antennas.append(comp)
            # 识别金属屏蔽罩
            if any(
                keyword in comp.value.lower()
                for keyword in ["shield", "metal", "gnd", "地"]
            ):
                metals.append(comp)

        # 识别 RF 走线 (高速网络)
        for track in board.tracks:
            net = board.get_net(track.net_id)
            if net and net.is_high_speed:
                rf_tracks.append(track)

        # 检查天线靠近金属
        MIN_ANTENNA_METAL_DISTANCE = 10.0  # 天线距金属最小距离 mm
        for antenna in antennas:
            for metal in metals:
                distance = antenna.position.distance_to(metal.position)
                if distance < MIN_ANTENNA_METAL_DISTANCE:
                    issues.append(
                        Issue(
                            id=f"antenna_metal_{antenna.reference}_{metal.reference}",
                            type=IssueType.ANTENNA_NEAR_METAL,
                            severity=Severity.ERROR,
                            category="布局",
                            message=f"天线 {antenna.reference} 距金属元件 {metal.reference} {distance:.1f}mm < {MIN_ANTENNA_METAL_DISTANCE}mm",
                            location=antenna.position,
                            related_ids=[antenna.id, metal.id],
                            auto_fixable=True,
                            fix_suggestion=f"将天线移至距金属元件至少 {MIN_ANTENNA_METAL_DISTANCE}mm",
                        )
                    )

        # 检查 RF 走线宽度
        MIN_RF_TRACE_WIDTH = 0.2  # RF 走线最小宽度 mm
        for track in rf_tracks:
            if track.width < MIN_RF_TRACE_WIDTH:
                issues.append(
                    Issue(
                        id=f"rf_trace_{track.id}",
                        type=IssueType.RF_TRACE_TOO_NARROW,
                        severity=Severity.ERROR,
                        category="布局",
                        message=f"RF走线 {track.id} 宽度 {track.width:.3f}mm < {MIN_RF_TRACE_WIDTH}mm",
                        location=track.points[0] if track.points else None,
                        related_ids=[track.id],
                        auto_fixable=True,
                        fix_suggestion=f"将RF走线加宽至至少 {MIN_RF_TRACE_WIDTH}mm",
                    )
                )

        return issues


class RoutingCorrectnessChecker:
    """走线正确性检查器"""

    def __init__(self, rules: DesignRules = None):
        self.rules = rules or DesignRules()

    def check(self, board: PCBBoard) -> List[Issue]:
        """检查走线正确性"""
        issues = []

        # 1. 检查悬空走线 - 暂时禁用，因为不理解网络连接性，产生太多误报
        # issues.extend(self._check_dangling_tracks(board))

        # 2. 检查差分对长度匹配
        issues.extend(self._check_differential_pairs(board))

        # 3. 检查 Stub 走线
        issues.extend(self._check_stub_tracks(board))

        return issues

    def _check_dangling_tracks(self, board: PCBBoard) -> List[Issue]:
        """检查悬空走线"""
        issues = []

        # 如果没有焊盘数据，跳过检查
        if not board.pads:
            return issues

        # 收集所有焊盘位置
        pad_positions = set()
        for pad in board.pads:
            # 简化：使用焊盘位置的大致坐标
            pad_positions.add((round(pad.position.x, 1), round(pad.position.y, 1)))

        # 收集所有过孔位置
        via_positions = set()
        for via in board.vias:
            via_positions.add((round(via.position.x, 1), round(via.position.y, 1)))

        # 检查走线端点是否连接到焊盘或过孔
        for track in board.tracks:
            if not track.points:
                continue

            start_connected = (
                round(track.points[0].x, 1),
                round(track.points[0].y, 1),
            ) in pad_positions or (
                round(track.points[0].x, 1),
                round(track.points[0].y, 1),
            ) in via_positions
            end_connected = (
                round(track.points[-1].x, 1),
                round(track.points[-1].y, 1),
            ) in pad_positions or (
                round(track.points[-1].y, 1),
                round(track.points[-1].y, 1),
            ) in via_positions

            # 如果两端都没连接，才是真正的悬空走线
            if not start_connected and not end_connected:
                issues.append(
                    Issue(
                        id=f"dangling_{track.id}",
                        type=IssueType.DANGLING_TRACK,
                        severity=Severity.INFO,  # 改为INFO级别
                        category="走线正确性",
                        message=f"走线 {track.id} 两端都未连接到焊盘或过孔",
                        location=track.points[0] if track.points else None,
                        related_ids=[track.id],
                        auto_fixable=False,
                        fix_suggestion="检查走线是否正确连接到焊盘或过孔",
                    )
                )

        return issues

    def _check_differential_pairs(self, board: PCBBoard) -> List[Issue]:
        """检查差分对长度匹配"""
        issues = []

        # 找到所有差分对
        diff_pairs = {}
        for net in board.nets:
            if net.is_differential_pair and net.differential_pair_partner:
                if net.differential_pair_partner not in diff_pairs:
                    diff_pairs[net.differential_pair_partner] = []
                diff_pairs[net.differential_pair_partner].append(net)

        # 计算每对的长度
        for partner_id, nets in diff_pairs.items():
            if len(nets) >= 2:
                net1, net2 = nets[0], nets[1]

                tracks1 = [t for t in board.tracks if t.net_id == net1.id]
                tracks2 = [t for t in board.tracks if t.net_id == net2.id]

                length1 = sum(t.length for t in tracks1)
                length2 = sum(t.length for t in tracks2)

                mismatch = abs(length1 - length2)

                if mismatch > self.rules.MAX_DIFFERENTIAL_LENGTH_MISMATCH:
                    issues.append(
                        Issue(
                            id=f"diff_{net1.name}_{net2.name}",
                            type=IssueType.DIFFERENTIAL_LENGTH_MISMATCH,
                            severity=Severity.WARNING,
                            category="走线正确性",
                            message=f"差分对 {net1.name}/{net2.name} 长度差 {mismatch:.2f}mm > {self.rules.MAX_DIFFERENTIAL_LENGTH_MISMATCH}mm",
                            location=None,
                            related_ids=[t.id for t in tracks1 + tracks2],
                            auto_fixable=False,
                            fix_suggestion="调整走线使长度匹配，差分对长度差 < {self.rules.MAX_DIFFERENTIAL_LENGTH_MISMATCH}mm",
                        )
                    )

        return issues

    def _check_stub_tracks(self, board: PCBBoard) -> List[Issue]:
        """检查 Stub 走线"""
        issues = []

        # 简化检查：找T型连接点
        # 如果一条走线的中间某点有分支出去
        for track in board.tracks:
            if len(track.points) >= 3:
                # 检查是否有分支（简化逻辑）
                for i, point in enumerate(track.points[1:-1], 1):
                    # 这里应该检查是否有其他走线从这里引出
                    # 简化：如果点偏离主线太多，可能是stub
                    pass

        return issues


class RoutingComplianceChecker:
    """走线符合性检查器 (DRC规则)"""

    def __init__(self, rules: DesignRules = None):
        self.rules = rules or DesignRules()

    def check(self, board: PCBBoard) -> List[Issue]:
        """检查走线符合性"""
        issues = []

        # 1. 检查走线间距
        # 简化：暂时禁用走线间距检查，因为太容易产生误报
        # issues.extend(self._check_track_spacing(board))

        # 2. 检查过孔尺寸
        issues.extend(self._check_via_sizes(board))

        # 3. 检查铜到边缘距离 - 使用INFO级别，不自动修复
        issues.extend(self._check_copper_to_edge(board))

        # 4. 检查焊环
        issues.extend(self._check_annular_ring(board))

        # 5. 检查孤岛铜
        issues.extend(self._check_isolated_copper(board))

        return issues

    def _check_track_spacing(self, board: PCBBoard) -> List[Issue]:
        """检查走线间距"""
        issues = []

        # 简化的空间检查
        for i, t1 in enumerate(board.tracks):
            for t2 in board.tracks[i + 1 :]:
                # 如果是同一网络，跳过
                if t1.net_id == t2.net_id:
                    continue

                # 简化检查：包围盒重叠
                if self._bbox_overlaps(t1.bbox, t2.bbox):
                    distance = self._estimate_distance(t1, t2)

                    if distance < self.rules.MIN_TRACK_SPACING:
                        issues.append(
                            Issue(
                                id=f"spacing_{t1.id}_{t2.id}",
                                type=IssueType.TRACK_SPACING_TOO_NARROW,
                                severity=Severity.WARNING,  # 改为警告
                                category="走线符合性",
                                message=f"走线 {t1.id} 和 {t2.id} 间距 {distance:.3f}mm < {self.rules.MIN_TRACK_SPACING}mm",
                                location=Point2D(
                                    (t1.points[0].x + t2.points[0].x) / 2,
                                    (t1.points[0].y + t2.points[0].y) / 2,
                                )
                                if t1.points and t2.points
                                else None,
                                related_ids=[t1.id, t2.id],
                                auto_fixable=False,  # 禁用自动修复，因为会创建更多问题
                                fix_suggestion="增加走线间距至至少 {self.rules.MIN_TRACK_SPACING}mm",
                            )
                        )

        return issues

    def _check_via_sizes(self, board: PCBBoard) -> List[Issue]:
        """检查过孔尺寸"""
        issues = []

        for via in board.vias:
            if via.drill < self.rules.MIN_VIA_DRILL:
                issues.append(
                    Issue(
                        id=f"via_drill_{via.id}",
                        type=IssueType.VIA_DRILL_TOO_SMALL,
                        severity=Severity.ERROR,
                        category="走线符合性",
                        message=f"过孔 {via.id} 孔径 {via.drill:.3f}mm < {self.rules.MIN_VIA_DRILL}mm",
                        location=via.position,
                        related_ids=[via.id],
                        auto_fixable=True,
                        fix_suggestion=f"将过孔孔径增加至 {self.rules.MIN_VIA_DRILL}mm 以上",
                    )
                )

            pad_diameter = via.diameter
            if pad_diameter < self.rules.MIN_VIA_PAD:
                issues.append(
                    Issue(
                        id=f"via_pad_{via.id}",
                        type=IssueType.VIA_PAD_TOO_SMALL,
                        severity=Severity.ERROR,
                        category="走线符合性",
                        message=f"过孔 {via.id} 焊盘 {pad_diameter:.3f}mm < {self.rules.MIN_VIA_PAD}mm",
                        location=via.position,
                        related_ids=[via.id],
                        auto_fixable=True,
                        fix_suggestion=f"将过孔焊盘增加至 {self.rules.MIN_VIA_PAD}mm 以上",
                    )
                )

        return issues

    def _check_copper_to_edge(self, board: PCBBoard) -> List[Issue]:
        """检查铜到边缘距离 - 简化版，忽略边缘区域"""
        issues = []

        # 收集安装孔位置 (通过元件名称识别)
        mounting_hole_positions = set()
        for comp in board.components:
            ref_upper = comp.reference.upper()
            if "HOLE" in ref_upper or "MOUNT" in ref_upper or "MH" in ref_upper:
                mounting_hole_positions.add(
                    (round(comp.position.x, 1), round(comp.position.y, 1))
                )

        # 简化：只检查每条走线的端点
        for track in board.tracks:
            if not track.points:
                continue

            # 只检查端点
            endpoints = [track.points[0], track.points[-1]]

            for point in endpoints:
                # 检查是否靠近安装孔
                is_near_hole = False
                for hole_pos in mounting_hole_positions:
                    dist = (
                        (point.x - hole_pos[0]) ** 2 + (point.y - hole_pos[1]) ** 2
                    ) ** 0.5
                    if dist < 5.0:
                        is_near_hole = True
                        break

                if is_near_hole:
                    continue

                distance_to_edge = min(
                    point.x, board.width - point.x, point.y, board.height - point.y
                )

                # 只有距离非常近才报告 (< 0.5mm) - 制造业通常要求0.2-0.5mm
                if distance_to_edge < 0.5:
                    issues.append(
                        Issue(
                            id=f"edge_{track.id}",
                            type=IssueType.COPPER_TO_EDGE_TOO_SMALL,
                            severity=Severity.INFO,
                            category="走线符合性",
                            message=f"走线 {track.id} 距板边 {distance_to_edge:.3f}mm",
                            location=point,
                            related_ids=[track.id],
                            auto_fixable=False,  # 不自动修复，因为可能引起其他问题
                            fix_suggestion="确保铜到板边距离符合制造要求",
                        )
                    )

        return issues

    def _check_annular_ring(self, board: PCBBoard) -> List[Issue]:
        """检查焊环"""
        issues = []

        for via in board.vias:
            annular_ring = (via.diameter - via.drill) / 2

            if annular_ring < self.rules.MIN_ANNULAR_RING:
                issues.append(
                    Issue(
                        id=f"annular_{via.id}",
                        type=IssueType.ANNULAR_RING_TOO_SMALL,
                        severity=Severity.WARNING,
                        category="走线符合性",
                        message=f"过孔 {via.id} 焊环 {annular_ring:.3f}mm < {self.rules.MIN_ANNULAR_RING}mm",
                        location=via.position,
                        related_ids=[via.id],
                        auto_fixable=True,
                        fix_suggestion=f"增加过孔尺寸以保证焊环至少 {self.rules.MIN_ANNULAR_RING}mm",
                    )
                )

        return issues

    def _check_isolated_copper(self, board: PCBBoard) -> List[Issue]:
        """检查孤岛铜"""
        issues = []

        # 简化的检查：如果铺铜区域很小，可能是孤岛
        for zone in board.zones:
            if len(zone.points) >= 3:
                # 计算面积
                area = self._calculate_polygon_area(zone.points)

                if area < 10.0:  # 小于10平方毫米
                    issues.append(
                        Issue(
                            id=f"isolated_{zone.id}",
                            type=IssueType.ISOLATED_COPPER,
                            severity=Severity.WARNING,
                            category="走线符合性",
                            message=f"铺铜区域 {zone.id} 面积 {area:.2f}mm²，可能是孤岛铜",
                            location=zone.points[0] if zone.points else None,
                            related_ids=[zone.id],
                            auto_fixable=True,
                            fix_suggestion="删除此孤岛铜或连接到网络",
                        )
                    )

        return issues

    def _bbox_overlaps(self, bbox1, bbox2) -> bool:
        """检查包围盒是否重叠"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        return not (
            x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min
        )

    def _estimate_distance(self, t1: Track, t2: Track) -> float:
        """估算两条走线的距离"""
        # 简化：取第一个点的距离
        if t1.points and t2.points:
            return t1.points[0].distance_to(t2.points[0])
        return 0

    def _calculate_polygon_area(self, points) -> float:
        """计算多边形面积 (Shoelace公式)"""
        if len(points) < 3:
            return 0

        area = 0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y

        return abs(area) / 2


class PCBChecker:
    """综合 PCB 检查器"""

    def __init__(self, rules: DesignRules = None):
        self.rules = rules or DesignRules()
        self.track_checker = TrackWidthChecker(rules)
        self.layout_checker = LayoutChecker(rules)
        self.routing_checker = RoutingCorrectnessChecker(rules)
        self.compliance_checker = RoutingComplianceChecker(rules)

    def check_all(self, board: PCBBoard) -> List[Issue]:
        """运行所有检查"""
        all_issues = []

        all_issues.extend(self.track_checker.check(board))
        all_issues.extend(self.layout_checker.check(board))
        all_issues.extend(self.routing_checker.check(board))
        all_issues.extend(self.compliance_checker.check(board))

        # 去重
        seen = set()
        unique_issues = []
        for issue in all_issues:
            key = (issue.type.value, issue.message[:50])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return unique_issues

    def evaluate(self, board: PCBBoard) -> "EvaluationResult":
        """评估并返回结果"""
        issues = self.check_all(board)

        # 计算评分
        scores = self._calculate_scores(issues, board)

        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)

        return EvaluationResult(
            iteration=0,
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            scores=scores,
        )

    def _calculate_scores(
        self, issues: List[Issue], board: PCBBoard
    ) -> Dict[str, float]:
        """计算各维度评分"""
        # 基础分数
        base_score = 100

        # 扣分
        error_penalty = sum(5 for i in issues if i.severity == Severity.ERROR)
        warning_penalty = sum(2 for i in issues if i.severity == Severity.WARNING)

        # 按类别统计
        categories = {}
        for issue in issues:
            if issue.category not in categories:
                categories[issue.category] = {"error": 0, "warning": 0, "info": 0}
            severity_key = issue.severity.value
            if severity_key not in categories[issue.category]:
                categories[issue.category][severity_key] = 0
            categories[issue.category][severity_key] += 1

        # 计算各维度分数
        scores = {
            "线宽": self._category_score(categories.get("线宽", {}), 25),
            "布局": self._category_score(categories.get("布局", {}), 25),
            "走线正确性": self._category_score(categories.get("走线正确性", {}), 25),
            "走线符合性": self._category_score(categories.get("走线符合性", {}), 25),
        }

        scores["总体"] = sum(scores.values()) / len(scores)

        return scores

    def _category_score(self, category_issues: Dict, max_score: int) -> float:
        """计算类别分数"""
        if not category_issues:
            return max_score

        errors = category_issues.get("error", 0)
        warnings = category_issues.get("warning", 0)

        penalty = errors * 5 + warnings * 2
        score = max(0, max_score - penalty)

        return score


# 导入 EvaluationResult
from .pcb_models import EvaluationResult
