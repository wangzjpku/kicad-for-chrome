# WebMCP 安装指南

## 方案一：使用 winget (推荐)

```powershell
# 安装 Chrome Canary
winget install Google.Chrome.Canary --accept-package-agreements --accept-source-agreements
```

## 方案二：手动下载

1. 访问: https://www.google.com/chrome/canary/
2. 下载 Windows 64-bit 版本
3. 安装到 `C:\Program Files\Google\Chrome Canary`

## 方案三：使用 Edge (如果有)

Edge 也支持部分实验性功能。

---

## 启用 WebMCP 标志

安装 Chrome Canary 后：

1. 在地址栏输入: `chrome://flags`
2. 搜索: `WebMCP` 或 `Experimental Web Platform Features`
3. 设置为: `Enabled`
4. 重启浏览器

---

## 快速启动脚本

创建文件 `C:\temp\chrome_webmcp.bat`:

```batch
@echo off
start "" "C:\Program Files\Google\Chrome Canary\Application\chrome.exe" --enable-features=WebMCP,WebMCPDeclarativeAPI,WebMCPImperativeAPI --chrome-flags="--enable-webmcp"
```

---

## 验证安装

在 Chrome Canary 中打开:
- `chrome://version` - 查看版本 (需要 146+)
- `chrome://flags` - 查看实验性功能
