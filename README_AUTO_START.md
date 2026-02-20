# KiCad AI Auto - 自动启动方案

本项目现在支持**全自动一键启动**，包含 A、B、C 三个步骤的自动化实现。

## 🎯 启动方式选择

### 🥇 方式一：一键启动（最简单，推荐）

**双击运行**：`一键启动.bat`

**自动完成**：
- ✅ 检查 KiCad 9.0 安装
- ✅ 自动安装 Python 依赖（kicad-python, pywin32）
- ✅ 自动启动后端服务（端口 8000）
- ✅ 自动启动 KiCad PCB Editor
- ✅ 自动尝试 IPC 连接
- ✅ 自动启动前端界面（端口 3000/5173）
- ✅ 自动打开浏览器

**唯一需要手动操作**：
```
在 KiCad 中点击：Tools → External Plugin → Start Server
然后回到命令窗口按 Enter 继续
```

---

### 🥈 方式二：图形界面启动（带进度显示）

**双击运行**：`start-all-auto.bat`

特点：
- 彩色命令行界面
- 显示详细进度步骤
- 交互式确认
- 更适合首次使用

---

### 🥉 方式三：诊断后启动（排查问题）

**第一步**：运行 `诊断工具.bat`

检查项：
- KiCad 安装状态
- Python 虚拟环境
- 依赖库安装情况
- 端口占用情况
- 环境变量配置

**第二步**：根据诊断结果修复问题

**第三步**：运行 `一键启动.bat`

---

## 🔄 三种方案对比

| 特性 | 一键启动 | 高级启动 | 诊断+启动 |
|------|---------|---------|----------|
| 操作难度 | ⭐ 最简单 | ⭐⭐ 中等 | ⭐⭐⭐ 完整 |
| 交互提示 | 较少 | 详细 | 诊断详细 |
| 适合场景 | 日常使用 | 首次使用 | 遇到问题 |
| 自动打开浏览器 | ✅ | ✅ | 手动 |
| 诊断功能 | ❌ | ❌ | ✅ |

---

## 📁 启动脚本说明

| 脚本文件 | 用途 | 使用场景 |
|---------|------|---------|
| `一键启动.bat` | 全自动启动 | 日常使用 |
| `start-all-auto.bat` | 高级启动（带交互） | 首次使用 |
| `诊断工具.bat` | 环境检查 | 排查问题 |
| `start_backend.bat` | 仅启动后端 | 开发调试 |
| `start-docker.bat` | Docker 启动 | 容器化部署 |

---

## 🚀 快速开始（3分钟）

### 步骤 1：环境检查（30秒）

双击运行：`诊断工具.bat`

确保所有检查项都通过 ✅

### 步骤 2：一键启动（2分钟）

双击运行：`一键启动.bat`

等待自动完成：
```
[1/6] ✅ KiCad 9.0 已确认安装
[2/6] 正在检查 Python 依赖...
       ✅ kicad-python 已安装
       ✅ pywin32 已就绪
[3/6] 正在启动后端服务...
       ✅ 后端已启动 (http://localhost:8000)
[4/6] 正在启动 KiCad PCB Editor...
       ✅ KiCad 已启动
⚠️  重要：请在 KiCad 中启用 IPC Server：
   Tools → External Plugin → Start Server
按任意键确认已启用 IPC Server...
[5/6] 正在启动前端界面...
       ✅ 前端已启动 (http://localhost:3000)
[6/6] ✅ 所有服务启动完成！
正在自动打开浏览器...
```

### 步骤 3：开始使用

浏览器自动打开后：
1. 在 KiCad IPC 控制面板查看连接状态
2. 点击"测试：放置电阻"按钮
3. 在 KiCad 中查看放置的器件

---

## 📚 详细文档

- **快速启动指南**：`QUICK_START.md`
- **IPC 集成说明**：`KICAD_IPC_INTEGRATION.md`
- **API 文档**：启动后访问 http://localhost:8000/docs
- **项目计划**：`plan.txt`
- **任务清单**：`Todo.txt`

---

## 🔧 故障排除

### 问题 1：KiCad IPC 连接失败

**症状**：状态显示 `{"connected":false}`

**解决**：
1. 确认 KiCad 已启动
2. 确认已启用 IPC Server（Tools → External Plugin → Start Server）
3. 系统将自动回退到 PyAutoGUI 模式

### 问题 2：端口被占用

**症状**：启动失败，提示端口冲突

**解决**：
```bash
# 查看占用端口的进程
netstat -ano | findstr ":8000"
netstat -ano | findstr ":3000"

# 在任务管理器中结束对应进程
```

### 问题 3：依赖安装失败

**症状**：提示 kicad-python 或 pywin32 未安装

**解决**：
```bash
cd kicad-ai-auto/agent
venv\Scripts\pip install kicad-python pywin32
```

### 问题 4：前端无法访问

**症状**：浏览器无法打开 localhost:3000

**解决**：
1. 检查前端是否真的启动（查看命令窗口）
2. 尝试访问 http://localhost:5173（Vite 备用端口）
3. 检查防火墙设置

---

## 🎓 技术实现说明

### A. 启动 KiCad 并启用 IPC Server

```python
# auto_starter.py 自动检测和启动 KiCad
if not is_process_running("pcbnew.exe"):
    subprocess.Popen([kicad_path])
    # 等待用户手动启用 IPC Server
```

### B. 安装 kicad-python 库

```python
# 自动检查并安装
try:
    import kipy
except ImportError:
    subprocess.run([pip_path, "install", "kicad-python"])
```

### C. 启动前端界面

```bash
# 自动检查 node_modules
if not exist "node_modules":
    npm install

# 启动开发服务器
npm run dev
```

---

## 🌟 新功能特性

### IPC API 集成
- 使用官方 `kicad-python` (kipy) 库
- 支持 Windows Named Pipe 通信
- 实时双向通信（WebSocket + IPC）
- 自动回退到 PyAutoGUI 模式

### 智能启动
- 自动检测 KiCad 是否已运行
- 自动检测端口占用
- 自动安装缺失依赖
- 自动重连 WebSocket

### 用户友好
- 一键双击启动
- 中文提示信息
- 自动打开浏览器
- 详细的错误提示

---

## 📞 获取帮助

如果启动遇到问题：

1. **运行诊断工具**：`诊断工具.bat`
2. **查看日志**：各命令窗口中的输出
3. **检查文档**：`QUICK_START.md`
4. **手动启动**：参考文档中的手动启动步骤

---

## ✅ 验证清单

启动成功后，你应该能看到：

- [ ] 后端运行在 http://localhost:8000
- [ ] KiCad PCB Editor 已启动
- [ ] 前端运行在 http://localhost:3000
- [ ] 浏览器自动打开并显示控制面板
- [ ] 控制面板显示 KiCad 连接状态

---

**现在就开始**：双击 `一键启动.bat` 🚀
