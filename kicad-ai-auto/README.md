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
- ODB++ (制造数据包)
- Drill (Excellon)
- BOM (CSV, 支持 LCSC 料号)
- Pick & Place (CSV)
- PDF
- SVG
- STEP (3D)

### 🔍 质量验证 (Phase 5)
- **高级 DRC**: 30+ 设计规则检查
- **SI 分析**: 阻抗控制、差分对、传输损耗、串扰
- **EMI 热点**: 时钟线、分割平面、串扰可视化
- **制造检查**: JLCPCB/PCBWay 规则验证
- **IPC-2221 进阶**: 多铜厚/温升/内层外层选项

### ⚡ Phase 6 增强功能
- **符号搜索**: 支持模糊匹配、类别过滤、分页检索 KiCad 符号库
- **批量放置**: 通过 BOM 文本批量放置元件，支持网格/水平/垂直布局策略
- **扇出引擎**: 自动为元件引脚生成扇出过孔和走线
- **交互式布线**: A* 寻路算法支持障碍规避、45度角约束
- **铜箔填充**: 支持地铜/电源铜箔、热焊盘、通孔隔离
- **项目模板**: 预定义项目模板（Arduino Shield、Raspberry Pi Pico 等）
- **原理图层次化**: 支持层次化原理图设计

### 🔧 Phase 7-8 布线与质量
- **DRC Dashboard**: 统一的 DRC/Safety/SI/EMI 检查面板
- **布线引擎**: A* 寻路、多引脚 MST 连接、网络感知路由
- **质量评分**: 布线密度、可制造性、信号完整性评分

### 📊 Phase 9-10 前端增强
- **布线可视化**: 走线、过孔、铜箔实时渲染
- **布线进度**: Web Worker 后台布线，实时进度反馈
- **视口剔除**: 大型 PCB 高性能渲染

### 🏭 Phase 11 制造生态
- **BOM Manager**: 元件生命周期、替代料、库存管理
- **Manufacturing Wizard**: JLCPCB/PCBWay 一键下单
- **成本估算**: 板材、工艺、数量综合估价

### 🌐 Phase 12 商业化
- **空间索引**: R-tree 碰撞检测、间距检查
- **缓存服务**: Redis/内存缓存，API 加速
- **用户认证**: JWT 登录、角色权限
- **项目共享**: 分享链接、权限管理
- **实时协作**: WebSocket 光标同步、变更广播
- **版本历史**: 快照、回滚、标签
- **插件生态**: 模板市场、自定义 DRC、SDK 生成
- **国际化**: en-US/zh-CN/ja-JP 多语言支持

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
- **符号搜索**: 点击工具栏"符号搜索"按钮，检索和放置符号
- **批量放置**: 点击"批量放置"按钮，通过 BOM 批量添加元件

### 3. 编辑 PCB

在 PCB 编辑器中可以：
- 调整元件位置
- 手动/自动布线
- 添加过孔
- 铺铜
- 设计规则检查 (DRC)
- **扇出**: 选中元件后点击"扇出"按钮，自动生成引脚扇出过孔

## 项目结构

```
kicad-ai-auto/
├── agent/                  # Python FastAPI 后端
│   ├── main.py             # 主入口
│   ├── routes/             # API 路由
│   │   ├── ai_routes.py   # AI 分析和生成
│   │   ├── project_routes.py  # 项目管理
│   │   ├── drc_routes.py  # DRC/SI/EMI 分析
│   │   ├── symbol_routes.py  # Phase 6 符号搜索
│   │   ├── template_routes.py  # Phase 6 项目模板
│   │   └── knowledge_routes.py  # Phase 6 知识库
│   ├── schematic/           # Phase 6 原理图引擎
│   │   ├── symbol_search.py  # 符号搜索引擎
│   │   ├── bulk_placement.py  # 批量放置引擎
│   │   └── hierarchical_sch.py  # 层次化原理图
│   ├── routing/            # Phase 6 布线引擎
│   │   ├── astar_router.py  # A* 寻路算法
│   │   └── copper_pour.py  # 铜箔填充
│   ├── placement/          # Phase 6 放置引擎
│   │   └── smart_placement_engine.py  # 智能放置
│   ├── drc/                # 设计规则检查
│   │   ├── advanced_drc.py
│   │   └── si_analyzer.py  # 信号完整性分析
│   ├── design_rules/       # 设计规则
│   │   └── emi_hotspot_analyzer.py  # EMI 热点分析
│   ├── export/              # 制造导出
│   │   ├── gerber_generator.py
│   │   ├── bom_generator.py
│   │   ├── odbxx_generator.py  # ODB++ 导出
│   │   └── manufacturing_checker.py
│   ├── pcb/                # PCB 生成
│   │   ├── net_classifier.py
│   │   ├── current_calculator.py  # IPC-2221 进阶
│   │   └── layer_stackup.py
│   ├── kb_quality/         # Phase 5/6 知识库质量体系
│   │   ├── validators.py
│   │   ├── cross_checker.py
│   │   └── quality_runner.py
│   ├── services/           # Phase 12 商业化服务
│   │   ├── auth_service.py   # JWT 认证
│   │   ├── sharing_service.py # 项目共享
│   │   ├── collaboration_service.py # 实时协作
│   │   ├── version_service.py # 版本历史
│   │   ├── spatial_index.py  # 空间索引 (R-tree)
│   │   ├── cache_service.py  # Redis/内存缓存
│   │   ├── marketplace_service.py # 模板市场
│   │   ├── custom_drc_service.py # 自定义 DRC
│   │   ├── sdk_generator.py  # SDK 生成
│   │   └── i18n_service.py   # 国际化
│   └── tests/              # 测试
├── web/                    # React 前端
│   ├── src/
│   │   ├── components/    # UI 组件
│   │   │   ├── SymbolSearchPanel.tsx  # Phase 6 符号搜索
│   │   │   ├── BulkPlacementDialog.tsx  # Phase 6 批量放置
│   │   │   ├── FanoutDialog.tsx  # Phase 6 扇出
│   │   │   ├── DRCDashboard.tsx  # Phase 7 DRC 面板
│   │   │   ├── RoutingQualityPanel.tsx  # Phase 9 布线质量
│   │   │   ├── BOMManagerPanel.tsx  # Phase 11 BOM 管理
│   │   │   └── ManufacturingWizard.tsx  # Phase 11 制造向导
│   │   ├── pages/         # 页面
│   │   │   └── AdminPanel.tsx  # 管理面板
│   │   ├── stores/        # 状态管理
│   │   ├── hooks/         # Phase 12 Hooks
│   │   │   ├── useI18n.ts     # 国际化
│   │   │   ├── useRoutingWorker.ts  # 布线 Worker
│   │   │   └── useVirtualRenderer.ts # 虚拟渲染
│   │   ├── workers/       # Web Workers
│   │   │   └── routerWorker.ts  # 布线 Worker
│   │   └── editors/       # 编辑器
│   └── package.json
├── docker/                # Docker 配置
├── playwright-tests/       # 自动化测试
└── docs/           # 文档
```

