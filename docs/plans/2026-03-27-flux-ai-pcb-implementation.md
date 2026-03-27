# AI PCB 设计系统 - 完整开发计划 (对标 Flux.ai)

> **Goal:** 将 kicad-for-chrome 项目打造为**可商业化**的 AI PCB 设计平台，完全对标 Flux.ai，具备自然语言输入 → AI 分析 → 原理图生成 → AI 布局布线 → 制造文件导出 的完整流程。

**Architecture:**
- **前端**: React + TypeScript + Konva.js，保持现有的编辑器架构，新增 AI Copilot UI
- **后端**: FastAPI + Python，新增 PCB 布局引擎、布线引擎、DFM 规则引擎
- **AI 层**: LLM 驱动的需求分析、层数判定、元器件推荐、价格优化
- **KiCad 集成**: KiCad 9.0+ IPC API + kicad-cli 制造文件导出
- **制造集成**: JLCPCB/LCSC API 实时价格、库存、DFM 检查

---

## Flux.ai 深度分析 (2026-03-27 实地访问)

### 核心功能发现

通过实地访问 flux.ai 网站并分析其产品功能，发现以下关键特性：

#### 1. AI Copilot (AI 实习生)
Flux 的 AI 不是简单的问答，而是**集成在项目中的 AI 助手**：
- **架构设计**：基于需求头脑风暴系统架构
- **组件研究**：查找合适元件、比较替代品、解释技术参数
- **设计评审**：识别潜在问题、改进信号完整性建议
- **测试调试**：SPICE 仿真验证电路行为

#### 2. 工作流自动化
```
Plan → Schematic → Layout → Manufacture
```
- **Plan**：理解需求，制定详细计划供用户确认
- **Schematic**：生成原理图和 BOM，自动遵循最佳实践
- **Layout**：AI 放置和布线，充分考虑约束条件
- **Manufacture**：输出可直接生产的文件，供应链感知元件建议

#### 3. 自然语言输入界面 (Mad Libs 风格)
```
"Make me a [温度湿度传感器] with [WiFi+蓝牙] powered by [USB-C 5V] for [消费电子]"
```
- 结构化引导用户输入
- 下拉选项确保设计意图清晰

#### 4. 实时元件数据
- **真实库存**：设计时显示真实可用性
- **实时价格**：BOM 成本即时计算
- **替代元件**：自动推荐替代料号避免供应风险

#### 5. 制造集成
支持的制造商：
- PCBWay, NextPCB, OSHPark, JLCPCB, SeeedStudio, LionCircuits, Aisler, MacroFab

#### 6. 协作与平台规模
- **1,099,361** 设计师
- **6,425,482** 项目
- **821,334** 元件库
- 实时协作 + 版本控制

#### 7. 商业模式
- 免费 2 周试用
- 付费计划：$20/月 (starter) → $142/月 (pro) → $158/月 (teams)
- 按使用量计费 (ACU)

### 当前项目与 Flux.ai 差距分析

| 差距领域 | Flux.ai | 当前项目 | 优先级 |
|---------|---------|---------|--------|
| **AI 理解深度** | 理解原理图、元件、连接、数据手册 | 仅基础问答 | P0 |
| **工作流集成** | Plan→Schematic→Layout→Manufacture 全流程 | 分离模块 | P0 |
| **实时元件数据** | 真实库存/价格/替代 | 静态库 | P1 |
| **设计评审** | AI 自动检查 DRC/ERC/DFM | 手动触发 | P1 |
| **供应链集成** | 多制造商直接下单 | 仅导出文件 | P2 |
| **协作功能** | 实时多人协作 | 单用户 | P2 |

### 迭代策略：通过图像识别和实际操作分析改进

#### Phase A: 逆向工程 Flux UI/UX (1周)
1. **图像分析**：截取 Flux 界面截图，分析布局、配色、交互模式
2. **用户流程录制**：观察用户如何使用 Flux 完成设计
3. **功能映射**：将 Flux 功能映射到当前系统

