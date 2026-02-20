# KiCad IPC API 集成方案

基于官方 `kicad-python` (kipy) 库的深度集成实现

## 架构说明

```
浏览器 (React) ←→ FastAPI 后端 ←→ kipy (IPC Client) ←→ KiCad PCB Editor
                                      ↑
                                 Unix Socket / Windows Pipe
                                      ↑
                              KiCad 内置 API Server
```

**关键特性**：
- 使用 KiCad 9.0+ 官方 IPC API（取代已弃用的 SWIG API）
- 需要 KiCad GUI 实际运行（架构要求）
- 支持 Windows（Named Pipe）和 Linux/macOS（Unix Socket）
- 实时双向通信（WebSocket + IPC）

---

## 安装要求

### 1. KiCad 9.0+

下载并安装 KiCad 9.0 或更高版本：
- Windows: https://www.kicad.org/download/windows/
- macOS: https://www.kicad.org/download/macos/
- Linux: https://www.kicad.org/download/linux/

**重要**：首次使用需在 KiCad 中启用 IPC Server：
```
Tools → External Plugin → Start Server
```

### 2. Python 依赖

```bash
cd kicad-ai-auto/agent

# 激活虚拟环境
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 安装 kicad-python
pip install kicad-python

# Windows 额外需要
pip install pywin32

# Docker/无头环境需要
pip install PyVirtualDisplay
```

### 3. 环境变量配置

创建 `.env` 文件：

```bash
# Windows 示例
KICAD_CLI_PATH=C:\Program Files\KiCad\9.0\bin\kicad-cli.exe
USE_VIRTUAL_DISPLAY=false

# Linux/macOS 示例
KICAD_CLI_PATH=/usr/bin/kicad-cli
USE_VIRTUAL_DISPLAY=false
```

---

## 启动步骤

### 1. 启动后端

```bash
cd kicad-ai-auto/agent
venv\Scripts\python main.py
```

后端将启动在 `http://localhost:8000`

### 2. 启动前端（可选）

```bash
cd kicad-ai-auto/web
npm install  # 如果还没安装
npm run dev
```

前端将启动在 `http://localhost:3000`

### 3. 使用流程

1. 打开浏览器访问 `http://localhost:3000`
2. 在 KiCad IPC 控制面板点击 "启动 KiCad"
3. 如果已安装 KiCad，它会自动启动并建立 IPC 连接
4. 连接成功后可以看到板子信息和实时状态

---

## API 端点

### REST API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/kicad-ipc/start` | POST | 启动 KiCad 并建立连接 |
| `/api/kicad-ipc/stop` | POST | 关闭 KiCad 连接 |
| `/api/kicad-ipc/status` | GET | 获取连接状态和板子信息 |
| `/api/kicad-ipc/action` | POST | 执行 KiCad 动作 |
| `/api/kicad-ipc/footprint` | POST | 创建封装（器件） |
| `/api/kicad-ipc/items` | GET | 获取 PCB 项目列表 |
| `/api/kicad-ipc/selection` | GET | 获取当前选中项 |
| `/api/kicad-ipc/screenshot` | POST | 导出截图（SVG） |

### WebSocket

连接地址：`ws://localhost:8000/api/kicad-ipc/ws`

**消息类型**：

```typescript
// 客户端 -> 服务端
{ type: 'get_status' }
{ type: 'execute_action', action: 'pcbnew.PlaceFootprint', params: {} }
{ type: 'create_footprint', footprint_name: 'R_0603', position: {x: 50, y: 50}, layer: 'F.Cu' }
{ type: 'ping' }

// 服务端 -> 客户端
{ type: 'status', data: { connected: true, items: [...] } }
{ type: 'status_update', data: {...}, timestamp: 123456 }
{ type: 'action_result', data: { success: true } }
{ type: 'error', message: '...' }
{ type: 'pong' }
```

---

## 使用示例

### JavaScript/TypeScript

```typescript
import { useKiCadIPC } from './hooks/useKiCadIPC';

function App() {
  const { connected, kicadState, startKiCad, createFootprint } = useKiCadIPC();

  return (
    <div>
      <button onClick={() => startKiCad()}>
        启动 KiCad
      </button>

      {connected && (
        <button onClick={() => createFootprint('R_0603', {x: 100, y: 100})}>
          放置电阻
        </button>
      )}

      <div>项目数: {kicadState?.item_count}</div>
    </div>
  );
}
```

