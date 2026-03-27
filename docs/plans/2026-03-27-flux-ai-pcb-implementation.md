# AI PCB 设计系统 - 完整开发计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 kicad-for-chrome 项目迭代为完整的 AI PCB 设计平台，类似 flux.ai，支持自然语言输入 → AI 分析 → 原理图生成 → AI 布局布线 → 完整 PCB 设计。

**Architecture:**
- **前端**: React + TypeScript + Konva.js + Zustand，保持现有的编辑器架构
- **后端**: FastAPI + Python，新增 PCB 布局引擎和元器件推荐系统
- **AI 层**: 增强现有 AI 分析能力，添加 LLM 驱动的元器件推荐
- **KiCad 集成**: 充分利用 KiCad 9.0+ IPC API，添加自动布局 API 支持

**Tech Stack:** Python 3.11+, FastAPI, KiCad 9.0+ IPC API (kicad-python), React 18+, Konva.js, Zustand, GLM-4/Kimi API

---

## 阶段划分

| 阶段 | 名称 | 目标 | 周期 |
|------|------|------|------|
| **Phase 0** | 稳定化 | 修复现有 bug，稳定核心功能 | 1-2周 |
| **Phase 1** | 原理图增强 | 提升原理图生成质量和完整性 | 2-3周 |
| **Phase 2** | AI 引擎升级 | 增强 AI 分析和元器件推荐能力 | 3-4周 |
| **Phase 3** | PCB 布局系统 | 实现 AI 自动布局算法 | 4-6周 |
| **Phase 4** | PCB 布线系统 | 实现 AI 自动布线算法 | 4-6周 |
| **Phase 5** | 集成测试 | 端到端测试和优化 | 2-3周 |

---

## Phase 0: 稳定化

### Task 0.1: 建立开发环境和测试框架

**Files:**
- Create: `kicad-ai-auto/agent/tests/conftest.py`
- Create: `kicad-ai-auto/agent/tests/__init__.py`

**Step 1: Create test structure**

```python
# kicad-ai-auto/agent/tests/__init__.py
# Test package
```

**Step 2: Create conftest.py with fixtures**

```python
# kicad-ai-auto/agent/tests/conftest.py
import pytest
import sys
from pathlib import Path

# Add agent to path
agent_path = Path(__file__).parent.parent
sys.path.insert(0, str(agent_path))

@pytest.fixture
def mock_kicad_response():
    """Mock KiCad IPC response for testing"""
    return {
        "status": "connected",
        "board": {"width": 100, "height": 80}
    }
```

**Step 3: Verify test discovery works**

Run: `cd kicad-ai-auto/agent && pytest --collect-only`
Expected: No errors, tests discovered

**Step 4: Commit**

```bash
git add kicad-ai-auto/agent/tests/
git commit -m "test: add test framework structure"
```

---

### Task 0.2: 修复 BOM 导出 API 错误

**Files:**
- Modify: `kicad-ai-auto/agent/routes/project_routes.py`

**Step 1: Write failing test for BOM export**

```python
# kicad-ai-auto/agent/tests/test_project_routes.py
def test_bom_export_returns_valid_json(project_id):
    """Test that BOM export returns valid JSON without 500 error"""
    response = client.post(f"/api/v1/projects/{project_id}/export/bom")
    assert response.status_code == 200
    data = response.json()
    assert "bom" in data or "components" in data
```

**Step 2: Run test to verify failure**

Run: `pytest tests/test_project_routes.py::test_bom_export_returns_valid_json -v`
Expected: FAIL with 500 error

**Step 3: Fix the bug in project_routes.py**

Find the BOM export endpoint and fix the issue with `_pcb_data.get(project_id, {})` → should be `_pcb_data.get(project_id) or {}`

**Step 4: Run test to verify pass**

Run: `pytest tests/test_project_routes.py::test_bom_export_returns_valid_json -v`
Expected: PASS

