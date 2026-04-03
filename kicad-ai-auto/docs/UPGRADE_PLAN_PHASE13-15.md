# KiCad for Chrome 升级开发计划

**版本**: v1.1.0
**计划周期**: 10 周
**目标**: 将布线质量从 4/10 提升至 8/10

---

## 一、项目目标

### 核心目标
- 🎯 **布线质量**: 4/10 → 8/10
- 🎯 **差分对支持**: 0% → 100%
- 🎯 **热分析能力**: 基础 → 专业级
- 🎯 **AI辅助**: 概念 → 实用化

### 竞争力提升
| 维度 | 当前 | 目标 | 竞品(Flux.ai) |
|------|------|------|---------------|
| 自动布线 | 4/10 | 8/10 | 8/10 |
| 差分对 | ❌ | ✅ | ✅ |
| 热分析 | ⚠️ 基础 | ✅ 专业 | ✅ 云端 |
| AI辅助 | ⚠️ 概念 | ✅ 实用 | ✅ 成熟 |

---

## 二、Phase 13: 专业布线引擎 (4周)

### 13-1: 差分对自动布线器 (3天)

**文件**: `agent/routing/differential_pair_router.py`

```python
class DifferentialPairRouter:
    """差分对布线器 - 支持USB/PCIe/HDMI等高速信号"""

    def __init__(self, pcb_data: PCBData, constraints: DifferentialConstraints):
        self.pcb = pcb_data
        self.constraints = constraints  # 间距、阻抗、容差

    def route_differential_pair(
        self,
        pin1: Pad,
        pin2: Pad,
        layer: str
    ) -> tuple[list[Point], list[Point]]:
        """布线差分对，返回两条走线的点序列"""

    def tune_length(
        self,
        trace_p: list[Point],
        trace_n: list[Point],
        tolerance: float = 0.127  # 5mil
    ) -> tuple[list[Point], list[Point]]:
        """长度调谐，确保等长匹配"""

    def calculate_impedance(
        self,
        trace_width: float,
        trace_spacing: float,
        layer: str
    ) -> float:
        """计算差分阻抗"""
```

**API端点**:
- `POST /api/v1/routing/differential-pair` - 布线差分对
- `POST /api/v1/routing/differential-pair/tune` - 长度调谐

**验收标准**:
- ✅ 等长匹配误差 < 5mil
- ✅ 等距耦合偏差 < 10%
- ✅ 支持 90Ω/100Ω 阻抗控制

---

### 13-2: 阻抗约束布线 (2天)

**文件**: `agent/routing/impedance_calculator.py`

```python
class ImpedanceCalculator:
    """阻抗计算器 - 基于层叠结构计算线宽"""

    def calculate_single_ended_width(
        self,
        target_impedance: float,  # 如 50Ω
        layer: str,
        copper_weight: float = 1.0  # oz
    ) -> float:
        """计算单端阻抗所需线宽"""

    def calculate_differential_width_spacing(
        self,
        target_impedance: float,  # 如 100Ω
        layer: str
    ) -> tuple[float, float]:
        """计算差分阻抗所需线宽和间距"""

    def get_stackup_presets(self) -> list[StackupPreset]:
        """获取预设层叠配置 (4层/6层/8层)"""
```

**API端点**:
- `GET /api/v1/routing/impedance/calculate` - 计算阻抗
- `GET /api/v1/routing/impedance/stackups` - 获取层叠预设

---

### 13-3: 布线平滑后处理 (2天)

**文件**: `agent/routing/trace_smoother.py`

```python
class TraceSmoother:
    """布线平滑器 - 消除锯齿和锐角"""

    def smooth_trace(
        self,
        points: list[Point],
        method: str = "arc"  # arc/bezier/chaikin
    ) -> list[Point]:
        """平滑走线"""

    def convert_corners_to_arcs(
        self,
        points: list[Point],
        min_radius: float = 0.5  # mm
    ) -> list[Point | Arc]:
        """将锐角转换为圆弧"""

    def remove_redundant_points(
        self,
        points: list[Point],
        tolerance: float = 0.01
    ) -> list[Point]:
        """移除冗余点"""
```

**效果对比**:
```
原始布线:  /|/|/|/|/|  (锯齿状)
平滑后:    ∿∿∿∿∿∿∿    (圆弧过渡)
```

---

### 13-4: 多层布线策略 (3天)

**文件**: `agent/routing/layer_strategy.py`

```python
class LayerStrategy:
    """多层布线策略 - 层分配和过孔优化"""

    def assign_layers(
        self,
        nets: list[Net],
        constraints: LayerConstraints
    ) -> dict[str, list[str]]:
        """分配网络到层"""

    def optimize_via_placement(
        self,
        trace: list[Point],
        layer_from: str,
        layer_to: str
    ) -> list[Via]:
        """优化过孔放置"""

    def create_shielding_vias(
        self,
        sensitive_net: str,
        spacing: float = 1.0  # mm
    ) -> list[Via]:
        """创建屏蔽过孔"""
```

