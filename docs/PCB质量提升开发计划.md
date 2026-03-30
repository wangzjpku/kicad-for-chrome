# PCB质量提升开发计划

**创建日期**: 2026-03-29
**最后更新**: 2026-03-30
**目标**: 利用开源资源，快速提升PCB生成质量至专业水平

---

## ✅ Phase 1-4 完成状态 (2026-03-30)

### Phase 1: 智能布局引擎 ✅ 完成
- [x] 创建智能布局引擎 (`agent/placement/smart_placement_engine.py`)
- [x] 实现组件分类算法 (MCU/连接器/被动元件等)
- [x] 实现货架装箱算法 (NFDH)
- [x] 实现力导向松弛算法
- [x] 实现边缘放置算法 (连接器放板边)
- [x] 集成到 PCB 生成 API (`ai_routes.py`)
- [x] 创建测试用例 (15个测试全部通过)

### Phase 2: 布线引擎升级 ✅ 完成
- [x] 创建布线引擎 (`agent/routing/routing_engine.py`)
- [x] 实现45度走线支持
- [x] 实现多层布线（自动过孔）
- [x] 实现差分对布线
- [x] 集成到 PCB 生成 API
- [x] 创建测试用例 (22个测试全部通过)

### Phase 3: DRC规则扩展 ✅ 完成
- [x] 创建高级DRC引擎 (`agent/drc/advanced_drc.py`)
- [x] 扩展规则至30+条
- [x] 支持网络类规则 (Power/Signal/HighSpeed/RF)
- [x] 支持JLCPCB/PCBWay制造规范
- [x] 集成到 DRC API 路由
- [x] 创建测试用例 (22个测试全部通过)

### Phase 4: 多层板支持 ✅ 完成
- [x] 创建层叠管理器 (`agent/pcb/layer_stackup.py`)
- [x] 支持2层/4层/6层板模板
- [x] 实现阻抗计算（单端/差分）
- [x] 实现线宽反推计算
- [x] 创建测试用例 (28个测试全部通过)

### W6: 集成测试与前端 ✅ 完成
- [x] 创建端到端集成测试 (15个测试全部通过)
- [x] 前端组件开发 (LayerStackupSelector, DRCReport, ImpedanceCalculator)
- [x] API服务集成

### 算法增强 ✅ 完成
- [x] A*避障布线 (`agent/routing/astar_router.py`)
- [x] 自动铺铜引擎 (`agent/routing/copper_pour.py`)
- [x] 热焊盘支持
- [x] 创建测试用例 (24个测试全部通过)

---

## 📊 测试统计

| 模块 | 测试文件 | 测试数量 | 状态 |
|------|---------|---------|------|
| 智能布局 | test_smart_placement.py | 15 | ✅ |
| 布线引擎 | test_routing_engine.py | 22 | ✅ |
| DRC规则 | test_advanced_drc.py | 22 | ✅ |
| 层叠管理 | test_layer_stackup.py | 28 | ✅ |
| 端到端 | test_e2e_integration.py | 15 | ✅ |
| 算法增强 | test_algorithm_enhancement.py | 24 | ✅ |
| **总计** | | **126** | ✅ |

---

## 一、问题分类与解决方案

### 1.1 可直接开发解决（无需模型训练）

| 问题 | 根本原因 | 解决方案 | 开源资源 |
|------|---------|---------|---------|
| **布局质量差** | 随机网格布局 | 约束驱动+货架装箱算法 | kicad-auto-designer |
| **走线只有直角** | Manhattan算法 | 45度路径优化 | straight-line-solver |
| **无自动布线** | 依赖KiCad FreeRouting | 集成独立布线引擎 | tscircuit-autorouter |
| **无障碍物避让** | 无避障算法 | A*+力导向优化 | tscircuit-autorouter |
| **仅支持2层板** | 数据模型限制 | 扩展层叠定义 | circuit-json |
| **DRC规则少** | 仅5条基础规则 | 扩展规则引擎 | FreeRouting BoardRules |

### 1.2 需要模型训练

