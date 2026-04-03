# KiCad for Chrome 工程化改进开发计划

**生成日期**: 2026-04-01
**基于**: 工程化审计报告 (qa-reports/ENGINEERING_AUDIT_REPORT.md)
**状态**: Phase 1 已执行完成

---

## 执行总览

### Phase 1: 紧急修复 (已完成 ✅)

| 编号 | 问题 | 修复状态 | 修复内容 |
|------|------|----------|----------|
| P0-1 | drc_routes.py 语法错误 | ✅ 已修复 | 第201行 `for...if` → 正常 `for` 循环 + `isinstance` 检查 |
| P0-1b | main.py 只捕获 ImportError | ✅ 已修复 | drc/manufacturing 路由改为 `except Exception` |
| P0-2 | phase11_routes.py 损坏 | ✅ 已绕过 | 创建新的 `manufacturing_routes.py` (9个端点) |
| P0-3 | manufacturing_routes.py 不存在 | ✅ 已修复 | 新建文件，正确导入 services/export 模块 |
| P0-4 | DRCDashboard.tsx 22处错误 | ✅ 已修复 | 完整重写，拆分为 ViolationCard + ResultPanel + 主组件 |
| P1-SEC | API Key 硬编码 | ✅ 已修复 | kimi_client.py 改用 `os.environ.get("KIMI_API_KEY")` |
| P1-4 | AdminPanel 硬编码 localhost | ✅ 已修复 | 22处 → `API_BASE` 常量 + env 变量 |
| P2-1 | drc_routes 静默异常 | ✅ 已修复 | `except Exception: pass` → `except Exception as e: logger.warning(...)` |
| P2-1b | project_snapshot 裸 except | ✅ 已修复 | `except:` → `except (json.JSONDecodeError, TypeError):` |

### 验证结果

| 检查项 | 状态 |
|--------|------|
| 后端可启动 | ✅ 所有路由注册成功 |
| DRC API Routes | ✅ 11 endpoints |
| Manufacturing Routes | ✅ 9 endpoints (新创建) |
| Phase 12B Routes | ✅ auth/sharing/collab/version |
| Phase 12C Routes | ✅ marketplace/custom DRC/SDK/i18n |
| Health Check | ✅ 200 OK |
| Swagger Docs | ✅ 200 OK |
| Symbols/Templates | ✅ 200 OK |
| DRCDashboard.tsx | ✅ 0 TS errors (从22→0) |
| API Key 安全 | ✅ 不再硬编码 |

---

## Phase 2: 核心功能完善 (下一步)

### 2.1 DRC 数据加载修复
**文件**: `agent/routes/drc_routes.py:580`
**问题**: `_load_pcb_data()` 始终返回 `{}`
**方案**:
- 连接 IPC Manager 获取实时 PCB 数据
- 回退到项目文件解析
- 无数据时返回明确的 "no_data" 状态而非空 dict

### 2.2 前端 TypeScript 类型安全
**文件**: `web/tsconfig.json`
**方案**:
- 修复 PCBEditor.tsx 中 `boardOutline` 类型 (`Point2D[]` vs `{width, height}`)
- 修复 api.ts 中 ~140 处 `as any`
- 修复 RoutingQualityPanel.tsx 的 `scoreRoutingQuality` 缺失方法
- 完成后启用 `strict: true`

### 2.3 数据持久化
**方案**:
- 创建 `agent/services/database.py` — SQLite 持久化层
- 迁移 auth_service.py 用户数据到 SQLite
- 迁移 version_service.py 版本快照到 SQLite
- 迁移 marketplace_service.py 模板到 SQLite
- collaboration/sharing 保持内存 + 定期快照

### 2.4 NetRenderer 真实实现
**文件**: `web/src/canvas/NetRenderer.tsx`
**方案**:
- 实现真实的 ratsnest 算法（基于网络表）
- 计算同一网络 pad 之间的最短路径
- 支持飞线显示/隐藏和交互

---

## Phase 3: 工程化提升

### 3.1 统一错误处理
- 创建 `agent/middleware.py` 的全局异常处理器
- 统一所有路由的错误响应格式
- 添加请求ID追踪

### 3.2 前端日志框架
- 替换 186 处 `console.log` 为结构化日志
- 支持日志级别控制 (debug/info/warn/error)
- 生产构建自动移除 debug 级别日志

### 3.3 配置集中管理
- 创建 `agent/config.py` 统一管理所有路径、端口、URL
- 替换 7 处硬编码 Windows 路径为配置项
- 前端 API_BASE 已完成，后端类似处理

### 3.4 测试补全
- 为 manufacturing_routes.py 添加 API 测试
- 为修复后的 drc_routes.py 添加回归测试
- 目标：核心路由 80%+ 覆盖率

### 3.5 CI/CD 配置
- GitHub Actions: lint + type check + test
- Pre-commit hooks: ruff (Python) + eslint (TS)
- 自动化 DRCDashboard.tsx 类型检查防止回退

---

## 修复后的代码统计

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 后端可启动 | ❌ | ✅ |
| 路由注册成功 | 25/27 | 27/27 |
| TS编译错误 | 22 | 9 (预存) |
| 硬编码API Key | 1 | 0 |
| 硬编码localhost | 22处 | 0 |
| 裸except | 7处 | 5处 |
| 静默吞异常 | 6处 | 4处 |

---

## 修改的文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `agent/routes/drc_routes.py` | Edit | 修复 for...if 语法 + 异常处理 |
| `agent/routes/manufacturing_routes.py` | **New** | 新建制造路由 (9 endpoints) |
| `agent/main.py` | Edit | try/except 改为捕获 Exception |
| `agent/kimi_client.py` | Edit | API Key 移到环境变量 |
| `agent/models/project_snapshot.py` | Edit | 裸except → 具体异常类型 |
| `web/src/components/DRCDashboard.tsx` | **Rewrite** | 完整重写，22→0 TS错误 |
| `web/src/pages/AdminPanel.tsx` | Edit | 22处localhost → API_BASE常量 |
