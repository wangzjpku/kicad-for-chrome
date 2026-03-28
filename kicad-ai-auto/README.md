# KiCad AI 自动化控制系统

[English](README_en.md) | 中文

## 项目概述

KiCad AI Automation 是一个完整的 AI 驱动的 KiCad PCB 设计自动化解决方案。通过自然语言描述需求，AI 可以自动生成原理图、PCB 布局，并支持导出各种格式的制造文件。

## 功能特性

### 🤖 AI 智能设计
- **自然语言输入**: 用中文描述您的电路需求
- **智能电路识别**: 自动识别 ESP32、Arduino、STM32、电源模块等
- **自动原理图生成**: AI 自动创建符合标准的原理图
- **自动 PCB 布局**: 从原理图自动转换并优化 PCB 布局

### 🖥️ 多种运行模式
- **IPC API 模式** (推荐): 使用 KiCad 9.0+ 官方 IPC API
- **Docker/X11 模式**: Linux 容器化运行
- **PyAutoGUI 模式**: 跨版本兼容（遗留模式）

### 📤 导出支持
- Gerber (RS-274X)
- Drill (Excellon)
- BOM (CSV)
- Pick & Place (CSV)
- PDF
- SVG
- STEP (3D)

## 快速开始

### Windows 本地运行 (推荐)

1. **启动后端服务**
```bash
cd kicad-ai-auto/agent
venv\Scripts\python main.py
```

2. **启动前端**
```bash
cd kicad-ai-auto/web
npm run dev
```

3. **打开浏览器**
访问 http://localhost:3000

### 使用 Docker (Linux)

```bash
cd kicad-ai-auto
docker-compose up -d
```

访问:
- Web 界面: http://localhost:3000
- API 文档: http://localhost:8000/docs

## 使用指南

### 1. 创建 AI 项目

1. 点击主页面的 "🤖 AI 创建" 按钮
2. 输入电路需求描述，例如：
   - "设计一个 ESP32 的智能控制器"
   - "做一个 5V 稳压电源"
   - "STM32 温度传感器模块"
3. AI 会分析需求并提出澄清问题
4. 回答问题后，AI 生成原理图和 BOM
5. 预览方案，可选择编辑
6. 确认创建，生成完整项目

### 2. 编辑原理图

在原理图编辑器中可以：
- 移动元件
- 添加/删除导线
- 添加网络标签
- 编辑元件属性

### 3. 编辑 PCB

在 PCB 编辑器中可以：
- 调整元件位置
- 手动/自动布线
- 添加过孔
- 铺铜
- 设计规则检查 (DRC)

## 项目结构

```
kicad-ai-auto/
├── agent/                  # Python FastAPI 后端
│   ├── main.py             # 主入口
│   ├── routes/             # API 路由
│   │   ├── ai_routes.py   # AI 分析和生成
│   │   ├── project_routes.py  # 项目管理
│   │   └── kicad_ipc_routes.py  # KiCad IPC
│   ├── schematic_generator.py  # 原理图生成器
│   ├── pcb_generator.py    # PCB 生成器
│   └── component_knowledge/  # 元件知识库
├── web/                    # React 前端
│   ├── src/
│   │   ├── components/    # UI 组件
│   │   ├── pages/         # 页面
│   │   ├── stores/        # 状态管理
│   │   └── editors/       # 编辑器
│   └── package.json
├── docker/                # Docker 配置
├── playwright-tests/       # 自动化测试
└── VERSION.md             # 版本信息
```

## API 文档

### AI 分析接口

- `POST /api/v1/ai/analyze` - 分析需求，生成方案和原理图

### 项目管理接口

- `GET /api/v1/projects` - 获取项目列表
- `POST /api/v1/projects` - 创建新项目
- `GET /api/v1/projects/{id}` - 获取项目详情
- `GET /api/v1/projects/{id}/schematic` - 获取原理图数据
- `GET /api/v1/projects/{id}/pcb/design` - 获取 PCB 数据

### KiCad IPC 接口

- `POST /api/kicad-ipc/start` - 启动 KiCad
- `POST /api/kicad-ipc/stop` - 停止 KiCad
- `POST /api/kicad-ipc/action` - 执行 KiCad 操作
- `GET /api/kicad-ipc/items` - 获取 PCB 元素列表

完整 API 文档请访问: http://localhost:8000/docs

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- KiCad Python API (kicad-python)
- Pydantic

### 前端
- React 18+
- TypeScript
- Vite
- Zustand (状态管理)
- Konva.js (画布)
- Tailwind CSS

### DevOps
- Docker
- Playwright

## 系统要求

- **KiCad**: 9.0+ (推荐)
- **Node.js**: 18+
- **Python**: 3.11+
- **操作系统**: Windows 10+, Linux, macOS

## 常见问题

### Q: AI 返回的是模板而不是我需要的电路
A: 请确保输入中包含具体的关键词（如"ESP32"、"STM32"），AI 会根据关键词触发动态生成。

### Q: 创建的项目原理图为空
A: 这是一个已知的 bug，已经修复。请确保使用最新版本。

### Q: Windows 下无法启动
A: 请确保已安装 KiCad 9.0+ 并配置正确的路径。检查 .env 文件中的 KICAD_CLI_PATH。

## 许可证

GPL-3.0

## 贡献

欢迎提交 Issue 和 Pull Request！