| 问题 | 解决方案 | 数据需求 | 训练周期 |
|------|---------|---------|---------|
| **智能布局推荐** | 布局质量评分模型 | 5,000+布局案例 | 1个月 |
| **高密度布线优化** | 强化学习布线 | 10,000+布线案例 | 3个月 |
| **SI/PI分析** | 阻抗预测模型 | S参数10,000+ | 2个月 |
| **热设计优化** | 温度预测CNN | 热仿真1,000+ | 2个月 |

---

## 二、开发计划（算法可实现部分）

### Phase 1: 布局引擎升级（1周）

#### 目标
- 实现约束驱动布局
- 支持连接器边缘放置
- 去耦电容自动靠近电源引脚

#### 集成资源
- **kicad-auto-designer** (nabheet/kicad-auto-designer)
- 语言: Python
- 许可证: GPLv3
- 核心算法: 货架装箱 + 力导向松弛

#### 实现步骤

**Step 1: 移植核心算法** (2天)
```python
# 文件: agent/placement/smart_placement_engine.py

from dataclasses import dataclass
from typing import List, Dict, Tuple
import math

@dataclass
class Component:
    reference: str
    footprint: str
    width: float
    height: float
    category: str  # MCU, Power, Connector, etc.
    nets: List[str]

class SmartPlacementEngine:
    """
    基于 kicad-auto-designer 的智能布局引擎
    """

    # 组件分类优先级
    CATEGORY_PRIORITY = {
        'Power': 1,
        'MCU': 2,
        'Wireless': 3,
        'Motor': 4,
        'Interface': 5,
        'Passive': 6
    }

    # 边缘放置规则
    EDGE_RULES = {
        'USB': {'edge': 'bottom', 'orientation': 0},
        'UART': {'edge': 'right', 'orientation': 90},
        'ANTENNA': {'edge': 'bottom-left', 'orientation': 0},
        'POWER': {'edge': 'bottom', 'orientation': 0},
    }

    def __init__(self, board_width: float, board_height: float):
        self.board_width = board_width
        self.board_height = board_height
        self.margin = 4.0  # mm
        self.spacing = 2.0  # mm

    def place(self, components: List[Component]) -> Dict[str, Tuple[float, float]]:
        """
        主布局方法

        Returns:
            {reference: (x, y)} 位置字典
        """
        # 1. 分类组件
        categorized = self._categorize_components(components)

        # 2. 提取边缘组件
        edge_components, inner_components = self._separate_edge_components(categorized)

        # 3. 货架装箱布局内部组件
        inner_positions = self._shelf_packing(inner_components)

        # 4. 边缘组件放置
        edge_positions = self._place_edge_components(edge_components)

        # 5. 力导向优化
        all_positions = {**inner_positions, **edge_positions}
        optimized = self._force_directed_relaxation(all_positions, components)

        # 6. 2D压缩
        compacted = self._compact_layout(optimized, components)

        return compacted

    def _categorize_components(self, components: List[Component]) -> Dict[str, List[Component]]:
        """按电气功能分类组件"""
        categories = {}
        for comp in components:
            cat = self._detect_category(comp)
            comp.category = cat
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(comp)
        return categories

    def _detect_category(self, comp: Component) -> str:
        """检测组件类别"""
        ref = comp.reference.upper()
        footprint = comp.footprint.lower()

        # 连接器检测
        if any(kw in ref for kw in ['USB', 'J_', 'JTAG', 'UART', 'DEBUG']):
            return 'Interface'
        if 'antenna' in footprint or 'ANT' in ref:
            return 'Antenna'

        # 电源检测
        if any(kw in footprint for kw in ['ldo', 'dcdc', 'pmic', 'mp1584', 'ams1117']):
            return 'Power'

        # MCU检测
        if any(kw in footprint for kw in ['qfn', 'qfp', 'bga', 'ufqfpn']):
            return 'MCU'

        # 无线模块
        if any(kw in footprint for kw in ['esp', 'wifi', 'ble', 'rf']):
            return 'Wireless'

        # 被动元件
        if ref.startswith(('R', 'C', 'L')):
            return 'Passive'

        return 'Other'

    def _shelf_packing(self, components: List[Component]) -> Dict[str, Tuple[float, float]]:
        """
        货架装箱算法 (Next-Fit Decreasing Height)
        """
        # 按优先级和面积排序
        sorted_comps = sorted(
            components,
            key=lambda c: (self.CATEGORY_PRIORITY.get(c.category, 99),
                          -(c.width * c.height))
        )

        positions = {}
        target_width = math.sqrt(self.board_width * self.board_height * 0.8)

        current_x = self.margin
        current_y = self.margin
        row_height = 0

        for comp in sorted_comps:
            # 检查是否需要换行
            if current_x + comp.width > target_width:
                current_x = self.margin
                current_y += row_height + self.spacing
                row_height = 0

            positions[comp.reference] = (current_x, current_y)

            current_x += comp.width + self.spacing
            row_height = max(row_height, comp.height)

        return positions

    def _force_directed_relaxation(
        self,
        positions: Dict[str, Tuple[float, float]],
        components: List[Component],
        iterations: int = 20
    ) -> Dict[str, Tuple[float, float]]:
        """
        力导向松弛算法 - 消除重叠
        """
        comp_dict = {c.reference: c for c in components}

        for _ in range(iterations):
            forces = {ref: [0.0, 0.0] for ref in positions}

            # 计算斥力
            refs = list(positions.keys())
            for i, ref1 in enumerate(refs):
                for ref2 in refs[i+1:]:
                    x1, y1 = positions[ref1]
                    x2, y2 = positions[ref2]

                    dx = x2 - x1
                    dy = y2 - y1
                    dist = math.sqrt(dx*dx + dy*dy) + 0.001

                    # 斥力大小
                    c1, c2 = comp_dict[ref1], comp_dict[ref2]
                    min_dist = (c1.width + c2.width) / 2 + self.spacing

                    if dist < min_dist:
                        force = (min_dist - dist) * 0.1
                        forces[ref1][0] -= force * dx / dist
                        forces[ref1][1] -= force * dy / dist
                        forces[ref2][0] += force * dx / dist
                        forces[ref2][1] += force * dy / dist

            # 应用力
            for ref in positions:
                x, y = positions[ref]
                positions[ref] = (
                    max(self.margin, min(self.board_width - self.margin, x + forces[ref][0])),
                    max(self.margin, min(self.board_height - self.margin, y + forces[ref][1]))
                )

        return positions
```

