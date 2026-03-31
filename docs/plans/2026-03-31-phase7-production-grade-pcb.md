# Phase 7+ 完整开发计划 — 对标工业级 PCB 设计

**日期**: 2026-03-31
**版本**: 1.0
**状态**: 待执行
**基准**: 三张真实商业 PCB 设计图 (1.jpg USB充电器, 2.jpg 25W快充, 3.png 布线效果) + Flux.ai 能力对比

---

## 背景分析

### 参考设计特征

通过分析三张真实 PCB 设计图 (D:\1.jpg, D:\2.jpg, D:\3.png)，提取出工业级设计的核心特征：

| 特征 | 图片表现 | 评分 | 本项目现状 |
|------|----------|------|-----------|
| 功能分区布局 | 输入→EMI→整流→DC-DC→协议→输出，五段分区 | 9/10 | 按元件类型分区，不按电路拓扑 |
| 安规物理隔离 | 初级/次级隔离槽、爬电距离 | 9/10 | safety_rules.py 有检测但无自动生成 |
| 网格铺铜 | 全板 Hatched Copper + 热焊盘 Relief | 8/10 | copper_pour.py 两种都有，未接 IPC |
| 缝合过孔阵列 | 功率IC下密集散热过孔 | 9/10 | ViaStitch 类存在但未自动化 |
| 功率走线宽度 | 大电流路径极宽铜皮 | 9/10 | current_calculator.py 有数据未接入 |
| 差分对布线 | USB D+/D- 等长匹配 | 8/10 | si_analyzer.py 有分析未接入路由 |
| 元件密度管理 | 高密度区紧凑+功率区留空 | 8/10 | shelf packing 有碰撞检测 |
| 丝印与标注 | 清晰的版本号、功率标注、测试点 | 8/10 | 基础标注存在 |

### 核心差距总结

```
本项目具备 70% 的底层算法模块，核心问题是"接通"而非"从零开发"。
主要差距在：端到端自动化流程、安规物理特征生成、热管理优化。
```

---

## 阶段总览

```
Phase 7A: DRC 真实引擎接通 ................... ✅ 已完成
Phase 7B: 拓扑感知自动布局 ................... ⬜ 待执行
Phase 7C: 铜铺 + 制造集成 .................... ⬜ 待执行
Phase 7D: 模板化原理图生成 ................... ⬜ 待执行
Phase 7E: AI Agent 多步工作流 ................. ⬜ 待执行
Phase 8:  安规特征自动化 + 热管理 ............. ⬜ 待执行 (新增)
Phase 9:  差分对/高速布线 + 阻抗控制 .......... ⬜ 待执行 (新增)
Phase 10: 实时设计审查 + AI 学习闭环 .......... ⬜ 待执行 (新增)
```

---

## Phase 7B: 拓扑感知自动布局 (P0)

**优先级**: 最高 (最大视觉/功能影响)
**预计工时**: 3-5 天
**依赖**: 无

### 目标

实现图片中的"输入→EMI→整流→DC-DC→协议→输出"式功能分区布局，替代当前按元件类型分类的方式。

### 任务清单

#### 7B-1: 网表拓扑分析器

**新建文件**: `agent/placement/netlist_topology.py` (~300行)

```python
class NetlistTopologyAnalyzer:
    """从网表数据中分析电路拓扑，识别功能分区"""

    def analyze(self, components: list, nets: list) -> TopologyResult:
        """
        输出:
        - functional_groups: {group_name: [component_refs]}
        - group_affinity: {(g1, g2): float}  # 0-1，两组应多近
        - isolation_requirements: [(g1, g2, distance_mm)]  # 安规隔离要求
        - power_flow: [group1 -> group2 -> ...]  # 功率流向
        """

    def _identify_groups(self, components, nets) -> dict:
        """
        分组规则 (从图片中学到):
        1. POWER_INPUT: AC输入、整流桥、保险丝、共模电感
        2. POWER_CONVERT: 变压器、DC-DC IC、开关管、功率电感
        3. POWER_OUTPUT: 输出滤波电容、USB连接器、充电协议IC
        4. CONTROL: MCU、反馈电路、光耦、基准电压
        5. PROTECTION: ESD保护、TVS、过压/过流检测
        6. PASSIVE: 去耦电容、上拉电阻 → 附属于最近的IC
        """

    def _detect_power_flow(self, groups, nets) -> list:
        """追踪功率路径: VIN → VCC5V → VCC3V3 → VOUT"""

    def _detect_isolation_needs(self, groups) -> list:
        """
        检测需要安规隔离的分区对:
        - AC输入 vs USB输出 → 6mm 隔离 (IEC 60950)
        - 高压初级 vs 低压次级 → 物理开槽
        """
```

