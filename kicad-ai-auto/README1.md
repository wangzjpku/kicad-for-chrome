# KiCad AI 自动化控制系统 - 详细技术文档

## 项目概述

**项目名称**: KiCad for Chrome  
**版本**: 0.4.3  
**项目类型**: 浏览器端 KiCad EDA 软件控制与 AI 自动化系统  
**核心功能**: 通过浏览器界面控制 KiCad PCB 设计软件，提供 REST API 和 WebSocket 接口，支持 AI 自动化操作

---

## 项目架构

```
kicad-for-chrome/
├── kicad-source/                    # 官方 KiCad 源代码（C++, CMake）
├── kicad-ai-auto/                   # AI 自动化层（主要开发目录）
│   ├── agent/                       # Python FastAPI 后端
│   ├── web/                         # React TypeScript 前端
│   ├── docker/                      # Docker 容器配置
│   ├── playwright-tests/             # Playwright E2E 测试
│   ├── docs/                        # 项目文档
│   └── scripts/                     # 辅助脚本
```

---

## 目录结构详解

### 1. 后端 (agent/)

```
agent/
├── main.py                         # FastAPI 主应用入口
├── middleware.py                   # 中间件（请求日志、错误处理）
├── kicad_controller.py             # KiCad 控制器核心
├── kicad_ipc_manager.py            # KiCad IPC 通信管理器
├── export_manager.py               # 文件导出管理器
├── state_monitor.py                # 状态监控器
├── footprint_library.py             # 封装库管理器
├── glm4_client.py                   # GLM-4 大模型客户端
├── diagnose_screenshot.py          # 截图诊断工具
├── auto_starter.py                  # 自动启动管理器
├── ralph_loop_tester.py             # PCB 测试工具
│
├── routes/                         # API 路由
│   ├── __init__.py
│   ├── project_routes.py            # 项目管理路由
│   ├── ai_routes.py                 # AI 功能路由
│   └── kicad_ipc_routes.py         # IPC 通信路由
│
├── component_knowledge/            # 组件知识库
│   └── component_db.json            # 组件数据库
│
├── pcb_evaluator/                  # PCB 评估模块
│   ├── checkers.py                  # PCB 检查器
│   ├── kicad_parser.py             # KiCad 文件解析器
│   ├── pcb_models.py                # PCB 数据模型
│   ├── ralph_loop.py                # PCB 测试循环
│   └── test_*.py                    # 测试文件
│
├── tests/                          # 测试文件
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_api.py                  # API 测试
│   ├── test_controller.py           # 控制器测试
│   ├── test_middleware.py           # 中间件测试
│   ├── test_export_manager.py       # 导出管理器测试
│   ├── test_state_monitor.py        # 状态监控测试
│   ├── test_ipc_manager.py          # IPC 管理器测试
│   ├── test_ipc_routes.py           # IPC 路由测试
│   ├── test_knowledge_base.py       # 知识库测试
│   ├── test_auto_starter.py         # 自动启动测试
│   ├── test_diagnose_screenshot.py  # 截图诊断测试
│   ├── test_footprint_library.py    # 封装库测试
│   └── test_glm4_client.py          # GLM 客户端测试
│
├── pytest.ini                      # Pytest 配置
├── requirements.txt                # Python 依赖
└── run_tests.py                    # 测试运行脚本
```

### 2. 前端 (web/)