#### Phase B: 复制核心体验 (2周)
1. **Mad Libs 需求输入**：实现结构化引导输入
2. **分步确认流程**：Plan → Schematic → Layout 每步确认
3. **设计预览**：每步显示 AI 生成结果的预览

#### Phase C:差异化竞争 (持续)
1. **开源优势**：KiCad 生态、插件扩展
2. **本地运行**：无需云端，保护知识产权
3. **成本优势**：免费开源 vs $20+/月

---

## 阶段总览

| 阶段 | 名称 | 目标 | 优先级 | 周期 |
|------|------|------|--------|------|
| **Phase 0** | 稳定化 | 修复现有 bug，稳定核心功能 | P0 | 1周 |
| **Phase 1** | 原理图增强 | 提升原理图生成质量和完整性 | P1 | 2周 |
| **Phase 2** | AI 分析引擎 | 需求分析、层数判定、元器件推荐 | P1 | 3周 |
| **Phase 3** | PCB 布局系统 | AI 自动布局算法 | P1 | 3周 |
| **Phase 4** | PCB 布线系统 | AI 自动布线算法 | P1 | 3周 |
| **Phase 5** | DFM 规则引擎 | 制造规则检查、DFM 优化 | P2 | 2周 |
| **Phase 6** | BOM 供应链集成 | 价格、库存、替代元件 | P2 | 2周 |
| **Phase 7** | 制造文件导出 | Gerber、BOM、位置文件一键导出 | P1 | 1周 |
| **Phase 8** | AI Copilot UI | 前端 AI 对话界面重构 | P1 | 3周 |
| **Phase 9** | 集成测试与优化 | 端到端测试、性能优化 | P1 | 2周 |

---

## Phase 0: 稳定化 (1周)

### Task 0.1: BOM 导出 API 错误修复
- 修复 `project_routes.py` 中 BOM 导出返回 500 错误
- 验证：所有 BOM 导出测试通过

### Task 0.2: 原理图组件实例生成修复
- 验证 `_fix_schematic_components()` 正确调用
- 验证生成的原理图在 KiCad GUI 中正常显示

### Task 0.3: 现有测试通过
- 运行全部 pytest 测试，确保无回归

---

## Phase 1: 原理图增强 (2周)

### Task 1.1: 符号库检索增强
- **已完成**: `services/symbol_library.py`
- 索引所有 KiCad 符号，支持关键字搜索

### Task 1.2: 引脚连接算法改进
- 改进 `schematic_v2.py` 的引脚连接逻辑
- 支持多引脚器件的正确连接

### Task 1.3: ERC 验证集成
- 生成原理图后自动运行 ERC 检查
- 返回 ERC 结果并在 UI 中显示

---

## Phase 2: AI 分析引擎 (3周) ⭐ 关键

### Task 2.1: 自然语言需求解析
**Files:** `agent/routes/ai_routes.py`

```python
class RequirementsAnalysisResult(BaseModel):
    circuit_type: str  # "power", "signal", "mixed"
    complexity: str  # "simple", "moderate", "complex"
    estimated_layers: int  # 1, 2, 4, 6, ...
    suggested_components: List[ComponentSpec]
    design_notes: List[str]
```

**API:** `POST /api/v1/ai/analyze-requirements`

```json
{
  "requirements": "I need a USB to 3.3V regulator circuit with LED indicator",
  "target_manufacturer": "JLCPCB",
  "budget_preference": "basic" // "basic", "standard", "premium"
}
```

**返回:**
```json
{
  "circuit_type": "power",
  "complexity": "simple",
  "estimated_layers": 2,
  "components": [
    {"ref": "U1", "symbol": "Regulator_Linear:AMS1117-3.3", "footprint": "SOT223", "reason": "3.3V regulator"},
    {"ref": "C1", "symbol": "Device:C", "footprint": "0805", "reason": "Input decoupling"}
  ],
  "estimated_cost": 2.50,
  "design_notes": ["Add TVS diode for USB protection", "Consider 10mil trace width for USB data lines"]
}
```