**关键识别规则** (来自图片分析):

| 分组 | 识别关键词 | 图片对应 |
|------|-----------|---------|
| POWER_INPUT | BD1, LF1, CX1, F1, AC, L线, N线 | 图片1右侧、图片2左下 |
| POWER_CONVERT | T1, transformer, L1, inductor, DCDC | 图片1中部 |
| POWER_OUTPUT | USB1-5, VBUS, CC1, PD | 图片1上方、图片2右侧 |
| CONTROL | U1, U3, MCU, feedback, opto | 图片2上方 |
| PROTECTION | SC1, TVS, ESD, clamp | 图片1外围 |

**复用**:
- `component_recommender.py` COMPONENT_PATTERNS → 元件分类
- `pcb/net_classifier.py` → 网络类型识别
- `design_rules/safety_rules.py` → 安规间距数据

#### 7B-2: 拓扑感知布局引擎

**新建文件**: `agent/placement/topology_placement.py` (~400行)

```python
class TopologyAwarePlacementEngine:
    """基于电路拓扑的功能分区布局"""

    def place(self, components, nets, board_constraints=None) -> PlacementResult:
        """
        布局策略 (模仿图片设计):
        1. 功率流向: 左→右 (输入在左, 输出在右)
        2. 安全隔离: 初级/次级之间留空
        3. 接口元件: 放在板边
        4. 控制电路: 居中
        5. 被动元件: 靠近所属IC
        """

    def _define_zones(self, topology, board) -> dict:
        """
        区域定义 (参考图片):
        - power_input_zone: 板子左 20%, 靠近板边
        - power_convert_zone: 板子中左 30%
        - isolation_gap: 3-6mm 空白带 (如果需要)
        - output_zone: 板子右 30%
        - connector_zone: 板子顶边/右边
        """

    def _force_directed_within_zone(self, comps, zone, nets):
        """
        区域内力导向布局:
        - 复用 smart_placement_engine.py 的力导向算法
        - 增加区域边界约束
        - 附加"连线吸引力": 有共同网络的元件互相吸引
        """

    def _attach_passives_to_parent(self, components, groups):
        """
        被动元件就近附着:
        - 去耦电容 → 紧贴IC的电源引脚
        - 上拉/下拉电阻 → 靠近对应信号引脚
        - 滤波电感/电容 → 串联在信号路径上
        """
```

**复用**:
- `smart_placement_engine.py` → 边缘放置规则、力导向松弛、2D压缩
- `placement_engine.py` → 热感知评分、SI感知评分
- `pcb_layout_optimizer.py` → 贪心迭代优化

#### 7B-3: 接入 IPC Manager + API

**修改文件**: `agent/kicad_ipc_manager.py`

```python
def auto_place(self, topology_aware=True):
    """自动布局"""
    if topology_aware:
        board_data = self.get_full_pcb_data()
        components = board_data.get("footprints", [])
        nets = self._extract_nets_from_board()

        engine = TopologyAwarePlacementEngine(board_width, board_height)
        result = engine.place(components, nets)

        for comp in result.placed_components:
            self.move_item(comp.reference, comp.position)
    else:
        # 现有 smart_placement_engine 回退
```

**新建路由**: `agent/routes/pcb_routes.py`

```
POST /api/v1/pcb/auto-layout
Body: { project_id, topology_aware: true, board_constraints: {...} }
Response: { zones: [...], placed: [...], score: float }
```

#### 7B-4: 前端布局控制

**修改文件**: `web/src/editors/PCBEditor.tsx`

- 添加"Auto Layout"按钮
- 区域可视化叠层 (半透明色块标注电源区/信号区/接口区)
- 布局质量评分显示

### 验证标准