**Step 5: Commit**

```bash
git add kicad-ai-auto/agent/routes/project_routes.py
git commit -m "fix: BOM export returns 500 error"
```

---

### Task 0.3: 验证原理图组件实例生成

**Files:**
- Modify: `kicad-ai-auto/agent/routes/netlist_routes.py`

**Step 1: Write test for schematic component instances**

```python
def test_schematic_has_component_instances(schematic_path):
    """Test that generated schematic contains symbol instances"""
    # Generate schematic
    result = generate_schematic(...)
    content = Path(result["path"]).read_text()

    # Count symbol instances
    instance_count = content.count("(symbol (lib_id")
    assert instance_count > 0, "No component instances found"
```

**Step 2: Run test**

Run: `pytest tests/test_netlist_routes.py::test_schematic_has_component_instances -v`

**Step 3: If failing, verify _fix_schematic_components is called**

Check that after `sch.save()`, the `_fix_schematic_components()` function is being called.

**Step 4: Commit**

---

## Phase 1: 原理图增强

### Task 1.1: 增强符号库检索

**Files:**
- Create: `kicad-ai-auto/agent/services/symbol_library.py`
- Modify: `kicad-ai-auto/agent/routes/netlist_routes.py`

**Step 1: Write test for symbol search**

```python
def test_symbol_search_by_keyword():
    """Test searching symbols by keyword"""
    library = SymbolLibrary()
    results = library.search("USB")
    assert len(results) > 0
    assert any("USB" in r["name"] for r in results)
```

**Step 2: Implement SymbolLibrary class**

```python
# kicad-ai-auto/agent/services/symbol_library.py
from dataclasses import dataclass
from typing import List, Optional
import json
from pathlib import Path

@dataclass
class SymbolInfo:
    name: str
    library: str
    unit_count: int
    pin_count: int
    keywords: List[str]

class SymbolLibrary:
    def __init__(self, lib_path: Optional[str] = None):
        self.lib_path = lib_path or "kicad-symbols"
        self._cache = {}

    def search(self, keyword: str, limit: int = 20) -> List[SymbolInfo]:
        # Search implementation
        pass
```

**Step 3: Run test**

**Step 4: Commit**

---

### Task 1.2: 改进引脚连接算法

**Files:**
- Modify: `kicad-ai-auto/agent/generators/schematic_v2.py`

**Step 1: Write test for pin connection**

```python
def test_connect_pins_creates_valid_wire():
    """Test that pin connection creates valid wire segment"""
    generator = SchematicGeneratorV2(project_path)
    component1 = Component(symbol="Device:R", ref="R1", at=(100, 100))
    component2 = Component(symbol="Device:C", ref="C1", at=(100, 150))

    wire = generator.connect_pins(component1, "1", component2, "1")

    assert wire.start == (100, 100)
    assert wire.end == (100, 150)
```

**Step 2: Run test**

**Step 3: Implement enhanced connection logic**

**Step 4: Commit**

---

## Phase 2: AI 引擎升级

### Task 2.1: 创建元器件推荐引擎

**Files:**
- Create: `kicad-ai-auto/agent/services/component_recommender.py`
- Create: `kicad-ai-auto/agent/data/component_db.json` (if not exists)

**Step 1: Write test for component recommendation**

```python
def test_recommend_by_function():
    """Test recommending components by function"""
    recommender = ComponentRecommender()

    # Recommend USB connector
    results = recommender.recommend_by_function("USB type-C connector 5V 3A")

    assert len(results) > 0
    assert all("USB" in r["symbol"] or "USB" in r["description"] for r in results)
```

**Step 2: Implement ComponentRecommender**

