# PCB设计质量迭代优化流程设计文档

## 日期
2026-04-05 (更新 v3.1)

## 设计目标
构建通用的PCB设计质量迭代优化框架，支持：
1. 随机/AI生成项目
2. 自动评分和根本原因分析
3. 候选方案生成与评审
4. 真实设计变更（拓扑/结构/全局)
5. 分数验证与回滚机制
6. 渐进式难度提升
7. **维度感知优化** (v3.1新增)
8. **学习机制** (v3.1新增)

## 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    PCB Iteration Optimizer v3.1                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ ProjectPool │  │ DesignEngine │  │ Scorer v2.0 │              │
│  │ (项目生成器) │  │ (设计引擎)   │  │ (评分器)    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                       │
│         ▼                ▼                ▼                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              IterationController (迭代控制器)                │  │
│  │  - 维度感知分析 (10个维度)                                    │  │
│  │  - 根本原因分析 (3层追问)                                      │  │
│  │  - 方案生成 & 学习机制选择                                    │  │
│  │  - 执行变更 & 验证                                            │  │
│  │  - 回滚机制                                                   │  │
│  │  - 失败动作记录                                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│         │                                                         │
│         ▼                                                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              DesignChangeEngine (设计变更引擎)                │  │
│  │  - TopologyChanger: 拓扑变更(重新布线)                        │  │
│  │  - StructureChanger: 结构变更(增删元件/过孔)            │  │
│  │  - GlobalReRouter: 全局重布(整体网络规划)             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## v3.1 新特性

### 1. 维度感知优化

系统分析10个评分维度，按优先级排序优化：

| 维度 | 满分 | 权重 | 优化动作 |
|------|------|------|----------|
| 功能正确性 | 15 | 2.5 | complete_routing, fix_drc |
| 电气正确性 | 15 | 2.0 | fix_erc_errors, check_floating_pins |
| 完整性 | 15 | 1.5 | add_component_values, add_footprints |
| 可制造性 | 10 | 1.5 | optimize_pad_nets, add_silkscreen |
| 信号完整性 | 10 | 1.8 | add_gnd_zone, add_decoupling_cap |
| EMC合规 | 5 | 1.5 | add_gnd_zone, add_decoupling_cap |
| 热设计 | 5 | 1.3 | add_gnd_copper_pour, add_thermal_vias |
| 规范性 | 10 | 1.0 | optimize_naming, add_annotations |
| 可读性 | 10 | 1.0 | (评分维度) |
| 美学评估 | 5 | 0.8 | optimize_track_angles |

### 2. 学习机制

- **策略有效性记录**: `strategy_effectiveness[dimension:action] = 0.0-1.0`
- **失败动作记录**: `failed_actions[dimension] = {action1, action2}`
- **指数移动平均更新**: `new = old + α * (target - old)` where α = 0.3

### 3. 智能动作选择

```
1. 过滤不可行动作 (如已完成的布线)
2. 过滤已失败动作 (failed_actions)
3. 若所有动作都失败 → 跳过此维度，尝试下一维度
4. 基于学习机制选择最优动作
```

---

## 测试结果 (2026-04-05)

### 测试项目: ESP32 WiFi蓝牙模块

| 迭代 | 动作 | 目标维度 | 分数变化 | 状态 |
|------|------|----------|----------|------|
| 1 | complete_routing | 功能正确性 | 57.0 → 65.3 | SUCCESS (+8.3) |
| 2 | fix_drc | 功能正确性 | 65.3 → 65.3 | ROLLED BACK |
| 3 | fix_erc_errors | 电气正确性 | 65.3 → 65.3 | ROLLED BACK |
| 4 | check_floating_pins | 电气正确性 | 65.3 → 65.3 | ROLLED BACK |
| 5 | add_gnd_zone | 信号完整性 | 65.3 → 71.3 | SUCCESS (+6.0) |
| 6 | optimize_pad_nets | 可制造性 | 71.3 → 78.3 | SUCCESS (+7.0) |