```
web/
├── package.json                    # 项目配置（版本 0.4.3）
├── tsconfig.json                   # TypeScript 配置
├── vite.config.ts                  # Vite 构建配置
├── tailwind.config.js              # Tailwind CSS 配置
├── postcss.config.js               # PostCSS 配置
│
├── src/
│   ├── main.tsx                    # React 应用入口
│   ├── App.tsx                     # 主应用组件
│   ├── vite-env.d.ts               # Vite 类型定义
│   │
│   ├── components/                 # React 组件
│   │   ├── AIProjectDialog.tsx     # AI 项目创建对话框
│   │   ├── SymbolSelector.tsx      # 符号选择器
│   │   ├── SimpleToolbar.tsx       # 简单工具栏
│   │   ├── MenuBar.tsx             # 菜单栏
│   │   ├── ToolBar.tsx             # 工具栏
│   │   ├── StatusBar.tsx           # 状态栏
│   │   ├── OutputPanel.tsx         # 输出面板
│   │   ├── PCBViewer3D.tsx         # 3D PCB 查看器
│   │   ├── KiCadIPCStatus.tsx      # IPC 状态显示
│   │   └── CanvasContainer.tsx     # 画布容器
│   │
│   ├── editors/                    # 编辑器组件
│   │   ├── SchematicEditor.tsx     # 原理图编辑器
│   │   └── PCBEditor.tsx           # PCB 编辑器
│   │
│   ├── canvas/                     # 画布渲染组件
│   │   ├── SimpleCanvas.tsx        # 基础画布
│   │   ├── PCBCanvas.tsx           # PCB 画布
│   │   ├── FootprintRenderer.tsx   # 封装渲染器
│   │   ├── TrackRenderer.tsx       # 走线渲染器
│   │   ├── ViaRenderer.tsx         # 过孔渲染器
│   │   ├── BoardOutlineRenderer.tsx # 板框渲染器
│   │   └── RoutingTool.tsx         # 布线工具
│   │
│   ├── panels/                     # 侧边面板
│   │   ├── DRCPanel.tsx            # DRC 检查面板
│   │   ├── PropertyPanel.tsx       # 属性面板
│   │   ├── ExportPanel.tsx         # 导出面板
│   │   └── LayerPanel.tsx          # 图层面板
│   │
│   ├── pages/                      # 页面组件
│   │   └── ProjectList.tsx         # 项目列表页面
│   │
│   ├── stores/                     # Zustand 状态管理
│   │   ├── kicadStore.ts           # KiCad 状态
│   │   ├── simpleStore.ts          # 简单状态
│   │   ├── pcbStore.ts             # PCB 状态
│   │   └── schematicStore.ts       # 原理图状态
│   │
│   ├── services/                   # API 服务
│   │   ├── api.ts                  # REST API 客户端
│   │   └── webmcp.ts               # WebMCP 服务
│   │
│   ├── types/                      # TypeScript 类型
│   │   └── index.ts                # 类型定义
│   │
│   └── test/                       # 测试文件
│       ├── setup.ts                # 测试设置
│       ├── api.test.ts             # API 测试
│       ├── kicadStore.test.ts      # 状态测试
│       ├── schematicStore.test.ts   # 原理图状态测试
│       ├── pcbStore.test.ts        # PCB 状态测试
│       ├── PCBCanvas.test.tsx      # PCB 画布测试
│       ├── MenuBar.test.tsx        # 菜单栏测试
│       ├── ToolBar.test.tsx        # 工具栏测试
│       ├── StatusBar.test.tsx      # 状态栏测试
│       ├── OutputPanel.test.tsx    # 输出面板测试
│       ├── FootprintRenderer.test.tsx
│       ├── TrackRenderer.test.tsx
│       ├── ViaRenderer.test.tsx
│       └── useWebSocket.test.ts    # WebSocket 测试
│
└── dist/                          # 构建输出
    ├── index.html
    └── assets/
```

### 3. Docker 配置

```
docker/
├── Dockerfile                      # KiCad 容器镜像
├── docker-entrypoint.sh            # 容器启动脚本
└── requirements.txt                # Python 依赖
```

### 4. 测试相关

```
playwright-tests/
├── kicad_ai_agent.py              # AI 自动化代理
└── test_kicad_automation.py       # E2E 测试

tests/
└── TEST_DOCUMENTATION.md          # 测试文档
```

---

## 核心技术栈

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主开发语言 |
| **FastAPI** | 最新 | Web 框架 |
| **Pydantic** | - | 数据验证 |
| **uvicorn** | - | ASGI 服务器 |
| **slowapi** | - | 限流中间件 |
| **requests** | - | HTTP 客户端 |
| **Pillow** | - | 图像处理 |
| **python-xlib** | - | X11 截图（Linux） |
| **pywin32** | - | Windows API 调用 |

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18.3 | UI 框架 |
| **TypeScript** | 5.5 | 类型系统 |
| **Vite** | 5.4 | 构建工具 |
| **Zustand** | 4.5 | 状态管理 |
| **React Router** | 6.22 | 路由管理 |
| **React Konva** | 18.2 | 2D 画布渲染 |
| **React Three Fiber** | 8.18 | 3D 渲染 |
| **Three.js** | 0.182 | 3D 引擎 |
| **Tailwind CSS** | 3.4 | 样式框架 |
| **Axios** | 1.6 | HTTP 客户端 |
| **Vitest** | 2.0 | 测试框架 |
| **Radix UI** | - | UI 组件库 |

---

## 核心模块详解

### 1. KiCadController (kicad_controller.py)

**功能**: KiCad 核心控制模块

**主要功能**:
- 菜单操作 (`click_menu`)
- 工具激活 (`activate_tool`)
- 鼠标操作 (点击、移动、拖拽)
- 键盘操作 (按键、文本输入)
- 屏幕截图
- DRC 检查
- 文件导出 (Gerber, Drill, BOM, PDF, SVG, STEP)

**平台支持**:
- Windows: 使用 pywin32 进行窗口管理和截图
- Linux: 使用 Xlib 进行 X11 截图
- 跨平台: 使用 PyAutoGUI 进行自动化操作

### 2. ExportManager (export_manager.py)

**功能**: 统一导出管理