### Task 2.2: 自动层数判定引擎 ⭐
**Files:** `agent/services/layer_calculator.py`

```python
class LayerCalculator:
    """根据电路复杂度自动判定 PCB 层数"""

    def calculate_layers(self, circuit: CircuitAnalysis) -> int:
        """
        判定逻辑:
        - 高频信号 > 5GHz 或差分对 > 4对 → 6层
        - 高频信号 > 1GHz 或 > 20个高速IO → 4层
        - 电源 > 3路 或 > 10A电流 → 4层
        - 普通数字电路 → 2层
        - 单面THT或简单电路 → 1层
        """
```

### Task 2.3: AI 元器件推荐引擎 ⭐
**Files:** `agent/services/component_recommender.py` (已创建，需增强)

**增强功能:**
- 调用 LLM 分析需求
- 查询 LCSC API 获取实时价格/库存
- 返回 JLCPCB 基础零件推荐

```python
async def recommend_components_with_lcsc(
    requirements: str,
    lcsc_api_key: str
) -> List[ComponentRecommendation]:
    """带供应链数据的元件推荐"""
    # 1. LLM 分析需求
    # 2. 查询 LCSC API 获取价格/库存
    # 3. 优先推荐 JLCPCB 基础零件
    # 4. 如果缺货，提供替代方案
```

### Task 2.4: KiCad IPC 原理图生成
**Files:** `agent/routes/netlist_routes.py`

增强 `kicad_sch_api` 生成，确保:
- 正确的符号实例块 (symbol instances)
- 正确的导线连接
- KiCad GUI 可正常打开

---

## Phase 3: PCB 布局系统 (3周) ⭐ 关键

### Task 3.1: PCB 布局引擎 ⭐
**Files:** `agent/placement/placement_engine.py` (已创建)

**策略支持:**
- `GRID`: 基础网格布局
- `THERMAL_AWARE`: 热管理优化
- `SIGNAL_INTEGRITY`: 高速信号优化
- `BALANCED`: 综合策略

### Task 3.2: 约束驱动布局 ⭐
**Files:** `agent/placement/constraint_placer.py`

```python
class ConstraintDrivenPlacer:
    """基于设计约束的智能布局"""

    def place_with_constraints(
        self,
        components: List[Component],
        constraints: List[PlacementConstraint]
    ) -> PlacementResult:
        """
        约束类型:
        - 相对位置: "U1 必须在 C1 左边"
        - 间距约束: "U1 和 U2 间距 > 5mm"
        - 区域约束: "电源元件放在左上角"
        - Keepout: "这里不能放元件"
        """
```

### Task 3.3: 布局质量评分
```python
class PlacementScoreCalculator:
    """评估布局质量的多个维度"""

    def calculate_score(self, placement: PlacementResult) -> Dict[str, float]:
        """
        评分维度:
        - 布线长度估计
        - 元件分布均匀度
        - 热分布评分
        - 信号完整性评分
        - DFM 可制造性评分
        """
```

---

## Phase 4: PCB 布线系统 (3周) ⭐ 关键

### Task 4.1: 布线引擎 ⭐
**Files:** `agent/routing/routing_engine.py` (已创建)

**功能:**
- Manhattan 布线 (L-shape)
- 多层布线 + 自动过孔
- 差分对布线
- 蛇形线等长布线

### Task 4.2: 高级布线算法 ⭐
**Files:** `agent/routing/advanced_routing.py`

```python
class AdvancedRouter:
    """高级布线功能"""

    def route_differential_pair(self, net1: Net, net2: Net) -> Route:
        """差分对等长布线"""

    def route_high_speed(self, net: Net, target_impedance: float) -> Route:
        """高速信号阻抗控制布线"""

    def route_power_plane(self, net: Net, current_ma: float) -> Zone:
        """电源平面铺铜"""
```