### 结果总结
- **初始分数**: 57.0 (D)
- **最终分数**: 78.3 (B+)
- **总提升**: +21.3 分
- **成功率**: 3/6 (50%)
- **目标达成**: ✅ (目标75分)

---

## 核心组件设计

### 1. ProjectPool (项目生成器)

负责生成不同难度的PCB项目模板：

```python
@dataclass
class ProjectTemplate:
    name: str                    # "最小系统-STM32F0"
    difficulty: int             # 1-4级难度
    category: str               # "mcu", "power", "sensor", "mixed"
    component_count: int        # 目标元件数量
    required_features: List[str]  # ["差分对", "多电源域", "热管理"]
```

### 2. DesignChange (设计变更记录)
支持回滚的数据结构：
```python
@dataclass
class DesignChange:
    change_id: str
    change_type: str          # "topology" | "structure" | "global"
    target_dimension: str     # 改进的维度

    before_state: Dict            # 变更前的设计数据
    after_state: Dict             # 变更后的设计数据
    modifications: List[Modification]  # 具体修改操作列表
```

### 3. IterationResult (迭代结果)
```python
@dataclass
class IterationResult:
    success: bool
    previous_score: float
    new_score: float
    change: DesignChange
    rolled_back: bool             # 是否回滚
    tried_alternatives: int       # 尝试的替代方案数
```

---

## 数据流

```
1. 项目选择 → ProjectPool.generate()
2. 初始评分 → Scorer.score()
3. 循环开始:
   a. 维度分析 → _analyze_dimensions() # 按优先级排序
   b. 选择目标维度 → 优先级最高且有可行动作
   c. 选择动作 → _select_best_action() # 过滤失败动作
   d. 执行变更 → _apply_action()
   e. 验证改进 → Scorer.score()
   f. 有效则保留，无效则回滚并记录失败
   g. 更新学习机制
4. 达标或达到最大迭代 → 项目完成
```

---

## 关键改进

### 1. 真实变更追踪
- 每个变更记录 before/after 状态
- 支持完整回滚到最新状态

### 2. 验证循环
- 执行变更 → 评分 → 无效则回滚 → 尝试下一方案
- 避免无效迭代

### 3. 渐进难度
- Level 1 (简单) → Level 4 (复杂)
- 达标后自动解锁下一级

### 4. 学习机制 (v3.1)
- 记录策略有效性 (0.0-1.0)
- 记录失败动作，避免重复
- 智能选择最优动作

### 5. 维度感知 (v3.1)
- 分析10个评分维度
- 计算优化优先级 (扣分 × 权重)
- 跳过所有动作都失败的维度

### 6. 回滚机制
- 保留原始状态快照
- 验证失败时恢复快照
- 确保不会重复无效操作

---

## 文件结构

```
agent/
├── iteration_optimizer_v3.py      # 主入口 (简化版)
├── pcb_quality_scorer.py          # 评分器
├── iteration/
│   ├── __init__.py
│   ├── project_pool.py            # 项目生成器
│   ├── iteration_optimizer.py     # 完整版优化器
│   ├── core/
│   │   └── iteration_controller.py # 迭代控制器
│   ├── engines/
│   │   ├── topology_changer.py    # 拓扑变更器
│   │   ├── structure_changer.py   # 结构变更器
│   │   └── global_re_router.py    # 全局重布器
│   └── utils/
│       ├── design_change.py       # 设计变更数据结构
│       └── state_manager.py       # 状态管理(快照/回滚)
```

---

## 运行方式

```bash
cd kicad-ai-auto/agent
python iteration_optimizer_v3.py --project "ESP32 WiFi蓝牙模块" --iterations 15 --target 75
```

---

## 下一步

1. ✅ 实现核心组件
2. ✅ 添加学习机制
3. ✅ 运行测试验证
4. ⏳ 集成到现有系统
5. ⏳ 添加更多优化动作