- [ ] 输入"USB充电器"需求 → 布局产生 左(输入)-中(整流)-右(USB) 的分区
- [ ] 含AC输入的设计 → 自动生成3-6mm隔离带
- [ ] 去耦电容紧贴IC电源引脚 (< 2mm)
- [ ] 区域可视化在画布上清晰显示

---

## Phase 7C: 铜铺 + 缝合过孔自动化 (P0)

**优先级**: 高
**预计工时**: 2-3 天
**依赖**: 7A (DRC用于铺铜后验证)

### 目标

实现图片中的大面积网格铺铜 + 密集缝合过孔阵列 + 热焊盘过孔，并输出到真实 KiCad。

### 任务清单

#### 7C-1: IPC Zone 创建

**修改文件**: `agent/kicad_ipc_manager.py`

```python
def create_zone(self, net_name: str, layer: str, boundary_points: list,
                clearance: float = 0.3, thermal_relief: bool = True,
                hatched: bool = False, hatch_width: float = 1.0,
                hatch_gap: float = 0.5) -> str:
    """
    通过 IPC 创建铺铜区域
    支持: 实心铺铜 + 网格铺铜 (图片中使用的是网格)
    """

def create_stitching_vias(self, zone_boundary: list,
                          spacing: float = 1.0,
                          via_size: float = 0.6,
                          via_drill: float = 0.3) -> list:
    """在铺铜区域内生成缝合过孔网格"""

def auto_copper_pour(self, nets=None, layers=None,
                     hatched=False, stitch_spacing=1.0):
    """一键铺铜: GND底层 + 电源顶层 + 缝合过孔"""
```

#### 7C-2: 铜铺路由

**修改文件**: `agent/routes/pcb_routes.py`

```
POST /api/v1/pcb/copper-pour
Body: {
  project_id: str,
  nets: ["GND", "VCC"],
  layers: ["B.Cu", "F.Cu"],
  style: "solid" | "hatched",     # 网格铺铜 vs 实心
  hatch_width: 1.0,               # 网格线宽
  hatch_gap: 0.5,                 # 网格间距
  thermal_relief: true,
  stitch_vias: true,
  stitch_spacing: 1.0,            # 缝合过孔间距
}
```

#### 7C-3: 铺铜后 DRC 验证

```python
# 铺铜后自动运行 DRC
drc_result = await run_drc(project_id)
# 过滤出铺铜相关的间距违规
copper_violations = [v for v in drc_result.violations
                     if "clearance" in v.code.lower()]
# 自动调整 clearance 并重试
```

#### 7C-4: 前端铜铺控制

**修改文件**: `web/src/editors/PCBEditor.tsx`

- "Copper Pour" 按钮
- 选项: 铺铜网络(GND/VCC)、铺铜样式(实心/网格)、缝合过孔
- 铺铜区域可视化 (半透明铜色渲染)

### 验证标准

- [ ] GND 网络在 B.Cu 层生成完整铺铜
- [ ] 缝合过孔以 1mm 间距排列在铺铜区内
- [ ] 网格铺铜样式与图片一致 (1mm 线宽, 0.5mm 间距)
- [ ] 铺铜后 DRC 通过 (无间距违规)
- [ ] 热焊盘 (Thermal Relief) 在元件焊盘处正确生成

---

## Phase 7D: 模板化原理图生成 (P0)

**优先级**: 高
**预计工时**: 3-4 天
**依赖**: 无

### 目标

从图片中提取的成熟设计模式转化为可复用模板，使 AI 生成原理图时优先从模板出发，LLM 仅做微调。

### 任务清单

#### 7D-1: 扩展模板库 (15+ 新模板)

**修改文件**: `agent/templates/template_data.py`

从图片设计和常见产品中提取模板:

