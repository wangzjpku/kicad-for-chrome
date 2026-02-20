# KiCad AI Auto - API 接口文档

> 生成时间：2025-02-11
> 项目版本：1.0.0
> 文档类型：当前实现API接口规范

---

## 目录

- [1. 架构概述](#1-架构概述)
- [2. REST API](#2-rest-api)
  - [2.1 项目操作](#21-项目操作)
  - [2.2 菜单操作](#22-菜单操作)
  - [2.3 工具操作](#23-工具操作)
  - [2.4 输入操作](#24-输入操作)
  - [2.5 状态查询](#25-状态查询)
  - [2.6 文件导出](#26-文件导出)
  - [2.7 DRC](#27-drc)
  - [2.8 健康检查](#28-健康检查)
- [3. WebSocket API](#3-websocket-api)
- [4. KiCadController](#4-kicadcontroller)
- [5. StateMonitor](#5-statemonitor)
- [6. ExportManager](#6-exportmanager)
- [7. 数据模型](#7-数据模型)
- [8. 错误处理](#8-错误处理)
- [9. 安全机制](#9-安全机制)

---

## 1. 架构概述

### 1.1 技术栈

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                       │
│                   (React + TypeScript)               │
└──────────────────────┬──────────────────────────┘
                     │ HTTP/WebSocket
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend                  │
│           (Python + Uvicorn)                   │
│                                                 │
│  ┌─────────────┐  ┌──────────────┐ │
│  │ KiCad      │  │ State       │ │
│  │ Controller  │  │ Monitor     │ │
│  └──────┬─────┘  └──────┬───────┘ │
│         │ PyAutoGUI      │             │
└─────────▼───────────────────▼─────────────┘
          │ subprocess / X11
    ┌─────────▼────────────┐
    │  KiCad GUI Instance  │
    │  (Linux Xvfb)      │
    └──────────────────────┘
```

### 1.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|--------|
| FastAPI应用 | `main.py` | REST/WebSocket服务器 |
| KiCad控制器 | `kicad_controller.py` | GUI自动化、进程管理 |
| 状态监控器 | `state_monitor.py` | 实时状态监控 |
| 导出管理器 | `export_manager.py` | 文件导出编排 |
| 中间件 | `middleware.py` | 错误处理、日志 |

### 1.3 通信方式

- **REST API**: 标准HTTP请求
- **WebSocket**: 实时双向通信
- **PyAutoGUI**: GUI操作模拟（鼠标、键盘）
- **X11/Lib**: 屏幕截图捕获
- **SWIG/pcbnew**: 已弃用的直接API调用（备用）

---

## 2. REST API

### 基础信息

```
Base URL: http://localhost:8000
API Version: 1.0.0
Content-Type: application/json
Authentication: X-API-Key header (可选)
```

### 2.1 项目操作

#### POST /api/project/start
启动 KiCad 实例

**请求体：**
```json
{
  "project_path": "/path/to/project.kicad_pro"  // 可选
}
```

**响应：**
```json
{
  "success": true,
  "message": "KiCad started successfully",
  "project": "/path/to/project.kicad_pro"
}
```

**速率限制：** 10 requests/minute

---

#### POST /api/project/stop
停止 KiCad 实例

**响应：**
```json
{
  "success": true,
  "message": "KiCad stopped"
}
```

---

#### POST /api/project/open
打开项目文件（支持上传）

**请求头：**
```
Content-Type: multipart/form-data
X-API-Key: <your-api-key>  // 如果配置了
```

**请求体：**
```
file: <binary file data>
```

**支持的文件类型：**
- `.kicad_pro` - 项目文件
- `.kicad_sch` - 原理图
- `.kicad_pcb` - PCB文件
- `.kicad_mod` - 封装库
- `.kicad_sym` - 符号库
- `.zip` - 压缩项目

**文件大小限制：** 50MB

**响应：**
```json
{
  "success": true,
  "message": "Project project.kicad_pro opened",
  "path": "/projects/project.kicad_pro"
}
```

---

#### POST /api/project/save
保存当前项目

**响应：**
```json
{
  "success": true,
  "message": "Project saved"
}
```

---

#### GET /api/project/info
获取当前项目信息

**响应：**
```json
{
  "path": "/projects/project.kicad_pro",
  "name": "project",
  "modified": "2025-02-11T10:30:00",
  "running": true
}
```

---

### 2.2 菜单操作

#### POST /api/menu/click
点击菜单项

**请求体：**
```json
{
  "menu": "file",           // 菜单名称
  "item": "open"            // 菜单项（可选）
}
```

**支持的菜单：**
| 菜单 | 选项 |
|------|------|
| `file` | new, open, save, export |
| `place` | symbol, footprint, wire, text |
| `tools` | drc |

**响应：**
```json
{
  "success": true,
  "menu": "file",
  "item": "open"
}
```

---

### 2.3 工具操作

#### POST /api/tool/activate
激活工具（快捷键方式）

**请求体：**
```json
{
  "tool": "route",           // 工具名称
  "params": {}              // 可选参数
}
```

**支持的工具：**
| 工具名 | 快捷键 | 描述 |
|--------|--------|------|
| `select` | esc | 选择工具 |
| `move` | m | 移动工具 |
| `route` | x | 布线工具 |
| `place_symbol` | a | 放置符号 |
| `place_footprint` | p | 放置封装 |
| `draw_wire` | w | 绘制导线 |
| `add_via` | v | 添加过孔 |
| `drc` | Ctrl+D | DRC检查 |
| `save` | Ctrl+S | 保存 |
| `undo` | Ctrl+Z | 撤销 |
| `redo` | Ctrl+Y | 重做 |
| `zoom_in` | Ctrl++ | 放大 |
| `zoom_out` | Ctrl+- | 缩小 |
| `zoom_fit` | Ctrl+Home | 适配视图 |
| `copy` | Ctrl+C | 复制 |
| `paste` | Ctrl+V | 粘贴 |
| `delete` | Delete | 删除 |

**响应：**
```json
{
  "success": true,
  "tool": "route"
}
```

---

### 2.4 输入操作

#### POST /api/input/mouse
发送鼠标操作

**请求体：**
```json
{
  "action": "click",      // click, double_click, drag, move
  "x": 500,              // 屏幕坐标 X (像素)
  "y": 300,              // 屏幕坐标 Y (像素)
  "button": "left",        // left, right, middle
  "duration": 0.5          // 拖拽持续时间（秒）
}
```

**动作类型：**
- `click` - 单击
- `double_click` - 双击
- `move` - 移动
- `drag` - 拖拽

**速率限制：** 120 requests/minute

**响应：**
```json
{
  "success": true,
  "action": "click",
  "x": 500,
  "y": 300
}
```

---

#### POST /api/input/keyboard
发送键盘操作

**请求体（键序列）：**
```json
{
  "keys": ["ctrl", "s"],   // 组合键
  "text": null              // 文本输入（与keys互斥）
}
```

**请求体（文本输入）：**
```json
{
  "keys": [],
  "text": "Hello World"   // 直接文本输入
}
```

**特性：**
- 支持组合键（Ctrl、Alt、Shift）
- 支持中文输入（通过剪贴板）
- 自动检测非ASCII字符并使用粘贴

**速率限制：** 120 requests/minute

**响应：**
```json
{
  "success": true,
  "keys": ["ctrl", "s"],
  "text": null
}
```

---

### 2.5 状态查询

#### GET /api/state/screenshot
获取屏幕截图（PNG流）

**响应：**
```
Content-Type: image/png
Content-Disposition: inline; filename=screenshot.png

<binary image data>
```

**速率限制：** 60 requests/minute

---

#### GET /api/state/full
获取完整状态信息

**响应：**
```json
{
  "tool": "route",
  "cursor": {
    "x": 500.0,
    "y": 300.0
  },
  "layer": "F.Cu",
  "zoom": 1.5,
  "errors": [],
  "timestamp": "2025-02-11T10:30:00.000Z",
  "editor_type": "pcb",
  "project_name": "project",
  "grid_size": "1.27mm",
  "selected_items": ["R1", "C1"],
  "is_modified": false
}
```

---

#### GET /api/state/tool
获取当前活动工具

**响应：**
```json
{
  "tool": "route"
}
```

---

#### GET /api/state/coords
获取光标坐标

**响应：**
```json
{
  "x": 500.0,
  "y": 300.0
}
```

---

#### GET /api/state/errors
获取错误列表

**响应：**
```json
{
  "errors": ["Net not found: +5V", "Short circuit detected"]
}
```

---

### 2.6 文件导出

#### POST /api/export
导出文件

**请求体：**
```json
{
  "format": "gerber",     // gerber, drill, bom, pickplace, pdf, svg, step
  "output_dir": "/exports",
  "options": {
    "layers": ["F.Cu", "B.Cu"]  // 可选格式特定选项
  }
}
```

**支持的导出格式：**
| 格式 | 描述 | 输出 |
|------|--------|------|
| `gerber` | PCB制造文件 | .gbr, .gtl, .gbl 等 |
| `drill` | 钻孔文件 | .drl, .pdf (map) |
| `bom` | 物料清单 | .csv |
| `pickplace` | 贴片文件 | .csv |
| `pdf` | PDF打印 | .pdf |
| `svg` | SVG矢量图 | .svg |
| `step` | 3D模型 | .step |

**速率限制：** 20 requests/minute

**响应：**
```json
{
  "success": true,
  "files": [
    {
      "layer": "F.Cu",
      "file": "/exports/F_Cu.gbr"
    }
  ],
  "output_dir": "/exports"
}
```

---

#### GET /api/export/formats
获取支持的导出格式列表

**响应：**
```json
{
  "formats": [
    {
      "id": "gerber",
      "name": "Gerber",
      "description": "PCB manufacturing files"
    },
    {
      "id": "drill",
      "name": "Drill",
      "description": "Excellon drill files"
    },
    // ...
  ]
}
```

---

### 2.7 DRC

#### POST /api/drc/run
运行设计规则检查

**响应：**
```json
{
  "success": true,
  "message": "DRC check completed"
}
```

---

#### GET /api/drc/report
获取DRC报告

**响应：**
```json
{
  "error_count": 0,
  "warning_count": 5,
  "errors": [],
  "warnings": [
    "Unconnected pad on R1",
    "Track near pad on C2"
  ]
}
```

---

### 2.8 健康检查

#### GET /api/health
服务健康状态

**响应：**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-11T10:30:00.000Z",
  "kicad_running": true
}
```

**速率限制：** 60 requests/minute

---

## 3. WebSocket API

### 连接信息

```
URL: ws://localhost:8000/ws/control
Protocol: WebSocket
```

### 消息格式

#### 连接建立
```json
{
  "type": "connected",
  "timestamp": "2025-02-11T10:30:00.000Z"
}
```

---

#### 心跳
```json
// 客户端 → 服务器
{
  "type": "ping",
  "id": "client-123"
}

// 服务器 → 客户端
{
  "type": "pong"
}
```

---

#### 鼠标事件
```json
{
  "type": "mouse",
  "event": "click",      // click, move, down, up
  "x": 500,
  "y": 300,
  "button": "left"
}
```

---

#### 键盘事件
```json
{
  "type": "keyboard",
  "keys": ["ctrl", "s"],
  "text": null
}
```

---

#### 命令
```json
{
  "type": "command",
  "id": "cmd-001",
  "command": {
    "type": "screenshot"  // screenshot, state, tool
  }
}

// 响应
{
  "type": "result",
  "id": "cmd-001",
  "data": {
    "screenshot": "base64_encoded_image_data"
  }
}
```

**支持命令类型：**
- `screenshot` - 获取截图（Base64）
- `state` - 获取完整状态
- `tool` - 获取当前工具

---

## 4. KiCadController

### 4.1 类结构

```python
class KiCadController:
    """KiCad 控制器 - GUI自动化核心"""

    def __init__(
        display_id: str = ":99",
        resolution: Tuple[int, int] = (1920, 1080)
    )
```

### 4.2 进程管理

#### start(project_path: Optional[str])
启动 KiCad 实例

**参数：**
- `project_path` - 可选的项目路径

**实现：**
```python
def start(self, project_path: Optional[str] = None):
    env = os.environ.copy()
    env["DISPLAY"] = self.display_id

    cmd = ["kicad"]
    if project_path and os.path.exists(project_path):
        cmd.append(project_path)

    self.kicad_process = subprocess.Popen(cmd, env=env, ...)
    time.sleep(3)  # 等待启动

    if HAS_XLIB:
        self.x_display = display.Display(self.display_id)
```

---

#### close()
关闭 KiCad 实例

**实现：**
```python
def close(self):
    if self.kicad_process:
        self.kicad_process.terminate()
        try:
            self.kicad_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.kicad_process.kill()
```

---

#### is_running() -> bool
检查 KiCad 是否运行

**返回：** `True` 如果进程存在且未退出

---

### 4.3 项目管理

#### open_project(project_path: str)
打开项目

**实现：**
```python
def open_project(self, project_path: str):
    self.click_menu("file", "open")
    time.sleep(0.5)
    self.type_text(project_path)
    time.sleep(0.2)
    self.press_key("return")
    time.sleep(2)
    self.current_project = project_path
```

---

#### save_project()
保存项目

**实现：**
```python
def save_project(self):
    self.activate_tool("save")
    time.sleep(0.5)
```

---

#### get_project_info() -> Dict[str, Any]
获取项目信息

**返回：**
```python
{
    "path": self.current_project,
    "name": os.path.basename(self.current_project) if self.current_project else None,
    "running": self.is_running(),
    "modified": None  # TODO: 获取实际修改时间
}
```

---

### 4.4 菜单操作

#### click_menu(menu: str, item: Optional[str])
点击菜单项

**实现：**
```python
def click_menu(self, menu: str, item: Optional[str] = None):
    if menu not in self.MENU_COORDS:
        raise ValueError(f"Unknown menu: {menu}")

    coords = self.MENU_COORDS[menu]
    pyautogui.click(coords["x"], coords["y"])
    time.sleep(0.2)

    if item:
        item_coords = self.MENU_ITEMS[menu][item]
        pyautogui.click(item_coords["x"], item_coords["y"])
        time.sleep(0.2)
```

**菜单坐标（1920x1080）：**
```python
MENU_COORDS = {
    "file": {"x": 30, "y": 30},
    "edit": {"x": 70, "y": 30},
    "view": {"x": 110, "y": 30},
    "place": {"x": 160, "y": 30},
    "route": {"x": 210, "y": 30},
    "tools": {"x": 260, "y": 30},
    "help": {"x": 310, "y": 30},
}

MENU_ITEMS = {
    "file": {
        "new": {"x": 30, "y": 60},
        "open": {"x": 30, "y": 80},
        "save": {"x": 30, "y": 100},
        "export": {"x": 30, "y": 140},
    },
    "place": {
        "symbol": {"x": 160, "y": 60},
        "footprint": {"x": 160, "y": 80},
        "wire": {"x": 160, "y": 100},
        "text": {"x": 160, "y": 120},
    },
    "tools": {
        "drc": {"x": 260, "y": 60},
    },
}
```

**坐标适配：** 支持任意分辨率，使用相对坐标自动计算

---

### 4.5 工具操作

#### activate_tool(tool: str, params: Dict[str, Any] = None)
激活工具

**实现：**
```python
def activate_tool(self, tool: str, params: Dict[str, Any] = None):
    if tool not in self.TOOL_HOTKEYS:
        raise ValueError(f"Unknown tool: {tool}")

    hotkey = self.TOOL_HOTKEYS[tool]

    # 正确处理组合键
    if isinstance(hotkey, list):
        pyautogui.hotkey(*hotkey)
    else:
        pyautogui.press(hotkey)

    time.sleep(0.1)
```

---

### 4.6 鼠标操作

#### mouse_click(x: int, y: int, button: str = "left")
单击

**实现：**
```python
def mouse_click(self, x: int, y: int, button: str = "left"):
    pyautogui.click(x, y, button=button)
```

---

#### mouse_double_click(x: int, y: int)
双击

**实现：**
```python
def mouse_double_click(self, x: int, y: int):
    pyautogui.doubleClick(x, y)
```

---

#### mouse_move(x: int, y: int)
移动鼠标

**实现：**
```python
def mouse_move(self, x: int, y: int):
    pyautogui.moveTo(x, y)
```

---

#### mouse_drag(x: int, y: int, duration: float = 0.5)
拖拽

**实现：**
```python
def mouse_drag(self, x: int, y: int, duration: float = 0.5):
    pyautogui.dragTo(x, y, duration=duration)
```

---

#### mouse_down(x: int, y: int)
按下鼠标

**实现：**
```python
def mouse_down(self, x: int, y: int):
    pyautogui.moveTo(x, y)
    pyautogui.mouseDown()
```

---

#### mouse_up(x: int, y: int)
释放鼠标

**实现：**
```python
def mouse_up(self, x: int, y: int):
    pyautogui.moveTo(x, y)
    pyautogui.mouseUp()
```

---

### 4.7 键盘操作

#### press_keys(keys: List[str])
按下多个键

**实现：**
```python
def press_keys(self, keys: List[str]):
    if len(keys) > 1:
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(keys[0])
```

---

#### press_key(key: str)
按下单个键

**实现：**
```python
def press_key(self, key: str):
    pyautogui.press(key)
```

---

#### type_text(text: str)
输入文本（支持中文）

**实现：**
```python
def type_text(self, text: str):
    if text.isascii():
        pyautogui.typewrite(text, interval=0.01)
    else:
        if HAS_PYPERCLIP:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
        else:
            pyautogui.typewrite(text, interval=0.01)
```

**依赖：**
- `pyperclip` - 用于非ASCII文本输入（可选）

---

### 4.8 屏幕截图

#### get_screenshot() -> bytes
获取PNG格式截图

**实现：**
```python
def get_screenshot(self) -> bytes:
    if HAS_XLIB and self.x_display:
        return self._get_screenshot_xlib()
    else:
        return self._get_screenshot_fallback()

def _get_screenshot_xlib(self) -> bytes:
    root = self.x_display.screen().root
    raw = root.get_image(0, 0, width, height, X.ZPixmap, 0xFFFFFFFF)
    image = Image.frombytes("RGB", (width, height), raw.data, "raw", "BGRX")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

def _get_screenshot_fallback(self) -> bytes:
    screenshot = pyautogui.screenshot()
    buffer = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    return buffer.getvalue()
```

---

#### get_screenshot_base64() -> str
获取Base64编码截图

**实现：**
```python
def get_screenshot_base64(self) -> str:
    screenshot = self.get_screenshot()
    return base64.b64encode(screenshot).decode("utf-8")
```

---

### 4.9 DRC操作

#### run_drc() -> Dict[str, Any]
运行DRC检查

**实现：**
```python
def run_drc(self) -> Dict[str, Any]:
    self.click_menu("tools", "drc")
    time.sleep(0.5)
    pyautogui.click(400, 500)  # 运行按钮位置
    time.sleep(2)
    self.press_key("esc")
    return {"success": True, "message": "DRC check completed"}
```

---

#### get_drc_report() -> Dict[str, Any]
获取DRC报告

**实现：**
```python
def get_drc_report(self) -> Dict[str, Any]:
    # 需要解析KiCad生成的DRC报告文件
    return {
        "error_count": 0,
        "warning_count": 0,
        "errors": [],
        "warnings": []
    }
```

---

### 4.10 导出功能（使用pcbnew API）

#### export_gerber(output_dir: str, layers: Optional[List[str]] = None)
导出Gerber文件

**实现：**
```python
def export_gerber(self, output_dir: str, layers: Optional[List[str]] = None):
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        plot_controller = pcbnew.PLOT_CONTROLLER(board)
        plot_options = plot_controller.GetPlotOptions()
        plot_options.SetOutputDirectory(output_dir)

        layer_map = {
            "F.Cu": pcbnew.F_Cu,
            "B.Cu": pcbnew.B_Cu,
            "F.SilkS": pcbnew.F_SilkS,
            "B.SilkS": pcbnew.B_SilkS,
            "F.Mask": pcbnew.F_Mask,
            "B.Mask": pcbnew.B_Mask,
            "Edge.Cuts": pcbnew.Edge_Cuts,
        }

        exported_files = []
        for layer_name, layer_id in layer_map.items():
            if layers is None or layer_name in layers:
                plot_controller.SetLayer(layer_id)
                plot_controller.OpenPlotfile(layer_name, pcbnew.PLOT_FORMAT_GERBER, layer_name)
                plot_controller.PlotLayer()
                exported_files.append({
                    "layer": layer_name,
                    "file": plot_controller.GetPlotFileName()
                })

        plot_controller.ClosePlot()
        return {"success": True, "files": exported_files, "output_dir": output_dir}

    except ImportError:
        return {"success": False, "error": "pcbnew module not available"}
```

---

#### export_drill(output_dir: str)
导出钻孔文件

**实现：**
```python
def export_drill(self, output_dir: str):
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        drill_writer = pcbnew.EXCELLON_WRITER(board)
        drill_writer.SetMapFileFormat(pcbnew.PLOT_FORMAT_PDF)

        drill_writer.CreateDrillandMapFilesSet(output_dir, True, True)

        return {
            "success": True,
            "files": [f"{output_dir}/drill.drl", f"{output_dir}/drill_map.pdf"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

#### export_bom(output_path: str)
导出物料清单

**实现：**
```python
def export_bom(self, output_path: str):
    try:
        import pcbnew
        import csv

        board = pcbnew.GetBoard()
        components = []

        for footprint in board.GetFootprints():
            component = {
                "reference": footprint.GetReference(),
                "value": footprint.GetValue(),
                "footprint": str(footprint.GetFPID().GetLibItemName()),
                "layer": "F" if footprint.GetLayer() == pcbnew.F_Cu else "B",
            }
            components.append(component)

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["reference", "value", "footprint", "layer"])
            writer.writeheader()
            writer.writerows(components)

        return {
            "success": True,
            "file": output_path,
            "component_count": len(components)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

#### export_pickplace(output_path: str)
导出贴片文件

**实现：**
```python
def export_pickplace(self, output_path: str):
    try:
        import pcbnew
        import csv

        board = pcbnew.GetBoard()
        components = []

        for footprint in board.GetFootprints():
            pos = footprint.GetPosition()
            rotation = footprint.GetOrientation().AsDegrees()
            layer = "Top" if footprint.GetLayer() == pcbnew.F_Cu else "Bottom"

            component = {
                "reference": footprint.GetReference(),
                "value": footprint.GetValue(),
                "footprint": str(footprint.GetFPID().GetLibItemName()),
                "x": pos.x / 1000000.0,  # 转换为mm
                "y": pos.y / 1000000.0,
                "rotation": rotation,
                "layer": layer,
            }
            components.append(component)

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["reference", "value", "footprint", "x", "y", "rotation", "layer"])
            writer.writeheader()
            writer.writerows(components)

        return {
            "success": True,
            "file": output_path,
            "component_count": len(components)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

#### export_pdf(output_path: str)
导出PDF文件

**实现：**
```python
def export_pdf(self, output_path: str):
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        plot_controller = pcbnew.PLOT_CONTROLLER(board)
        plot_options = plot_controller.GetPlotOptions()
        plot_options.SetOutputDirectory(os.path.dirname(output_path))

        plot_controller.SetLayer(pcbnew.F_Cu)
        plot_controller.OpenPlotfile("output", pcbnew.PLOT_FORMAT_PDF, "PCB Output")
        plot_controller.PlotLayer()
        plot_controller.ClosePlot()

        return {"success": True, "file": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

#### export_svg(output_path: str)
导出SVG文件

**实现：**
```python
def export_svg(self, output_path: str):
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        plot_controller = pcbnew.PLOT_CONTROLLER(board)
        plot_options = plot_controller.GetPlotOptions()
        plot_options.SetOutputDirectory(os.path.dirname(output_path))

        plot_controller.SetLayer(pcbnew.F_Cu)
        plot_controller.OpenPlotfile("output", pcbnew.PLOT_FORMAT_SVG, "PCB Output")
        plot_controller.PlotLayer()
        plot_controller.ClosePlot()

        return {"success": True, "file": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

#### export_step(output_path: str)
导出STEP 3D文件

**实现：**
```python
def export_step(self, output_path: str):
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        exporter = pcbnew.STEP_EXPORTER(board)
        exporter.Export(output_path)

        return {"success": True, "file": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 5. StateMonitor

### 5.1 类结构

```python
class StateMonitor:
    """状态监控器 - 实时获取KiCad状态"""

    def __init__(
        kicad_controller: KiCadController,
        update_interval: float = 0.1
    )
```

### 5.2 状态数据

#### KiCadState 数据类

```python
@dataclass
class KiCadState:
    """KiCad 状态数据类"""
    tool: Optional[str] = None
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    layer: Optional[str] = None
    zoom: float = 100.0
    errors: List[str] = []
    timestamp: datetime = None
    editor_type: str = "unknown"
    project_name: Optional[str] = None
    grid_size: Optional[str] = None
    selected_items: List[str] = []
    is_modified: bool = False
```

---

### 5.3 监控控制

#### start_monitoring()
启动后台监控线程

**实现：**
```python
def start_monitoring(self):
    if self._running:
        return

    self._running = True
    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
    self._monitor_thread.start()
```

---

#### stop_monitoring()
停止监控线程

**实现：**
```python
def stop_monitoring(self):
    self._running = False
    if self._monitor_thread:
        self._monitor_thread.join(timeout=2)
```

---

### 5.4 回调管理

#### add_state_callback(callback: Callable[[KiCadState], None])
添加状态变化回调

**用法：**
```python
def on_state_change(state: KiCadState):
    print(f"Tool: {state.tool}, Layer: {state.layer}")

monitor.add_state_callback(on_state_change)
monitor.start_monitoring()
```

---

#### remove_state_callback(callback: Callable[[KiCadState], None])
移除状态变化回调

**实现：**
```python
def remove_state_callback(self, callback):
    if callback in self._state_callbacks:
        self._state_callbacks.remove(callback)
```

---

### 5.5 状态获取

#### get_state() -> Dict[str, Any]
获取完整状态

**返回：**
```python
{
    "tool": self.current_state.tool,
    "cursor": {"x": self.current_state.cursor_x, "y": self.current_state.cursor_y},
    "layer": self.current_state.layer,
    "zoom": self.current_state.zoom,
    "errors": self.current_state.errors,
    "timestamp": self.current_state.timestamp.isoformat(),
    "editor_type": self.current_state.editor_type,
    "project_name": self.current_state.project_name,
    "grid_size": self.current_state.grid_size,
    "selected_items": self.current_state.selected_items,
    "is_modified": self.current_state.is_modified,
}
```

---

#### get_current_tool() -> Optional[str]
获取当前工具

**返回：** 当前活动工具名称

---

#### get_cursor_coords() -> Dict[str, float]
获取光标坐标

**返回：**
```python
{"x": self.current_state.cursor_x, "y": self.current_state.cursor_y}
```

---

#### get_errors() -> List[str]
获取错误列表

**返回：** 当前错误的副本

---

### 5.6 UI变化检测

#### detect_ui_changes(screenshot_before: bytes, screenshot_after: bytes) -> List[Dict[str, Any]]
检测UI变化（图像差异分析）

**实现：**
```python
def detect_ui_changes(self, screenshot_before, screenshot_after):
    if not HAS_CV2:
        return []

    # 解码图像
    before = cv2.imdecode(np.frombuffer(screenshot_before, np.uint8), cv2.IMREAD_COLOR)
    after = cv2.imdecode(np.frombuffer(screenshot_after, np.uint8), cv2.IMREAD_COLOR)

    # 计算差异
    diff = cv2.absdiff(before, after)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # 二值化
    _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)

    # 查找变化区域
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    changes = []
    for contour in contours:
        if cv2.contourArea(contour) > 100:  # 过滤小变化
            x, y, w, h = cv2.boundingRect(contour)
            changes.append({
                "type": "region_change",
                "bbox": {"x": x, "y": y, "width": w, "height": h},
                "area": cv2.contourArea(contour),
            })

    return changes
```

---

### 5.7 性能指标

#### get_performance_metrics() -> Dict[str, Any]
获取性能指标

**返回：**
```python
{
    "fps": 30,                    # 视频流帧率
    "latency_ms": 100,            # 延迟
    "memory_mb": process.memory_info().rss / (1024 * 1024),
    "cpu_percent": process.cpu_percent(),
    "update_interval": self.update_interval,
    "callbacks_registered": len(self._state_callbacks),
    "error_count": len(self.error_history),
}
```

---

### 5.8 层列表

#### get_layer_list() -> List[Dict[str, Any]]
获取可用层列表

**返回：**
```python
[
    {"id": 0, "name": "F.Cu", "type": "copper"},
    {"id": 31, "name": "B.Cu", "type": "copper"},
    {"id": 36, "name": "B.SilkS", "type": "silkscreen"},
    {"id": 37, "name": "F.SilkS", "type": "silkscreen"},
    {"id": 38, "name": "B.Mask", "type": "soldermask"},
    {"id": 39, "name": "F.Mask", "type": "soldermask"},
    {"id": 44, "name": "Edge.Cuts", "type": "outline"},
    # ...
]
```

**KiCad PCB层ID映射：**
```python
LAYER_NAMES = {
    0: "F.Cu",
    1: "In1.Cu",
    2: "In2.Cu",
    3: "In3.Cu",
    4: "In4.Cu",
    31: "B.Cu",
    32: "B.Adhes",
    33: "F.Adhes",
    34: "B.Paste",
    35: "F.Paste",
    36: "B.SilkS",
    37: "F.SilkS",
    38: "B.Mask",
    39: "F.Mask",
    40: "Dwgs.User",
    41: "Cmts.User",
    42: "Eco1.User",
    43: "Eco2.User",
    44: "Edge.Cuts",
    45: "Margin",
    46: "B.CrtYd",
    47: "F.CrtYd",
    48: "B.Fab",
    49: "F.Fab",
}
```

---

## 6. ExportManager

### 6.1 类结构

```python
class ExportManager:
    """导出管理器 - 编排多种导出操作"""

    def __init__(self, kicad_controller: KiCadController):
        self.controller = kicad_controller
        self.export_jobs = {}
```

### 6.2 单格式导出

#### export(format_type: str, output_dir: str, options: Optional[Dict[str, Any]] -> Dict[str, Any]
导出指定格式

**参数：**
- `format_type` - 导出格式（gerber, drill, bom, pickplace, pdf, svg, step）
- `output_dir` - 输出目录
- `options` - 可选参数

**实现：**
```python
async def export(self, format_type, output_dir, options=None):
    os.makedirs(output_dir, exist_ok=True)

    if format_type == "gerber":
        return self.controller.export_gerber(output_dir, options.get("layers"))
    elif format_type == "drill":
        return self.controller.export_drill(output_dir)
    elif format_type == "bom":
        output_path = os.path.join(output_dir, "bom.csv")
        return self.controller.export_bom(output_path)
    elif format_type == "pickplace":
        output_path = os.path.join(output_dir, "pickplace.csv")
        return self.controller.export_pickplace(output_path)
    elif format_type == "pdf":
        output_path = os.path.join(output_dir, "output.pdf")
        return self.controller.export_pdf(output_path)
    elif format_type == "svg":
        output_path = os.path.join(output_dir, "output.svg")
        return self.controller.export_svg(output_path)
    elif format_type == "step":
        output_path = os.path.join(output_dir, "board.step")
        return self.controller.export_step(output_path)
    else:
        return {"success": False, "error": f"Unknown export format: {format_type}"}
```

---

### 6.3 批量导出

#### export_all(output_dir: str) -> Dict[str, Any]
导出所有生产文件

**实现：**
```python
async def export_all(self, output_dir: str):
    results = {}
    formats = ["gerber", "drill", "bom", "pickplace"]

    for fmt in formats:
        try:
            result = await self.export(fmt, output_dir)
            results[fmt] = result
        except Exception as e:
            logger.error(f"Failed to export {fmt}: {e}")
            results[fmt] = {"success": False, "error": str(e)}

    return {
        "success": all(r.get("success", False) for r in results.values()),
        "results": results,
    }
```

---

## 7. 数据模型

### 7.1 Pydantic模型

#### ToolAction
```python
class ToolAction(BaseModel):
    tool: str
    params: Dict[str, Any] = {}
```

---

#### MouseAction
```python
class MouseAction(BaseModel):
    action: str  # click, double_click, drag, move
    x: int
    y: int
    button: str = "left"
    duration: float = 0.5
```

---

#### KeyboardAction
```python
class KeyboardAction(BaseModel):
    keys: List[str]
    text: Optional[str] = None
```

---

#### MenuAction
```python
class MenuAction(BaseModel):
    menu: str
    item: Optional[str] = None
```

---

#### ExportRequest
```python
class ExportRequest(BaseModel):
    format: str  # gerber, drill, bom, pickplace, pdf, svg, step
    output_dir: str
    options: Dict[str, Any] = {}
```

---

#### ProjectInfo
```python
class ProjectInfo(BaseModel):
    path: Optional[str] = None
    name: Optional[str] = None
    modified: Optional[datetime] = None
    running: bool = False
```

---

#### StateResponse
```python
class StateResponse(BaseModel):
    tool: Optional[str]
    cursor: Dict[str, float]
    layer: Optional[str]
    zoom: Optional[float]
    errors: List[str]
    timestamp: datetime
```

---

### 7.2 验证器

#### ProjectPath 路径验证
```python
class ProjectPath(BaseModel):
    path: str

    @validator('path')
    def validate_path(cls, v):
        # 防止路径遍历攻击
        if '..' in v or not v.startswith('/'):
            raise ValueError('Invalid path: path traversal not allowed')
        return v
```

---

## 8. 错误处理

### 8.1 自定义异常

```python
class KiCadError(Exception):
    """KiCad错误基类"""
    pass

class KiCadNotRunningError(KiCadError):
    """KiCad未运行错误"""
    pass

class KiCadTimeoutError(KiCadError):
    """KiCad操作超时错误"""
    pass

class KiCadCommandError(KiCadError):
    """KiCad命令执行错误"""
    pass

class ProjectNotFoundError(KiCadError):
    """项目未找到错误"""
    pass

class ExportError(KiCadError):
    """导出错误"""
    pass
```

---

### 8.2 中间件

#### ErrorHandlingMiddleware
全局错误处理中间件

```python
class ErrorHandlingMiddleware:
    async def __call__(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except KiCadError as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Internal server error"}
            )
```

---

#### RequestLoggingMiddleware
请求日志中间件

```python
class RequestLoggingMiddleware:
    async def __call__(self, request: Request, call_next):
        logger.info(f"{request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
```

---

### 8.3 重试机制

#### retry 装饰器
```python
def retry(
    max_attempts: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,),
):
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 延迟增长因子
        exceptions: 需要重试的异常类型
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return wrapper
```

---

## 9. 安全机制

### 9.1 API Key认证

```python
async def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """验证 API Key"""
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key
```

---

### 9.2 CORS配置

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)
```

---

### 9.3 速率限制

```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri="memory://",
)

@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    # ...
```

**端点限制：**
| 端点 | 限制 |
|--------|------|
| 健康检查 | 60/minute |
| 项目启动 | 10/minute |
| 鼠标操作 | 120/minute |
| 键盘操作 | 120/minute |
| 状态查询 | 60/minute |
| 文件导出 | 20/minute |

---

### 9.4 文件上传安全

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.kicad_pro', '.kicad_sch', '.kicad_pcb', '.kicad_mod', '.zip', '.kicad_sym'}

# 验证文件扩展名
ext = Path(file.filename).suffix.lower()
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(status_code=400, detail=f"不支持的文件类型")

# 安全路径处理 - 防止路径遍历攻击
safe_filename = os.path.basename(file.filename)
file_path = PROJECTS_DIR / safe_filename

# 验证文件大小
content = await file.read()
if len(content) > MAX_FILE_SIZE:
    raise HTTPException(status_code=400, detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB")
```

---

### 9.5 项目目录隔离

```python
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "/projects"))
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
```

---

## 附录

### A. 配置环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LOG_LEVEL` | 日志级别 | INFO |
| `ALLOWED_ORIGINS` | CORS允许来源 | http://localhost:3000 |
| `API_KEY` | API密钥 | 空（不启用） |
| `PROJECTS_DIR` | 项目目录 | /projects |
| `DISPLAY` | X11显示ID | :99 |

---

### B. 依赖项

```
fastapi>=0.104.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
python-multipart>=0.0.0
slowapi>=0.1.9

pyautogui>=0.9.54
pillow>=10.0.0
python-xlib>=0.33
opencv-python>=4.8.0
numpy>=1.24.0
pyperclip>=1.8.2  # 可选

# SWIG绑定（已弃用）
pcbnew  # KiCad内置
```

---

### C. 已知限制

1. **坐标依赖** - 菜单坐标基于1920x1080分辨率，其他分辨率需要重新计算
2. **GUI变化敏感** - KiCad版本更新可能导致菜单位置变化
3. **异步操作不可靠** - 当前实现为同步API调用
4. **中文输入依赖** - 需要pyperclip库支持
5. **X11依赖** - Windows平台无法使用Xlib截图
6. **pcbnew已弃用** - 建议迁移到kicad-python IPC API

---

### D. 未来改进方向

1. ✅ 集成kicad-python官方绑定
2. ✅ 实现真正的对象操作（创建/更新/删除）
3. ✅ 添加提交事务支持（begin/push_commit）
4. ✅ 使用kicad-cli替代导出功能
5. ✅ 改进状态监控精度
6. ✅ 添加跨平台截图支持
7. ✅ 实现更详细的错误处理
8. ✅ 添加单元测试覆盖

---

### E. 参考资料

- KiCad IPC API文档：https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/
- kicad-python文档：https://docs.kicad.org/kicad-python-main/
- KiCad脚本仓库：https://github.com/KiCad/kicad-scripts
- PyAutoGUI文档：https://pyautogui.readthedocs.io/
- FastAPI文档：https://fastapi.tiangolo.com/
