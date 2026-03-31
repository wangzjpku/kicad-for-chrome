# 性能提升与竞争力补强开发计划

**日期**: 2026-04-01
**状态**: 待执行
**基准分析**: 基于竞品对比(Flux.ai / JITX / Quilter / CELUS / CircuitMind)与参考设计(25W USB充电器PCB)

---

## 一、现状评估矩阵

| 模块 | 当前水平 | 目标水平 | 差距等级 |
|------|---------|---------|---------|
| 原理图生成 | 8/10 | 9/10 | 小 |
| PCB布局引擎 | 7/10 | 9/10 | 中 |
| **自动布线** | **3/10** | **8/10** | **严重** |
| DRC检查 | 9/10 | 9/10 | 无 |
| 安全合规 | 6/10 | 9/10 | 中 |
| 制造输出 | 8/10 | 9/10 | 小 |
| 前端可视化 | 5/10 | 8/10 | 中 |
| 元件数据库 | 5/10 | 8/10 | 中 |
| 端到端AI Agent | 7/10 | 9/10 | 中 |

---

## 二、开发路线图总览

```
Phase 8  ─── 布线引擎突破 (核心短板)         ← 优先级 P0
Phase 9  ─── 端到端质量提升                    ← 优先级 P0
Phase 10 ─── 前端可视化与用户体验              ← 优先级 P1
Phase 11 ─── 制造生态与供应链集成              ← 优先级 P2
Phase 12 ─── 商业化准备与性能优化              ← 优先级 P2
```

---

## Phase 8: 布线引擎突破 (P0 — 核心短板)

> **目标**: 将自动布线从"基础A*"提升到"专业可用"水平
> **参考**: Quilter(强化学习), Flux.ai(集成布线引擎), FreeRouting(开源推挤布线)
> **预计工作量**: ~15个任务

### 8A. Push-and-Shove 路由器实现 (核心)

**现状**: `push_router.py` 的 `_handle_obstacles()` 仅检测冲突，不实际推挤
**目标**: 实现完整的推挤布线算法

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 8A-1 | 定义推挤数据结构 | `routing/shove_types.py` (新建) | ShoveResult, ShoveConflict, ShoveOptions, CostFunction | 无 |
| 8A-2 | 实现线段碰撞解析 | `routing/push_router.py` | `_resolve_collision()`: 计算推移方向和距离 | 8A-1 |
| 8A-3 | 实现单线推移 | `routing/push_router.py` | `_shove_track()`: 沿法线方向推移一条已有线段 | 8A-2 |
| 8A-4 | 实现级联推移 | `routing/push_router.py` | `_cascade_shove()`: 递归推移被影响的相邻线段，最大递归深度10 | 8A-3 |
| 8A-5 | 实现推移成本函数 | `routing/push_router.py` | `_calculate_shove_cost()`: DRC违规惩罚 + 推移距离惩罚 + 过孔惩罚 | 8A-1 |
| 8A-6 | 集成到A*路径搜索 | `routing/push_router.py` | 修改 `_astar_path()` 在遇到障碍时调用推挤，而不是直接标记blocked | 8A-4, 8A-5 |
| 8A-7 | 添加rip-up & retry | `routing/ripup_router.py` (新建) | `RipupRouter.route_all()`: 对失败网络执行拆除→重试循环，最多3轮 | 8A-6 |

**验收标准**:
- [ ] 能自动推移已有线段为新网络腾出空间
- [ ] 推移后不产生DRC违规
- [ ] 10条网络以内100%布通率
- [ ] 支持50条网络，布通率>80%

### 8B. FreeRouter 完整集成

**现状**: `freerouter_cli.py` 仅检测JAR路径，不实际调用
**目标**: 完整调用FreeRouting Java引擎

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 8B-1 | 实现 DSN 文件导出 | `routing/dsn_exporter.py` (新建) | 将KiCad PCB数据转为Specctra DSN格式（FreeRouter输入） | 无 |
| 8B-2 | 实现 FreeRouter 进程管理 | `freerouter_cli.py` | `_execute_freerouter()`: 启动Java进程，传入DSN，监听SES输出 | 8B-1 |
| 8B-3 | 实现 SES 文件导入 | `routing/ses_importer.py` (新建) | 解析Specctra SES格式，提取路由结果转为KiCad track格式 | 8B-2 |
| 8B-4 | 添加布线进度回调 | `freerouter_cli.py` | 通过stdout解析FreeRouter进度，WebSocket推送给前端 | 8B-2 |
| 8B-5 | 集成到布线API | `routes/pcb_routes.py` | `/api/v1/pcb/auto-route` 端点：优先FreeRouter，fallback到SimpleAutoRouter | 8B-3 |