| # | 模板名 | 来源 | 关键元件 |
|---|--------|------|---------|
| 1 | USB-C PD 充电器 | 图片2/3 | USB-C ×4, PD控制器, DC-DC |
| 2 | 多口USB充电器 | 图片1 | USB-A ×5, 整流桥, 变压器 |
| 3 | USB-Serial Adapter | CH340C常见设计 | CH340C, USB-B, 12MHz晶体 |
| 4 | ESP32 最小系统 | ESP32-WROOM | ESP32, AMS1117-3.3, USB-Serial |
| 5 | STM32 最小系统 | STM32F103 | STM32, 8MHz晶体, LDO, SWD |
| 6 | 5V/3.3V 双电源 | AMS1117设计 | AMS1117-5.0, AMS1117-3.3, 电容 |
| 7 | 锂电池充电 | TP4056设计 | TP4056, FS8205, USB-C |
| 8 | 电机驱动 | L298N设计 | L298N, 续流二极管, 采样电阻 |
| 9 | 音频放大 | LM386设计 | LM386, 耦合电容, 增益电阻 |
| 10 | RS485通信 | MAX485设计 | MAX485, 终端电阻, 偏置电阻 |
| 11 | I2C电平转换 | BSS138设计 | BSS138 ×2, 上拉电阻 |
| 12 | 电池保护 | DW01+FS8205 | DW01, FS8205, 采样电阻 |
| 13 | LED恒流驱动 | AL8805设计 | AL8805, 采样电阻, LED串 |
| 14 | 传感器接口 | ADC前端 | 运放, 基准电压, 滤波网络 |
| 15 | NFC/RFID | PN532设计 | PN532, 天线匹配, 晶体 |

每个模板包含:
- **经过验证的原理图连接** (非 LLM 生成)
- **预设元件位置** (优化后的坐标)
- **网络定义** (正确的电源/信号分类)
- **制造验证的封装分配**
- **安规标注** (需要隔离的位置)

#### 7D-2: 模板匹配器

**新建文件**: `agent/templates/template_matcher.py` (~200行)

```python
class TemplateMatcher:
    """从自然语言需求匹配已有模板"""

    def match(self, requirements: str) -> list[TemplateMatch]:
        """
        匹配策略:
        1. 关键词提取: USB, 充电, ESP32, STM32...
        2. 模板标签匹配: 每个模板有 tags + description
        3. 评分排序: confidence 0-1
        """

    def customize(self, template, requirements) -> dict:
        """
        模板定制:
        - 调整电压: 3.3V → 5V (更换LDO)
        - 调整电流: 1A → 2A (更换电感/二极管)
        - 增减接口: 4口USB → 6口USB
        """
```

#### 7D-3: 混合生成管线

**修改文件**: `agent/routes/ai_design_routes.py`

```python
# 新的生成优先级:
# 1. 模板匹配 (confidence > 0.8) → 直接使用模板
# 2. 模板+定制 (0.5 < confidence < 0.8) → 模板+LLM微调
# 3. 纯AI生成 (无匹配) → 现有 SchematicGenerator
```

#### 7D-4: 模板质量验证器

**新建文件**: `agent/templates/template_validator.py` (~120行)

```python
class TemplateValidator:
    """验证模板质量"""
    def validate(self, template) -> ValidationResult:
        checks = [
            self._all_power_pins_connected,    # 所有电源引脚已连接
            self._no_floating_pins,            # 无悬空引脚
            self._decoupling_caps_present,     # IC旁有去耦电容
            self._signal_paths_complete,       # 信号路径完整
            self._footprints_assigned,         # 封装已分配
            self._nets_classified,             # 网络已分类
        ]
```

### 验证标准

- [ ] 15个新模板全部通过 TemplateValidator
- [ ] "设计一个USB充电器" → 匹配到 USB-C PD 充电器模板 (confidence > 0.85)
- [ ] 模板生成的原理图无悬空引脚
- [ ] 模板 vs 纯LLM 质量对比: 模板通过率 > 95%, LLM < 60%

---

## Phase 7E: AI Agent 多步工作流 (P1)

**优先级**: 中
**预计工时**: 3-5 天
**依赖**: 7A + 7B

### 目标

实现从需求到成品的一键设计流水线: 需求→模板→原理图→ERC→布局→布线→DRC→铺铜→制造检查。

### 任务清单

#### 7E-1: 多步设计 Agent

**新建文件**: `agent/loops/multi_step_agent.py` (~400行)