### Python 直接调用

```python
from kicad_ipc_manager import KiCadIPCManager, KiCadConnectionConfig

# 创建配置
config = KiCadConnectionConfig(
    kicad_cli_path="/usr/bin/kicad-cli",
    use_virtual_display=False
)

# 创建管理器
manager = KiCadIPCManager(config)

# 启动 KiCad
success = manager.start_kicad("/path/to/your/project.kicad_pcb")

if success:
    # 获取板子状态
    status = manager.get_board_status()
    print(f"项目数: {status['item_count']}")

    # 创建封装
    result = manager.create_footprint(
        footprint_name="R_0603_1608Metric",
        position=(50, 50),
        layer="F.Cu"
    )
    print(f"创建结果: {result}")

    # 关闭连接
    manager.cleanup()
```

### cURL 测试

```bash
# 启动 KiCad
curl -X POST http://localhost:8000/api/kicad-ipc/start

# 获取状态
curl http://localhost:8000/api/kicad-ipc/status

# 创建封装
curl -X POST http://localhost:8000/api/kicad-ipc/footprint \
  -H "Content-Type: application/json" \
  -d '{
    "footprint_name": "R_0603_1608Metric",
    "position": {"x": 50, "y": 50},
    "layer": "F.Cu"
  }'

# 停止 KiCad
curl -X POST http://localhost:8000/api/kicad-ipc/stop
```

---

## 已知限制

1. **必须运行 KiCad GUI**：IPC API 要求 pcbnew 实际运行，无法纯后台处理
2. **单实例限制**：目前难以同时连接多个 KiCad 实例
3. **平台差异**：
   - Windows: 使用 Named Pipe
   - Linux/macOS: 使用 Unix Socket
4. **API 稳定性**：KiCad 9 的 IPC API 仍在发展中，部分功能可能变化
5. **性能**：IPC 通信比内存内 API 慢，不适合高频操作

---

## 与旧方案对比

| 特性 | 旧方案 (PyAutoGUI) | 新方案 (IPC API) |
|------|-------------------|-----------------|
| 截图方式 | PyAutoGUI 截图 | KiCad CLI 导出 |
| 控制精度 | 模拟鼠标/键盘 | 直接 API 调用 |
| 稳定性 | 依赖 UI 坐标 | 程序化精确控制 |
| 需要 GUI | 是 | 是（架构要求） |
| 学习曲线 | 简单 | 较复杂 |
| 未来发展 | 有限 | KiCad 官方支持 |

---

## 故障排除

### 问题1: "kicad-python not installed"

**解决**：
```bash
pip install kicad-python
```

### 问题2: "KiCad returned error: no handler available"

**解决**：
1. 确保 KiCad 9.0+ 已安装
2. 在 KiCad 中启用 API Server：`Tools → External Plugin → Start Server`
3. 检查 KiCad 是否正在运行

### 问题3: Windows 上连接失败

**解决**：
```bash
pip install pywin32
```

### 问题4: Docker/无头环境无法启动

**解决**：
```python
config = KiCadConnectionConfig(
    use_virtual_display=True,  # 启用虚拟显示
    virtual_display_size=(1920, 1080)
)
```

---

## 参考资料

- [KiCad IPC API 官方文档](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/)
- [kicad-python PyPI](https://pypi.org/project/kicad-python/)
- [GitHub: kicad-mcp-python](https://github.com/Finerestaurant/kicad-mcp-python) - 参考实现
- [KiCad Forum: IPC API 讨论](https://forum.kicad.info/t/kicad-9-0-python-api-ipc-api/57236)

---

## 下一步开发

1. **实现更多 API 功能**：
   - 布线 (CreateTrack)
   - 过孔 (CreateVia)
   - 铺铜 (CreateZone)
   - DRC 检查

2. **前端可视化**：
   - 使用 KiCad CLI 导出 SVG/PNG 预览
   - 交互式画布（点击选择项目）

3. **AI 集成**：
   - 大模型通过 API 自动设计 PCB
   - 自然语言转 PCB 操作

---

**最后更新**: 2026-02-12
**兼容版本**: KiCad 9.0+
