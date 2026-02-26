# KiCad AI Auto - 版本信息

## 当前版本

- **项目版本**: v0.9.0
- **后端 (agent)**: 1.0.0
- **前端 (web)**: 0.9.0
- **最后更新**: 2026-02-26

## 版本历史

### v0.9.0 - 2026-02-26 (安全加固版本)

#### 安全修复 (36+)
- **路径遍历防护**: 8 处修复
- **线程安全**: 4 处修复
- **资源泄漏**: 4 处修复
- **输入验证**: 6 处修复
- **命令注入防护**: 3 处修复
- **敏感信息保护**: 3 处修复
- **逻辑缺陷**: 5 处修复
- **配置问题**: 3 处修复

#### 修改文件
- main.py (6次修改)
- kicad_ipc_manager.py (5次修改)
- project_routes.py (5次修改)
- kicad_ipc_routes.py (4次修改)
- chip_data_checker.py (3次修改)
- kicad_controller.py (3次修改)
- validators/__init__.py (2次修改)
- 其他文件 (8个)

### v0.8.7 - 2026-02-26
- 修复AI电路生成电压和芯片识别

### v0.8.6 - 2026-02-25
- 增强PCB封装设计和AI电路生成功能

### v0.8.0 - 2026-02-24
- AI电路生成功能正式上线
- 支持ESP32/Arduino/STM32等单片机识别
- 支持标准原理图生成
- 支持PCB自动布局

### v0.7.x - 早期版本
- 基础框架搭建
- FastAPI后端服务
- React前端界面
- KiCad IPC API集成

---

## 组件版本

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ / 3.14 | 后端运行时 |
| Node.js | 18.0+ | 前端构建 |
| KiCad | 9.0+ | IPC API 支持 |
| FastAPI | 0.115+ | Web 框架 |
| React | 18.3+ | 前端框架 |
| Vite | 6.1+ | 构建工具 |

---

## 升级指南

### 从 v0.8.x 升级到 v0.9.0

1. **更新代码**
   ```bash
   git pull origin main
   ```

2. **配置环境变量**
   ```bash
   # .env 文件
   OUTPUT_DIR=/path/to/output
   KICAD_CLI_PATH=/path/to/kicad-cli
   ```

3. **更新依赖**
   ```bash
   # 后端
   cd agent
   pip install -r requirements.txt

   # 前端
   cd web
   npm install
   ```

4. **验证安装**
   ```bash
   # 启动后端
   python main.py

   # 访问 API 文档
   # http://localhost:8000/docs
   ```

### 破坏性变更

1. **Screenshot API**: 不再接受用户提供的 `output_path` 参数
2. **Project ID**: 必须匹配正则表达式 `^[a-zA-Z0-9_-]+$`
3. **WebSocket 消息**: 必须包含 `type` 字段

---

## 相关文档

- [CHANGELOG.md](../CHANGELOG.md) - 完整更新日志
- [WORK_LOG.md](./agent/WORK_LOG.md) - 工作日志
- [安全审查报告](./docs/plans/2026-02-26-security-audit-report.md)
