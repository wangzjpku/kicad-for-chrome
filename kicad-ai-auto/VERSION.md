# KiCad AI Auto - 版本信息

## 当前版本

- **项目版本**: v0.9.12
- **后端 (agent)**: 0.9.12
- **前端 (web)**: 0.9.12
- **最后更新**: 2026-03-06T21:00

## 版本历史

### v0.9.12 - 2026-03-06 (NE555修复版本)

#### 严重问题修复
- NE555芯片原理图缺失 - 添加定时器电路检测，优先使用NE555模板
- NE555芯片PCB封装缺失 - 修复封装数据生成逻辑

#### 功能优化
- 电路类型检测优化 - NE555关键词检测优先级提高
- 输入电压自动检测 - 根据用户输入自动选择正确电压值
- DeepEDA API认证修复 - model-info接口无需认证即可访问

#### 修改文件
- agent/routes/ai_routes.py - NE555检测和电压检测
- agent/routes/auth_routes.py - 添加get_optional_user可选认证
- agent/routes/deepeda_routes.py - model-info使用可选认证

### v0.9.11 - 2026-03-06 (安全修复版本)

#### 安全修复
- JWT密钥必须从环境变量获取 - 移除硬编码默认密钥
- 危险API添加管理员认证 - /clear-all 需要管理员权限
- 密码哈希添加盐值保护 - 防止彩虹表攻击

#### 功能修复
- AI原理图引脚信息 - 使用知识库获取元件引脚定义
- 封装搜索优化 - 支持前缀匹配和单词边界匹配
- 封装类型推断优化 - 改进LED/电阻/电容识别逻辑

#### 修改文件
- agent/routes/auth_routes.py - JWT密钥验证
- agent/routes/project_routes.py - clear-all管理员认证
- agent/models/user.py - 密码盐值哈希
- agent/routes/ai_routes.py - 引脚信息获取
- agent/routes/footprint_routes.py - 搜索算法
- agent/footprint_library.py - 封装类型推断

### v0.9.11 - 2026-03-06 (走线修复版本)

#### 功能修复
- 走线连接到焊盘 - 新增 `_generate_tracks_from_footprints` 函数
- 项目名称冲突处理 - 添加 409 状态码重试逻辑
- PCB 焊盘数据完整性 - 使用 footprint_parser 正确读取封装数据

#### 修改文件
- project_routes.py - 走线生成逻辑
- web/test_results/PLAN.md - 计划完成
- web/test_results/问题.md - 问题状态更新

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

### 从 v0.8.x 升级到 v0.9.11

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