### Task 4.3: 自动 DRC 检查
```python
async def route_with_drc(
    nets: List[Net],
    design_rules: DesignRules
) -> RoutingResult:
    """
    布线 + 实时 DRC 检查
    - 最小线宽
    - 最小间距
    - 最小过孔
    - 环形圈要求
    """
```

---

## Phase 5: DFM 规则引擎 (2周)

### Task 5.1: JLCPCB 制造规则 ⭐
**Files:** `agent/services/jlcpcb_rules.py`

```python
class JLCPCBDesignRules:
    """JLCPCB 设计规则"""

    LAYER_OPTIONS = {
        "1Layer": {"price": "$5", "turnaround": "2-3 days"},
        "2Layer": {"price": "$10", "turnaround": "2-3 days"},
        "4Layer": {"price": "$30", "turnaround": "5-7 days"},
    }

    DESIGN_RULES = {
        "min_trace_width": 0.1,  # mm
        "min_trace_spacing": 0.1,
        "min_hole_size": 0.3,
        "min_via_drill": 0.3,
        "min_via_outer": 0.6,
        "slot_width": 1.0,
        "edge_clearance": 0.5,
    }

    # 可选表面处理
    SURFACE_FINISH = ["HASL", "ENIG", "OSP"]

    # 基材选项
    BASE_MATERIAL = ["FR-4", "Aluminum", "Rogers"]
```

### Task 5.2: DFM 检查 API
**Files:** `agent/routes/drc_routes.py`

```python
@router.post("/api/v1/drc/check-design")
async def check_dfm(design: PCBSchematic) -> DFMReport:
    """
    DFM 检查:
    1. JLCPCB 可制造性规则
    2. 最小线宽/间距
    3. 钻孔尺寸检查
    4. 铜皮最小面积
    5. 丝印与焊盘距离
    """
```

---

## Phase 6: BOM 供应链集成 (2周)

### Task 6.1: LCSC API 集成 ⭐
**Files:** `agent/services/lcsc_fetcher.py` (已有部分)

**增强功能:**
- 实时价格查询
- 库存数量查询
- 替代元件推荐
- 批量查询优化

### Task 6.2: BOM 成本优化 ⭐
```python
class BOMOptimizer:
    """BOM 成本优化"""

    async def optimize_bom(
        self,
        components: List[ComponentSpec],
        preferences: BOMPreferences
    ) -> BOMOptimizationResult:
        """
        优化策略:
        1. 优先 JLCPCB 基础零件
        2. 批量采购折扣
        3. 库存不足时推荐替代品
        4. 考虑交期影响
        """
```

### Task 6.3: BOM 生成与导出
```python
@router.post("/api/v1/bom/generate")
async def generate_bom(
    components: List[ComponentSpec],
    format: str = "csv"  # "csv", "excel", "json"
) -> BOMDocument:
    """
    生成 BOM 文件:
    - 包含 LCSC 零件号
    - 包含实时价格
    - 包含数据手册链接
    """
```

---

## Phase 7: 制造文件导出 (1周) ⭐

### Task 7.1: 一键导出制造文件 ⭐
**Files:** `agent/routes/export_routes.py`

```python
@router.post("/api/v1/export/manufacturing")
async def export_manufacturing_files(
    project_id: str,
    options: ManufacturingExportOptions
) -> ManufacturingPackage:
    """
    导出完整制造包:
    1. Gerber 文件 (各层)
    2. 钻孔文件 (NPTH + PTH)
    3. 位置文件 (Pick and Place)
    4. BOM 文件
    5. 装配图 (PDF)
    """
    return ManufacturingPackage(
        gerber_zip="path/to/gerber.zip",
        bom="path/to/bom.csv",
        pick_place="path/to/pos.csv",
        drill_files="path/to/drill.zip",
        views=["path/to/front.pdf", "path/to/back.pdf"]
    )
```