**策略规则**:
| 层 | 用途 | 典型网络 |
|----|------|----------|
| L1 (Top) | 信号/元件 | 高速信号、关键网络 |
| L2 (GND) | 地参考 | GND |
| L3 (PWR) | 电源分割 | VCC, 3V3, 5V |
| L4 (Bottom) | 信号/元件 | 一般信号 |

---

### 13-5: 电源/地平面自动铺铜 (3天)

**文件**: `agent/routing/copper_pour.py`

```python
class CopperPourGenerator:
    """铺铜生成器 - 自动填充电源和地平面"""

    def generate_copper_pour(
        self,
        layer: str,
        net: str,
        clearance: float = 0.2,  # mm
        thermal_spoke_width: float = 0.5
    ) -> Polygon:
        """生成铺铜区域"""

    def create_thermal_relief(
        self,
        pad: Pad,
        spoke_count: int = 4,
        spoke_width: float = 0.3
    ) -> list[Line]:
        """创建热焊盘连接"""

    def add_stitching_vias(
        self,
        copper_pour: Polygon,
        spacing: float = 2.0,  # mm
        drill_size: float = 0.3
    ) -> list[Via]:
        """添加缝合过孔"""
```

**效果**:
```
原始: 破碎的地平面，大量碎铜
优化后: 完整的GND平面 + 均匀分布的缝合过孔
```

---

## 三、Phase 14: 高级分析集成 (3周)

### 14-1: 热仿真引擎 (3天)

**文件**: `agent/analysis/thermal_simulator.py`

```python
class ThermalSimulator:
    """热仿真引擎 - 基于有限元分析"""

    def analyze_thermal(
        self,
        pcb_data: PCBData,
        power_distribution: dict[str, float],
        ambient_temp: float = 25.0
    ) -> ThermalResult:
        """执行热分析"""

    def identify_hotspots(
        self,
        threshold_temp: float = 85.0
    ) -> list[Hotspot]:
        """识别热点区域"""

    def suggest_thermal_optimization(
        self,
        hotspot: Hotspot
    ) -> list[ThermalSuggestion]:
        """提供散热优化建议"""
```

**API端点**:
- `POST /api/v1/analysis/thermal` - 热分析
- `GET /api/v1/analysis/thermal/hotspots` - 热点识别

---

### 14-2: 信号完整性增强 (2天)

**文件**: `agent/analysis/signal_integrity.py`

```python
class SignalIntegrityAnalyzer:
    """信号完整性分析器 - 增强版"""

    def load_ibis_model(
        self,
        model_path: str
    ) -> IBISModel:
        """加载IBIS模型"""

    def run_eye_diagram(
        self,
        net: str,
        data_rate: float,  # Gbps
        pattern: str = "PRBS7"
    ) -> EyeDiagramResult:
        """运行眼图分析"""

    def analyze_crosstalk(
        self,
        victim_net: str,
        aggressor_nets: list[str]
    ) -> CrosstalkResult:
        """分析串扰"""
```

---

### 14-3: EMC预认证检查 (3天)

**文件**: `agent/analysis/emc_analyzer.py`

```python
class EMCAnalyzer:
    """EMC分析器 - 预认证检查"""

    def check_emc_compliance(
        self,
        pcb_data: PCBData,
        standard: str = "FCC_Part15"
    ) -> EMCResult:
        """检查EMC合规性"""

    def predict_radiated_emission(
        self,
        frequency_range: tuple[float, float] = (30e6, 1e9)
    ) -> list[EmissionPeak]:
        """预测辐射发射"""

    def suggest_emc_improvements(
        self,
        issues: list[EMCIssue]
    ) -> list[EMCSuggestion]:
        """提供EMC改进建议"""
```

---

## 四、Phase 15: AI辅助优化 (3周)

### 15-1: 布局质量评分AI (2天)

**文件**: `agent/ai/layout_scorer.py`

```python
class LayoutScorer:
    """AI驱动的布局质量评分"""

    def score_layout(
        self,
        pcb_data: PCBData
    ) -> LayoutScore:
        """评估布局质量 (0-100分)"""

    def analyze_routing_quality(self) -> float:
        """分析布线质量"""

    def analyze_emi_risk(self) -> float:
        """分析EMI风险"""

    def analyze_thermal_distribution(self) -> float:
        """分析热分布"""
```

**评分维度**:
| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 布线整齐度 | 25% | 走线角度、间距一致性 |
| 信号完整性 | 20% | 阻抗匹配、串扰控制 |
| 热管理 | 20% | 热分布均匀度、散热路径 |
| EMC合规 | 20% | 回路面积、屏蔽效果 |
| 可制造性 | 15% | 间距、线宽、过孔密度 |

