# KiCad AI Auto - 三阶段开发计划

**目标**: B+ (85分) → A+ (95分)
**总工作量**: 15-20小时
**日期**: 2026-04-02

---

## Phase 1: 快速修复 (2-4小时)

**目标评分**: B+ → A- (88分)

### 任务 1.1: 修复 Middleware 测试 (预计: 30分钟)

**问题**: Mock对象序列化失败
**文件**: `tests/test_middleware.py`
**失败数**: 5个测试

**修复方案**:

```python
# 当前问题代码
def test_value_error_returns_400(client):
    response = client.get("/test-value-error")
    # Mock对象的request_id无法序列化

# 修复后代码
from unittest.mock import MagicMock

@pytest.fixture
def mock_request():
    """创建可序列化的Mock请求对象"""
    mock = MagicMock()
    mock.state.request_id = "test-request-id-12345"  # 使用string而非Mock对象
    mock.client.host = "127.0.0.1"
    return mock

def test_value_error_returns_400(client, mock_request, monkeypatch):
    # 使用monkeypatch替换request对象
    monkeypatch.setattr("fastapi.Request", lambda: mock_request)
    response = client.get("/test-value-error")
    assert response.status_code == 400
```

**验证命令**:
```bash
cd kicad-ai-auto/agent
./venv/Scripts/python.exe -m pytest tests/test_middleware.py -v
```

---

### 任务 1.2: 修复 Manufacturing 测试路由 (预计: 20分钟)

**问题**: 测试使用旧路由导致404
**文件**: `tests/test_manufacturing_routes.py`
**失败数**: 8个测试

**修复方案**:

```python
# 当前问题代码
def test_gerber_export_missing_project(self, client):
    response = client.post("/export/gerber", json={...})  # 旧路由

# 修复后代码
def test_gerber_export_missing_project(self, client):
    response = client.post(
        "/api/v1/projects/non-existent/export/gerber",  # 新路由
        json={"project_id": "non-existent"}
    )
    assert response.status_code in [404, 500]

# 需要更新的路由映射:
旧路由                    →  新路由
/export/gerber           →  /api/v1/projects/{id}/export/gerber
/export/bom              →  /api/v1/projects/{id}/export/bom
/manufacturing/check     →  /api/v1/manufacturing/check
/manufacturing/cost      →  /api/v1/manufacturing/cost-estimate
```

**验证命令**:
```bash
./venv/Scripts/python.exe -m pytest tests/test_manufacturing_routes.py -v
```

---

### 任务 1.3: 清理硬编码敏感信息 (预计: 10分钟)

**问题**: 示例代码中包含硬编码API Key
**文件**:
- `kb_quality/lcsc_fetcher.py:45`
- `tests/test_glm4_client.py:22`

**修复方案**:

```python
# 当前问题代码
fetcher = LcscFetcher(api_key="YOUR_KEY")
client = GLM4Client(api_key="test_api_key_123")

# 修复后代码
fetcher = LcscFetcher(api_key=os.environ.get("LCSC_API_KEY", ""))
client = GLM4Client(api_key=os.environ.get("GLM4_API_KEY", "test_key"))
```

---

### Phase 1 验证清单

- [ ] `pytest tests/test_middleware.py` - 5/5 通过
- [ ] `pytest tests/test_manufacturing_routes.py` - 8/8 通过
- [ ] 无硬编码API Key

---

## Phase 2: 性能优化 (4-6小时)

**目标评分**: A- → A (92分)

### 任务 2.1: 前端代码分割 (预计: 2小时)

**问题**: vendor-three.js 1MB 过大
**文件**: `web/vite.config.ts`

**当前状态**:
```
vendor-three.js: 1,001 KB (警告: >500KB)
index.js:         359 KB
vendor-konva.js:  300 KB
```

**优化方案**:

```typescript
// web/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Three.js 分离
          'three-core': ['three'],
          'three-addons': [
            'three/examples/jsm/controls/OrbitControls',
            'three/examples/jsm/loaders/OBJLoader',
          ],
          // UI库分离
          'react-vendor': ['react', 'react-dom'],
          'konva-vendor': ['konva', 'react-konva'],
          'ui-components': [
            '@headlessui/react',
            '@heroicons/react',
          ],
        },
      },
    },
    chunkSizeWarningLimit: 400, // 降低警告阈值
  },
  // 添加预加载优化
  experimental: {
    renderBuiltUrl(filename, { hostType }) {
      if (hostType === 'html') {
        return '/' + filename;
      }
      return filename;
    },
  },
});
```