**验收标准**:
- [ ] 自动检测Java和FreeRouter JAR
- [ ] 成功导出DSN并导入SES
- [ ] 布线结果可通过KiCad IPC写入PCB
- [ ] 前端显示实时布线进度

### 8C. 差分对布线集成到主流程

**现状**: `differential_pair_router.py` 已完整实现（576行），但未接入主布线流程
**目标**: 将差分对布线集成到自动布线和设计向导

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 8C-1 | 添加差分对网络识别 | `routing/net_classifier.py` (新建) | 从网络名/元件自动识别差分对（D+/D-, TX+/TX-等模式） | 无 |
| 8C-2 | 集成到自动布线器 | `freerouter_cli.py` | `SimpleAutoRouter` 先路由差分对，再路由普通网络 | 8C-1 |
| 8C-3 | 等长匹配后处理 | `routing/length_tuner.py` | 差分对布线后自动调用 `LengthTuner.tune()` | 8C-2 |
| 8C-4 | 阻抗约束自动设置 | `routing/differential_pair_router.py` | 根据板层叠构自动计算线宽/间距 | 8C-2 |

**验收标准**:
- [ ] 自动识别USB/HDMI/PCIe差分对
- [ ] 差分对阻抗误差<5%
- [ ] 差分对长度匹配误差<0.1mm

### 8D. 布线质量评估系统

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 8D-1 | 定义质量评分模型 | `routing/quality_scorer.py` (新建) | RoutingQualityScore: 布通率(30%) + DRC通过率(30%) + 走线长度(20%) + 过孔数(10%) + 差分对质量(10%) | 无 |
| 8D-2 | 实现评分计算 | `routing/quality_scorer.py` | `score_routing()`: 对完整布线结果打分，输出0-100分 + 改进建议 | 8D-1 |
| 8D-3 | 集成到布线完成回调 | `routes/pcb_routes.py` | 布线完成后自动评分，返回给前端 | 8D-2 |
| 8D-4 | 前端布线质量面板 | `web/src/components/RoutingQualityPanel.tsx` (新建) | 显示评分雷达图 + 具体问题列表 | 8D-3 |

**验收标准**:
- [ ] 自动评分0-100
- [ ] 给出具体改进建议（如"走线总长度偏长，建议调整X元件位置"）

---

## Phase 9: 端到端质量提升 (P0)

> **目标**: 从"能生成"到"生成质量可用"
> **关键**: 强化10步Agent pipeline，添加AI后优化

### 9A. 安规设计自动化

**现状**: `isolation_generator.py` 已实现IEC标准隔离，但未集成到自动设计流程
**目标**: SMPS/电源类设计自动识别高低压区域并生成隔离

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 9A-1 | 高低压区域自动识别 | `schematic_generator.py` | 在布局规划阶段识别primary/secondary侧元件 | 无 |
| 9A-2 | 隔离槽自动规划 | `placement/smart_placement_engine.py` | SMPS类设计自动添加隔离区域约束 | 9A-1 |
| 9A-3 | 敷铜区域自动划分 | `pcb/copper_pour_planner.py` (新建) | AGND/DGND/GND 分区域铺铜策略 | 9A-2 |
| 9A-4 | 安全合规检查报告 | `drc/advanced_drc.py` | 新增安规专项检查（creepage/clearance/隔离槽宽度） | 9A-2 |

**验收标准**:
- [ ] SMPS设计自动识别高低压侧
- [ ] 自动生成符合IEC 62368-1的隔离槽
- [ ] 安规检查报告通过率>95%

### 9B. 布线后AI优化

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 9B-1 | 走线长度优化 | `routing/post_optimizer.py` (新建) | 布线后缩短走线总长度，减少过孔数 | 8A-7 |
| 9B-2 | 拐角平滑化 | `routing/post_optimizer.py` | 90度拐角→45度圆角优化 | 9B-1 |
| 9B-3 | 走线宽度优化 | `routing/post_optimizer.py` | 根据电流负载自动加宽电源走线 | 9B-1 |
| 9B-4 | 热过孔自动推荐 | `pcb/thermal_via_generator.py` | 对发热元件（MOSFET、LDO等）自动推荐热过孔方案 | 无 |