```python
class MultiStepDesignAgent:
    """端到端设计自动化"""

    STEPS = [
        ("requirements_analysis", "需求分析"),
        ("template_matching", "模板匹配"),
        ("schematic_generation", "原理图生成"),
        ("erc_validation", "ERC验证"),
        ("auto_fix", "自动修复"),
        ("pcb_layout", "PCB布局"),
        ("pcb_routing", "PCM布线"),
        ("drc_check", "DRC检查"),
        ("copper_pour", "铺铜"),
        ("final_validation", "最终验证"),
    ]

    def design(self, requirements: str, max_iterations: int = 3) -> DesignResult:
        # Step 1: 分析需求
        analysis = self.analyze_requirements(requirements)

        # Step 2: 并行 - 原理图 + BOM
        with ThreadPoolExecutor() as pool:
            schematic = pool.submit(self.gen_schematic, analysis)
            bom = pool.submit(self.gen_bom, analysis)

        # Step 3: 验证循环 (最多 max_iterations 次)
        for i in range(max_iterations):
            erc = self.run_erc(schematic.result())
            if erc.passed:
                break
            schematic = self.auto_fix(schematic.result(), erc)

        # Step 4: PCB 布局 (拓扑感知)
        layout = self.gen_layout(schematic.result(), bom.result())

        # Step 5: 布线
        routing = self.gen_routing(layout)

        # Step 6: 铺铜
        pour = self.gen_copper_pour(routing)

        # Step 7: 最终 DRC
        final = self.run_drc(pour)
        if not final.passed:
            pour = self.refine(pour, final)

        return DesignResult(
            schematic=schematic, layout=layout,
            drc=final, iterations=i+1
        )
```

#### 7E-2: 进度 API

```
GET /api/v1/ai/design/{task_id}/progress
Response: {
  current_step: "pcb_layout",
  step_index: 5,
  total_steps: 10,
  progress_pct: 50,
  intermediate_results: {...}
}
```

#### 7E-3: 前端进度 UI

**修改文件**: `web/src/components/DesignWizard/DesignWizard.tsx`

- 步骤指示器: 需求→原理图→ERC→布局→布线→DRC→铺铜→完成
- 每步的进度条和中间结果预览
- 自动修复通知
- 错误回退重试按钮

### 验证标准

- [ ] 输入"设计一个ESP32最小系统" → 全流程自动完成 → DRC 通过
- [ ] 注入一个错误 → Agent 自动检测并修复
- [ ] 进度 API 返回正确的步骤信息
- [ ] 总设计时间 < 60 秒 (不含 KiCad 操作)

---

## Phase 8: 安规特征自动化 + 热管理 (P1 新增)

**优先级**: 中高 (图片设计中最突出的特征)
**预计工时**: 3-4 天
**依赖**: 7B (布局引擎)

### 目标

自动生成图片中可见的安规隔离带、物理开槽、散热过孔阵列等安全与热管理特征。

### 任务清单

#### 8-1: 安规隔离带生成器

**新建文件**: `agent/pcb/isolation_generator.py` (~200行)

```python
class IsolationGenerator:
    """自动生成安规隔离特征"""

    def generate_isolation_slot(self, board, primary_zone, secondary_zone,
                                 min_creepage_mm: float = 6.0):
        """
        在初级/次级区域之间生成物理隔离槽:
        - 类型1: 无铜开槽 (板上挖空, 图片3可见)
        - 类型2: 无铜隔离带 (保留基材, 去除所有铜)
        - 宽度: IEC 60950-1 规定 220VAC → 6mm 最小
        """

    def generate_creepage_barriers(self, board, voltage: float):
        """
        生成爬电距离增强特征:
        - 在隔离带中添加锯齿/沟槽增加爬电路径
        - 自动放置安规标识 (⚡ 符号)
        """

    def to_kicad_format(self) -> str:
        """输出为 KiCad S-expression (Edge.Cuts 层上的槽)"""
```

#### 8-2: 散热过孔阵列生成器

**新建文件**: `agent/pcb/thermal_via_generator.py` (~150行)

```python
class ThermalViaGenerator:
    """为功率器件生成散热过孔阵列"""

    def generate_thermal_vias(self, component, thermal_resistance_target: float = 10.0):
        """
        参数计算:
        - 单孔热阻: ~50-100 °C/W (0.3mm drill)
        - N孔并联: Rth/N
        - 需要的孔数 = ceil(Rth_single / target)

        布局策略 (参考图片2):
        - 在 IC 中心区域均匀分布
        - 避开信号引脚走线
        - 连接到底层大面积铜皮
        """
```

#### 8-3: 安规 DRC 规则增强

**修改文件**: `agent/drc/advanced_drc.py`