**预期结果**:
```
three-core.js:      ~350 KB
three-addons.js:    ~300 KB
react-vendor.js:    ~100 KB
konva-vendor.js:    ~200 KB
index.js:           ~150 KB
```

**验证命令**:
```bash
cd kicad-ai-auto/web
npm run build
ls -la dist/assets/*.js | awk '{print $5, $9}'
```

---

### 任务 2.2: API响应缓存 (预计: 1小时)

**问题**: 重复请求无缓存
**文件**: `main.py`

**优化方案**:

```python
# 安装依赖
# pip install fastapi-cache2

# main.py 添加
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化缓存
    FastAPICache.init(InMemoryBackend(), prefix="kicad-cache")
    yield
    # 关闭时清理

app = FastAPI(lifespan=lifespan)

# 缓存静态数据端点
@router.get("/api/v1/manufacturing/manufacturers")
@cache(expire=300)  # 5分钟缓存
async def list_manufacturers():
    ...

@router.get("/api/v1/templates")
@cache(expire=600)  # 10分钟缓存
async def list_templates():
    ...

@router.get("/api/v1/ecosystem/marketplace/templates")
@cache(expire=300)
async def marketplace_templates():
    ...
```

---

### 任务 2.3: 空间索引预热 (预计: 1小时)

**问题**: 首次查询需要构建索引
**文件**: `services/spatial_index.py`

**优化方案**:

```python
# services/spatial_index.py 添加

class PCBSpatialIndex:
    def __init__(self, pcb_data: Dict):
        self.pcb_data = pcb_data
        self._index = None
        self._build_index()  # 初始化时构建

    def _build_index(self):
        """预热构建空间索引"""
        items = []
        for fp in self.pcb_data.get("footprints", []):
            items.append(IndexedItem(
                id=fp["name"],
                type="footprint",
                bbox=BBox(
                    fp["position"]["x"] - fp["width"]/2,
                    fp["position"]["y"] - fp["height"]/2,
                    fp["position"]["x"] + fp["width"]/2,
                    fp["position"]["y"] + fp["height"]/2
                )
            ))
        self._index = GridIndex(items, cell_size=10.0)
```

---

### Phase 2 验证清单

- [ ] 最大chunk < 400KB
- [ ] API缓存响应头正确
- [ ] 空间索引查询 < 10ms

---

## Phase 3: 质量提升 (8-10小时)

**目标评分**: A → A+ (95分)

### 任务 3.1: TypeScript 类型改进 (预计: 4小时)

**问题**: 67处 `any` 类型
**优先文件**:
1. `web/src/editors/PCBEditor.tsx` (10处)
2. `web/src/App.tsx` (8处)
3. `web/src/stores/kicadStore.ts` (核心)

**修复方案**:

```typescript
// 1. 创建类型定义文件
// web/src/types/pcb.ts
export interface Position {
  x: number;
  y: number;
}

export interface Footprint {
  name: string;
  reference: string;
  position: Position;
  rotation: number;
  layer: string;
  width: number;
  height: number;
  pads: Pad[];
}

export interface Track {
  start: Position;
  end: Position;
  width: number;
  layer: string;
  net: string;
}

export interface Via {
  position: Position;
  diameter: number;
  drill: number;
  layers: string[];
  net: string;
}

export interface PCBData {
  footprints: Footprint[];
  tracks: Track[];
  vias: Via[];
  zones: Zone[];
  nets: Net[];
  boardOutline: Position[];
  layers: Layer[];
}

// 2. 替换 any 为具体类型
// 修改前
const renderFootprints = (footprints: any[]) => { ... }

// 修改后
const renderFootprints = (footprints: Footprint[]) => { ... }
```

**需要更新的文件**:
```
web/src/editors/PCBEditor.tsx      - 10处
web/src/editors/SchematicEditor.tsx - 5处
web/src/App.tsx                     - 8处
web/src/stores/kicadStore.ts        - 15处
web/src/services/api.ts             - 10处
web/src/canvas/*.tsx                - 19处
```

---

