# 系统架构

> 当前版本: v0.9.12

## 架构概览

KiCad AI Auto 是一个基于 KiCad 9.0+ IPC API 的 AI 驱动 PCB 设计自动化系统，采用前后端分离架构。

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (React + Konva)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │ PCB Editor   │ │Schematic     │ │ AI Chat          │   │
│  │ (Konva.js)  │ │Editor        │ │ Assistant        │   │
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘   │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│              ┌─────────────┴─────────────┐                 │
│              │   Zustand State Store      │                 │
│              └─────────────┬─────────────┘                 │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTP/WS
              ┌──────────────┴──────────────┐
              │       FastAPI Backend         │
              │         (Port 8000)           │
              └──────────────┬──────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴───────┐  ┌─────────┴─────────┐  ┌──────┴──────┐
│ KiCad IPC API │  │   AI Providers    │  │ File System │
│ (kipy/kicad-  │  │ (GLM-4 / Kimi /  │  │  (projects/ │
│  python)      │  │  DeepSeek)        │  │   exports/) │
└───────────────┘  └───────────────────┘  └─────────────┘
```

## 核心组件

### 前端 (web/)

| 组件 | 技术 | 职责 |
|------|------|------|
| `editors/PCBEditor.tsx` | Konva.js | PCB 画布渲染和交互 |
| `editors/SchematicEditor.tsx` | Konva.js | 原理图画布渲染 |
| `canvas/FootprintRenderer.tsx` | Konva.js | 封装/焊盘渲染 |
| `stores/kicadStore.ts` | Zustand | 全局状态管理 |
| `services/api.ts` | Axios | REST API 调用 |

### 后端 (agent/)

| 组件 | 技术 | 职责 |
|------|------|------|
| `kicad_ipc_manager.py` | kipy | KiCad 9.0+ IPC API 客户端 |
| `kicad_controller.py` | PyAutoGUI | PyAutoGUI 模式控制 (旧) |
| `routes/kicad_ipc_routes.py` | FastAPI | IPC API 路由 (24个端点) |
| `routes/ai_routes.py` | FastAPI | AI 电路生成路由 (7个端点) |
| `kb_quality/` | 自研 | 知识库质量保障体系 (4阶段) |
| `generators/` | 自研 | 电路/PCB 生成器 |

## 操作模式

### 1. IPC API 模式 (推荐, KiCad 9.0+)

```
Backend → kipy (kicad-python) → KiCad GUI (Named Pipe)
```

- 使用 KiCad 官方 IPC API
- 需要 KiCad GUI 运行 + `Tools → External Plugin → Start Server`
- 支持精确的 PCB 元件操作
- Windows/Linux/macOS 均支持

### 2. PyAutoGUI 模式 (旧版)

```
Backend → PyAutoGUI → X11 Virtual Display (Linux) / 物理屏幕
```

- 跨 KiCad 版本
- 需要 X11 虚拟显示 (Linux Docker)
- Windows 下截图受限
- 已逐步被 IPC API 模式取代

## 数据流

### PCB 项目创建流程

```
用户输入 → AI分析 → 知识库查询 → 原理图生成 → PCB生成 → DRC验证
    ↓          ↓           ↓           ↓           ↓         ↓
 /api/v1/ai/analyze  kb_quality  /api/v1/projects  /api/kicad-ipc
```

### 知识库质量保障 (4阶段)

```
Phase 1: 格式校验     → 元件数据格式完整性
Phase 2: 引脚校验     → 符号引脚数量与类型匹配
Phase 3: KiCad校验    → 符号库/封装库存在性
Phase 4: AI质量门控   → 多模态 AI 视觉验证
```

详见: `agent/kb_quality/`

## API 分层

```
/api/v1/projects/*      项目 CRUD + PCB/原理图数据
/api/v1/ai/*             AI 电路分析与生成
/api/kicad-ipc/*         KiCad IPC 直接控制 (24端点)
/api/v1/knowledge/*      知识库查询 (25端点)
/api/v1/netlist/*        网表解析与验证
/api/v1/footprints/*     封装库查询
/api/v1/symbols/*        符号库查询
/api/auth/*              认证
/api/admin/*             管理
```

## 依赖关系

```
main.py (FastAPI app)
  ├── routes/ (14个路由文件)
  │     ├── project_routes.py    → kicad_ipc_manager.py
  │     ├── ai_routes.py       → glm4_client.py, kimi_client.py
  │     └── kicad_ipc_routes.py → kicad_ipc_manager.py
  ├── kicad_ipc_manager.py      → kipy (kicad-python)
  ├── state_monitor.py          → pcbnew (KiCad Python bindings)
  ├── kb_quality/              → validators.py, cross_checker.py
  └── generators/               → schematic_generator.py, pcb_generator.py
```

## 部署

- **Windows**: `start-all-auto.bat` 或 `agent/main.py`
- **Linux/macOS**: Docker Compose (`docker-compose up`)
- **前端**: Vite dev server (`web/` 目录)
