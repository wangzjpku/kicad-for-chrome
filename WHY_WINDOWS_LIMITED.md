# Windows 本地环境无法显示 KiCad 画面的原因

## 🔍 根本原因分析

### 1. 架构设计差异

这套系统是为 **Docker/Linux 环境**设计的，Windows 本地运行会有架构不匹配问题。

#### Docker/Linux 架构（设计目标）
```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Container                        │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │  KiCad GUI   │──────│  X11 Virtual │──────│  Backend │  │
│  │  (X11 Display)│      │  Display (:99)│      │  (Python)│  │
│  └──────────────┘      └──────────────┘      └────┬─────┘  │
└───────────────────────────────────────────────────┼─────────┘
                                                    │
                                               screenshot
                                                    │
                                               WebSocket
                                                    │
                                              ┌─────┴─────┐
                                              │  Browser  │
                                              │ (Web UI)  │
                                              └───────────┘
```

**工作原理**：
- KiCad 运行在 **X11 虚拟显示**中（不是真实显示器）
- 后端通过 **Xlib** 直接读取虚拟显示的像素数据
- 截图是**程序化**的，不需要真实显示器

#### Windows 本地架构（当前情况）
```
┌──────────────┐           ┌──────────────┐           ┌──────────┐
│  KiCad GUI   │           │   Backend    │           │  Browser │
│  (Windows    │  ───X───  │   (Python)   │  ───────  │ (Web UI) │
│   Window)    │  无连接   │              │  WebSocket │         │
└──────────────┘           └──────┬───────┘           └──────────┘
                                  │
                          PyAutoGUI 截图
                                  │
                          只能截整个屏幕
                                  │
                          无法定位 KiCad 窗口
```

**问题所在**：
- KiCad 是**独立的 Windows 窗口**，与后端没有关联
- 后端使用 **PyAutoGUI** 截图，只能截取**整个屏幕**
- 无法精确捕获 KiCad 窗口的内容

---

## 🔧 技术细节

### 截图代码分析

在 `kicad_controller.py` 中，截图逻辑如下：

```python
def get_screenshot(self) -> bytes:
    """获取屏幕截图（PNG 格式）"""
    if HAS_XLIB and self.x_display:
        # Linux/Docker 环境 - 使用 Xlib 截图 ✅
        return self._get_screenshot_xlib()
    else:
        # Windows 环境 - 使用 PyAutoGUI 截图 ❌
        return self._get_screenshot_fallback()

def _get_screenshot_xlib(self) -> bytes:
    """使用 Xlib 截图 - 只能在 Linux/X11 环境工作"""
    root = self.x_display.screen().root
    raw = root.get_image(0, 0, self.resolution[0], self.resolution[1], ...)
    # 直接读取 X11 显示的像素数据
    
def _get_screenshot_fallback(self) -> bytes:
    """备用截图方法 - PyAutoGUI"""
    screenshot = pyautogui.screenshot()  # 截取整个屏幕！
    # 问题：截到了整个屏幕，不只是 KiCad 窗口
```

### Windows 本地的问题

| 问题 | 说明 |
|------|------|
| **没有 X11** | Windows 没有 X11 虚拟显示，只有真实显示器 |
| **PyAutoGUI 局限** | 只能截取整个屏幕，无法精确定位 KiCad 窗口 |
| **窗口分离** | KiCad 是独立进程，后端不知道 KiCad 窗口的位置和句柄 |
| **截图内容** | 可能截到的是桌面、其他窗口，或者黑屏（如果 KiCad 被最小化） |

---

## 🎯 为什么显示"等待连接..."

### 前端逻辑

前端 `CanvasContainer.tsx` 中的显示逻辑：

```typescript
{screenshotUrl ? (
    // 如果有截图数据，显示 KiCad 画面
    <img src={screenshotUrl} alt="KiCad Canvas" />
) : (
    // 如果没有截图数据，显示"等待连接..."
    <div>
        <div>🔌</div>
        <div>等待连接...</div>
    </div>
)}
```

### 数据传输流程

1. **前端请求截图**：`sendCommand({ type: 'screenshot' })`
2. **后端尝试截图**：调用 `get_screenshot_base64()`
3. **后端发送数据**：通过 WebSocket 发送截图数据
4. **前端接收数据**：更新 `screenshotUrl` 状态

