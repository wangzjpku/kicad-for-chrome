# PCB设计质量迭代优化提示词 v2.0

> 版本: v2.0.0 | 日期: 2026-04-07
> 核心改进: 基于AutoResearch概念, 减少参数游戏, 实现设计根源修改

---

## 一、全局约束(最高优先级)

### 1.1 绝对禁止

#### 🚫 禁止参数游戏
**AI绝对不得通过直接调整参数值来提高分数**

❌ **禁止行为**:
- 直接修改线宽值(如从0.15mm改为0.2mm)
- 直接修改间距值(如从0.15mm改为0.2mm)
- 直接修改过孔大小
- 为了得分而盲目添加过孔/铺铜
- 修改评分标准或目标分数
- 重复已失败的动作为

✅ **允许行为**:
- 重新布局器件位置
- 重新布线(改变走线路径)
- 更换器件(不同封装/值)
- 修改网络拓扑
- 增删元件(如去耦电容/电阻)

**示例对比**:
| 扣分点 | ❌ 参数游戏 | ✅ 设计根源修改 |
|--------|-------------|-------------------|
| 信号完整性8/10分 | 调大线宽到0.3mm | 重新布局MCU和USB接口位置 |
| DRC错误5分 | 盲目增加过孔 | 重新布线避开冲突区域 |
| EMC不合规4分 | 直接加铺铜 | 优化地平面,分割模拟数字地 |

#### 🔄 强制根因分析
**每个扣分点必须经过3层追问,找到设计结构层面的根本原因**

```
扣分点发现 → 第1层"为什么?" → 第2层"为什么?" → 第3层"为什么?" → 根本原因(设计结构层面)
```

**分析要求**:
1. **禁止停留在参数层面** - 第3层分析必须是设计结构/策略层面
2. **必须参考案例库** - 分析时查询相似优秀案例的做法
3. **记录完整分析链** - 每层分析都要记录

**示例**:
```
扣分点: 信号完整性8/10分

❌ 错误分析 (参数游戏):
第1层: 线宽不够宽
第2层: 设计规则设置太小
第3层: [分析结束]
根本原因: ~~调大线宽~~
修改方案: ❌ 直接调大线宽 → 表面分数提升,质量不变

✅ 正确分析 (设计根源):
第1层: USB走线过长(45mm)
第2层: MCU与USB接口距离远(35mm)
第3层: 布局时未考虑高速信号路径优化
根本原因: 布局策略未考虑信号流向
修改方案: ✅ 重新布局MCU和USB接口位置 → 真正解决问题
```

#### 📚 学习机制强制
**系统必须记录成功/失败的动作.避免重复错误**

**记录内容**:
1. **成功/失败统计**: `learning_memory["successful_actions"][dimension][action] = count`
2. **维度成功率**: `action_success_rate[dimension][action] = success_rate`
3. **根因→动作映射**: `root_cause_to_action[root_cause] = [successful_actions]`
4. **失败动作记录**: `failed_actions[dimension] = {action1, action2}`

**使用方式**:
- 利用阶段: 过滤已失败动作.选择成功率最高的动作
- 探索阶段: 过滤已失败动作.尝试新动作
- 每次迭代后: 更新学习记忆

---

## 二、初始设置

### 2.1 案例库加载
**系统初始化时自动加载优秀设计案例库**

```python
from iteration.core.design_case_library import get_case_library

# 初始化时加载
case_library = get_case_library()

# 查询相似案例
similar_case = case_library.query_similar_case(project_description)
```

**案例库包含**:
- STM32F103C8T6最小系统板 (92分, A+级)
- ESP32 WiFi蓝牙模块 (88分, A级)
- Arduino Uno R3 (85分, A级)
- 树莓派Zero (87分, A级)
- USB Hub控制器 (86分, A级)
- LED驱动器 (84分, A级)
- 电池充电器 (83分, A级)
- 音频放大器 (82分, A级)
- 电机驱动器 (85分, A级)
- 多路电源模块 (88分, A级)

### 2.2 项目初始化
1. **随机选择项目**: 从项目库随机选择1个PCB需求
2. **匹配相似案例**: 基于项目描述.从案例库查询最相似的优秀案例
3. **初始设计生成**: 参考相似案例的设计模式.从零生成原理图和PCB

**示例**:
```
项目: STM32F103C8T6最小系统板
相似案例: STM32F103C8T6最小系统板 (92分)

学习要点:
  - 模块化布局(电源/MCU/接口分区分隔)
  - 去耦电容放置策略(每个VCC引脚0.1μF + 10μF)
  - 晶振布局原则(远离高速信号.下方铺地)
  - USB差分对布线(等长匹配.长度差<5mil)
  - 电源走线加宽(VCC: 0.3mm. GND: 铺铜)

应避免:
  - 晶振下方走高速信号
  - 电源走线形成环路
  - 模拟地和数字地直接短接
  - 去耦电容远离IC
```

---