## API 文档

### AI 分析接口

- `POST /api/v1/ai/analyze` - 分析需求，生成方案和原理图
- `POST /api/v1/ai/enhance` - 电路增强

### 项目管理接口

- `GET /api/v1/projects` - 获取项目列表
- `POST /api/v1/projects` - 创建新项目
- `GET /api/v1/projects/{id}` - 获取项目详情
- `GET /api/v1/projects/{id}/schematic` - 获取原理图数据
- `GET /api/v1/projects/{id}/pcb/design` - 获取 PCB 数据

### DRC / SI / EMI 接口

- `POST /drc/check` - 设计规则检查
- `POST /drc/si/analyze` - 信号完整性分析
- `POST /drc/emi/analyze` - EMI 热点分析
- `POST /drc/emi/visualization` - EMI 可视化数据

### 制造导出接口

- `POST /export/gerber` - 导出 Gerber 文件
- `POST /export/bom` - 导出 BOM
- `POST /export/odb` - 导出 ODB++ 制造包
- `POST /export/manufacturing-check` - 制造可行性检查
- `POST /export/cost-estimate` - 费用估算

### 设置管理接口

- `POST /api/admin/settings/pcb` - PCB 参数设置
- `POST /api/admin/settings/ai` - AI 模型配置
- `POST /api/admin/settings/manufacturing` - 制造选项

### KiCad IPC 接口

- `POST /api/kicad-ipc/start` - 启动 KiCad
- `POST /api/kicad-ipc/stop` - 停止 KiCad
- `POST /api/kicad-ipc/action` - 执行 KiCad 操作
- `GET /api/kicad-ipc/items` - 获取 PCB 元素列表

### Phase 6 符号与模板接口

- `POST /api/v1/symbols/search` - 搜索符号（支持模糊匹配、分类过滤）
- `GET /api/v1/symbols/categories` - 获取符号类别列表
- `POST /api/v1/symbols/bulk-place` - 批量放置元件
- `POST /api/v1/pcb/fanout` - PCB 扇出
- `GET /api/v1/pcb/fanout/pin-spacing/{package_type}` - 获取引脚间距
- `GET /api/v1/templates` - 获取项目模板列表
- `GET /api/v1/templates/categories` - 获取模板类别
- `POST /api/v1/templates/create-project` - 从模板创建项目

### Phase 6 知识库接口

- `GET /api/v1/knowledge/health` - 知识库健康状态
- `GET /api/v1/knowledge/quality/summary` - 质量门控统计
- `GET /api/v1/knowledge/categories` - 元件类别列表
- `POST /api/v1/knowledge/lcsc/search` - LCSC 元件搜索
- `POST /api/v1/knowledge/parse/ad` - 解析 Altium Designer 原理图
- `POST /api/v1/knowledge/parse/jlc` - 解析嘉立创 EDA 项目

### Phase 7-8 DRC 与布线接口

- `POST /drc/check` - 设计规则检查 (30+ 规则)
- `POST /drc/si/analyze` - 信号完整性分析
- `POST /drc/emi/analyze` - EMI 热点分析
- `GET /drc/emi/visualization` - EMI 可视化数据

### Phase 11 制造接口

- `POST /export/manufacturing-check` - 制造可行性检查 (JLCPCB/PCBWay)
- `POST /export/cost-estimate` - 成本估算
- `POST /export/bom` - BOM 导出 (含 LCSC 料号)
- `POST /export/odb` - ODB++ 制造包导出

### Phase 12 商业化接口

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新 Token
- `GET /api/v1/auth/me` - 当前用户信息
- `POST /api/v1/projects/{id}/share` - 共享项目
- `GET /api/v1/projects/{id}/revisions` - 版本历史
- `POST /api/v1/projects/{id}/rollback` - 回滚版本
- `WS /api/v1/collab/{project_id}` - 实时协作 WebSocket
- `GET /api/v1/spatial/collisions` - 碰撞检测
- `POST /api/v1/spatial/clearance-check` - 间距检查
- `GET /api/v1/cache/stats` - 缓存统计
- `GET /api/v1/ecosystem/templates` - 模板市场
- `POST /api/v1/ecosystem/drc/run` - 自定义 DRC
- `GET /api/v1/ecosystem/sdk/python` - Python SDK
- `GET /api/v1/ecosystem/i18n/translations` - 多语言翻译

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