### Windows 本地的问题

```
前端 ──请求截图──> 后端 ──PyAutoGUI 截图──> 整个屏幕（不是 KiCad）
                                                    │
前端 <──发送数据── 后端 <──截图完成（无效数据）─────┘
    │
    └── 截图数据可能是：
        - 桌面背景（没有 KiCad）
        - 其他应用程序窗口
        - 黑屏（KiCad 被遮挡或最小化）
        - 空数据（截图失败）
```

**结果**：
- 如果截图数据无效或为空，前端无法正确显示
- 可能显示黑屏、花屏，或者保持"等待连接..."
- WebSocket 连接是成功的，但截图数据不正确

---

## ✅ 为什么 WebSocket 显示"已连接"

WebSocket 连接和截图是两个独立的功能：

| 功能 | 状态 | 说明 |
|------|------|------|
| **WebSocket 连接** | ✅ 正常 | 前后端通信通道已建立 |
| **命令传输** | ✅ 正常 | 可以发送鼠标/键盘命令 |
| **截图功能** | ❌ 异常 | Windows 本地无法正确截图 |

---

## 🐳 Docker 为什么可以工作

Docker 环境使用 **X11 虚拟显示**：

```dockerfile
# docker-compose.yml
environment:
  - DISPLAY=:99  # 虚拟显示 :99
```

**优势**：
1. **虚拟显示**：KiCad 运行在虚拟的 X11 显示 :99，不依赖真实显示器
2. **程序化截图**：后端可以直接读取虚拟显示的像素数据
3. **一致性**：无论宿主机是什么系统，容器内都是 Linux 环境

```
Docker 容器内部：
┌────────────────────────────────────────┐
│  Xvfb (虚拟显示服务器)                  │
│  ┌────────────────────────────────┐   │
│  │       虚拟屏幕 :99              │   │
│  │  ┌──────────┐ ┌──────────┐   │   │
│  │  │  KiCad   │ │  KiCad   │   │   │
│  │  │Schematic │ │   PCB    │   │   │
│  │  └──────────┘ └──────────┘   │   │
│  └────────────────────────────────┘   │
│           ↑                           │
│      Xlib 截图（读取像素）              │
│           ↓                           │
│     Python 后端                        │
└────────────────────────────────────────┘
```

---

## 💡 解决方案

### 方案 1：使用 Docker（推荐）

这是最简单可靠的方案，架构与设计目标一致。

```bash
docker-compose up -d
```

### 方案 2：修改代码支持 Windows 窗口截图

需要修改 `kicad_controller.py`，添加 Windows 窗口捕获功能：

```python
import win32gui
import win32ui
import win32con

def _get_screenshot_windows(self) -> bytes:
    """Windows 窗口截图"""
    # 1. 找到 KiCad 窗口句柄
    hwnd = win32gui.FindWindow(None, "KiCad")
    
    # 2. 获取窗口位置和大小
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    
    # 3. 创建设备上下文
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    
    # 4. 创建位图
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)
    
    # 5. 截图
    saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
    
    # 6. 转换为 PNG
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    
    # 清理资源
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    
    return bmpstr
```

**缺点**：
- 需要安装 `pywin32` 库
- 需要处理窗口最小化、遮挡等情况
- 需要适配不同版本的 KiCad 窗口标题

### 方案 3：使用 VNC/RDP

在 Windows 上安装 VNC 服务器，让 KiCad 运行在 VNC 会话中，类似于 Docker 的 X11 虚拟显示。

---

## 📊 总结

| 环境 | 显示方式 | 截图方法 | 结果 |
|------|----------|----------|------|
| **Docker/Linux** | X11 虚拟显示 | Xlib 直接读取像素 | ✅ 正常工作 |
| **Windows 本地** | 真实显示器 | PyAutoGUI 截整个屏幕 | ❌ 无法定位 KiCad 窗口 |

**核心问题**：
> Windows 本地环境中，KiCad 是独立窗口，后端无法精确捕获 KiCad 窗口的图像。而后端设计期望的是 X11 虚拟显示，可以直接读取整个显示的像素数据。

**这就是为什么 Windows 本地显示"等待连接..."的根本原因。**