---

### 15-2: 自动布局优化建议 (3天)

**文件**: `agent/ai/layout_optimizer.py`

```python
class LayoutOptimizer:
    """AI驱动的布局优化"""

    def suggest_improvements(
        self,
        pcb_data: PCBData,
        focus: str = "all"  # all/emi/thermal/si
    ) -> list[Improvement]:
        """提供优化建议"""

    def auto_optimize(
        self,
        constraints: OptimizationConstraints
    ) -> PCBData:
        """自动优化布局"""

    def explain_optimization(
        self,
        improvement: Improvement
    ) -> str:
        """解释优化原因 (AI生成)"""
```

---

### 15-3: 一键优化向导 (2天)

**文件**: `web/src/components/OptimizationWizard.tsx`

```tsx
interface OptimizationWizardProps {
  projectId: string;
  onComplete: (result: OptimizationResult) => void;
}

// 优化步骤:
// 1. DRC修复 - 自动修复所有DRC错误
// 2. 布线优化 - 平滑走线、优化过孔
// 3. 铺铜填充 - 自动填充电源/地平面
// 4. 热优化 - 添加散热铺铜和过孔
// 5. EMC检查 - 识别并修复EMI隐患
```

---

## 五、时间表

```
Week 1-2:  Phase 13-1 ~ 13-3 (差分对 + 阻抗 + 平滑)
Week 3-4:  Phase 13-4 ~ 13-5 (多层策略 + 铺铜)
Week 5-6:  Phase 14-1 ~ 14-2 (热仿真 + SI增强)
Week 7:    Phase 14-3 (EMC检查)
Week 8-9:  Phase 15-1 ~ 15-2 (AI评分 + 优化建议)
Week 10:   Phase 15-3 (一键优化向导) + 集成测试
```

---

## 六、里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| M1 | Week 2 | 差分对布线器可用 |
| M2 | Week 4 | 专业布线引擎完成 |
| M3 | Week 7 | 高级分析集成完成 |
| M4 | Week 10 | AI辅助优化完成，v1.1.0发布 |

---

## 七、资源需求

### 人力
- 后端开发: 1人 (Python/FastAPI)
- 前端开发: 1人 (React/TypeScript)
- 算法工程师: 0.5人 (布线算法)

### 依赖
- Python库: numpy, scipy, shapely, networkx
- 前端库: konva, zustand
- 外部API: 无 (完全本地化)

---

## 八、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 差分对算法复杂度高 | 中 | 高 | 先实现基础版本，迭代优化 |
| 热仿真精度不足 | 中 | 中 | 使用简化模型，明确精度限制 |
| AI模型训练数据不足 | 高 | 低 | 使用规则引擎 + 启发式算法 |

---

## 九、验收标准

### 最终目标达成标准

| 指标 | 当前值 | 目标值 | 验收方法 |
|------|--------|--------|----------|
| 布线质量评分 | 4/10 | 8/10 | 专家评审 + 自动化测试 |
| 差分对成功率 | 0% | 95% | 测试用例通过率 |
| 热分析精度 | - | ±10°C | 与专业工具对比 |
| DRC一次通过率 | 60% | 90% | 制造验证 |

### 测试用例

```python
# tests/test_upgrade_phase13.py

def test_differential_pair_routing():
    """测试差分对布线"""
    router = DifferentialPairRouter(pcb, constraints)
    trace_p, trace_n = router.route_differential_pair(pin1, pin2, "F.Cu")

    # 验证等长
    length_diff = abs(len(trace_p) - len(trace_n))
    assert length_diff < 0.127  # 5mil

    # 验证等距
    for p, n in zip(trace_p, trace_n):
        assert abs(distance(p, n) - constraints.spacing) < 0.05

def test_trace_smoothing():
    """测试布线平滑"""
    original = load_trace("jagged_trace.json")
    smoothed = TraceSmoother().smooth_trace(original)

    # 验证无锐角
    for i in range(1, len(smoothed) - 1):
        angle = calculate_angle(smoothed[i-1], smoothed[i], smoothed[i+1])
        assert angle > 90  # 无锐角

def test_copper_pour():
    """测试铺铜生成"""
    generator = CopperPourGenerator(pcb)
    pour = generator.generate_copper_pour("F.Cu", "GND")

    # 验证避让
    for pad in pcb.pads:
        if pad.net != "GND":
            assert distance(pour, pad) >= clearance
```

---

## 十、后续规划 (v1.2.0+)

- **v1.2.0**: 云端协作 + 版本控制增强
- **v1.3.0**: 3D PCB 预览 + MCAD集成
- **v2.0.0**: 完整的EDA套件 (原理图 + PCB + 仿真)
