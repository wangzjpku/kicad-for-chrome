# 故障排查指南

> 当前版本: v0.9.12

## 快速诊断

```bash
# 检查后端是否运行
curl http://localhost:8000/api/health

# 检查IPC连接
curl http://localhost:8000/api/kicad-ipc/status

# 检查前端
curl http://localhost:3000
```

---

## 常见问题

### 1. 后端启动失败

**症状**: `python main.py` 报错或端口被占用

**排查步骤**:
```bash
# 检查端口占用
netstat -ano | findstr :8000

# 杀掉旧进程
taskkill //F //IM python.exe

# 重启后端
cd agent && ./venv/Scripts/python.exe main.py
```

**常见原因**:
- 端口 8000 被占用 → 杀掉占用进程
- Python 依赖缺失 → `pip install -r requirements.txt`
- `.env` 文件缺失 → 复制 `.env.example` 为 `.env`

---

### 2. KiCad IPC 连接失败

**症状**: `/api/kicad-ipc/status` 返回 `"connected": false`

**排查步骤**:
1. 确保 KiCad GUI 已启动
2. 在 KiCad 中: `Tools → External Plugin → Start Server`
3. 检查 KiCad 版本 ≥ 9.0

**如使用 IPC API 模式失败**:
```bash
# 检查 kicad-python 是否安装
./venv/Scripts/python.exe -c "import kipy; print('kipy OK')"

# 检查 kicad-cli 路径
echo %KICAD_CLI_PATH%
# 应指向: E:\Program Files\KiCad\9.0\bin\kicad-cli.exe
```

---

### 3. PCB 画布显示空白

**症状**: Konva 画布无内容，显示 NaN 警告

**排查步骤**:
1. 检查浏览器控制台是否有错误
2. 确认 PCB 数据已通过 `/api/v1/projects/{id}/pcb/design` 加载
3. 尝试放大/缩小画布 (滚轮)

**已修复**: v0.9.12+ 版本已修复空内容时的 NaN 警告

---

### 4. AI 电路生成超时

**症状**: `/api/v1/ai/analyze` 请求超时

**排查步骤**:
1. 检查 AI API Key 配置 (`GLM_API_KEY` / `KIMI_API_KEY`)
2. 检查网络连接
3. 查看后端日志中的 `GLM-4` 或 `Kimi` 错误

**备用方案**: 使用 DeepSeek 或其他 AI 提供商

---

### 5. 原理图/PCB 数据不保存

**症状**: 刷新页面后数据丢失

**排查步骤**:
1. 检查 `agent/` 目录写权限
2. 确认 `_save_schematic_data()` 被调用 (project_routes.py)
3. 检查 `projects_data.json` 是否被正确写入

---

### 6. 网表导出失败

**症状**: `/api/v1/netlist/export` 返回 500 错误

**排查步骤**:
1. 确保 KiCad GUI 已打开对应项目
2. 检查 `kicad-cli.exe` 路径是否正确
3. 查看后端日志中的具体错误信息

---

### 7. 前端构建失败

**症状**: `npm run build` 报错

**排查步骤**:
```bash
# 清理并重装依赖
cd web
rm -rf node_modules package-lock.json
npm install

# 构建
npm run build
```

---

### 8. Windows 下截图不工作

**症状**: PyAutoGUI 模式截图返回空白/黑屏

**原因**: Windows 上截图受限，PyAutoGUI 模式不适合生产环境

**解决方案**: 使用 IPC API 模式 (KiCad 9.0+ 推荐)

---

### 9. 代码修改后不生效

**症状**: 修改 Python 代码后行为没变

**排查步骤**:
```bash
# 杀掉所有 Python 进程
taskkill //F //IM python.exe

# 重启后端
cd agent && ./venv/Scripts/python.exe main.py
```

---

### 10. Docker 模式下 KiCad 崩溃

**症状**: Docker 容器中的 KiCad 无响应

**排查步骤**:
```bash
# 查看容器日志
docker-compose logs kicad-runtime

# 重启容器
docker-compose restart kicad-runtime
```

---

## 日志位置

| 组件 | 日志位置 |
|------|---------|
| 后端 | `agent/` 标准输出 + `logging` 配置 |
| 前端 | 浏览器开发者工具 Console |
| KiCad | KiCad GUI 内置日志 |
| Docker | `docker-compose logs` |

---

## 获取帮助

- 查看 API 文档: http://localhost:8000/docs
- 查看系统状态: http://localhost:8000/api/kicad-ipc/status
- 查看版本: http://localhost:8000/api/version
- 查看知识库健康: http://localhost:8000/api/v1/knowledge/health
