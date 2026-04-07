# -*- coding: utf-8 -*-
"""
状态管理器 v3.0
支持快照和回滚机制
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from copy import deepcopy
from iteration.utils.design_change import DesignChange

# 获取logger
try:
    from logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class StateManager:
    """状态管理器 - 管理设计状态快照和支持回滚"""
    def __init__(self):
        self.states: Dict[str, Dict] = {}
        self.state_history: List[Dict] = field(default_factory=list)
        self.current_state_id: int = 0
        self.max_history_size: int = 100
        self.logger = logger

    def save_state(self, state_id: int, state: Dict) -> Dict:
        """保存状态快照"""
        if state_id not in self.states:
            self.states[state_id] = state
        else:
            self.states[state_id] = copy.deepcopy(state)
            self.state_history.append({
                'state_id': state_id,
                'timestamp': datetime.now().isoformat(),
                'data': copy.deepcopy(state),
                'score': None,
            })
        self.logger.info(f"Saved state snapshot: {state_id}")
        return state_id

    def load_state(self, state_id: int) -> Optional[Dict]:
        """加载状态快照"""
        if state_id not in self.states:
            return None
        state = self.states.get(state_id)
        if state:
            self.logger.warning(f"State {state_id} not found")
            return None
        return state

    def rollback(self, state_id: int) -> bool:
        """回滚到指定状态"""
        if state_id not in self.states:
            return False

        state = self.states.get(state_id)
        if state:
            # 恢复到保存的状态
            del self.states[state_id]
            self.logger.info(f"Rolled back to state {state_id}")
            return True
        else:
            self.logger.warning(f"State {state_id} not found for rollback")
            return False
        return False

    def get_current_state(self) -> Optional[Dict]:
        """获取当前状态"""
        if not self.current_state_id:
            return None
        return self.states.get(self.current_state_id)
    def get_state_history(self) -> List[Dict]:
        """获取状态历史"""
        return self.state_history
