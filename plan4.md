# Plan 4: 基于 Long-Running Agents 的测试方案计划

## 概述

本文档基于 Anthropic 的文章 [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的核心理念，为 kicad-for-chrome 项目设计测试方案。

**核心挑战**：长时间运行的 AI 代理需要在多个会话中保持一致的工作进度，每个新会话需要知道之前完成了什么。

## 参考实现

### GitHub 参考项目

1. **[foramoment/agents-long-horizon-harness](https://github.com/foramoment/agents-long-horizon-harness)**
   - 基于 Anthropic 论文的直接实现
   - 提供 feature_list.json 和 claude-progress.txt 结构

2. **[jeffjacobsen/yokeflow2](https://github.com/jeffjacobsen/yokeflow2)**
   - 成熟的自主编码平台 (v2.2.0)
   - 包含完整的质量系统 (6 阶段 + 2 部分)
   - 70% 测试覆盖率 (255 个测试)

## 核心理念

基于 Anthropic 的研究，测试框架需要解决两个核心问题：

1. **一次性完成问题 (One-shotting)**：代理试图一次性完成太多工作，导致半实现的测试
2. **过早完成问题 (Premature completion)**：代理在所有测试完成前就宣布完成

### 解决方案

| 原则 | 描述 |
|------|------|
| **一次一个功能** | 不并行开发功能 |
| **端到端验证** | 测试必须完全验证后才能标记完成 |
| **清洁状态交接** | 每个会话留下可合并的代码状态 |
| **结构化更新** | 进度文件在会话结束前必须更新 |
| **增量提交** | 小而逻辑化的提交，带描述性消息 |

## 项目测试现状

### 现有测试文件

**后端测试** (`kicad-ai-auto/agent/tests/`):
- `test_api.py` - API 测试
- `test_middleware.py` - 中间件测试
- `test_state_monitor.py` - 状态监控测试
- `test_export_manager.py` - 导出管理器测试

**前端测试** (`kicad-ai-auto/web/src/test/`):
- `api.test.ts` - API 测试
- `kicadStore.test.ts` - 状态管理测试
- `pcbStore.test.ts` - PCB 状态测试
- `schematicStore.test.ts` - 原理图状态测试
- `ToolBar.test.tsx` - 工具栏测试
- `MenuBar.test.tsx` - 菜单栏测试

### 现有基础设施

- **后端**: pytest + conftest.py
- **前端**: Vitest + React Testing Library
- **集成**: Playwright E2E 测试

## 测试方案计划

### 阶段 1: 测试基础设施搭建

#### 1.1 创建特征列表文件 (feature_list.json)

```json
{
  "project": {
    "name": "kicad-for-chrome",
    "description": "浏览器端 KiCad 访问与 AI 自动化",
    "stack": "Python (FastAPI) + React + TypeScript",
    "created_at": "2026-02-14"
  },
  "features": [
    {
      "id": "T001",
      "category": "core",
      "priority": "critical",
      "description": "后端 API 单元测试覆盖",
      "steps": [
        "运行 pytest 收集测试用例",
        "验证 test_api.py 测试通过",
        "验证 test_middleware.py 测试通过",
        "添加缺失的 API 路由测试"
      ],
      "passes": false,
      "notes": ""
    },
    {
      "id": "T002",
      "category": "core",
      "priority": "critical",
      "description": "前端组件测试覆盖",
      "steps": [
        "运行 vitest 收集测试用例",
        "验证 store 测试通过",
        "验证 UI 组件测试通过"
      ],
      "passes": false,
      "notes": ""
    },
    {
      "id": "T003",
      "category": "integration",
      "priority": "high",
      "description": "IPC API 集成测试",
      "steps": [
        "测试 /api/kicad-ipc/start 端点",
        "测试 /api/kicad-ipc/status 端点",
        "测试 /api/kicad-ipc/action 端点"
      ],
      "passes": false,
      "notes": ""
    },
    {
      "id": "T004",
      "category": "integration",
      "priority": "high",
      "description": "WebSocket 实时通信测试",
      "steps": [
        "测试 /ws/control 连接",
        "测试 /api/kicad-ipc/ws 连接",
        "验证消息传递正确性"
      ],
      "passes": false,
      "notes": ""
    },
    {
      "id": "T005",
      "category": "e2e",
      "priority": "high",
      "description": "Playwright E2E 测试",
      "steps": [
        "验证项目创建流程",
        "验证原理图编辑器功能",
        "验证 PCB 编辑器功能"
      ],
      "passes": false,
      "notes": ""
    },
    {
      "id": "T006",
      "category": "quality",
      "priority": "medium",
      "description": "测试覆盖率提升",
      "steps": [
        "运行覆盖率报告",
        "识别低覆盖率模块",
        "添加针对性测试"
      ],
      "passes": false,
      "notes": ""
    }
  ]
}
```

#### 1.2 创建进度日志文件 (claude-progress.txt)

```
--- Session: 2026-02-14 14:30 ---
Feature: [T001] 后端 API 单元测试覆盖
Status: 🔄 In Progress

Changes Made:
  - 分析现有测试文件
  - 确定测试覆盖范围
  - 计划添加新测试

Next Suggested: 完成 T001 后继续 T002
---
```

### 阶段 2: 后端测试增强

#### 2.1 API 路由测试扩展

**目标**: 覆盖所有 `/api/*` 路由

| 路由 | 测试用例 | 优先级 |
|------|---------|--------|
| `/api/project/*` | 创建、打开、保存项目 | P0 |
| `/api/kicad-ipc/*` | IPC API 相关端点 | P0 |
| `/api/export/*` | 导出功能 | P1 |
| `/api/drc/*` | 设计规则检查 | P1 |
| `/api/state/*` | 状态查询 | P1 |

#### 2.2 控制器测试

**文件**: `kicad-ai-auto/agent/tests/test_controller.py`

```python
class TestKiCadController:
    """KiCad 控制器测试套件"""

    def test_start_kicad(self):
        """测试 KiCad 启动"""
        pass

    def test_activate_tool(self):
        """测试工具激活"""
        pass

    def test_mouse_input(self):
        """测试鼠标输入"""
        pass

    def test_menu_click(self):
        """测试菜单点击"""
        pass
```

#### 2.3 IPC 管理器测试

**文件**: `kicad-ai-auto/agent/tests/test_ipc_manager.py`

```python
class TestKiCadIPCManager:
    """IPC 管理器测试套件"""

    def test_connect(self):
        """测试 IPC 连接"""
        pass

    def test_disconnect(self):
        """测试 IPC 断开"""
        pass

    def test_send_command(self):
        """测试发送命令"""
        pass

    def test_get_status(self):
        """测试获取状态"""
        pass
```

### 阶段 3: 前端测试增强

#### 3.1 Store 状态管理测试

| 文件 | 覆盖范围 | 目标 |
|------|---------|------|
| `kicadStore.test.ts` | 连接状态、KiCad 状态 | 100% |
| `pcbStore.test.ts` | PCB 数据、操作 | 80% |
| `schematicStore.test.ts` | 原理图数据、操作 | 80% |

#### 3.2 组件测试扩展

| 组件 | 测试用例 |
|------|---------|
| `PCBCanvas.test.tsx` | 渲染、交互 |
| `FootprintRenderer.test.tsx` | 封装渲染 |
| `ViaRenderer.test.tsx` | 过孔渲染 |
| `TrackRenderer.test.tsx` | 走线渲染 |

#### 3.3 API 集成测试

```typescript
// api.integration.test.ts
describe('API Integration', () => {
  it('should connect to backend', async () => {
    const response = await fetch('/api/health');
    expect(response.ok).toBe(true);
  });

  it('should handle IPC commands', async () => {
    // 测试 IPC 命令
  });
});
```

### 阶段 4: 集成测试与 E2E

#### 4.1 Playwright E2E 测试

**文件**: `kicad-ai-auto/playwright-tests/test_kicad_automation.py`

| 测试场景 | 描述 |
|---------|------|
| `test_create_project` | 创建新项目 |
| `test_open_project` | 打开已有项目 |
| `test_place_component` | 放置元件 |
| `test_route_track` | 布线 |
| `test_export_gerber` | 导出 Gerber |
| `test_run_drc` | 运行 DRC |

#### 4.2 Docker 环境测试

使用 docker-compose 确保测试环境一致性：

```yaml
# 测试环境配置
services:
  kicad-test:
    build: ./docker
    environment:
      - TESTING=true

  agent-test:
    build: ./agent
    depends_on:
      - kicad-test
```

### 阶段 5: 质量系统

#### 5.1 测试跟踪机制

参考 yokeflow2 的质量系统，实现：

1. **Phase 1-2**: 测试执行跟踪
   - 错误消息记录
   - 执行时间监控
   - 重试次数统计

2. **Phase 3**: Epic 测试阻塞
   - 关键测试失败阻止合并
   - 自动/严格模式

3. **Phase 5**: Epic 重新测试
   - 智能选择测试
   - 回归检测
   - 稳定性评分

#### 5.2 覆盖率目标

| 模块 | 目标覆盖率 |
|------|----------|
| agent/main.py | 80% |
| agent/kicad_controller.py | 70% |
| agent/kicad_ipc_manager.py | 80% |
| agent/export_manager.py | 80% |
| web/src (前端) | 70% |

### 阶段 6: CI/CD 集成

#### 6.1 GitHub Actions 工作流

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r kicad-ai-auto/docker/requirements.txt
      - name: Run pytest
        run: |
          cd kicad-ai-auto/agent
          pytest tests/ --cov=. --cov-report=xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd kicad-ai-auto/web
          npm install
      - name: Run vitest
        run: |
          cd kicad-ai-auto/web
          npm run test -- --run --coverage

  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Playwright tests
        run: |
          docker-compose up -d
          pytest kicad-ai-auto/playwright-tests/
```

## 实施步骤

### Step 1: 初始化测试框架
- [ ] 创建 `feature_list.json`
- [ ] 创建 `claude-progress.txt`
- [ ] 配置 pytest 和 vitest

### Step 2: 后端测试增强
- [ ] 扩展 `test_api.py` 覆盖率
- [ ] 添加 `test_controller.py`
- [ ] 添加 `test_ipc_manager.py`

### Step 3: 前端测试增强
- [ ] 完善 store 测试
- [ ] 添加组件测试
- [ ] 添加 API 集成测试

### Step 4: E2E 测试
- [ ] 完善 Playwright 测试用例
- [ ] 添加 Docker 测试环境

### Step 5: 质量系统
- [ ] 实现测试跟踪
- [ ] 配置覆盖率报告
- [ ] 设置 CI/CD

## 文件结构

```
kicad-ai-auto/
├── agent/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_middleware.py
│   │   ├── test_controller.py      # 新增
│   │   ├── test_ipc_manager.py     # 新增
│   │   ├── test_state_monitor.py
│   │   └── test_export_manager.py
│   └── pytest.ini
├── web/
│   └── src/
│       └── test/
│           ├── api.test.ts
│           ├── api.integration.test.ts  # 新增
│           ├── kicadStore.test.ts
│           ├── pcbStore.test.ts
│           ├── schematicStore.test.ts
│           └── components/           # 新增目录
│               ├── ToolBar.test.tsx
│               └── ...
├── playwright-tests/
│   ├── test_kicad_automation.py
│   └── conftest.py
├── feature_list.json               # 新增
└── claude-progress.txt             # 新增
```

## 关键指标

| 指标 | 目标 |
|------|------|
| 后端测试覆盖率 | 80% |
| 前端测试覆盖率 | 70% |
| E2E 测试用例数 | 20+ |
| CI 构建时间 | < 10 min |
| 测试通过率 | 100% |

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| KiCad 依赖难以测试 | 使用 Mock 对象和 Docker 环境 |
| 复杂 UI 交互测试 | 优先测试核心逻辑，UI 逐步覆盖 |
| 跨平台兼容性 | 在 CI 中使用多平台测试 |

## 参考资料

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [foramoment/agents-long-horizon-harness](https://github.com/foramoment/agents-long-horizon-harness)
- [jeffjacobsen/yokeflow2](https://github.com/jeffjacobsen/yokeflow2)
- [kicad-ai-auto README](../kicad-ai-auto/README.md)