**验收标准**:
- [ ] 走线总长度减少>15%
- [ ] 所有走线无90度拐角
- [ ] 电源走线宽度符合电流要求

### 9C. 多方案布局对比

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 9C-1 | 布局方案生成器 | `placement/layout_candidate.py` (新建) | 生成3种不同布局方案（紧凑/均衡/散热优先） | 无 |
| 9C-2 | 布局评分系统 | `placement/layout_scorer.py` (新建) | 评分维度：面积(25%) + 走线长度预估(30%) + 热分布(25%) + 可制造性(20%) | 9C-1 |
| 9C-3 | 方案对比API | `routes/pcb_routes.py` | `/api/v1/pcb/layout-candidates` 返回3个方案+评分 | 9C-2 |
| 9C-4 | 前端方案选择器 | `web/src/components/LayoutCandidatePanel.tsx` (新建) | 3方案并排预览 + 雷达图评分对比 | 9C-3 |

**验收标准**:
- [ ] 3秒内生成3种布局方案
- [ ] 方案间有显著差异（不同策略）
- [ ] 前端可视化对比

---

## Phase 10: 前端可视化与用户体验 (P1)

> **目标**: 从"文本摘要"到"所见即所得"

### 10A. 设计向导可视化预览

**现状**: `DesignWizard.tsx` 仅文本摘要，无图形化预览
**目标**: 每步都有图形化预览

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 10A-1 | 原理图预览组件 | `web/src/components/DesignWizard/SchematicPreview.tsx` (新建) | 在向导Step 2中渲染Mini原理图预览 | 无 |
| 10A-2 | PCB布局预览组件 | `web/src/components/DesignWizard/PCBLayoutPreview.tsx` (新建) | 在向导Step 3中渲染元件位置预览 | 无 |
| 10A-3 | 布线结果预览组件 | `web/src/components/DesignWizard/RoutingPreview.tsx` (新建) | 在向导Step 4中渲染走线预览 | 无 |
| 10A-4 | 集成到向导 | `web/src/components/DesignWizard/DesignWizard.tsx` | 替换文本摘要为可视化预览 | 10A-1~3 |
| 10A-5 | 实时生成进度动画 | `web/src/components/DesignWizard/GenerationAnimation.tsx` (新建) | 每步生成时的动画效果 | 10A-4 |

**验收标准**:
- [ ] 向导4步每步都有图形化预览
- [ ] 生成过程有动画反馈
- [ ] 预览可交互（缩放/平移）

### 10B. PCB编辑器增强

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 10B-1 | 走线实时渲染 | `web/src/editors/PCBEditor.tsx` | WebSocket推送布线进度，实时显示新走线 | 无 |
| 10B-2 | 差分对高亮显示 | `web/src/editors/PCBEditor.tsx` | 差分对走线用特殊颜色高亮，长度差标注 | 无 |
| 10B-3 | DRC热力图 | `web/src/components/DRCDashboard.tsx` | DRC违规在PCB上用热力图显示严重程度 | 无 |
| 10B-4 | 布线引导线 | `web/src/editors/PCBEditor.tsx` | 未布线网络用虚线引导显示 | 无 |
| 10B-5 | 3D预览增强 | `web/src/components/PCBViewer3D.tsx` (新建或增强) | 元件3D模型渲染，支持旋转/缩放 | 无 |

**验收标准**:
- [ ] 布线过程实时可见
- [ ] DRC违规可视化
- [ ] 3D预览可交互

### 10C. AI交互增强

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 10C-1 | AI建议可视化 | `web/src/components/AIChatAssistant.tsx` | AI建议的布局/走线变更在画布上高亮预览 | 无 |
| 10C-2 | 上下文感知增强 | `web/src/components/AIChatAssistant.tsx` | AI自动感知当前选中元件/网络，提供针对性建议 | 无 |
| 10C-3 | 流式响应 | `routes/ai_routes.py` | LLM响应改为SSE流式推送，前端逐字显示 | 无 |
| 10C-4 | 设计意图理解 | `agent/services/context_builder.py` | 增强上下文构建：添加当前PCB布局状态、DRC状态 | 无 |