**支持格式**:
- Gerber (RS-274X)
- Drill (Excellon)
- BOM (CSV)
- Pick & Place (CSV)
- PDF
- SVG
- STEP (3D)

### 3. StateMonitor (state_monitor.py)

**功能**: 实时监控 KiCad 状态

**监控内容**:
- 当前工具
- 活动层
- PCB 元素（走线、过孔、封装）
- 截图变化检测

### 4. KiCadIPCManager (kicad_ipc_manager.py)

**功能**: KiCad IPC 通信管理

**通信方式**:
- 命名管道 (Windows)
- Unix Socket (Linux)

### 5. GLM4Client (glm4_client.py)

**功能**: 智谱 AI GLM-4 大模型集成

**用途**: 
- 根据需求描述生成电路项目方案
- 解析 AI 返回的 JSON 项目规格
- 包含多种 JSON 解析容错机制

### 6. FootprintLibrary (footprint_library.py)

**功能**: 封装库管理

**功能特性**:
- 默认封装映射表（电阻、电容、IC 等）
- 元件类型推断
- 符号到封装的推荐映射
- KiCad 封装库目录扫描

### 7. ComponentKnowledge (component_knowledge/)

**组件数据库**:
- `component_db.json`: 包含常用电子元件的参数信息

---

## API 接口文档

### REST API 端点

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/project/start` | 启动 KiCad |
| POST | `/api/project/open` | 打开项目 |
| POST | `/api/project/save` | 保存项目 |
| POST | `/api/menu/click` | 点击菜单 |
| POST | `/api/tool/activate` | 激活工具 |
| POST | `/api/input/mouse` | 鼠标操作 |
| POST | `/api/input/keyboard` | 键盘操作 |
| POST | `/api/export` | 导出文件 |
| POST | `/api/drc/run` | 运行 DRC |
| GET | `/api/state/screenshot` | 获取截图 |
| GET | `/api/state/full` | 获取完整状态 |
| POST | `/api/ai/create-project` | AI 创建项目 |

### WebSocket 端点

| 端点 | 功能 |
|------|------|
| `/ws/control` | 实时控制通道 |

---

## 测试状态

### 测试统计

| 类别 | 数量 |
|------|------|
| 后端测试文件 | 15 |
| 前端测试文件 | 16 |
| 后端测试用例 | 226 |
| 前端测试用例 | 163 |

### 后端测试文件

```
tests/
├── test_api.py                   # API 端点测试
├── test_controller.py            # 控制器逻辑测试
├── test_middleware.py            # 中间件测试
├── test_export_manager.py        # 导出管理器测试
├── test_state_monitor.py         # 状态监控测试
├── test_ipc_manager.py          # IPC 管理器测试
├── test_ipc_routes.py           # IPC 路由测试
├── test_knowledge_base.py        # 知识库测试
├── test_auto_starter.py         # 自动启动测试
├── test_diagnose_screenshot.py  # 截图诊断测试
├── test_footprint_library.py    # 封装库测试
└── test_glm4_client.py          # GLM 客户端测试
```

### 前端测试文件

```
src/test/
├── api.test.ts
├── kicadStore.test.ts
├── schematicStore.test.ts
├── pcbStore.test.ts
├── PCBCanvas.test.tsx
├── MenuBar.test.tsx
├── ToolBar.test.tsx
├── StatusBar.test.tsx
├── OutputPanel.test.tsx
├── FootprintRenderer.test.tsx
├── TrackRenderer.test.tsx
├── ViaRenderer.test.tsx
└── useWebSocket.test.ts
```

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOG_LEVEL` | INFO | 日志级别 |
| `PROJECTS_DIR` | /projects | 项目目录 |
| `ALLOWED_ORIGINS` | localhost:3000,localhost:3001 | CORS 允许域名 |
| `API_KEY` | - | API 认证密钥 |
| `ZHIPU_API_KEY` | - | 智谱 AI API 密钥 |

### KiCad 路径配置

- **Windows**: `E:\Program Files\KiCad\9.0`
- **Linux**: `/usr/share/kicad`

---

## 快速开始

### 后端启动

```bash
cd kicad-ai-auto/agent

# 创建虚拟环境（首次）
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt

# 启动服务
venv\Scripts\python main.py
```

### 前端启动

```bash
cd kicad-ai-auto/web

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

### 运行测试

```bash
# 后端测试
cd kicad-ai-auto/agent
pytest tests/ -v

# 前端测试
cd kicad-ai-auto/web
npm run test

# 所有测试
cd kicad-ai-auto
python run_all_tests.py
```

---

## 已知限制

1. **kicad_controller.py 覆盖率低**: 包含大量需要真实 KiCad 环境的 GUI 自动化代码，难以单元测试
2. **平台依赖**: 某些功能仅在特定平台可用（Windows/Linux）
3. **外部依赖**: 需要 KiCad 9.0+ 安装在系统中

---

## 许可证

GPL-3.0