```python
# kicad-ai-auto/agent/services/component_recommender.py
from dataclasses import dataclass
from typing import List, Dict, Optional
import json
from pathlib import Path

@dataclass
class ComponentRecommendation:
    symbol: str
    footprint: str
    description: str
    parameters: Dict
    score: float
    source: str  # "jlcpcb", "lcsc", "local"

class ComponentRecommender:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "component_db.json"
        self._load_db()

    def _load_db(self):
        if self.db_path.exists():
            with open(self.db_path) as f:
                self.db = json.load(f)
        else:
            self.db = {"components": []}

    def recommend_by_function(self, description: str, limit: int = 5) -> List[ComponentRecommendation]:
        # LLM-powered recommendation logic
        pass
```

**Step 3: Run test**

**Step 4: Commit**

---

### Task 2.2: 增强 AI 分析路由

**Files:**
- Modify: `kicad-ai-auto/agent/routes/ai_routes.py`

**Step 1: Write test for enhanced AI analysis**

```python
def test_ai_analyze_returns_component_recommendations():
    """Test that AI analysis returns component recommendations"""
    response = client.post("/api/v1/ai/analyze", json={
        "requirements": "I need a USB charging circuit for 5V 3A"
    })

    assert response.status_code == 200
    data = response.json()
    assert "components" in data or "recommendations" in data
```

**Step 2: Enhance ai_analyze endpoint to include recommendations**

**Step 3: Run test**

**Step 4: Commit**

---

## Phase 3: PCB 布局系统

### Task 3.1: 创建 PCB 布局引擎

**Files:**
- Create: `kicad-ai-auto/agent/placement/placement_engine.py`
- Create: `kicad-ai-auto/agent/placement/__init__.py`

**Step 1: Write test for basic placement**

```python
def test_place_components_on_board():
    """Test placing components on PCB board"""
    engine = PlacementEngine(board_width=100, board_height=80)

    components = [
        Component(ref="U1", width=20, height=15),
        Component(ref="C1", width=5, height=5),
        Component(ref="R1", width=3, height=2),
    ]

    result = engine.place(components)

    assert len(result.placements) == 3
    # Verify no overlaps
    for i, p1 in enumerate(result.placements):
        for p2 in result.placements[i+1:]:
            assert not p1.overlaps(p2)
```

**Step 2: Implement PlacementEngine with basic algorithm**

```python
# kicad-ai-auto/agent/placement/placement_engine.py
from dataclasses import dataclass
from typing import List, Tuple
import random

@dataclass
class Placement:
    ref: str
    x: float
    y: float
    rotation: float = 0

@dataclass
class Component:
    ref: str
    width: float
    height: float

class PlacementEngine:
    def __init__(self, board_width: float, board_height: float, margin: float = 5):
        self.board_width = board_width
        self.board_height = board_height
        self.margin = margin

    def place(self, components: List[Component]) -> List[Placement]:
        # Simple random placement with collision avoidance
        placements = []

        for comp in sorted(components, key=lambda c: c.width * c.height, reverse=True):
            pos = self._find_position(placements, comp)
            placements.append(Placement(ref=comp.ref, x=pos[0], y=pos[1]))

        return placements

    def _find_position(self, existing: List[Placement], comp: Component) -> Tuple[float, float]:
        # Grid-based placement with margin
        grid_size = 5
        for y in range(self.margin, self.board_height - self.margin, grid_size):
            for x in range(self.margin, self.board_width - self.margin, grid_size):
                if self._is_valid_position(x, y, comp, existing):
                    return (x, y)
        return (self.margin, self.margin)

    def _is_valid_position(self, x: float, y: float, comp: Component, existing: List[Placement]) -> bool:
        # Check bounds
        if x + comp.width > self.board_width - self.margin:
            return False
        if y + comp.height > self.board_height - self.margin:
            return False

        # Check overlaps
        for p in existing:
            other_comp = next((c for c in existing if c.ref == p.ref), None)
            if self._overlaps(x, y, comp, p, other_comp):
                return False

        return True

    def _overlaps(self, x, y, comp1, pos2, comp2) -> bool:
        if comp2 is None:
            return False
        # Simple AABB collision
        return not (x + comp1.width <= pos2.x or pos2.x + comp2.width <= x or
                   y + comp1.height <= pos2.y or pos2.y + comp2.height <= y)
```