**Step 2: 集成到现有API** (1天)
```python
# 修改: agent/routes/ai_routes.py

def generate_pcb_layout(schematic_data, pcb_params):
    # 替换简单网格布局
    engine = SmartPlacementEngine(
        board_width=pcb_params.get('width', 100),
        board_height=pcb_params.get('height', 80)
    )

    components = [Component(**c) for c in schematic_data.get('components', [])]
    positions = engine.place(components)

    # 应用位置
    for comp in components:
        comp.position = positions[comp.reference]
```

**Step 3: 测试验证** (1天)
- 创建测试用例
- 对比旧算法与新算法的布局质量
- DRC通过率测试

---

### Phase 2: 布线引擎集成（2周）

#### 目标
- 实现45度走线
- 自动避障布线
- 多层板支持

#### 集成资源
- **tscircuit-autorouter** (tscircuit/tscircuit-autorouter)
- 语言: TypeScript
- 许可证: MIT
- 核心算法: A* + 力导向 + 路径简化

#### 架构设计

```
布线引擎架构
├── Python后端
│   ├── 数据转换层: circuit_json ↔ SimpleRouteJson
│   └── 子进程调用: node tscircuit-autorouter
│
├── TypeScript布线引擎
│   ├── SingleHighDensityRouteSolver (A*寻路)
│   ├── MultiHeadPolyLineIntraNodeSolver (力导向)
│   └── SingleSimplifiedPathSolver5_Deg45 (45度简化)
│
└── 输出处理
    └── 转换为KiCad格式
```

#### 实现步骤

**Step 1: 安装依赖** (0.5天)
```bash
cd kicad-ai-auto
npm init -y
npm install @tscircuit/capacity-autorouter
```