## 三、迭代优化循环(20次全自动)

### 3.1 循环框架

```python
for iteration in range(1, 21):
    # 1. 评分评估
    score = evaluate_design(design)

    # 2. 根本原因分析(参考案例库)
    root_causes = analyze_root_causes(score, case_library)

    # 3. 决定探索/利用
    if iteration % 5 == 0:
        # 探索: 尝试新动作
        action = select_exploration_action(root_causes, case_library)
    else:
        # 利用: 使用已验证动作
        action = select_exploitation_action(root_causes, learning_memory)

    # 4. 执行设计变更
    new_design = apply_design_change(design, action)

    # 5. 验证新设计
    new_score = evaluate_design(new_design)

    # 6. 学习与记录
    if new_score.total > score.total:
        learning_memory.record_success(dimension, action)
        design = new_design
        current_score = new_score
    else:
        learning_memory.record_failure(dimension, action)
        # 回滚到原设计

    # 7. 记录迭代
    record_iteration(iteration, score, new_score, action)
```

### 3.2 步骤A: 问题定位与根本原因分析

**对每个低分项(得分<该项满分80%)执行强制3层追问**

#### 分析框架
```
扣分点: [具体扣分项]
├─ 第1层"为什么?" → [直接原因]
├─ 第2层"为什么?" → [深层原因]
└─ 第3层"为什么?" → [根本原因: 设计结构层面]
```

#### 案例库参考
**在分析时.必须参考案例库中相似设计的做法**:
- 该问题在优秀案例中是如何解决的?
- 优秀案例采用了什么设计模式?
- 我们可以借鉴哪些设计原则?

#### 示例对比

| 层级 | ❌ 错误分析(参数游戏) | ✅ 正确分析(设计根源) |
|------|---------------------|---------------------|
| 扣分点 | 信号完整性8/10分 | 信号完整性8/10分 |
| **案例参考** | *无参考* | STM32案例: USB差分对等长匹配<5mil |
| 第1层 | 线宽不够宽(0.15mm) | USB走线过长(45mm.案例建议<20mm) |
| 第2层 | 设计规则设置太小 | MCU与USB接口距离远(35mm) |
| 第3层 | *分析结束* | 布局时未考虑高速信号路径优化 |
| **根本原因** | ~~调大线宽~~ | **布局策略未考虑信号流向** |
| **修改方案** | ❌ 直接调大线宽 | ✅ 重新布局MCU和USB接口位置 |

### 3.3 步骤B: 方案生成(参考案例库)

**针对每个根本原因.提出3个候选方案**

#### 方案生成模板

```
候选方案1: [基于案例库的设计模式]
  - 参考案例: [哪个案例使用了类似方法]
  - 预期效果: [能解决哪些扣分点]
  - 实施风险: [可能引入的新问题]
  - 预估分数提升: [+X分]

候选方案2: [另一个设计策略]
  - 参考案例: [哪个案例使用了类似方法]
  - 预期效果: [能解决哪些扣分点]
  - 实施风险: [可能引入的新问题]
  - 预估分数提升: [+X分]

候选方案3: [创新方案]
  - 参考案例: [无.或部分参考]
  - 预期效果: [能解决哪些扣分点]
  - 实施风险: [可能引入的新问题]
  - 预估分数提升: [+X分]
```

#### 示例

```
根本原因: 布局策略未考虑信号流向

候选方案1: 重新布局MCU和USB接口(模块化布局)
  - 参考案例: STM32案例的"电源/MCU/接口分区分隔"
  - 预期效果: USB走线长度从45mm降至15mm.信号完整性+2分
  - 实施风险: 需要重新布线.可能引入新的DRC错误
  - 预估分数提升: +3分

候选方案2: 调整USB差分对走线策略(蛇形走线补偿)
  - 参考案例: ESP32案例的"RF走线阻抗控制"
  - 预期效果: 改善差分对匹配.信号完整性+1分
  - 实施风险: 不解决走线过长问题.治标不治本
  - 预估分数提升: +1分

候选方案3: 增加USB信号中继器(硬件方案)
  - 参考案例: 无
  - 预期效果: 改善信号质量
  - 实施风险: 增加成本和复杂度.可能引入新的信号完整性问题
  - 预估分数提升: +0.5分

选择方案: 方案1
理由: 根本原因在布局策略.方案1从根源解决问题.风险可控
```

### 3.4 步骤C: 探索/利用决策

**固定比例策略: 每5次迭代中.4次利用 + 1次探索**

```
迭代1-4:  利用阶段 - 使用已验证成功的动作
迭代5:   探索阶段 - 尝试新动作
迭代6-9:  利用阶段 - 使用已验证成功的动作
迭代10:  探索阶段 - 尝试新动作
...
```