新增规则:
```
SAFETY_010: 初级/次级间距检查 (6mm for 220V)
SAFETY_011: 隔离槽完整性 (无铜断裂)
SAFETY_012: 热焊盘过孔密度 (≥4个/W)
SAFETY_013: 高压走线与板边距离 (≥1mm)
```

### 验证标准

- [ ] AC-DC 设计 → 自动生成 6mm 隔离槽
- [ ] 功率 IC → 自动生成散热过孔阵列 (数量基于热阻计算)
- [ ] 安规 DRC 规则检测到隔离带缺失时报警
- [ ] 输出的 KiCad 文件在 PCB 编辑器中正确显示隔离槽

---

## Phase 9: 差分对/高速布线 + 阻抗控制 (P2 新增)

**优先级**: 中 (图片中 USB 差分对的关键需求)
**预计工时**: 4-5 天
**依赖**: 7C (铜铺完成)

### 目标

实现 USB D+/D- 等差分对的等长匹配布线和阻抗控制。

### 任务清单

#### 9-1: 差分对布线器

**新建文件**: `agent/routing/differential_pair_router.py` (~300行)

```python
class DifferentialPairRouter:
    """差分对布线: 等长匹配 + 阻抗控制"""

    def route_pair(self, pos_net, neg_net,
                   target_impedance: float = 90.0,  # USB: 90Ω
                   max_length_mismatch: float = 0.5):
        """
        策略 (参考图片中 USB 布线):
        1. 两线平行布线 (耦合布线)
        2. 根据阻抗目标计算线宽/间距
        3. 长度匹配: 短线添加蛇形等长 (serpentine tuning)
        4. 避免跨分割平面
        """
```

#### 9-2: 阻抗感知布线

**修改文件**: `agent/routing/astar_router.py`

```python
# 接入 si_analyzer.py 的阻抗计算
# 布线时动态调整线宽以维持目标阻抗
# 高速信号避免90°拐角 (使用45°或圆弧)
```

#### 9-3: 等长调谐器

**新建文件**: `agent/routing/length_tuner.py` (~200行)

```python
class LengthTuner:
    """蛇形等长: 匹配差分对和网络组内的走线长度"""

    def tune(self, traces, target_length: float,
             style: str = "serpentine"):  # or "sawtooth"
        """
        在短走线上添加蛇形弯曲以匹配长度
        参数: 振幅、间距、最小弯曲半径
        """
```

### 验证标准

- [ ] USB D+/D- 差分对长度差 < 0.5mm
- [ ] 阻抗计算结果与 SiAnalyzer 一致 (误差 < 5%)
- [ ] 高速信号无 90° 拐角
- [ ] 差分对布线不跨越参考平面分割

---

## Phase 10: 实时设计审查 + AI 学习 (P2 新增)

**优先级**: 低 (长期竞争力)
**预计工时**: 2-3 周
**依赖**: 7A-7E + 8 + 9

### 目标

对标 Flux.ai 的实时设计审查和 AI 学习能力。

### 任务清单

#### 10-1: 实时 DRC 引擎

```python
# 每次 PCB 数据变更时自动运行增量 DRC
# 通过 WebSocket 推送违规到前端
# 前端实时在画布上高亮违规位置
```

#### 10-2: 设计规则学习

```python
# 从用户的手动修正中提取设计规则
# 例: 用户移动了去耦电容位置 → 学习"去耦电容应靠近引脚"
# 存储到用户偏好数据库
# 下次设计时自动应用
```

#### 10-3: 智能审查助手

```python
# 类似 Flux.ai 的 AI 审查:
# - 检查布局是否遵循功率流向
# - 检查高速信号是否远离干扰源
# - 检查散热路径是否畅通
# - 提供改进建议 (非仅报错)
```

---

## 执行时间线

```
Week 1:  7B (拓扑布局 Step 1-2) + 7D (模板库 Step 1)
Week 2:  7B (拓扑布局 Step 3-4) + 7D (模板 Step 2-4) + 7C (铜铺 Step 1)
Week 3:  7C (铜铺 Step 2-4) + 7E (Agent Step 1-2) + 8 (安规 Step 1-2)
Week 4:  7E (Agent Step 3) + 8 (安规 Step 3) + 集成测试
Week 5:  9 (差分对 Step 1-3) + Bug修复
Week 6+: 10 (实时审查, 长期迭代)
```

