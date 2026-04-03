# KiCad for Chrome 功能测试报告

**测试日期**: 2026-04-03
**测试人员**: 硬件工程师 (模拟实际使用场景)
**测试环境**: Windows 10, Python 3.14.2, Node.js 18+

---

## 发现的 Bug 汇总

### 🔴 严重 Bug (P0)

| # | 问题 | 位置 | 影响 | 复现步骤 |
|---|------|------|------|----------|
| **#1** | 401 认证错误 | `ProjectList.tsx:55` | 页面加载时立即调用 API 但未登录 | 1. 打开首页 2. 控制台显示 401 错误 |
| **#2** | 登录对话框不显示 | `UserBar.tsx` + `App.tsx` | 点击登录按钮无反应 | 1. 点击"登录/注册" 2. 对话框未弹出 |
| **#4** | DRC API 404 | `api.ts:178` | DRC 检查功能无法使用 | 1. 打开项目 2. 工具→设计规则检查 |

### 🟡 中等 Bug (P1)

| # | 问题 | 位置 | 影响 | 复现步骤 |
|---|------|------|------|----------|
| **#3** | Invalid PCB data | `pcbStore.ts` | 加载项目时 PCB 数据无效 | 1. 打开任何项目 2. 控制台多次显示错误 |
| **#5** | API 路径不匹配 | 前端 `api.ts` vs 后端 | 部分功能 404 | DRC: 前端 `/api/v1/drc/run`, 后端 `/api/drc/run` |
| **#6** | AI 分析超时 | `AIProjectDialog.tsx` | AI 创建功能无法完成 | 1. 点击"🤖 AI 创建" 2. 输入需求 3. 点击"生成方案" 4. 等待超时 |

---

## 详细 Bug 分析

### Bug #1: 401 认证错误

**问题描述**:
- 页面加载时立即调用 `/api/v1/projects`
- 如果用户未登录，返回 401 错误
- 用户体验差：显示错误而不是引导登录

**根因**:
```typescript
// ProjectList.tsx:55
const response = await projectApi.listProjects();
// 没有检查 isAuthenticated 状态就调用 API
```

**建议修复**:
```typescript
// 应该先检查登录状态
if (!isAuthenticated) {
  setError('请先登录后查看项目');
  return;
}
const response = await projectApi.listProjects();
```

---

### Bug #2: 登录对话框不显示

**问题描述**:
- 点击"登录 / 注册"按钮
- 按钮状态变为 `active`
- 但 AuthDialog 组件没有渲染

**根因分析**:
- `UserBar.tsx` 有本地状态 `localShowAuthDialog`
- 但实际渲染的是 `App.tsx` 中的 `showAuthDialog`
- 状态传递可能存在问题

**代码位置**:
```typescript
// UserBar.tsx:66-72
const handleLoginClick = () => {
  if (onOpenLogin) {
    onOpenLogin();  // 调用外部回调
  } else {
    setLocalShowAuthDialog(true);  // 使用本地状态
  }
};
```

**建议修复**:
- 检查 `onOpenLogin` 回调是否正确传递
- 确保 `App.tsx` 中的 `showAuthDialog` 状态正确更新

---

### Bug #3: Invalid PCB Data

**问题描述**:
- 打开项目时控制台多次显示 `[ERROR] [store] Invalid PCB data`
- 可能是 PCB 数据格式不符合预期

**代码位置**:
```typescript
// pcbStore.ts 中的 loadPCBData 函数
```

---

### Bug #4 & #5: DRC API 路径不匹配

**问题描述**:
- 前端调用: `POST /api/v1/drc/run`
- 后端实际: `POST /api/drc/run`
- 导致 404 Not Found

**建议修复**:
```typescript
// api.ts 中修改
runDRC: (projectId: string) =>
  api.post(`/api/drc/run`, { project_id: projectId })
// 或在后端添加 /api/v1/drc/run 路由
```

---

### Bug #6: AI 分析超时

**问题描述**:
- AI 创建流程第2步"生成方案"后
- 等待约30秒后显示"AI 分析超时，请稍后重试"
- 可能是后端 AI 服务配置问题或超时时间设置过短

**可能原因**:
1. Kimi API 未配置或不可用
2. 前端超时设置过短
3. 后端处理时间过长

---

## 功能测试结果

| 功能 | 状态 | 备注 |
|------|------|------|
| 后端健康检查 | ✅ 正常 | `/api/health` 返回 healthy |
| 用户认证 API | ✅ 正常 | 登录/注册 API 工作正常 |
| 项目列表 | ✅ 正常 | 登录后可正常显示 |
| 创建项目 | ✅ 正常 | 手动创建项目成功 |
| 项目打开 | ⚠️ 部分正常 | 可打开但有 PCB 数据错误 |
| 菜单栏 | ✅ 正常 | 文件/编辑/视图/放置/工具/帮助 |
| AI 创建向导 | ⚠️ 部分正常 | UI 正常，但后端超时 |
| DRC 检查 | ❌ 失败 | API 路径不匹配 |
| 原理图编辑器 | ⚠️ 部分正常 | 可切换，但部分按钮禁用 |

---

## 测试截图

1. `01-login-dialog-bug.png` - 登录对话框未显示
2. `02-project-list-loaded.png` - 项目列表正常显示
3. `03-editor-view.png` - 编辑器视图
4. `04-ai-create-dialog.png` - AI 创建对话框
5. `05-ai-step2-details.png` - AI 创建第2步
6. `06-editor-opened.png` - 编辑器打开状态
7. `07-schematic-editor.png` - 原理图编辑器

---

## 优先修复建议

1. **P0-1**: 修复登录对话框不显示问题（影响用户首次使用体验）
2. **P0-2**: 修复 DRC API 路径不匹配（功能完全不可用）
3. **P1-1**: 修复 401 认证错误处理（用户体验）
4. **P1-2**: 检查 AI 服务配置（核心功能）
5. **P1-3**: 修复 Invalid PCB data 问题

---

## 结论

软件基本架构完整，UI 设计专业，但存在几个关键问题影响实际使用：

1. **登录流程有问题** - 新用户无法正常登录
2. **DRC 功能不可用** - API 路径不匹配
3. **AI 功能超时** - 可能是后端配置问题

建议优先修复 P0 级别的问题，确保基本功能可用。