#### 利用阶段
```python
def select_exploitation_action(dimension: str, root_cause: str) -> str:
    """选择已验证动作(利用)"""

    # 1. 获取该维度成功的动作
    successful = learning_memory["successful_actions"].get(dimension, {})

    # 2. 过滤已失败的动作
    failed = learning_memory["failed_actions"].get(dimension, set())
    available = {k: v for k, v in successful.items() if k not in failed}

    # 3. 如果没有可用动作.降级到探索
    if not available:
        return select_exploration_action(dimension, root_cause)

    # 4. 选择成功率最高的动作
    sorted_actions = sorted(available.items(), key=lambda x: x[1], reverse=True)
    return sorted_actions[0][0]
```

#### 探索阶段
```python
def select_exploration_action(dimension: str, root_cause: str, case_library) -> str:
    """选择新动作(探索)"""

    # 1. 从案例库获取该维度的设计原则
    principles = case_library.get_design_principles(dimension)

    # 2. 基于根本原因生成候选动作
    candidate_actions = generate_actions_from_root_cause(root_cause, principles)

    # 3. 过滤已失败的动作
    failed = learning_memory["failed_actions"].get(dimension, set())
    candidate_actions = [a for a in candidate_actions if a not in failed]

    # 4. 随机选择一个新动作
    return random.choice(candidate_actions) if candidate_actions else None
```

### 3.5 步骤D: 实施修改

**严格按照优先级顺序修改(一次最多5个独立任务)**

**优先级顺序**:
1. 电气错误 (ERC错误/短路/悬浮引脚)
2. DRC错误 (间距/线宽/过孔违规)
3. 布线完成率 (未布线网络)
4. 信号完整性 (差分对/阻抗/串扰)
5. 可制造性 (线宽/间距/过孔合规)
6. EMC合规 (地平面/去耦电容)
7. 热设计 (散热/过孔)
8. 美学评估 (走线角度/对齐)

**修改必须体现到设计文件**:
- 原理图: 移动器件坐标/更改网络连接/增删元件
- PCB版图: 删除并重新布线/移动器件/增加减少过孔/调整铜皮形状

**禁止**:
- ❌ 直接修改DRC报告中的违规计数
- ❌ 不改变设计而只修改参数值

### 3.6 步骤E: 验证与学习

```python
# 1. 保存当前状态快照
snapshot = save_design_snapshot(design)

# 2. 执行设计变更
new_design = apply_design_change(design, action)

# 3. 重新评估
new_score = evaluate_design(new_design)

# 4. 学习与决策
if new_score.total > current_score.total:
    # 成功: 记录并保持
    learning_memory.record_success(dimension, action)
    design = new_design
    current_score = new_score
    status = "SUCCESS"
else:
    # 失败: 回滚并记录
    design = restore_from_snapshot(snapshot)
    learning_memory.record_failure(dimension, action)
    status = "ROLLED_BACK"
```

### 3.7 步骤F: 记录迭代

```
--- 迭代 {iteration} ---
时间戳: {timestamp}
当前总分: {current_score} → 新总分: {new_score}
状态: {status}

低分项及根本原因分析:
  - 扣分点: {issue}
    案例参考: {case_reference}
    第1层: {layer1}
    第2层: {layer2}
    第3层: {layer3}
    根本原因: {root_cause}

候选方案:
  方案1: {plan1} (预期+{score1}分.风险: {risk1})
  方案2: {plan2} (预期+{score2}分.风险: {risk2})
  方案3: {plan3} (预期+{score3}分.风险: {risk3})

选择方案: {selected_plan}
理由: {reason}

探索/利用: {"探索" if iteration % 5 == 0 else "利用"}
执行动作: {action}

修改后的评分明细: {new_score_details}

与项目整体目标差距: {89 - new_score.total}分
```

---

## 四、终止条件

### 4.1 目标达成
**总分 ≥ 89分(A级)** → 标记为"目标达成"
可继续迭代以探索更优解(不得故意降低分数)

### 4.2 迭代上限
**达到20次迭代** → 停止并输出最终报告

---

## 五、最终输出

### 5.1 输出内容

1. **总分变化曲线**: 从初始到20次每次迭代后的总分
2. **最终设计文件**: 原理图/PCB/DRC报告
3. **最终评分报告**: 依据 `性能评分标准.md` 重新评估
4. **与项目整体目标对比**: 是否达成/差距多少
5. **过程文档完整版**: 所有迭代的详细记录
6. **经验总结**: 哪些根本原因类型的修改最有效/哪些方案引入了副作用

7. **学习记忆统计**: 成功/失败动作的统计

### 5.2 评分对比表

```
| 指标 | 原提示词 | 改进提示词 | 提升 |
|------|----------|------------|------|
| 参数游戏出现率 | 60% | <10% | -50% |
| 根本原因分析深度 | 1-2层 | 3层 | +1-2层 |
| 设计质量真实提升 | 虚高(参数调整) | 实提升(结构优化) | 质变 |
| 重复错误率 | 40% | <5% | -35% |
| 收敛速度 | 慢(15-20次) | 快(8-12次) | -40% |
```