---

## 新建文件总表

| 文件 | 行数 | Phase |
|------|------|-------|
| `agent/placement/netlist_topology.py` | ~300 | 7B |
| `agent/placement/topology_placement.py` | ~400 | 7B |
| `agent/pcb/isolation_generator.py` | ~200 | 8 |
| `agent/pcb/thermal_via_generator.py` | ~150 | 8 |
| `agent/routing/differential_pair_router.py` | ~300 | 9 |
| `agent/routing/length_tuner.py` | ~200 | 9 |
| `agent/templates/template_matcher.py` | ~200 | 7D |
| `agent/templates/template_validator.py` | ~120 | 7D |
| `agent/loops/multi_step_agent.py` | ~400 | 7E |

## 修改文件总表

| 文件 | Phase | 改动 |
|------|-------|------|
| `agent/kicad_ipc_manager.py` | 7B/7C | auto_place(), create_zone(), create_stitching_vias(), auto_copper_pour() |
| `agent/routes/pcb_routes.py` | 7B/7C | auto-layout, copper-pour 路由 |
| `agent/routes/ai_design_routes.py` | 7D/7E | 模板优先生成, Agent 进度 API |
| `agent/templates/template_data.py` | 7D | 15+ 新模板 |
| `agent/drc/advanced_drc.py` | 8 | 安规 DRC 规则 SAFETY_010-013 |
| `agent/routing/astar_router.py` | 9 | 阻抗感知布线 |
| `web/src/editors/PCBEditor.tsx` | 7B/7C | 布局/铺铜控制按钮 |
| `web/src/services/api.ts` | 7B/7C/7E | 新 API 方法 |
| `web/src/components/DesignWizard/DesignWizard.tsx` | 7E | Agent 进度 UI |

---

## 关键复用模块

| 模块 | 文件 | 复用内容 |
|------|------|---------|
| AdvancedDRCEngine | `drc/advanced_drc.py` | 30规则引擎, 直接调用 |
| ProfessionalDesignEngine | `design_rules/__init__.py` | 8模块安全规则 |
| SmartPlacementEngine | `placement/smart_placement_engine.py` | 力导向/边缘放置/压缩 |
| CopperPourEngine | `routing/copper_pour.py` | KiCad S-expression 输出 |
| AStarRouter | `routing/astar_router.py` | 路径搜索核心 |
| SIAnalyzer | `drc/si_analyzer.py` | 阻抗/损耗/串扰分析 |
| SafetyRules | `design_rules/safety_rules.py` | IEC 60950 间距表 |
| CurrentCalculator | `pcb/current_calculator.py` | IPC-2221 走线宽度 |
| NetClassifier | `pcb/net_classifier.py` | 网络分类 |
| SchematicGenerator | `schematic_generator.py` | 10策略原理图生成 |

---

## 端到端验证场景

### 场景1: USB 充电器 (对标图片1/2/3)

```
输入: "设计一个25W USB充电器，4个USB-C + 1个USB-A"
预期输出:
├── 原理图: 匹配 USB-C PD 充电器模板 (Phase 7D)
├── ERC: 通过，无悬空引脚
├── 布局: 功率流向分区 + 安规隔离带 (Phase 7B/8)
├── 布线: 功率走线自动加宽 (Phase 9)
├── 铺铜: GND 网格铺铜 + 缝合过孔阵列 (Phase 7C)
├── DRC: 30规则 + 安规规则全部通过 (Phase 7A/8)
└── 制造: JLCPCB 规则检查通过
```

### 场景2: ESP32 IoT 设备

```
输入: "设计一个ESP32温湿度传感器，WiFi上报"
预期输出:
├── 原理图: 匹配 ESP32 最小系统模板
├── 布局: 信号区居中，WiFi天线在板边
├── 差分对: USB D+/D- 等长匹配
├── SI 分析: USB 阻抗 ~90Ω
└── 最终: 完整 Gerber + BOM + 坐标文件
```

### 场景3: Agent 全自动

```
输入: "设计一个STM32最小系统板"
流程: 需求分析→模板匹配→原理图→ERC→布局→布线→铺铜→DRC
结果: 一键完成，0次人工干预
```