### Task 7.2: 直接下单集成 (可选)
```python
@router.post("/api/v1/order/jlcpcb")
async def create_jlcpcb_order(
    manufacturing_package: ManufacturingPackage,
    jlcpcb_api_key: str
) -> OrderStatus:
    """
    直接向 JLCPCB 下单:
    - 上传 Gerber
    - 选择参数 (层数、尺寸、表面处理)
    - 自动填入 BOM
    - 返回价格和交期
    """
```

---

## Phase 8: AI Copilot UI (3周)

### Task 8.1: 前端 AI 对话界面 ⭐
**Files:** `web/src/components/ai-copilot/`

```typescript
// AI Copilot 组件
interface AICopilotProps {
  onRequirementsSubmit: (req: string) => Promise<CircuitDesign>;
  onSuggestionAccept: (suggestion: Suggestion) => void;
}

// 聊天界面功能:
// 1. 自然语言输入需求
// 2. AI 逐步确认 (元件选择、参数调整)
// 3. 显示设计预览
// 4. 一键生成原理图 + PCB
```

### Task 8.2: 设计向导流程
**Files:** `web/src/pages/design-wizard/`

```
Step 1: 需求输入
  └─> "我想做一个 USB 充电电路，5V 3A"

Step 2: AI 分析 + 确认
  └─> 显示推荐的元件清单
  └─> 用户可以修改/替换

Step 3: 参数配置
  └─> PCB 尺寸 (或 AI 推荐)
  └─> 层数 (AI 已判定)
  └─> 制造选项

Step 4: 生成 + 预览
  └─> AI 生成原理图
  └─> AI 布局 + 布线
  └─> 3D 预览

Step 5: 导出
  └─> 制造文件下载
  └─> 直接下单
```

### Task 8.3: KiCad 协同编辑
```typescript
// KiCad IPC 实时同步
interface KiCadSyncProps {
  projectId: string;
  onSchematicChange: (diff: SchematicDiff) => void;
  onPCBChange: (diff: PCBDiff) => void;
  syncMode: "realtime" | "ondemand";
}
```

---

## Phase 9: 集成测试与优化 (2周)

### Task 9.1: 端到端测试
```python
def test_full_flow():
    """
    完整流程测试:
    1. 需求输入 → "USB to 3.3V regulator with LED"
    2. AI 分析 → 确认元件清单
    3. 生成原理图 → 验证 ERC
    4. PCB 布局 → 验证无重叠
    5. PCB 布线 → 验证 DRC
    6. DFM 检查 → 验证可制造性
    7. 导出制造文件 → 验证文件完整
    """
```

### Task 9.2: 性能基准测试
```python
def test_placement_performance():
    """50元件布局 < 500ms"""
    def test_routing_performance():
    """100网络布线 < 2s"""
    def test_full_generation():
    """完整流程 < 30s"""
```

### Task 9.3: 竞品对比测试
```
对比项目:
1. Flux.ai
2. Cadence Allegro X AI
3. Altium Copilot

测试指标:
- 生成时间
- 布局质量 (布线长度、过孔数)
- DFM 通过率
- BOM 成本
```

---

## 核心 API 端点清单

### AI 分析
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/ai/analyze-requirements` | POST | 自然语言需求分析 |
| `/api/v1/ai/calculate-layers` | POST | 自动层数判定 |
| `/api/v1/ai/recommend-components` | POST | AI 元器件推荐 |

### PCB 生成
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/pcb/generate` | POST | 完整 PCB 生成 |
| `/api/v1/pcb/placement` | POST | 元器件布局 |
| `/api/v1/pcb/routing` | POST | 走线布线 |
| `/api/v1/pcb/optimize-placement` | POST | 布局优化 |

### 设计与验证
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/drc/check-design` | POST | DFM 设计规则检查 |
| `/api/v1/erc/run` | POST | ERC 电气规则检查 |
| `/api/v1/drc/run` | POST | DRC 设计规则检查 |

### 导出与下单
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/export/manufacturing` | POST | 制造文件导出 |
| `/api/v1/bom/generate` | POST | BOM 生成 |
| `/api/v1/order/jlcpcb` | POST | 直接下单 (可选) |