**Step 2: 创建Python-TypeScript桥接** (3天)
```python
# 文件: agent/routing/tscircuit_bridge.py

import json
import subprocess
from typing import Dict, Any, List

class TSCircuitRouter:
    """
    tscircuit-autorouter Python桥接
    """

    def __init__(self):
        self.router_path = "node_modules/@tscircuit/capacity-autorouter"

    def route(self, pcb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行自动布线

        Args:
            pcb_data: KiCad格式PCB数据

        Returns:
            包含走线结果的PCB数据
        """
        # 1. 转换为SimpleRouteJson格式
        simple_route_json = self._convert_to_simple_route_json(pcb_data)

        # 2. 保存输入文件
        with open("temp_input.json", "w") as f:
            json.dump(simple_route_json, f)

        # 3. 调用TypeScript布线器
        result = subprocess.run(
            ["node", "router_worker.js", "temp_input.json", "temp_output.json"],
            capture_output=True,
            text=True
        )

        # 4. 读取结果
        with open("temp_output.json", "r") as f:
            routed_json = json.load(f)

        # 5. 转换回KiCad格式
        return self._convert_to_kicad_format(routed_json, pcb_data)

    def _convert_to_simple_route_json(self, pcb_data: Dict) -> Dict:
        """
        转换KiCad格式到tscircuit SimpleRouteJson格式
        """
        obstacles = []
        connections = []

        # 转换元件为障碍物
        for comp in pcb_data.get('components', []):
            obstacles.append({
                "type": "rect",
                "layers": [0],  # F.Cu
                "center": {"x": comp['position']['x'], "y": comp['position']['y']},
                "width": comp.get('width', 5),
                "height": comp.get('height', 5),
                "connectedTo": []
            })

        # 转换网络为连接
        for net in pcb_data.get('nets', []):
            if len(net.get('pins', [])) >= 2:
                connections.append({
                    "name": net['name'],
                    "points": [
                        {"x": net['pins'][0]['x'], "y": net['pins'][0]['y'], "z": 0},
                        {"x": net['pins'][1]['x'], "y": net['pins'][1]['y'], "z": 0}
                    ]
                })

        return {
            "layerCount": pcb_data.get('layers', 2),
            "minTraceWidth": 0.25,
            "obstacles": obstacles,
            "connections": connections,
            "bounds": {
                "minX": 0,
                "minY": 0,
                "maxX": pcb_data.get('width', 100),
                "maxY": pcb_data.get('height', 80)
            }
        }

    def _convert_to_kicad_format(self, routed_json: Dict, original: Dict) -> Dict:
        """
        转换tscircuit结果回KiCad格式
        """
        traces = []

        for trace in routed_json.get('traces', []):
            kicad_trace = {
                "id": trace.get('trace_id', f"trace-{len(traces)}"),
                "net": trace.get('net_name', ''),
                "layer": "F.Cu" if trace.get('z', 0) == 0 else "B.Cu",
                "width": trace.get('thickness', 0.25),
                "points": trace.get('route', [])
            }
            traces.append(kicad_trace)

        result = original.copy()
        result['tracks'] = traces
        return result
```

**Step 3: 创建TypeScript布线Worker** (2天)
```typescript
// 文件: router_worker.ts

import { CapacityMeshSolver } from "@tscircuit/capacity-autorouter"
import * as fs from "fs"

const inputFile = process.argv[2]
const outputFile = process.argv[3]

// 读取输入
const input = JSON.parse(fs.readFileSync(inputFile, "utf-8"))

// 创建求解器
const solver = new CapacityMeshSolver(input)

// 运行求解
while (!solver.solved && !solver.failed) {
    solver.step()
}

// 输出结果
if (solver.solved) {
    const output = solver.getOutputSimpleRouteJson()
    fs.writeFileSync(outputFile, JSON.stringify(output, null, 2))
    console.log("Routing completed successfully")
} else {
    console.error("Routing failed")
    process.exit(1)
}
```

**Step 4: 集成到现有系统** (2天)
```python
# 修改: agent/routes/ai_routes.py

from routing.tscircuit_bridge import TSCircuitRouter

def generate_pcb_layout(schematic_data, pcb_params):
    # ... 布局完成后 ...

    # 自动布线
    router = TSCircuitRouter()
    routed_pcb = router.route(pcb_data)

    return routed_pcb
```