**验收标准**:
- [ ] AI建议可在画布上预览
- [ ] 响应延迟<500ms（首token）
- [ ] 上下文包含当前设计状态

---

## Phase 11: 制造生态与供应链集成 (P2)

> **目标**: 从"设计完成"到"可直接下单制造"

### 11A. LCSC 深度集成

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 11A-1 | 实时库存查询 | `services/lcsc_api.py` (新建/增强) | 调用LCSC API查询实时库存和价格 | 无 |
| 11A-2 | 元件替代推荐 | `services/component_alternative.py` (新建) | 当首选元件缺货时推荐替代型号 | 11A-1 |
| 11A-3 | BOM成本优化 | `services/bom_optimizer.py` (新建) | 多供应商比价，总成本最小化 | 11A-1 |
| 11A-4 | 生命周期状态检查 | `services/lcsc_api.py` | 检查元件是否NRFND（Not Recommended For New Design） | 11A-1 |
| 11A-5 | 前端BOM管理面板 | `web/src/components/BOMManagerPanel.tsx` (新建) | BOM表格 + 库存状态 + 成本 + 替代推荐 | 11A-3 |

**验收标准**:
- [ ] BOM中每个元件显示实时库存
- [ ] 缺货元件自动推荐替代
- [ ] 显示总BOM成本估算

### 11B. 制造商深度适配

#### 任务清单

| # | 任务 | 文件 | 说明 | 依赖 |
|---|------|------|------|------|
| 11B-1 | JLCPCB一键下单 | `export/jlcpcb_order.py` (新建) | 生成JLCPCB格式的Gerber+BOM+CPL打包 | 无 |
| 11B-2 | PCBWay适配 | `export/pcbway_order.py` (新建) | PCBWay格式导出 | 无 |
| 11B-3 | 制造可行性预检 | `export/manufacturing_checker.py` (增强) | 增加更多制造商能力配置 | 无 |
| 11B-4 | 前端制造向导 | `web/src/components/ManufacturingWizard.tsx` (新建) | 选择制造商→预检→导出→下单全流程 | 11B-1 |

**验收标准**:
- [ ] 一键生成JLCPCB下单包
- [ ] 制造前自动检查所有约束
- [ ] 显示制造成本估算

---

## Phase 12: 商业化准备 (P2)

### 12A. 性能优化

| # | 任务 | 说明 |
|---|------|------|
| 12A-1 | 布线算法性能优化 | A*搜索空间剪枝、空间索引(R-tree) |
| 12A-2 | 前端渲染优化 | 虚拟化渲染、Web Worker布线计算 |
| 12A-3 | API响应缓存 | Redis缓存元件查询、模板数据 |
| 12A-4 | 大型PCB支持 | >500元件板的流式渲染 |

### 12B. 多人协作

| # | 任务 | 说明 |
|---|------|------|
| 12B-1 | 用户认证系统 | JWT + 角色权限 |
| 12B-2 | 项目共享 | 多人只读/编辑权限 |
| 12B-3 | 实时协作 | WebSocket同步光标和编辑 |
| 12B-4 | 版本历史 | 设计变更diff和回滚 |

### 12C. 插件生态

| # | 任务 | 说明 |
|---|------|------|
| 12C-1 | 设计模板市场 | 用户上传/下载电路模板 |
| 12C-2 | 自定义规则插件 | 用户自定义DRC规则 |
| 12C-3 | API文档 | OpenAPI spec + SDK生成 |
| 12C-4 | 国际化 | 中/英双语界面 |

---

## 三、执行优先级排序

### 第一批 (立即执行) — 解除核心短板

```
8A-1 ~ 8A-7  Push-and-Shove 路由器      (7个任务)
8B-1 ~ 8B-5  FreeRouter 集成            (5个任务)
8C-1 ~ 8C-4  差分对集成                  (4个任务)
8D-1 ~ 8D-4  布线质量评估                (4个任务)
───
共 20 个任务
```

### 第二批 (布线突破后) — 质量提升

```
9A-1 ~ 9A-4  安规设计自动化              (4个任务)
9B-1 ~ 9B-4  布线后AI优化               (4个任务)
9C-1 ~ 9C-4  多方案布局对比              (4个任务)
───
共 12 个任务
```