**Step 3: Run test**

**Step 4: Commit**

---

### Task 3.2: 添加布局优化算法

**Files:**
- Modify: `kicad-ai-auto/agent/placement/placement_engine.py`

**Step 1: Add thermal-aware placement**

```python
def test_thermal_aware_placement():
    """Test that thermal constraints are considered"""
    engine = PlacementEngine(board_width=100, board_height=80)

    components = [
        Component(ref="U1", width=20, height=15, thermal_load=1.0),  # High heat
        Component(ref="C1", width=5, height=5, thermal_load=0.1),
        Component(ref="R1", width=3, height=2, thermal_load=0.1),
    ]

    result = engine.place_thermal_aware(components, ambient_temps=[25, 30, 35])

    # High thermal component should be placed near edge/vent
    assert result.placements[0].ref == "U1"
```

**Step 2: Run test**

**Step 3: Implement thermal placement**

**Step 4: Commit**

---

## Phase 4: PCB 布线系统

### Task 4.1: 创建布线引擎

**Files:**
- Create: `kicad-ai-auto/agent/routing/routing_engine.py`
- Create: `kicad-ai-auto/agent/routing/__init__.py`

**Step 1: Write test for basic routing**

```python
def test_route_between_pads():
    """Test routing between two pads"""
    engine = RoutingEngine()

    pad1 = Pad(x=10, y=10, net="VCC")
    pad2 = Pad(x=50, y=30, net="VCC")

    routes = engine.route([pad1], [pad2])

    assert len(routes) > 0
    assert routes[0].net == "VCC"
```

**Step 2: Implement basic routing**

```python
# kicad-ai-auto/agent/routing/routing_engine.py
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class Pad:
    x: float
    y: float
    net: str
    layer: str = "top"

@dataclass
class Route:
    net: str
    segments: List[Tuple[float, float, float, float]]  # [(x1,y1,x2,y2), ...]
    layer: str = "top"

class RoutingEngine:
    def __init__(self, board_width: float = 100, board_height: float = 80):
        self.board_width = board_width
        self.board_height = board_height
        self.grid_size = 2.5  # KiCad default grid

    def route(self, source_pads: List[Pad], target_pads: List[Pad]) -> List[Route]:
        """Manhattan routing between pads"""
        routes = []

        for src in source_pads:
            for tgt in target_pads:
                if src.net == tgt.net:
                    route = self._manhattan_route(src, tgt)
                    routes.append(route)

        return routes

    def _manhattan_route(self, pad1: Pad, pad2: Pad) -> Route:
        """Create L-shaped Manhattan route"""
        x1, y1 = pad1.x, pad1.y
        x2, y2 = pad2.x, pad2.y

        # L-shaped route: horizontal then vertical
        mid_x = x2
        segments = [
            (x1, y1, mid_x, y1),  # Horizontal
            (mid_x, y1, mid_x, y2),  # Vertical
        ]

        return Route(net=pad1.net, segments=segments, layer=pad1.layer)
```

**Step 3: Run test**

**Step 4: Commit**

---

### Task 4.2: 添加过孔和多层布线

**Files:**
- Modify: `kicad-ai-auto/agent/routing/routing_engine.py`

**Step 1: Write test for via insertion**

```python
def test_insert_via_for_layer_change():
    """Test that via is inserted when changing layers"""
    engine = RoutingEngine(layers=["top", "bottom"])

    pad1 = Pad(x=10, y=10, net="VCC", layer="top")
    pad2 = Pad(x=50, y=30, net="VCC", layer="bottom")

    route = engine.route_with_vias([pad1], [pad2])

    # Should have a via
    assert any(s.startswith("via") for s in route.segments)
```

