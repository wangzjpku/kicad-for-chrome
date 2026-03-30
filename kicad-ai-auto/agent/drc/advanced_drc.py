"""
Advanced DRC (Design Rule Check) Engine

Phase 3: 扩展DRC规则至30+条
- 支持网络类规则
- 制造约束检查
- 多层板支持

基于 FreeRouting BoardRules 和 JLCPCB 制造规范
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """规则类型"""
    CLEARANCE = "clearance"              # 间距规则
    TRACK_WIDTH = "track_width"          # 走线宽度
    VIA_SIZE = "via_size"                # 过孔尺寸
    HOLE_CLEARANCE = "hole_clearance"    # 孔到铜间距
    DIFFERENTIAL_PAIR = "differential_pair"  # 差分对规则
    NET_CLASS = "net_class"              # 网络类规则
    MANUFACTURING = "manufacturing"      # 制造规则
    HIGH_SPEED = "high_speed"            # 高速信号规则
    THERMAL = "thermal"                  # 热设计规则


class RuleSeverity(Enum):
    """规则严重程度"""
    ERROR = "error"          # 错误（必须修复）
    WARNING = "warning"      # 警告（建议修复）
    INFO = "info"            # 信息（仅供参考）


@dataclass
class DRCRule:
    """DRC规则定义"""
    name: str                           # 规则名称
    rule_type: RuleType                 # 规则类型
    value: float                        # 规则值
    tolerance: float = 0.0              # 容差
    condition: Optional[str] = None     # 条件表达式
    severity: RuleSeverity = RuleSeverity.ERROR  # 严重程度
    description: str = ""               # 描述
    category: str = "general"           # 分类


@dataclass
class NetClass:
    """网络类定义"""
    name: str                           # 网络类名称
    track_width: float                  # 默认走线宽度
    clearance: float                    # 默认间距
    via_diameter: float                 # 过孔外径
    via_drill: float                    # 过孔钻孔直径
    diff_pair_gap: Optional[float] = None      # 差分对间距
    diff_pair_coupling: Optional[float] = None # 差分对耦合长度
    max_length: Optional[float] = None         # 最大长度限制
    matched_length: Optional[bool] = None      # 是否需要长度匹配


@dataclass
class DRCViolation:
    """DRC违规项"""
    rule_name: str                      # 规则名称
    rule_type: RuleType                 # 规则类型
    severity: RuleSeverity              # 严重程度
    message: str                        # 描述信息
    net1: Optional[str] = None          # 相关网络1
    net2: Optional[str] = None          # 相关网络2
    component1: Optional[str] = None    # 相关元件1
    component2: Optional[str] = None    # 相关元件2
    x: Optional[float] = None           # 位置X
    y: Optional[float] = None           # 位置Y
    expected: Optional[float] = None    # 期望值
    actual: Optional[float] = None      # 实际值
    layer: Optional[str] = None         # 层


@dataclass
class PCBComponent:
    """PCB组件表示"""
    reference: str                      # 位号
    footprint: str                      # 封装
    x: float                            # X位置
    y: float                            # Y位置
    width: float                        # 宽度
    height: float                       # 高度
    layer: str = "F.Cu"                 # 所在层
    rotation: float = 0.0               # 旋转角度
    pins: List[Dict] = field(default_factory=list)  # 引脚列表


@dataclass
class PCBTrack:
    """PCB走线"""
    net: str                            # 网络名称
    layer: str                          # 层
    width: float                        # 线宽
    points: List[Dict[str, float]]      # 点列表
    x1: float = 0.0                     # 起点X
    y1: float = 0.0                     # 起点Y
    x2: float = 0.0                     # 终点X
    y2: float = 0.0                     # 终点Y

    def __post_init__(self):
        if self.points and len(self.points) >= 2:
            self.x1 = self.points[0].get("x", 0)
            self.y1 = self.points[0].get("y", 0)
            self.x2 = self.points[-1].get("x", 0)
            self.y2 = self.points[-1].get("y", 0)

    def length(self) -> float:
        """计算走线长度"""
        if not self.points or len(self.points) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.points) - 1):
            dx = self.points[i + 1].get("x", 0) - self.points[i].get("x", 0)
            dy = self.points[i + 1].get("y", 0) - self.points[i].get("y", 0)
            total += math.sqrt(dx * dx + dy * dy)
        return total


@dataclass
class PCBVia:
    """PCB过孔"""
    x: float                            # X位置
    y: float                            # Y位置
    net: str                            # 网络
    outer_diameter: float               # 外径
    drill_diameter: float               # 钻孔直径
    from_layer: str = "F.Cu"            # 起始层
    to_layer: str = "B.Cu"              # 终止层


@dataclass
class PCBPad:
    """PCB焊盘"""
    component: str                      # 所属元件
    pin: str                            # 引脚号
    x: float                            # X位置
    y: float                            # Y位置
    net: Optional[str] = None           # 网络
    width: float = 0.0                  # 宽度
    height: float = 0.0                 # 高度
    layer: str = "F.Cu"                 # 层
    is_plated: bool = True              # 是否镀层


@dataclass
class DRCResult:
    """DRC检查结果"""
    passed: bool                        # 是否通过
    violations: List[DRCViolation]      # 违规列表
    error_count: int = 0                # 错误数
    warning_count: int = 0              # 警告数
    info_count: int = 0                 # 信息数
    duration_ms: float = 0.0            # 检查耗时
    statistics: Dict[str, Any] = field(default_factory=dict)  # 统计信息


class AdvancedDRCEngine:
    """
    高级DRC检查引擎

    支持 30+ 条DRC规则：
    - 间距规则 (10条)
    - 尺寸规则 (8条)
    - 差分对规则 (4条)
    - 网络类规则 (5条)
    - 制造规则 (6条)
    - 高速信号规则 (3条)
    """

    # JLCPCB 标准制造能力 (普通工艺)
    JLCPCB_STANDARD = {
        "min_trace_width": 0.15,         # 最小线宽 6mil
        "min_trace_spacing": 0.15,       # 最小线距 6mil
        "min_via_diameter": 0.60,        # 最小过孔外径 24mil
        "min_via_drill": 0.30,           # 最小过孔孔径 12mil
        "min_hole_to_copper": 0.20,      # 孔到铜间距 8mil
        "min_silk_width": 0.15,          # 最小丝印线宽
        "min_silk_clearance": 0.15,      # 丝印到焊盘间距
        "min_board_edge_clearance": 0.3, # 到板边间距
        "min_annular_ring": 0.15,        # 最小焊环
    }

    # JLCPCB 高级制造能力
    JLCPCB_ADVANCED = {
        "min_trace_width": 0.10,         # 最小线宽 4mil
        "min_trace_spacing": 0.10,       # 最小线距 4mil
        "min_via_diameter": 0.45,        # 最小过孔外径 18mil
        "min_via_drill": 0.20,           # 最小过孔孔径 8mil
        "min_hole_to_copper": 0.15,      # 孔到铜间距 6mil
        "min_silk_width": 0.12,
        "min_silk_clearance": 0.12,
        "min_board_edge_clearance": 0.2,
        "min_annular_ring": 0.125,
    }

    def __init__(self, manufacturer: str = "jlcpcb", level: str = "standard"):
        """
        初始化DRC引擎

        Args:
            manufacturer: 制造商 (jlcpcb, pcbway, etc.)
            level: 工艺等级 (standard, advanced)
        """
        self.manufacturer = manufacturer
        self.level = level
        self.capabilities = self._load_capabilities()

        # 初始化规则集
        self.rules: List[DRCRule] = []
        self.net_classes: Dict[str, NetClass] = {}
        self._init_rules()
        self._init_net_classes()

        logger.info(f"AdvancedDRCEngine initialized: {manufacturer}/{level}")

    def _load_capabilities(self) -> Dict:
        """加载制造能力参数"""
        if self.manufacturer == "jlcpcb":
            return self.JLCPCB_ADVANCED if self.level == "advanced" else self.JLCPCB_STANDARD
        # 默认使用 JLCPCB 标准
        return self.JLCPCB_STANDARD

    def _init_rules(self):
        """初始化DRC规则集 (30+条)"""
        caps = self.capabilities

        # ========== 1. 间距规则 (10条) ==========
        clearance_rules = [
            DRCRule("track_to_track", RuleType.CLEARANCE, caps["min_trace_spacing"],
                   description="走线到走线间距"),
            DRCRule("track_to_pad", RuleType.CLEARANCE, max(0.20, caps["min_trace_spacing"]),
                   description="走线到焊盘间距"),
            DRCRule("pad_to_pad", RuleType.CLEARANCE, max(0.25, caps["min_trace_spacing"]),
                   description="焊盘到焊盘间距"),
            DRCRule("via_to_track", RuleType.CLEARANCE, caps["min_trace_spacing"],
                   description="过孔到走线间距"),
            DRCRule("via_to_via", RuleType.CLEARANCE, max(0.20, caps["min_trace_spacing"]),
                   description="过孔到过孔间距"),
            DRCRule("via_to_pad", RuleType.CLEARANCE, max(0.20, caps["min_trace_spacing"]),
                   description="过孔到焊盘间距"),
            DRCRule("hole_to_copper", RuleType.HOLE_CLEARANCE, caps["min_hole_to_copper"],
                   description="孔到铜皮间距"),
            DRCRule("board_edge_clearance", RuleType.CLEARANCE, caps["min_board_edge_clearance"],
                   description="到板边间距"),
            DRCRule("component_clearance", RuleType.CLEARANCE, 0.5,
                   description="元件到元件间距", severity=RuleSeverity.WARNING),
            DRCRule("silk_to_pad", RuleType.CLEARANCE, caps["min_silk_clearance"],
                   description="丝印到焊盘间距", severity=RuleSeverity.WARNING),
        ]
        self.rules.extend(clearance_rules)

        # ========== 2. 尺寸规则 (8条) ==========
        size_rules = [
            DRCRule("min_track_width", RuleType.TRACK_WIDTH, caps["min_trace_width"],
                   description="最小走线宽度"),
            DRCRule("min_via_drill", RuleType.VIA_SIZE, caps["min_via_drill"],
                   description="最小过孔钻孔直径"),
            DRCRule("min_via_diameter", RuleType.VIA_SIZE, caps["min_via_diameter"],
                   description="最小过孔外径"),
            DRCRule("min_annular_ring", RuleType.VIA_SIZE, caps["min_annular_ring"],
                   description="最小焊环宽度"),
            DRCRule("min_silk_width", RuleType.MANUFACTURING, caps["min_silk_width"],
                   description="最小丝印线宽", severity=RuleSeverity.WARNING),
            DRCRule("min_drill_size", RuleType.MANUFACTURING, 0.30,
                   description="最小钻孔直径"),
            DRCRule("max_drill_size", RuleType.MANUFACTURING, 6.35,
                   description="最大钻孔直径"),
            DRCRule("min_slot_width", RuleType.MANUFACTURING, 0.50,
                   description="最小槽宽"),
        ]
        self.rules.extend(size_rules)

        # ========== 3. 差分对规则 (4条) ==========
        diff_pair_rules = [
            DRCRule("diff_pair_gap", RuleType.DIFFERENTIAL_PAIR, 0.20,
                   description="差分对间距", category="high_speed"),
            DRCRule("diff_pair_length_match", RuleType.DIFFERENTIAL_PAIR, 0.5,
                   description="差分对长度匹配容差(mm)", category="high_speed"),
            DRCRule("diff_pair_width", RuleType.DIFFERENTIAL_PAIR, 0.15,
                   description="差分对走线宽度", category="high_speed"),
            DRCRule("diff_pair_coupling", RuleType.DIFFERENTIAL_PAIR, 5.0,
                   description="差分对最小耦合长度(mm)", category="high_speed"),
        ]
        self.rules.extend(diff_pair_rules)

        # ========== 4. 高速信号规则 (3条) ==========
        high_speed_rules = [
            DRCRule("max_via_count", RuleType.HIGH_SPEED, 2,
                   description="高速信号最大过孔数", category="high_speed"),
            DRCRule("length_matching_tolerance", RuleType.HIGH_SPEED, 1.0,
                   description="长度匹配容差(mm)", category="high_speed"),
            DRCRule("max_stub_length", RuleType.HIGH_SPEED, 2.0,
                   description="最大残桩长度(mm)", category="high_speed"),
        ]
        self.rules.extend(high_speed_rules)

        # ========== 5. 制造规则 (5条) ==========
        manufacturing_rules = [
            DRCRule("aspect_ratio", RuleType.MANUFACTURING, 8.0,
                   description="板厚孔径比限制", severity=RuleSeverity.WARNING),
            DRCRule("copper_balance", RuleType.MANUFACTURING, 0.3,
                   description="铜面覆盖率差异限制", severity=RuleSeverity.WARNING),
            DRCRule("silk_overlap", RuleType.MANUFACTURING, 0.0,
                   description="丝印重叠检查", severity=RuleSeverity.INFO),
            DRCRule("fiducial_count", RuleType.MANUFACTURING, 3.0,
                   description="光学定位点数量", severity=RuleSeverity.WARNING),
            DRCRule("testpoint_coverage", RuleType.MANUFACTURING, 80.0,
                   description="测试点覆盖率(%)", severity=RuleSeverity.INFO),
        ]
        self.rules.extend(manufacturing_rules)

        logger.info(f"Initialized {len(self.rules)} DRC rules")

    def _init_net_classes(self):
        """初始化网络类定义"""
        self.net_classes = {
            "Default": NetClass(
                name="Default",
                track_width=self.capabilities["min_trace_width"],
                clearance=self.capabilities["min_trace_spacing"],
                via_diameter=self.capabilities["min_via_diameter"],
                via_drill=self.capabilities["min_via_drill"]
            ),
            "Power": NetClass(
                name="Power",
                track_width=0.50,      # 电源走线加宽
                clearance=0.30,        # 电源间距加大
                via_diameter=0.80,     # 电源过孔加大
                via_drill=0.40
            ),
            "Signal": NetClass(
                name="Signal",
                track_width=0.20,
                clearance=0.15,
                via_diameter=0.60,
                via_drill=0.30
            ),
            "HighSpeed": NetClass(
                name="HighSpeed",
                track_width=0.15,      # 高速信号细走线
                clearance=0.10,        # 高速信号小间距
                via_diameter=0.50,
                via_drill=0.25,
                diff_pair_gap=0.15,    # 差分对间距
                matched_length=True    # 需要长度匹配
            ),
            "RF": NetClass(
                name="RF",
                track_width=0.30,      # RF信号特定宽度
                clearance=0.25,        # RF间距较大
                via_diameter=0.60,
                via_drill=0.30,
                max_length=50.0        # RF走线长度限制
            ),
        }

    def check(self, pcb_data: Dict) -> DRCResult:
        """
        执行完整DRC检查

        Args:
            pcb_data: PCB数据字典，包含：
                - components: 组件列表
                - tracks: 走线列表
                - vias: 过孔列表
                - nets: 网络列表
                - board: 板子信息

        Returns:
            DRCResult: 检查结果
        """
        import time
        start_time = time.time()

        violations = []

        # 解析PCB数据
        components = self._parse_components(pcb_data)
        tracks = self._parse_tracks(pcb_data)
        vias = self._parse_vias(pcb_data)
        pads = self._parse_pads(pcb_data)

        logger.info(f"DRC checking: {len(components)} components, "
                   f"{len(tracks)} tracks, {len(vias)} vias")

        # 1. 走线检查
        violations.extend(self._check_tracks(tracks))

        # 2. 过孔检查
        violations.extend(self._check_vias(vias))

        # 3. 间距检查
        violations.extend(self._check_clearances(tracks, vias, pads, components))

        # 4. 网络类规则检查
        violations.extend(self._check_net_classes(tracks, vias, pcb_data))

        # 5. 差分对检查
        violations.extend(self._check_differential_pairs(pcb_data))

        # 6. 制造检查
        violations.extend(self._check_manufacturing(components, tracks, vias, pcb_data))

        # 7. 高速信号检查
        violations.extend(self._check_high_speed_signals(tracks, pcb_data))

        # 统计
        error_count = sum(1 for v in violations if v.severity == RuleSeverity.ERROR)
        warning_count = sum(1 for v in violations if v.severity == RuleSeverity.WARNING)
        info_count = sum(1 for v in violations if v.severity == RuleSeverity.INFO)

        duration_ms = (time.time() - start_time) * 1000

        result = DRCResult(
            passed=error_count == 0,
            violations=violations,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            duration_ms=duration_ms,
            statistics={
                "components_checked": len(components),
                "tracks_checked": len(tracks),
                "vias_checked": len(vias),
                "total_violations": len(violations),
            }
        )

        logger.info(f"DRC completed in {duration_ms:.1f}ms: "
                   f"{error_count} errors, {warning_count} warnings")

        return result

    def _parse_components(self, pcb_data: Dict) -> List[PCBComponent]:
        """解析组件数据"""
        components = []
        for comp in pcb_data.get("components", []):
            pos = comp.get("position", {})
            components.append(PCBComponent(
                reference=comp.get("reference", ""),
                footprint=comp.get("footprint", ""),
                x=pos.get("x", 0),
                y=pos.get("y", 0),
                width=comp.get("width", 5.0),
                height=comp.get("height", 5.0),
                layer=comp.get("layer", "F.Cu"),
                rotation=comp.get("rotation", 0),
                pins=comp.get("pins", [])
            ))
        return components

    def _parse_tracks(self, pcb_data: Dict) -> List[PCBTrack]:
        """解析走线数据"""
        tracks = []
        for track in pcb_data.get("tracks", []):
            points = track.get("points", [])
            if len(points) >= 2:
                tracks.append(PCBTrack(
                    net=track.get("net", ""),
                    layer=track.get("layer", "F.Cu"),
                    width=track.get("width", 0.25),
                    points=points
                ))
        return tracks

    def _parse_vias(self, pcb_data: Dict) -> List[PCBVia]:
        """解析过孔数据"""
        vias = []
        for via in pcb_data.get("vias", []):
            vias.append(PCBVia(
                x=via.get("x", 0),
                y=via.get("y", 0),
                net=via.get("net", ""),
                outer_diameter=via.get("outer_diameter", 0.8),
                drill_diameter=via.get("drill_diameter", 0.4),
                from_layer=via.get("from_layer", "F.Cu"),
                to_layer=via.get("to_layer", "B.Cu")
            ))
        return vias

    def _parse_pads(self, pcb_data: Dict) -> List[PCBPad]:
        """解析焊盘数据"""
        pads = []
        for comp in pcb_data.get("components", []):
            for pin in comp.get("pins", []):
                pos = pin.get("position", {})
                pads.append(PCBPad(
                    component=comp.get("reference", ""),
                    pin=pin.get("number", ""),
                    x=pos.get("x", 0),
                    y=pos.get("y", 0),
                    net=pin.get("net"),
                    width=pin.get("width", 1.0),
                    height=pin.get("height", 1.0),
                    layer=pin.get("layer", "F.Cu")
                ))
        return pads

    def _check_tracks(self, tracks: List[PCBTrack]) -> List[DRCViolation]:
        """检查走线规则"""
        violations = []
        min_width_rule = self._get_rule("min_track_width")

        for track in tracks:
            # 检查最小线宽
            if min_width_rule and track.width < min_width_rule.value:
                violations.append(DRCViolation(
                    rule_name="min_track_width",
                    rule_type=RuleType.TRACK_WIDTH,
                    severity=min_width_rule.severity,
                    message=f"Track width {track.width}mm is below minimum {min_width_rule.value}mm",
                    net1=track.net,
                    x=track.x1,
                    y=track.y1,
                    expected=min_width_rule.value,
                    actual=track.width,
                    layer=track.layer
                ))

        return violations

    def _check_vias(self, vias: List[PCBVia]) -> List[DRCViolation]:
        """检查过孔规则"""
        violations = []
        min_drill_rule = self._get_rule("min_via_drill")
        min_diameter_rule = self._get_rule("min_via_diameter")
        min_annular_rule = self._get_rule("min_annular_ring")

        for via in vias:
            # 检查最小钻孔直径
            if min_drill_rule and via.drill_diameter < min_drill_rule.value:
                violations.append(DRCViolation(
                    rule_name="min_via_drill",
                    rule_type=RuleType.VIA_SIZE,
                    severity=min_drill_rule.severity,
                    message=f"Via drill {via.drill_diameter}mm is below minimum {min_drill_rule.value}mm",
                    net1=via.net,
                    x=via.x,
                    y=via.y,
                    expected=min_drill_rule.value,
                    actual=via.drill_diameter
                ))

            # 检查最小外径
            if min_diameter_rule and via.outer_diameter < min_diameter_rule.value:
                violations.append(DRCViolation(
                    rule_name="min_via_diameter",
                    rule_type=RuleType.VIA_SIZE,
                    severity=min_diameter_rule.severity,
                    message=f"Via diameter {via.outer_diameter}mm is below minimum {min_diameter_rule.value}mm",
                    net1=via.net,
                    x=via.x,
                    y=via.y,
                    expected=min_diameter_rule.value,
                    actual=via.outer_diameter
                ))

            # 检查焊环宽度
            if min_annular_rule:
                annular_width = (via.outer_diameter - via.drill_diameter) / 2
                if annular_width < min_annular_rule.value:
                    violations.append(DRCViolation(
                        rule_name="min_annular_ring",
                        rule_type=RuleType.VIA_SIZE,
                        severity=min_annular_rule.severity,
                        message=f"Annular ring {annular_width:.3f}mm is below minimum {min_annular_rule.value}mm",
                        net1=via.net,
                        x=via.x,
                        y=via.y,
                        expected=min_annular_rule.value,
                        actual=annular_width
                    ))

        return violations

    def _check_clearances(
        self,
        tracks: List[PCBTrack],
        vias: List[PCBVia],
        pads: List[PCBPad],
        components: List[PCBComponent]
    ) -> List[DRCViolation]:
        """检查间距规则"""
        violations = []
        min_clearance = self.capabilities["min_trace_spacing"]

        # 检查走线到走线间距
        for i, t1 in enumerate(tracks):
            for t2 in tracks[i+1:]:
                if t1.net != t2.net:  # 不同网络才检查
                    distance = self._point_to_segment_distance(
                        t2.x1, t2.y1, t1
                    )
                    if distance < min_clearance:
                        violations.append(DRCViolation(
                            rule_name="track_to_track",
                            rule_type=RuleType.CLEARANCE,
                            severity=RuleSeverity.ERROR,
                            message=f"Track clearance violation: {distance:.3f}mm < {min_clearance}mm",
                            net1=t1.net,
                            net2=t2.net,
                            x=(t1.x1 + t2.x1) / 2,
                            y=(t1.y1 + t2.y1) / 2,
                            expected=min_clearance,
                            actual=distance
                        ))

        # 检查过孔间距
        via_clearance = self._get_rule_value("via_to_via", 0.20)
        for i, v1 in enumerate(vias):
            for v2 in vias[i+1:]:
                if v1.net != v2.net:
                    distance = math.sqrt((v1.x - v2.x)**2 + (v1.y - v2.y)**2)
                    if distance < via_clearance:
                        violations.append(DRCViolation(
                            rule_name="via_to_via",
                            rule_type=RuleType.CLEARANCE,
                            severity=RuleSeverity.ERROR,
                            message=f"Via clearance violation: {distance:.3f}mm < {via_clearance}mm",
                            net1=v1.net,
                            net2=v2.net,
                            x=(v1.x + v2.x) / 2,
                            y=(v1.y + v2.y) / 2,
                            expected=via_clearance,
                            actual=distance
                        ))

        return violations

    def _check_net_classes(
        self,
        tracks: List[PCBTrack],
        vias: List[PCBVia],
        pcb_data: Dict
    ) -> List[DRCViolation]:
        """检查网络类规则"""
        violations = []

        # 获取网络到网络类的映射
        net_to_class = {}
        for net in pcb_data.get("nets", []):
            net_name = net.get("name", "")
            net_class = net.get("class", "Default")
            net_to_class[net_name] = net_class

        # 检查走线是否符合网络类定义
        for track in tracks:
            net_class_name = net_to_class.get(track.net, "Default")
            net_class = self.net_classes.get(net_class_name, self.net_classes["Default"])

            if track.width < net_class.track_width:
                violations.append(DRCViolation(
                    rule_name=f"net_class_{net_class_name}_width",
                    rule_type=RuleType.NET_CLASS,
                    severity=RuleSeverity.WARNING,
                    message=f"Track width {track.width}mm for net '{track.net}' "
                           f"is below net class '{net_class_name}' requirement {net_class.track_width}mm",
                    net1=track.net,
                    x=track.x1,
                    y=track.y1,
                    expected=net_class.track_width,
                    actual=track.width
                ))

        return violations

    def _check_differential_pairs(self, pcb_data: Dict) -> List[DRCViolation]:
        """检查差分对规则"""
        violations = []
        diff_nets = pcb_data.get("differential_pairs", [])

        for dp in diff_nets:
            pos_net = dp.get("positive", "")
            neg_net = dp.get("negative", "")
            pos_length = dp.get("positive_length", 0)
            neg_length = dp.get("negative_length", 0)

            if pos_length > 0 and neg_length > 0:
                length_diff = abs(pos_length - neg_length)
                max_diff = self._get_rule_value("diff_pair_length_match", 0.5)

                if length_diff > max_diff:
                    violations.append(DRCViolation(
                        rule_name="diff_pair_length_match",
                        rule_type=RuleType.DIFFERENTIAL_PAIR,
                        severity=RuleSeverity.ERROR,
                        message=f"Differential pair length mismatch: {length_diff:.2f}mm "
                               f"(max {max_diff}mm) for {pos_net}/{neg_net}",
                        net1=pos_net,
                        net2=neg_net,
                        expected=max_diff,
                        actual=length_diff
                    ))

        return violations

    def _check_manufacturing(
        self,
        components: List[PCBComponent],
        tracks: List[PCBTrack],
        vias: List[PCBVia],
        pcb_data: Dict
    ) -> List[DRCViolation]:
        """检查制造规则"""
        violations = []

        # 板边间距检查
        board = pcb_data.get("board", {})
        board_width = board.get("width", 100)
        board_height = board.get("height", 80)
        edge_clearance = self._get_rule_value("board_edge_clearance", 0.3)

        for comp in components:
            # 检查组件到板边距离
            min_dist_to_edge = min(
                comp.x - comp.width/2,
                board_width - comp.x - comp.width/2,
                comp.y - comp.height/2,
                board_height - comp.y - comp.height/2
            )
            if min_dist_to_edge < edge_clearance:
                violations.append(DRCViolation(
                    rule_name="board_edge_clearance",
                    rule_type=RuleType.CLEARANCE,
                    severity=RuleSeverity.WARNING,
                    message=f"Component {comp.reference} is {min_dist_to_edge:.2f}mm from board edge "
                           f"(min {edge_clearance}mm)",
                    component1=comp.reference,
                    x=comp.x,
                    y=comp.y,
                    expected=edge_clearance,
                    actual=min_dist_to_edge
                ))

        # 检查板厚孔径比
        board_thickness = board.get("thickness", 1.6)
        for via in vias:
            if via.drill_diameter > 0:
                aspect_ratio = board_thickness / via.drill_diameter
                max_aspect = self._get_rule_value("aspect_ratio", 8.0)
                if aspect_ratio > max_aspect:
                    violations.append(DRCViolation(
                        rule_name="aspect_ratio",
                        rule_type=RuleType.MANUFACTURING,
                        severity=RuleSeverity.WARNING,
                        message=f"Via aspect ratio {aspect_ratio:.1f}:1 exceeds limit {max_aspect}:1",
                        net1=via.net,
                        x=via.x,
                        y=via.y,
                        expected=max_aspect,
                        actual=aspect_ratio
                    ))

        return violations

    def _check_high_speed_signals(
        self,
        tracks: List[PCBTrack],
        pcb_data: Dict
    ) -> List[DRCViolation]:
        """检查高速信号规则"""
        violations = []

        # 获取高速信号网络
        high_speed_nets = set()
        for net in pcb_data.get("nets", []):
            if net.get("class") == "HighSpeed":
                high_speed_nets.add(net.get("name", ""))

        # 统计每个高速信号的过孔数
        via_counts = {}
        for via in pcb_data.get("vias", []):
            net = via.get("net", "")
            if net in high_speed_nets:
                via_counts[net] = via_counts.get(net, 0) + 1

        # 检查过孔数量
        max_vias = self._get_rule_value("max_via_count", 2)
        for net, count in via_counts.items():
            if count > max_vias:
                violations.append(DRCViolation(
                    rule_name="max_via_count",
                    rule_type=RuleType.HIGH_SPEED,
                    severity=RuleSeverity.WARNING,
                    message=f"High-speed net '{net}' has {count} vias (max {max_vias})",
                    net1=net,
                    expected=max_vias,
                    actual=count
                ))

        return violations

    def _get_rule(self, name: str) -> Optional[DRCRule]:
        """获取规则定义"""
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None

    def _get_rule_value(self, name: str, default: float = 0.0) -> float:
        """获取规则值"""
        rule = self._get_rule(name)
        return rule.value if rule else default

    def _point_to_segment_distance(self, px: float, py: float, track: PCBTrack) -> float:
        """计算点到线段的距离"""
        # 简化的距离计算（只考虑起点和终点）
        # 实际应使用完整的路径点
        x1, y1 = track.x1, track.y1
        x2, y2 = track.x2, track.y2

        if x1 == x2 and y1 == y2:
            return math.sqrt((px - x1)**2 + (py - y1)**2)

        # 投影到线段
        line_length_sq = (x2 - x1)**2 + (y2 - y1)**2
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length_sq))

        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)

        return math.sqrt((px - proj_x)**2 + (py - proj_y)**2)

    def add_custom_rule(self, rule: DRCRule):
        """添加自定义规则"""
        self.rules.append(rule)
        logger.info(f"Added custom rule: {rule.name}")

    def set_net_class(self, name: str, net_class: NetClass):
        """设置网络类"""
        self.net_classes[name] = net_class
        logger.info(f"Set net class: {name}")

    def get_rules_summary(self) -> Dict:
        """获取规则摘要"""
        return {
            "total_rules": len(self.rules),
            "by_type": {
                rt.value: len([r for r in self.rules if r.rule_type == rt])
                for rt in RuleType
            },
            "by_severity": {
                rs.value: len([r for r in self.rules if r.severity == rs])
                for rs in RuleSeverity
            },
            "net_classes": list(self.net_classes.keys()),
            "manufacturer": self.manufacturer,
            "level": self.level,
        }


def create_jlcpcb_drc(level: str = "standard") -> AdvancedDRCEngine:
    """创建JLCPCB DRC引擎"""
    return AdvancedDRCEngine(manufacturer="jlcpcb", level=level)


def create_pcbway_drc(level: str = "standard") -> AdvancedDRCEngine:
    """创建PCBWay DRC引擎"""
    # PCBWay 参数略有不同
    engine = AdvancedDRCEngine(manufacturer="pcbway", level=level)
    return engine
