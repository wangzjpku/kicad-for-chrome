# PCB迭代优化系统 v2.0

基于AutoResearch概念的智能PCB设计迭代优化系统。

## 核心特性

### 1. 案例库引导
- **20个优秀PCB设计案例**：覆盖MCU、电源、通信、驱动等场景
- **智能相似度匹配**：基于电路特征（元件类型、接口、应用领域）匹配
- **设计原则提取**：从案例中学习最佳实践
- **避免模式学习**：从案例中学习常见错误

### 2. 探索/利用平衡
- **固定比例策略**：每5次迭代中1次探索 + 4次利用
- **学习记忆**：记录成功/失败动作，避免重复错误
- **成功率过滤**：优先选择成功率>80%的动作

### 3. 根本原因分析
- **强制3层追问**：确保分析到设计结构层面
- **禁止参数游戏**：不得直接修改参数值，必须进行设计根源修改

### 4. 可视化工具
- **实时分数曲线**：Chart.js交互式图表
- **收敛检测**：自动判断是否达到目标
- **参数游戏检测**：识别AI是否陷入"调参数"模式
- **多格式导出**：HTML/JSON/Markdown

## 文件结构

```
iteration/
├── core/
│   ├── design_case_library.py    # 案例库 (20个案例)
│   ├── similarity_matcher.py     # 电路特征相似度匹配器
│   ├── exploration_exploitation.py # 探索/利用策略
│   └── visualization.py          # 可视化工具
├── engines/
│   ├── topology_changer.py       # 拓扑结构修改
│   ├── structure_changer.py      # 结构修改
│   └── global_re_router.py       # 全局重布线
├── utils/
│   ├── design_change.py          # 设计变更工具
│   └── state_manager.py          # 状态管理
├── iteration_controller.py       # 迭代控制器
└── project_pool.py               # 项目池

iteration_optimizer_v3.py         # 主优化器 (集成v2模块)
pcb_quality_scorer.py             # PCB质量评分器
```

## 快速开始

### 1. 导入模块

```python
from iteration.core.design_case_library import get_case_library
from iteration.core.exploration_exploitation import get_exploration_exploitation
from iteration.core.visualization import create_visualizer

# 获取案例库
case_library = get_case_library()
print(f"案例数量: {len(case_library.cases)}")

# 获取探索/利用策略
exploration = get_exploration_exploitation()

# 创建可视化器
visualizer = create_visualizer()
```

### 2. 查询相似案例

```python
# 简单查询
case = case_library.query_similar_case("STM32F103C8T6最小系统板")
print(f"匹配案例: {case.name}, 分数: {case.quality_score}")

# 增强版查询 (返回多个)
from iteration.core.similarity_matcher import EnhancedCaseMatcher
matcher = EnhancedCaseMatcher(case_library)
results = matcher.query_similar_cases("ESP32 WiFi蓝牙模块", top_k=3)
for case_id, similarity, scores in results:
    print(f"{case_id}: {similarity:.2f}")
```

### 3. 选择优化动作

```python
# 探索/利用选择
action, source = exploration.select_action(
    dimension="信号完整性",
    root_cause="走线过长",
    iteration=1
)
print(f"动作: {action}, 来源: {source}")

# 记录结果
exploration.record_success("信号完整性", action, improvement=2.5)
# 或
exploration.record_failure("信号完整性", action)
```

### 4. 运行完整优化

```python
from iteration_optimizer_v3 import IterationOptimizer, OptimizationConfig

config = OptimizationConfig(
    target_score=89.0,
    max_iterations=20,
    max_changes_per_iteration=5,
    min_improvement=0.3,
    enable_rollback=True
)

optimizer = IterationOptimizer(config)

# 运行优化
result = optimizer.optimize(project_description="STM32F103C8T6最小系统板")
print(f"最终分数: {result.final_score}")
print(f"迭代次数: {result.iterations}")
```

## API参考

### DesignCaseLibrary

#### `get_case_library() -> DesignCaseLibrary`
获取案例库单例。

#### `query_similar_case(project_description: str, use_enhanced: bool = True) -> Optional[DesignCase]`
查询最相似的案例。