**Step 2: Run test**

**Step 3: Implement via routing**

**Step 4: Commit**

---

## Phase 5: 集成测试

### Task 5.1: 端到端 AI PCB 生成测试

**Files:**
- Create: `kicad-ai-auto/agent/tests/test_e2e_ai_pcb.py`

**Step 1: Write E2E test**

```python
def test_full_ai_pcb_generation():
    """Test complete flow: requirements -> schematic -> PCB"""
    # 1. Send requirements
    response = client.post("/api/v1/ai/generate-pcb", json={
        "requirements": "Simple USB to 3.3V regulator circuit",
        "board_size": {"width": 100, "height": 80}
    })

    assert response.status_code == 200
    result = response.json()

    assert "schematic" in result
    assert "pcb" in result
    assert "components" in result

    # 2. Verify schematic file exists and has content
    sch_path = Path(result["schematic"]["path"])
    assert sch_path.exists()

    # 3. Verify PCB has placements
    pcb_data = result["pcb"]
    assert len(pcb_data.get("placements", [])) > 0

    # 4. Verify routes exist
    assert len(pcb_data.get("routes", [])) > 0
```

**Step 2: Run test**

**Step 3: Fix any integration issues**

**Step 4: Commit**

---

### Task 5.2: 性能测试

**Files:**
- Create: `kicad-ai-auto/agent/tests/test_performance.py`

**Step 1: Write performance test**

```python
def test_placement_performance():
    """Test that placement completes within time limit"""
    import time

    engine = PlacementEngine(board_width=200, board_height=150)
    components = [Component(ref=f"R{i}", width=5, height=3) for i in range(50)]

    start = time.time()
    result = engine.place(components)
    elapsed = time.time() - start

    assert elapsed < 1.0, f"Placement took {elapsed:.2f}s, expected < 1.0s"
    assert len(result) == 50
```

**Step 2: Run test**

**Step 3: Optimize if needed**

**Step 4: Commit**

---

## 里程碑检查点

| 里程碑 | 完成标准 | 验证方式 |
|--------|---------|---------|
| M1: 稳定运行 | 所有现有测试通过，无 500 错误 | `pytest -v` |
| M2: 原理图增强 | 符号库搜索可用，生成质量提升 | E2E 测试 |
| M3: AI 推荐 | 元器件推荐返回结果 | API 测试 |
| M4: 基本布局 | 50 个元件布局 < 1 秒，无重叠 | 性能测试 |
| M5: 基本布线 | 简单网络布线正确 | 单元测试 |
| M6: 完整流程 | 需求 → 原理图 → PCB 端到端 | E2E 测试 |

---

## 依赖关系

```
Phase 0 (稳定化)
    ↓
Phase 1 (原理图增强) ← Phase 0 完成
    ↓
Phase 2 (AI 引擎) ← Phase 1 完成
    ↓
Phase 3 (PCB 布局) ← Phase 2 完成
    ↓
Phase 4 (PCB 布线) ← Phase 3 完成
    ↓
Phase 5 (集成测试) ← Phase 4 完成
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| KiCad IPC API 限制 | 某些操作无法通过 API 完成 | 保留 PyAutoGUI 作为后备 |
| AI 生成质量不稳定 | 原理图/PCB 可能有问题 | 增加验证层，保留手动编辑 |
| 布局算法性能 | 大板可能很慢 | 优化算法，分批处理 |
| 测试覆盖不足 | 难以保证质量 | 增加 E2E 测试 |

---

## 后续优化方向

1. **AI 布局优化**: 考虑信号完整性、热管理、EMI
2. **高级布线**: 差分对、蛇形线、等长布线
3. **实时协作**: 多用户同时编辑
4. **云端 KiCad**: 使用 Docker 运行 KiCad
5. **增量学习**: 根据用户反馈优化 AI 模型