---

### Phase 3: DRC规则扩展（1周）

#### 目标
- 扩展DRC规则至30+条
- 支持网络类规则
- 制造约束检查

#### 实现步骤

**Step 1: 扩展DRC数据结构** (1天)
```python
# 文件: agent/drc/advanced_drc.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class RuleType(Enum):
    CLEARANCE = "clearance"
    TRACK_WIDTH = "track_width"
    VIA_SIZE = "via_size"
    HOLE_CLEARANCE = "hole_clearance"
    DIFFERENTIAL_PAIR = "differential_pair"
    NET_CLASS = "net_class"
    MANUFACTURING = "manufacturing"

@dataclass
class DRCRule:
    name: str
    rule_type: RuleType
    value: float
    tolerance: float = 0.0
    condition: Optional[str] = None  # 条件表达式

@dataclass
class NetClass:
    name: str
    track_width: float
    clearance: float
    via_diameter: float
    via_drill: float
    diff_pair_gap: Optional[float] = None

class AdvancedDRCEngine:
    """
    高级DRC检查引擎
    """

    def __init__(self):
        # 默认规则集
        self.rules: List[DRCRule] = [
            # 间距规则
            DRCRule("track_to_track", RuleType.CLEARANCE, 0.15),
            DRCRule("track_to_pad", RuleType.CLEARANCE, 0.20),
            DRCRule("pad_to_pad", RuleType.CLEARANCE, 0.25),
            DRCRule("via_to_track", RuleType.CLEARANCE, 0.15),
            DRCRule("via_to_via", RuleType.CLEARANCE, 0.20),

            # 尺寸规则
            DRCRule("min_track_width", RuleType.TRACK_WIDTH, 0.15),
            DRCRule("min_via_drill", RuleType.VIA_SIZE, 0.30),
            DRCRule("min_via_diameter", RuleType.VIA_SIZE, 0.60),

            # 差分对规则
            DRCRule("diff_pair_gap", RuleType.DIFFERENTIAL_PAIR, 0.20),
            DRCRule("diff_pair_length_match", RuleType.DIFFERENTIAL_PAIR, 0.5),

            # 制造规则 (JLCPCB)
            DRCRule("min_hole_to_copper", RuleType.MANUFACTURING, 0.20),
            DRCRule("min_silk_width", RuleType.MANUFACTURING, 0.15),
            DRCRule("min_silk_clearance", RuleType.MANUFACTURING, 0.15),
        ]

        # 网络类定义
        self.net_classes: Dict[str, NetClass] = {
            "Power": NetClass("Power", 0.50, 0.30, 0.80, 0.40),
            "Signal": NetClass("Signal", 0.20, 0.15, 0.60, 0.30),
            "HighSpeed": NetClass("HighSpeed", 0.15, 0.10, 0.50, 0.25, diff_pair_gap=0.15),
        }

    def check(self, pcb_data: Dict) -> List[Dict]:
        """
        执行完整DRC检查

        Returns:
            错误列表
        """
        errors = []

        # 1. 走线检查
        errors.extend(self._check_tracks(pcb_data.get('tracks', [])))

        # 2. 过孔检查
        errors.extend(self._check_vias(pcb_data.get('vias', [])))

        # 3. 间距检查
        errors.extend(self._check_clearances(pcb_data))

        # 4. 差分对检查
        errors.extend(self._check_differential_pairs(pcb_data))

        # 5. 制造检查
        errors.extend(self._check_manufacturing(pcb_data))

        return errors
```

---

### Phase 4: 多层板支持（1周）

#### 目标
- 支持4层板
- 电源/地平面定义
- 层叠阻抗计算