### 任务 3.2: 测试覆盖率提升 (预计: 4小时)

**当前**: 70% → **目标**: 80%+

**需要新增测试**:

```python
# tests/test_lcsc_api.py (新建)
import pytest
from services.lcsc_api import LcscClient

class TestLcscAPI:
    def test_search_components(self):
        """测试LCSC组件搜索"""
        client = LcscClient()
        results = client.search("STM32", limit=10)
        assert len(results) <= 10
        assert all("LCSC" in r.get("part_number", "") for r in results)

    def test_get_component_details(self):
        """测试获取组件详情"""
        client = LcscClient()
        details = client.get_details("C8734")  # STM32F103C8T6
        assert details is not None

# tests/test_spatial_index.py (新建)
import pytest
from services.spatial_index import PCBSpatialIndex, BBox

class TestSpatialIndex:
    @pytest.fixture
    def sample_pcb(self):
        return {
            "footprints": [
                {"name": "U1", "position": {"x": 50, "y": 50}, "width": 10, "height": 10},
                {"name": "R1", "position": {"x": 100, "y": 100}, "width": 5, "height": 3},
            ],
            "tracks": [],
            "vias": []
        }

    def test_find_nearby(self, sample_pcb):
        """测试邻近查询"""
        index = PCBSpatialIndex(sample_pcb)
        nearby = index.find_nearby(55, 55, radius=20)
        assert len(nearby) == 1
        assert nearby[0]["name"] == "U1"

    def test_collision_detection(self, sample_pcb):
        """测试碰撞检测"""
        index = PCBSpatialIndex(sample_pcb)
        collisions = index.check_collisions()
        assert isinstance(collisions, list)
```

---

### 任务 3.3: 文档完善 (预计: 2小时)

**需要创建的文档**:

```markdown
# docs/API_EXAMPLES.md (新建)

## API 使用示例

### 1. 创建项目
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "MyProject", "description": "Test"}'
```

### 2. 运行DRC检查
```bash
curl -X POST http://localhost:8000/api/v1/projects/{id}/drc/run
```

### 3. 导出Gerber
```bash
curl -X POST http://localhost:8000/api/v1/projects/{id}/export/gerber
```

# docs/DEPLOYMENT.md (新建)

## 部署指南

### Windows 本地部署
1. 安装 KiCad 9.0+
2. 配置 .env 文件
3. 启动后端: `python main.py`
4. 启动前端: `npm run dev`

### Docker 部署
```bash
docker-compose up -d
```
```

---

### Phase 3 验证清单

- [ ] TypeScript `any` 类型 < 20处
- [ ] 测试覆盖率 > 80%
- [ ] API示例文档完整
- [ ] 部署指南完整

---

## 执行顺序与依赖关系

```
Phase 1 (快速修复)
    ├── 1.1 Middleware测试 ──┐
    ├── 1.2 Manufacturing测试 ──┼──> 验证点: pytest通过率 100%
    └── 1.3 敏感信息清理 ──────┘
              │
              ▼
Phase 2 (性能优化)
    ├── 2.1 前端代码分割 ──┐
    ├── 2.2 API缓存 ───────┼──> 验证点: chunk < 400KB, 响应 < 100ms
    └── 2.3 空间索引预热 ──┘
              │
              ▼
Phase 3 (质量提升)
    ├── 3.1 TypeScript类型 ──┐
    ├── 3.2 测试覆盖率 ───────┼──> 验证点: any < 20, 覆盖率 > 80%
    └── 3.3 文档完善 ────────┘
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| TypeScript改动引入bug | 中 | 每个文件改完后运行前端测试 |
| 缓存导致数据不一致 | 低 | 设置合理TTL，添加缓存失效机制 |
| 测试路由不匹配 | 低 | 参考OpenAPI文档确认正确路由 |

---

## 最终验证

```bash
# Phase 1 验证
pytest tests/ -v --tb=short
# 期望: 所有测试通过

# Phase 2 验证
npm run build && ls -la web/dist/assets/*.js
# 期望: 最大文件 < 400KB

# Phase 3 验证
npm run type-check
# 期望: 无 any 类型警告
```

---

**预计完成时间**:
- Phase 1: 今天
- Phase 2: 明天
- Phase 3: 后天

**最终评分**: A+ (95分)