#### `query_similar_cases(project_description: str, top_k: int = 3) -> List[Tuple[DesignCase, float, Dict]]`
查询多个相似案例。

#### `get_design_principles(dimension: str) -> List[str]`
获取特定维度的设计原则。

#### `get_successful_actions(dimension: str, min_success_rate: float = 0.0) -> List[str]`
获取某维度成功率高的动作。

### ExplorationExploitation

#### `select_action(dimension: str, root_cause: str, iteration: int) -> Tuple[str, str]`
选择下一个动作。返回 (动作, 来源)。

#### `record_success(dimension: str, action: str, improvement: float, root_cause: str = "", context: Dict = None)`
记录成功动作。

#### `record_failure(dimension: str, action: str, root_cause: str = "", context: Dict = None)`
记录失败动作。

#### `get_actions_for_root_cause(root_cause: str) -> List[Tuple[str, float]]`
根据根因获取推荐动作。

#### `get_cross_dimension_actions(target_dimension: str) -> List[Tuple[str, str, float]]`
获取跨维度迁移的动作。

#### `save_to_file(filepath: str)` / `load_from_file(filepath: str)`
持久化学习记忆。

### IterationVisualizer

#### `record_iteration(iteration, total_score, dimension_scores, action, ...)`
记录一次迭代。

#### `generate_score_curve_data() -> Dict`
生成分数曲线数据。

#### `check_convergence() -> Dict`
检查收敛状态。

#### `detect_parameter_game_pattern() -> Dict`
检测参数游戏模式。

#### `export_to_html(filepath: str, learning_memory=None)`
导出为HTML可视化页面。

## 案例库列表

| ID | 名称 | 分数 | 难度 |
|----|------|------|------|
| stm32_minimal | STM32F103C8T6最小系统板 | 92 | medium |
| esp32_wifi | ESP32 WiFi蓝牙模块 | 88 | hard |
| arduino_uno_r3 | Arduino Uno R3 | 85 | easy |
| raspberry_pi_zero | 树莓派Zero | 87 | hard |
| usb_hub_controller | USB Hub控制器 | 86 | easy |
| led_driver | LED驱动器 | 84 | easy |
| battery_charger | 锂电池充电器 | 83 | medium |
| audio_amplifier | 音频放大器 | 82 | medium |
| motor_driver | 电机驱动器 | 85 | medium |
| power_module | 多路电源模块 | 88 | hard |
| can_bus_module | CAN总线通信模块 | 85 | medium |
| wireless_charger_rx | 无线充电接收器 | 84 | hard |
| sensor_signal_conditioning | 传感器信号调理模块 | 86 | medium |
| bluetooth_audio | 蓝牙音频模块 | 83 | hard |
| gps_module | GPS定位模块 | 87 | medium |
| ethernet_phy | 以太网PHY模块 | 86 | hard |
| lcd_display | LCD显示模块 | 84 | medium |
| nfc_reader | NFC读写器模块 | 85 | medium |
| current_loop | 4-20mA电流环模块 | 86 | medium |
| rs485_module | RS485通信模块 | 87 | medium |

## 性能对比

| 指标 | v1版本 | v2版本 | 改进 |
|------|--------|--------|------|
| 最终分数 | 68.4 | 106.6 | +38.2 |
| 参数游戏率 | 65% | 0% | -65% |
| 收敛迭代 | 未收敛 | 14次 | 达标 |

## 设计原则

### 禁止事项
1. ❌ 直接修改线宽、间距、过孔大小等数值参数
2. ❌ 为了得分而盲目添加过孔/铺铜
3. ❌ 修改评分标准或目标分数

### 强制要求
1. ✅ 每个扣分点必须经过3层追问
2. ✅ 必须找到设计结构层面的根本原因
3. ✅ 修改方案必须改变设计本身
4. ✅ 记录成功/失败的动作

## 更新日志

### v2.0 (2026-04-07)
- 新增: 20个优秀PCB设计案例库
- 新增: 电路特征相似度匹配器
- 新增: 探索/利用平衡策略
- 新增: 学习记忆持久化
- 新增: 迭代过程可视化工具
- 新增: 跨维度知识迁移
- 改进: 根因分析深度 (1-2层 → 3层)
- 改进: 参数游戏率 (65% → 0%)
