# KiCad AI 自动化控制系统

## 项目概述

这是一个完整的 KiCad AI 自动化控制解决方案，允许通过浏览器界面控制 KiCad，并提供 Playwright 接口供 AI 自动化操作。

## 项目结构

```
kicad-ai-auto/
├── agent/                  # Python FastAPI 后端
│   ├── main.py            # FastAPI 主应用
│   ├── kicad_controller.py # KiCad 控制核心
│   ├── export_manager.py   # 导出管理器
│   ├── state_monitor.py    # 状态监控器
│   └── requirements.txt    # Python 依赖
├── web/                    # React 前端（待开发）
├── docker/                 # Docker 配置
│   ├── Dockerfile          # KiCad 容器
│   ├── docker-entrypoint.sh
│   └── requirements.txt
├── playwright-tests/       # Playwright 自动化测试
│   └── kicad_ai_agent.py  # AI 控制接口
├── docs/                   # 文档
│   ├── plan.txt           # 项目方案
│   └── Todo.txt           # 执行计划
└── scripts/               # 辅助脚本
```

## 快速开始

### 1. 使用 Docker 启动

```bash
# 构建镜像
cd docker
docker build -t kicad-ai-auto .

# 运行容器
docker run -d \
  -p 6080:6080 \
  -p 8000:8000 \
  -v $(pwd)/projects:/projects \
  -v $(pwd)/output:/output \
  -e ENABLE_NOVNC=true \
  kicad-ai-auto
```

### 2. 启动控制代理

```bash
cd agent
pip install -r requirements.txt
python main.py
```

### 3. 使用 Playwright 自动化

```python
from playwright_tests.kicad_ai_agent import KiCadAIAgent
import asyncio

async def main():
    agent = KiCadAIAgent()
    await agent.connect()
    
    # 创建项目
    await agent.create_project("test")
    
    # 放置器件
    await agent.place_symbol("R", 50000000, 50000000)
    
    # 导出 Gerber
    await agent.export_gerber("/output/gerber")
    
    await agent.disconnect()

asyncio.run(main())
```

## API 文档

### REST API

- `POST /api/project/start` - 启动 KiCad
- `POST /api/project/open` - 打开项目
- `POST /api/project/save` - 保存项目
- `POST /api/menu/click` - 点击菜单
- `POST /api/tool/activate` - 激活工具
- `POST /api/input/mouse` - 鼠标操作
- `POST /api/input/keyboard` - 键盘操作
- `POST /api/export` - 导出文件
- `POST /api/drc/run` - 运行 DRC
- `GET /api/state/screenshot` - 获取截图
- `GET /api/state/full` - 获取完整状态
- `WS /ws/control` - WebSocket 控制通道

### 支持的导出格式

- Gerber (RS-274X)
- Drill (Excellon)
- BOM (CSV)
- Pick & Place (CSV)
- PDF
- SVG
- STEP (3D)

## 开发计划

参见 `docs/Todo.txt`

## 许可证

GPL-3.0