### 第三批 (质量达标后) — 用户体验

```
10A-1 ~ 10A-5  设计向导可视化            (5个任务)
10B-1 ~ 10B-5  PCB编辑器增强            (5个任务)
10C-1 ~ 10C-4  AI交互增强               (4个任务)
───
共 14 个任务
```

### 第四批 (用户可用后) — 生态完善

```
11A-1 ~ 11A-5  LCSC深度集成              (5个任务)
11B-1 ~ 11B-4  制造商适配                (4个任务)
12A-1 ~ 12A-4  性能优化                  (4个任务)
12B-1 ~ 12B-4  多人协作                  (4个任务)
12C-1 ~ 12C-4  插件生态                  (4个任务)
───
共 21 个任务
```

**总计: 67 个任务**

---

## 四、竞品对标检查点

每完成一个Phase后，对照竞品进行验证：

### Phase 8 完成后 vs Quilter
- [ ] 自动布线布通率 > 80% (Quilter: ~90%)
- [ ] 差分对布线质量接近手工水平
- [ ] 布线时间 < 60秒/50网络

### Phase 9 完成后 vs Flux.ai
- [ ] 端到端生成质量接近Flux.ai输出
- [ ] 安规设计自动化（Flux.ai不具备）
- [ ] 多方案对比选择

### Phase 10 完成后 vs Flux.ai
- [ ] 前端可视化体验接近Flux.ai
- [ ] AI交互响应速度 < Flux.ai
- [ ] 设计预览即时可见

### Phase 11 完成后 vs CELUS
- [ ] LCSC库存实时查询
- [ ] BOM成本优化
- [ ] 一键制造下单（CELUS无此功能）

---

## 五、技术风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Push-and-Shove算法复杂度高 | 开发周期长 | 先实现基础推移，迭代优化 |
| FreeRouter需要Java运行时 | 部署复杂 | 提供内置SimpleAutoRouter作为fallback |
| 差分对阻抗计算精度 | 质量问题 | 使用验证过的微带线公式，对照Saturn PCB |
| 前端渲染性能瓶颈 | 用户体验差 | 虚拟化渲染+Web Worker |
| LCSC API限制/不稳定 | 功能不可用 | 本地缓存+降级方案 |

---

## 六、已有资产盘点（可复用）

以下模块已完整实现，可直接集成到新流程中：

| 模块 | 文件 | 行数 | 状态 |
|------|------|------|------|
| 差分对路由器 | `routing/differential_pair_router.py` | 576 | 完整，待集成 |
| 长度调谐器 | `routing/length_tuner.py` | 505 | 完整，待集成 |
| 扇出引擎 | `pcb/fanout_engine.py` | 360 | 完整，待集成 |
| 隔离生成器 | `pcb/isolation_generator.py` | 419 | 完整，待集成 |
| 热过孔生成器 | `pcb/thermal_via_generator.py` | 349 | 完整，待集成 |
| 交互式路由器 | `pcb/interactive_router.py` | 437 | 部分，需增强 |
| 高级DRC | `drc/advanced_drc.py` | 900 | 完整 |
| 设计审查 | `drc/design_review.py` | 新增 | 完整 |
| 多步Agent | `loops/multi_step_agent.py` | 新增 | 完整 |
| 原理图生成器 | `schematic_generator.py` | 2465 | 完整 |
| 布局引擎 | `placement/smart_placement_engine.py` | 499 | 完整 |

**关键发现**: 大量后端模块已经完整实现（差分对、长度调谐、扇出、隔离、热过孔），只是没有集成到主流程中。Phase 8的工作重点是**集成**而非**从零开发**。

---

## 七、成功指标

| 指标 | Phase 8 后 | Phase 9 后 | Phase 10 后 | 最终目标 |
|------|-----------|-----------|------------|---------|
| 布线布通率 | >80% | >90% | >90% | >95% |
| 差分对质量 | 阻抗±5% | 阻抗±3% | 阻抗±3% | ±2% |
| 端到端生成时间 | <5分钟 | <3分钟 | <2分钟 | <1分钟 |
| DRC通过率 | >85% | >95% | >95% | >98% |
| 前端响应时间 | <500ms | <300ms | <200ms | <100ms |
| 用户满意度 | 能用 | 好用 | 爱用 | 离不开 |
