# KiCad AI Auto - 快速启动指南

## 🚀 一键启动（推荐）

### 方式一：双击启动（最简单）

1. **双击运行**：`一键启动.bat`
2. **等待自动完成**：
   - 自动检查 KiCad 安装
   - 自动安装 Python 依赖（kicad-python, pywin32）
   - 自动启动后端服务
   - 自动启动 KiCad PCB Editor
   - 自动启动前端界面
   - 自动打开浏览器

3. **手动操作（仅需一次）**：
   - 在 KiCad 中点击：`Tools → External Plugin → Start Server`
   - 回到命令窗口按 Enter 继续

### 方式二：高级启动脚本

1. **双击运行**：`start-all-auto.bat`
2. 按提示操作，脚本会引导你完成所有步骤

### 方式三：Python 自动启动器

```bash
cd kicad-ai-auto/agent
venv\Scripts\python auto_starter.py
```

## 📋 启动流程详解

```
┌─────────────────────────────────────────────────────┐
│                  一键启动流程                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  步骤 0: 检查 KiCad 9.0 安装                        │
│     └── 检查 E:\Program Files\KiCad\9.0            │
│         ✅ 已确认安装                               │
│                                                     │
│  步骤 B: 安装 Python 依赖                           │
│     ├── 检查 kicad-python                          │
│     │   └── pip install kicad-python               │
│     ├── 检查 pywin32                               │
│     │   └── pip install pywin32                    │
│     └── ✅ 依赖就绪                                 │
│                                                     │
│  启动后端                                           │
│     └── python main.py                             │
│         └── http://localhost:8000                  │
│             ✅ 后端运行中                           │
│                                                     │
│  步骤 A: 启动 KiCad                                 │
│     └── 启动 pcbnew.exe                            │
│         └── ⚠️  需要手动启用 IPC Server            │
│             Tools → External Plugin → Start Server │
│             ✅ KiCad 运行中                         │
│                                                     │
│  连接 KiCad IPC                                     │
│     └── POST /api/kicad-ipc/start                  │
│         └── 尝试 IPC 连接                          │
│             ✅ 已连接 / ⚠️  PyAutoGUI 模式         │
│                                                     │
│  步骤 C: 启动前端                                   │
│     └── npm run dev                                │
│         └── http://localhost:3000                  │
│             ✅ 前端运行中                           │
│                                                     │
│  自动打开浏览器                                     │
│     └── 打开 http://localhost:3000                 │
│         ✅ 启动完成！                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 🔧 手动启动（备用）

如果自动启动遇到问题，可以手动分步启动：

### 1. 启动后端

```bash
cd kicad-ai-auto/agent
venv\Scripts\python main.py
```

等待看到：
```
Uvicorn running on http://0.0.0.0:8000
KiCad IPC API routes registered
```

### 2. 启动 KiCad

双击：`E:\Program Files\KiCad\9.0\bin\pcbnew.exe`

启用 IPC Server：`Tools → External Plugin → Start Server`

### 3. 连接 KiCad

```bash
curl -X POST http://localhost:8000/api/kicad-ipc/start
```

### 4. 启动前端

```bash
cd kicad-ai-auto/web
npm run dev
```

访问：http://localhost:3000

## 🌐 访问地址

启动完成后，可以通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端界面** | http://localhost:3000 | React Web UI |
| **API 文档** | http://localhost:8000/docs | Swagger UI |
| **健康检查** | http://localhost:8000/api/health | 后端状态 |
| **KiCad IPC** | http://localhost:8000/api/kicad-ipc/status | IPC 连接状态 |

## ✅ 验证启动成功

### 检查 1: 后端运行

```bash
curl http://localhost:8000/api/health
```

**预期返回**：
```json
{"status":"healthy","kicad_running":false}
```

### 检查 2: KiCad IPC 连接

```bash
curl http://localhost:8000/api/kicad-ipc/status
```

**预期返回**（KiCad 运行后）：
```json
{
  "connected": true,
  "board_path": "xxx.kicad_pcb",
  "item_count": 42,
  "items": [...]
}
```

### 检查 3: 前端界面

浏览器访问 http://localhost:3000

应该看到：
- KiCad IPC 控制面板
- 连接状态显示
- 操作按钮

## 📝 重要提示

### 首次使用

1. **KiCad 必须启动**：IPC API 要求 KiCad GUI 实际运行
2. **启用 IPC Server**：首次使用需在 KiCad 中手动启用
3. **Windows 防火墙**：可能需要允许 KiCad 网络访问

### 常见问题

**Q: 提示 "KiCad not connected"**

A: 需要在 KiCad 中启用 IPC Server：
`Tools → External Plugin → Start Server`

**Q: 提示 "kicad-python not installed"**

A: 自动安装可能失败，手动安装：
```bash
cd kicad-ai-auto/agent
venv\Scripts\pip install kicad-python pywin32
```

**Q: 前端无法连接**

A: 检查：
1. 后端是否运行在 8000 端口
2. `.env` 文件中的 `ALLOWED_ORIGINS` 是否包含前端地址
3. 浏览器控制台是否有 CORS 错误

**Q: 端口被占用**

A: 检查并关闭占用端口的程序：
```bash
# 查看端口占用
netstat -ano | findstr "8000"
netstat -ano | findstr "3000"
```

## 🔄 重启服务

如果服务意外停止：

1. **关闭所有命令窗口**
2. **重新双击** `一键启动.bat`

或单独重启某个服务：

```bash
# 重启后端
cd kicad-ai-auto/agent
venv\Scripts\python main.py

# 重启前端
cd kicad-ai-auto/web
npm run dev
```

## 🎯 下一步

启动成功后，你可以：

1. **在浏览器中操作 KiCad**
   - 放置器件
   - 查看板子状态
   - 获取项目列表

2. **使用 API**
   ```bash
   # 放置一个电阻
   curl -X POST http://localhost:8000/api/kicad-ipc/footprint \
     -H "Content-Type: application/json" \
     -d '{"footprint_name": "R_0603_1608Metric", "position": {"x": 100, "y": 100}}'
   ```

3. **开发新功能**
   - 修改前端组件
   - 添加后端 API
   - 集成 AI 功能

## 📞 故障排除

如果启动失败：

1. 查看命令窗口中的错误信息
2. 检查 `logs/` 目录下的日志文件
3. 确认 KiCad 9.0+ 已正确安装
4. 确认 Python 虚拟环境已正确设置

---

**最后更新**: 2026-02-12
**兼容版本**: KiCad 9.0+
**一键启动脚本**: `一键启动.bat`