---

## 关键文件结构

```
kicad-ai-auto/agent/
├── services/
│   ├── layer_calculator.py      # ⭐ NEW: 自动层数判定
│   ├── component_recommender.py  # ✅ EXISTING: 元器件推荐
│   ├── lcsc_fetcher.py          # ✅ EXISTING: LCSC API
│   ├── bom_optimizer.py         # ⭐ NEW: BOM 优化
│   └── jlcpcb_rules.py          # ⭐ NEW: 制造规则
├── placement/
│   ├── placement_engine.py      # ✅ EXISTING: 基础布局
│   └── constraint_placer.py     # ⭐ NEW: 约束驱动布局
├── routing/
│   ├── routing_engine.py       # ✅ EXISTING: 基础布线
│   └── advanced_routing.py     # ⭐ NEW: 高级布线
├── routes/
│   ├── ai_routes.py           # ✅ EXISTING: AI 分析
│   ├── pcb_gen_routes.py      # ✅ EXISTING: PCB 生成
│   ├── drc_routes.py          # ⭐ NEW: DRC 检查
│   └── export_routes.py        # ⭐ NEW: 导出
└── generators/
    └── schematic_v2.py        # ✅ EXISTING: 原理图生成
```

---

## 里程碑

| 里程碑 | 目标日期 | 完成标准 |
|--------|---------|---------|
| M0: 稳定运行 | Week 1 | 所有现有测试通过 |
| M1: 原理图增强 | Week 3 | ERC 检查可用 |
| M2: AI 分析引擎 | Week 6 | 需求分析 + 层数判定 |
| M3: PCB 布局布线 | Week 9 | 完整 PCB 生成 |
| M4: DFM + BOM | Week 11 | 制造可行性检查 |
| M5: 制造文件 | Week 12 | 一键导出 |
| M6: AI Copilot UI | Week 15 | 对话式设计 |
| M7: 完整集成 | Week 17 | E2E 测试通过 |

---

## 与 Flux.ai 功能对比

| 功能 | Flux.ai | 当前项目 | 状态 |
|------|---------|---------|------|
| 自然语言输入 | ✅ | ⚠️ 基础 | Phase 2 |
| AI 元器件推荐 | ✅ | ⚠️ 基础 | Phase 2 |
| 自动层数判定 | ✅ | ❌ | Phase 2 |
| 原理图生成 | ✅ | ⚠️ 基础 | Phase 1 |
| AI 布局 | ✅ | ⚠️ 基础 | Phase 3 |
| AI 布线 | ✅ | ⚠️ 基础 | Phase 4 |
| DFM 检查 | ✅ | ❌ | Phase 5 |
| BOM 优化 | ✅ | ❌ | Phase 6 |
| 制造文件导出 | ✅ | ⚠️ 基础 | Phase 7 |
| 直接下单 | ✅ | ❌ | Phase 7 |
| 浏览器端设计 | ✅ | ✅ | 现有 |

---

## 技术风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| KiCad IPC API 限制 | 某些操作无法完成 | 保留 PyAutoGUI 后备 |
| LLM 生成质量不稳定 | 设计可能有问题 | 保留人工审核 |
| LCSC API 限流 | 价格查询失败 | 本地缓存 + 降级 |
| 布局算法性能 | 大板太慢 | 分布式计算 |
| 制造文件兼容性 | 板厂不认 | 多种格式支持 |

---

## 商业化考虑

1. **定价模式**
   - 免费: 基础功能 (5个项目/月)
   - Pro: $19/月 (无限项目 + 优先生成)
   - Enterprise: 私有部署 + API

2. **收入来源**
   - 硬件销售佣金 (JLCPCB 等)
   - Pro 订阅费
   - 企业定制开发

3. **竞争优势**
   - 开源可定制
   - 中文界面
   - 本地部署选项
   - 深度 KiCad 集成
