# KiCad AI Auto - A+ 级别改进计划

**目标**: 从 B+ 提升到 A+ (95分以上)
**当前评分**: B+ (85分)

---

## 一、代码质量 (当前: 85/100 → 目标: 95/100)

### 1.1 TypeScript 类型改进 (预计提升: +5分)

**当前问题**:
- 67处 `any` 类型使用
- 部分组件缺少完整类型定义

**改进措施**:

```typescript
// 替换前
const handleData = (data: any) => { ... }

// 替换后
interface PCBData {
  footprints: Footprint[];
  tracks: Track[];
  vias: Via[];
  nets: Net[];
}
const handleData = (data: PCBData) => { ... }
```

**优先级文件**:
1. `web/src/editors/PCBEditor.tsx` - 10处 any
2. `web/src/App.tsx` - 8处 any
3. `web/src/stores/kicadStore.ts` - 核心状态类型

---

## 二、测试覆盖率 (当前: 70/100 → 目标: 90/100)

### 2.1 修复失败测试 (预计提升: +10分)

**当前问题**:
- 13个测试失败
- 5个 Middleware Mock问题
- 8个 Manufacturing路由问题

**修复方案**:

#### A. Middleware 测试修复
```python
# tests/test_middleware.py
# 问题: Mock对象无法序列化
# 解决: 使用string类型的request_id

def test_value_error_returns_400(client):
    response = client.get("/test-error")
    # 添加: 确保response.json()能正确处理
    assert response.status_code == 400
```

#### B. Manufacturing 路由修复
```python
# tests/test_manufacturing_routes.py
# 更新路由路径

# 旧: "/export/gerber"
# 新: "/api/v1/projects/{project_id}/export/gerber"

def test_gerber_export_success(self, client):
    response = client.post(
        "/api/v1/projects/test-project/export/gerber",  # 更新路由
        json={"project_id": "test-project"}
    )
```

### 2.2 增加测试覆盖 (预计提升: +5分)

**需要新增测试**:
- [ ] `services/lcsc_api.py` - LCSC API 集成测试
- [ ] `services/spatial_index.py` - 空间索引单元测试
- [ ] `routes/collaboration_routes.py` - 协作功能测试

---

## 三、性能优化 (当前: 75/100 → 目标: 90/100)

### 3.1 前端代码分割 (预计提升: +10分)

**当前问题**:
- `vendor-three.js`: 1MB (过大)
- `index.js`: 370KB
- `vendor-konva.js`: 300KB

**优化方案**:

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'three-core': ['three'],
          'three-addons': ['three/examples/jsm/controls/OrbitControls'],
          'konva': ['konva'],
          'react-vendor': ['react', 'react-dom'],
          'ui-vendor': ['@headlessui/react', '@heroicons/react'],
        }
      }
    },
    chunkSizeWarningLimit: 500, // 500KB
  }
});
```

**预期效果**:
- 最大chunk: ~400KB (从1MB降低60%)
- 首屏加载: 提升40%

### 3.2 后端性能优化 (预计提升: +5分)

**当前问题**:
- 无响应缓存
- 空间索引未预热

**优化方案**:
```python
# 添加API响应缓存
from fastapi_cache import Coder, FastAPICache
from fastapi_cache.decorator import cache

@router.get("/api/v1/manufacturing/manufacturers")
@cache(expire=300)  # 5分钟缓存
async def list_manufacturers():
    ...
```

---

## 四、安全性 (当前: 80/100 → 目标: 95/100)

### 4.1 敏感信息管理 (预计提升: +10分)

**当前问题**:
- 645处敏感词 (password/token/secret)
- 部分硬编码API Key示例

**改进方案**:

```python
# 添加 secrets 扫描脚本
# scripts/check_secrets.py
import re

SENSITIVE_PATTERNS = [
    r'api_key\s*=\s*["\'][^"\']{10,}["\']',  # 硬编码API Key
    r'password\s*=\s*["\'][^"\']{8,}["\']',   # 硬编码密码
]

def scan_for_secrets(directory):
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.py'):
                check_file(os.path.join(root, f))
```

**验证清单**:
- [ ] 所有API Key使用 `os.environ.get()`
- [ ] 密码使用 bcrypt 哈希
- [ ] 敏感配置使用 `.env` 文件

---

## 五、API一致性 (当前: 90/100 → 目标: 98/100)

### 5.1 路由标准化 (预计提升: +5分)

**当前问题**:
- `/api/project/list` vs `/api/v1/projects`
- `/drc/run` vs `/api/v1/projects/{id}/drc/run`

**统一方案**:
```
/api/v1/projects                    # 项目列表
/api/v1/projects/{id}               # 项目详情
/api/v1/projects/{id}/drc/run       # DRC检查
/api/v1/projects/{id}/export/gerber # 导出Gerber
/api/v1/manufacturing/check        # 制造检查
```

---

## 六、文档完善 (当前: 70/100 → 目标: 90/100)

### 6.1 需要补充的文档

| 文档 | 状态 | 优先级 |
|------|------|--------|
| API使用示例 | 缺失 | 高 |
| 部署指南 | 部分 | 高 |
| 贡献指南 | 缺失 | 中 |
| 架构设计文档 | 缺失 | 中 |
| 故障排除指南 | 缺失 | 低 |

---

## 七、实施计划

### Phase 1: 快速修复 (1-2天)

| 任务 | 影响 | 工作量 |
|------|------|--------|
| 修复 Middleware 测试 | +5分 | 2h |
| 更新 Manufacturing 测试路由 | +5分 | 1h |
| 删除硬编码API Key | +5分 | 1h |

### Phase 2: 性能优化 (3-5天)

| 任务 | 影响 | 工作量 |
|------|------|--------|
| 前端代码分割 | +10分 | 4h |
| API响应缓存 | +5分 | 2h |
| 空间索引预热 | +3分 | 2h |

### Phase 3: 质量提升 (5-7天)

| 任务 | 影响 | 工作量 |
|------|------|--------|
| TypeScript类型改进 | +5分 | 8h |
| 测试覆盖率提升 | +5分 | 8h |
| 文档完善 | +5分 | 4h |

---

## 八、评分预测

| 维度 | 当前 | Phase 1后 | Phase 2后 | Phase 3后 |
|------|------|-----------|-----------|-----------|
| 代码质量 | 85 | 88 | 88 | **95** |
| 测试覆盖 | 70 | 80 | 80 | **90** |
| API设计 | 90 | 90 | 90 | **98** |
| 安全性 | 80 | 85 | 85 | **95** |
| 性能 | 75 | 75 | 90 | **90** |
| 文档 | 70 | 70 | 70 | **90** |
| **总分** | **B+** | **A-** | **A** | **A+** |

---

## 九、立即可以执行的改进

### 9.1 修复 Middleware 测试 (5分钟)

```python
# 在 tests/test_middleware.py 中添加
import uuid

@pytest.fixture
def mock_request():
    class MockRequest:
        def __init__(self):
            self.state = type('State', (), {'request_id': str(uuid.uuid4())})()
    return MockRequest()
```

### 9.2 前端代码分割 (10分钟)

```typescript
// vite.config.ts 添加
manualChunks: (id) => {
  if (id.includes('three')) {
    return 'three-vendor';
  }
  if (id.includes('konva')) {
    return 'konva-vendor';
  }
}
```

### 9.3 API响应缓存 (5分钟)

```python
# main.py 添加
from fastapi_cache.backends.inmemory import InMemoryBackend

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())
```

---

**预计总工作量**: 15-20小时
**预计评分提升**: B+ (85) → A+ (95+)