```python
# 文件: agent/pcb/layer_stackup.py

from dataclasses import dataclass
from typing import List, Dict
import math

@dataclass
class Layer:
    name: str
    layer_number: int
    type: str  # signal, plane, mixed
    thickness: float  # mm
    copper_weight: float  # oz

@dataclass
class Dielectric:
    thickness: float  # mm
    dk: float  # 介电常数
    df: float  # 损耗因子

class LayerStackup:
    """
    多层板层叠结构管理
    """

    # 预定义层叠模板
    TEMPLATES = {
        "2layer": {
            "layers": [
                Layer("F.Cu", 0, "signal", 0.035, 1),
                Layer("B.Cu", 31, "signal", 0.035, 1),
            ],
            "dielectrics": [Dielectric(1.6, 4.5, 0.02)]
        },
        "4layer": {
            "layers": [
                Layer("F.Cu", 0, "signal", 0.035, 1),
                Layer("GND", 1, "plane", 0.035, 1),
                Layer("PWR", 30, "plane", 0.035, 1),
                Layer("B.Cu", 31, "signal", 0.035, 1),
            ],
            "dielectrics": [
                Dielectric(0.2, 4.5, 0.02),  # prepreg
                Dielectric(1.0, 4.5, 0.02),  # core
                Dielectric(0.2, 4.5, 0.02),  # prepreg
            ]
        }
    }

    def calculate_impedance(
        self,
        trace_width: float,
        layer_idx: int,
        reference_layer: int
    ) -> float:
        """
        计算阻抗

        使用微带线/带状线公式
        """
        # 获取层叠参数
        h = self.get_dielectric_thickness(layer_idx, reference_layer)
        er = self.get_dk(layer_idx)
        t = self.get_copper_thickness(layer_idx)

        # 微带线阻抗公式
        # Z0 = 87 / sqrt(er+1.41) * ln(5.98h / (0.8w + t))

        z0 = 87 / math.sqrt(er + 1.41) * math.log(5.98 * h / (0.8 * trace_width + t))

        return z0
```

---

## 三、开发时间表

| 周次 | 任务 | 产出 | 依赖 |
|------|------|------|------|
| W1 | 布局引擎升级 | smart_placement_engine.py | kicad-auto-designer |
| W2-3 | 布线引擎集成 | tscircuit_bridge.py | tscircuit-autorouter |
| W4 | DRC规则扩展 | advanced_drc.py | - |
| W5 | 多层板支持 | layer_stackup.py | - |
| W6 | 集成测试与优化 | 测试报告 | 所有模块 |

---

## 四、预期效果

| 指标 | 当前 | Phase 1后 | Phase 2后 | 最终 |
|------|------|-----------|-----------|------|
| 布局质量评分 | 30/100 | 70/100 | 75/100 | 80/100 |
| 布线完成率 | 20% | 60% | 85% | 90% |
| DRC通过率 | 40% | 70% | 85% | 95% |
| 支持层数 | 2 | 2 | 4 | 6 |
| 走线美观度 | 差 | 中 | 良 | 优 |

---

## 五、资源需求

### 人力
- 后端开发: 1人
- 前端集成: 0.5人
- 测试: 0.5人

### 技术栈
- Python 3.10+
- Node.js 18+ (tscircuit-autorouter)
- TypeScript 5.0+

### 依赖
```bash
# Python
pip install numpy scipy

# Node.js
npm install @tscircuit/capacity-autorouter
npm install @tscircuit/straight-line-solver
```

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| TypeScript模块集成困难 | 中 | 高 | 使用子进程方式调用 |
| 布线引擎性能问题 | 低 | 中 | 添加缓存机制 |
| DRC规则冲突 | 中 | 中 | 建立规则优先级系统 |
| 多层板数据模型不兼容 | 低 | 高 | 参考circuit-json标准 |

---

## 七、后续迭代（需要模型训练）

在算法开发完成后，可启动模型训练进一步提升质量：

1. **布局优化模型** (Phase 5, 1-2个月)
   - 收集5,000+优质布局案例
   - 训练布局评分模型
   - 实现智能布局推荐

2. **布线优化模型** (Phase 6, 2-3个月)
   - 收集10,000+布线案例
   - 训练高密度布线模型
   - 强化学习优化

3. **SI/PI分析模型** (Phase 7, 2个月)
   - 收集S参数数据
   - 训练阻抗预测模型
   - 集成到DRC检查

---

*文档版本: v1.0*
*下次更新: Phase 1完成后*