# -*- coding: utf-8 -*-
"""
设计变更数据结构 v3.0
支持回滚的设计变更记录
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import copy
import json


class ModificationType(Enum):
    """修改类型"""
    MOVE = "move"              # 移动元件
    ADD = "add"                 # 添加元件/过孔/走线
    REMOVE = "remove"           # 删除元件/过孔/走线
    REROUTE = "reroute"           # 重新布线
    RESIZE = "resize"             # 调整尺寸（线宽、过孔等）
    MODIFY_PROPERTY = "modify"   # 修改属性（网络、层等）
    RESTRUCTURE = "restructure"   # 结构变更（全局重布）


    GLOBAL_REROUTE = "global"   # 全局重布


@dataclass
class Modification:
    """单个修改操作"""
    action: ModificationType
    target_type: str           # "component", "track", "via", "zone", "pad"
    target_ref: str            # 元件引用（如 "C4", "track-15", "via-3"）
    before: Optional[Dict]     # 修改前的数据
    after: Optional[Dict]      # 修改后的数据
    details: str = ""            # 详细描述

    def to_dict(self) -> Dict:
        return {
            'action': self.action.value,
            'target_type': self.target_type,
            'target_ref': self.target_ref,
            'before': self.before,
            'after': self.after,
            'details': self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Modification':
        return cls(
            action=ModificationType(data['action']),
            target_type=data['target_type'],
            target_ref=data['target_ref'],
            before=data.get('before'),
            after=data.get('after'),
            details=data.get('details', ''),
        )

    def is_reversible(self) -> bool:
        """检查是否可回滚"""
        # 所有修改都应该可回滚
        return True

    def apply(self, design_data: Dict) -> Dict:
        """应用修改到设计数据"""
        result = copy.deepcopy(design_data)

        if self.target_type == "component":
            result = self._apply_to_components(result)
        elif self.target_type == "track":
            result = self._apply_to_tracks(result)
        elif self.target_type == "via":
            result = self._apply_to_vias(result)
        elif self.target_type == "zone":
            result = self._apply_to_zones(result)
        elif self.target_type == "pad":
            result = self._apply_to_pads(result)

        return result

    def rollback(self, design_data: Dict) -> Dict:
        """回滚修改"""
        # 应用before状态
        result = copy.deepcopy(design_data)

        if self.before is not None:
            if self.target_type == "component":
                result = self._rollback_component(result)
            elif self.target_type == "track":
                result = self._rollback_track(result)
            elif self.target_type == "via":
                result = self._rollback_via(result)
            elif self.target_type == "zone":
                result = self._rollback_zone(result)

        return result

    def _apply_to_components(self, data: Dict) -> Dict:
        """应用到元件列表"""
        footprints = data.get('footprints', data.get('components', []))

        if self.action == ModificationType.ADD:
            # 添加新元件
            if self.after:
                footprints.append(self.after)
        elif self.action == ModificationType.REMOVE:
            # 删除元件
            data['footprints'] = [f for f in footprints if f.get('reference') != self.target_ref]
            data['components'] = data.get('components', [])
        elif self.action in [ModificationType.MOVE, ModificationType.MODIFY_PROPERTY]:
            # 移动或修改元件
            for fp in footprints:
                if fp.get('reference') == self.target_ref and self.after:
                    fp.update(self.after)

        return data

    def _apply_to_tracks(self, data: Dict) -> Dict:
        """应用到走线列表"""
        tracks = data.get('tracks', [])

        if self.action == ModificationType.ADD:
            if self.after:
                tracks.append(self.after)
        elif self.action == ModificationType.REMOVE:
            data['tracks'] = [t for t in tracks if t.get('id') != self.target_ref]
        elif self.action in [ModificationType.REROUTE, ModificationType.RESIZE, ModificationType.MODIFY_PROPERTY]:
            for track in tracks:
                if track.get('id') == self.target_ref and self.after:
                    track.update(self.after)

        return data

    def _apply_to_vias(self, data: Dict) -> Dict:
        """应用到过孔列表"""
        vias = data.get('vias', [])

        if self.action == ModificationType.ADD:
            if self.after:
                vias.append(self.after)
        elif self.action == ModificationType.REMOVE:
                data['vias'] = [v for v in vias if v.get('id', f"{v.get('x')},{v.get('y')}") != self.target_ref]
        elif self.action in [ModificationType.MOVE, ModificationType.RESIZE]:
            for via in vias:
                via_id = f"{via.get('x')},{via.get('y')}"
                if via_id == self.target_ref and self.after:
                    via.update(self.after)

        return data

    def _apply_to_zones(self, data: Dict) -> Dict:
        """应用到铺铜列表"""
        zones = data.get('zones', [])

        if self.action == ModificationType.ADD:
            if self.after:
                zones.append(self.after)
        elif self.action == ModificationType.REMOVE:
                # 通过net和layer识别
                data['zones'] = [z for z in zones
                               if not (z.get('net') == self.after.get('net') if self.after else False
                               and z.get('layer') == self.after.get('layer') if self.after else False)]
        elif self.action == ModificationType.MODIFY_PROPERTY:
            for zone in zones:
                if zone.get('net') == self.target_ref and self.after:
                    zone.update(self.after)

        return data

    def _apply_to_pads(self, data: Dict) -> Dict:
        """应用到焊盘"""
        footprints = data.get('footprints', [])
        ref_parts = self.target_ref.split('.')

        if len(ref_parts) == 2:
            comp_ref, pad_num = ref_parts
            for fp in footprints:
                if fp.get('reference') == comp_ref:
                    pads = fp.get('pads', [])
                    for pad in pads:
                        if str(pad.get('number')) == str(pad_num) and self.after:
                            pad.update(self.after)

        return data

    def _rollback_component(self, data: Dict) -> Dict:
        """回滚元件变更"""
        footprints = data.get('footprints', [])

        if self.action == ModificationType.ADD:
            # 回滚添加 = 删除
            data['footprints'] = [f for f in footprints if f.get('reference') != self.target_ref]
        elif self.action == ModificationType.REMOVE:
            # 回滚删除 = 添加
            if self.before:
                footprints.append(self.before)
        else:
            # 回滚修改 = 恢复原状态
            for fp in footprints:
                if fp.get('reference') == self.target_ref and self.before:
                    fp.update(self.before)

        return data

    def _rollback_track(self, data: Dict) -> Dict:
        """回滚走线变更"""
        tracks = data.get('tracks', [])

        if self.action == ModificationType.ADD:
            data['tracks'] = [t for t in tracks if t.get('id') != self.target_ref]
        elif self.action == ModificationType.REMOVE:
            if self.before:
                tracks.append(self.before)
        else:
            for track in tracks:
                if track.get('id') == self.target_ref and self.before:
                    track.update(self.before)

        return data

    def _rollback_via(self, data: Dict) -> Dict:
        """回滚过孔变更"""
        vias = data.get('vias', [])

        if self.action == ModificationType.ADD:
            data['vias'] = [v for v in vias if f"{v.get('x')},{v.get('y')}" != self.target_ref]
        elif self.action == ModificationType.REMOVE:
            if self.before:
                vias.append(self.before)
        else:
            for via in vias:
                if f"{via.get('x')},{via.get('y')}" == self.target_ref and self.before:
                    via.update(self.before)

        return data

    def _rollback_zone(self, data: Dict) -> Dict:
        """回滚铺铜变更"""
        zones = data.get('zones', [])

        if self.action == ModificationType.ADD:
            # 删除添加的zone
            if self.after:
                data['zones'] = [z for z in zones
                                if not (z.get('net') == self.after.get('net')
                                and z.get('layer') == self.after.get('layer'))]
        elif self.action == ModificationType.REMOVE:
            if self.before:
                zones.append(self.before)

        return data


@dataclass
class DesignChange:
    """设计变更记录 - 支持回滚"""
    change_id: str
    change_type: str                      # "topology", "structure", "global"
    target_dimension: str                # 针对的评分维度
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 变更前后状态
    before_state: Dict = field(default_factory=dict)
    after_state: Dict = field(default_factory=dict)

    # 修改列表
    modifications: List[Modification] = field(default_factory=list)

    # 元数据
    description: str = ""
    expected_improvement: float = 0.0
    actual_improvement: float = 0.0
    success: bool = False

    # 回滚相关
    rolled_back: bool = False
    rollback_reason: str = ""

    def to_dict(self) -> Dict:
        return {
            'change_id': self.change_id,
            'change_type': self.change_type,
            'target_dimension': self.target_dimension,
            'timestamp': self.timestamp,
            'description': self.description,
            'expected_improvement': self.expected_improvement,
            'actual_improvement': self.actual_improvement,
            'success': self.success,
            'rolled_back': self.rolled_back,
            'rollback_reason': self.rollback_reason,
            'modifications': [m.to_dict() for m in self.modifications],
            'before_state': self.before_state,
            'after_state': self.after_state,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DesignChange':
        return cls(
            change_id=data['change_id'],
            change_type=data['change_type'],
            target_dimension=data['target_dimension'],
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            description=data.get('description', ''),
            expected_improvement=data.get('expected_improvement', 0.0),
            actual_improvement=data.get('actual_improvement', 0.0),
            success=data.get('success', False),
            rolled_back=data.get('rolled_back', False),
            rollback_reason=data.get('rollback_reason', ''),
            modifications=[Modification.from_dict(m) for m in data.get('modifications', [])],
            before_state=data.get('before_state', {}),
            after_state=data.get('after_state', {}),
        )

    def apply(self, design_data: Dict) -> Dict:
        """应用所有修改到设计数据"""
        result = copy.deepcopy(design_data)

        # 保存before状态
        self.before_state = {
            'footprints': copy.deepcopy(design_data.get('footprints', [])),
            'tracks': copy.deepcopy(design_data.get('tracks', [])),
            'vias': copy.deepcopy(design_data.get('vias', [])),
            'zones': copy.deepcopy(design_data.get('zones', [])),
        }

        # 应用所有修改
        for mod in self.modifications:
            result = mod.apply(result)

        # 保存after状态
        self.after_state = {
            'footprints': copy.deepcopy(result.get('footprints', [])),
            'tracks': copy.deepcopy(result.get('tracks', [])),
            'vias': copy.deepcopy(result.get('vias', [])),
            'zones': copy.deepcopy(result.get('zones', [])),
        }

        return result

    def rollback(self, design_data: Dict) -> Dict:
        """回滚所有修改"""
        if not self.before_state:
            return design_data

        result = copy.deepcopy(design_data)

        # 按相反顺序回滚
        for mod in reversed(self.modifications):
            result = mod.rollback(result)

        self.rolled_back = True
        return result

    def verify_improvement(self, before_score: float, after_score: float) -> bool:
        """验证是否真正改进"""
        self.actual_improvement = after_score - before_score
        self.success = self.actual_improvement > 0

        return self.success

    def get_summary(self) -> str:
        """获取变更摘要"""
        status = "ROLLED BACK" if self.rolled_back else ("SUCCESS" if self.success else "FAILED")
        return (
            f"[{self.change_id}] {self.change_type} -> {self.target_dimension}\n"
            f"  {len(self.modifications)} modifications, {self.description}\n"
            f"  Expected: +{self.expected_improvement:.1f}, Actual: {self.actual_improvement:+.1f}\n"
            f"  Status: {status}"
        )
