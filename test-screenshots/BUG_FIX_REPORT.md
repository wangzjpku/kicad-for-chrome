# KiCad for Chrome Bug 修复报告

**修复日期**: 2026-04-03
**修复人员**: Claude Code AI

---

## 修复摘要

| Bug # | 问题 | 状态 | 修复文件 |
|-------|------|------|----------|
| **#1** | 登录对话框不显示 | ✅ 已修复 | `App.tsx` |
| **#2** | DRC API 404 | ✅ 已修复 | `main.py` |
| **#3** | AI 分析超时 | ✅ 已修复 | `AIProjectDialog.tsx` |
| **#4** | 401 认证错误处理 | ✅ 已修复 | `ProjectList.tsx` |
| **#5** | Invalid PCB Data | ✅ 已修复 | `pcbStore.ts` |

---

## 详细修复说明

### Bug #1: 登录对话框不显示

**问题**: 点击"登录/注册"按钮后，对话框不弹出。

**根因**: `App.tsx` 中 AuthDialog 只在编辑器视图渲染，项目列表页面缺少渲染代码。

**修复**:
```tsx
// App.tsx - 在项目列表视图中添加 AuthDialog 渲染
{showAuthDialog && (
  <AuthDialog
    isOpen={true}
    onClose={() => setShowAuthDialog(false)}
    onSuccess={() => setShowAuthDialog(false)}
  />
)}
```

**文件**: `web/src/App.tsx`

---

### Bug #2: DRC API 404

**问题**: 调用 `/api/v1/drc/run` 返回 404。

**根因**: DRC 路由注册时缺少 `/api/v1` 前缀。

**修复**:
```python
# main.py - 添加 prefix 参数
app.include_router(drc_router, prefix="/api/v1")
```

**文件**: `agent/main.py`

---

### Bug #3: AI 分析超时

**问题**: AI 分析在 60 秒后超时。

**根因**:
1. 超时时间设置过短
2. 错误消息不够友好

**修复**:
```tsx
// AIProjectDialog.tsx - 增加超时时间到 120 秒
const timeoutId = setTimeout(() => controller.abort(), 120000);

// 更友好的错误消息
setError('AI 分析超时 (120秒)，请检查网络连接或稍后重试...');
```

**文件**: `web/src/components/AIProjectDialog.tsx`

---

### Bug #4: 401 认证错误处理

**问题**: 页面加载时立即调用 API，未登录时产生 401 错误。

**根因**: `ProjectList.tsx` 在调用 API 前未检查登录状态。

**修复**:
```tsx
// ProjectList.tsx - 添加登录状态检查
import { useAuthStore } from '../stores/authStore';

const { isAuthenticated } = useAuthStore();

useEffect(() => {
  if (!isAuthenticated) {
    setError('请先登录后查看项目');
    setLoading(false);
    return;
  }
  loadProjects();
}, [isAuthenticated]);
```

**文件**: `web/src/pages/ProjectList.tsx`

---

### Bug #5: Invalid PCB Data

**问题**: 打开项目时显示 "Invalid PCB data" 错误。

**根因**: 前端检查 `id` 字段，但后端返回 `project_id`。

**修复**:
```tsx
// pcbStore.ts - 兼容多种字段名
if (pcbData && typeof pcbData === 'object' &&
    ('id' in pcbData || 'project_id' in pcbData || 'footprints' in pcbData)) {
  const normalizedData = {
    ...pcbData,
    id: pcbData.id || pcbData.project_id || projectId,
  };
  // ...
}
```

**文件**: `web/src/stores/pcbStore.ts`

---

## 验证结果

### ✅ 测试通过

1. **登录对话框** - 点击登录按钮，对话框正常弹出
2. **项目列表** - 未登录时显示提示，不产生 401 错误
3. **DRC API** - 路由正确注册到 `/api/v1/drc/*`

### 📸 测试截图

- `08-login-dialog-fixed.png` - 登录对话框修复验证

---

## 剩余已知问题

1. **WebSocket 连接失败** - KiCad IPC WebSocket 需要运行 KiCad GUI
2. **defaultProps 警告** - React 未来版本将移除支持，建议迁移到默认参数
3. **AI 服务配置** - 需要配置 Kimi/GLM-4 API Key 才能使用 AI 功能

---

## 建议

1. **配置 AI API Key** - 在 `.env` 文件中配置 `KIMI_API_KEY` 或 `GLM4_API_KEY`
2. **更新 React 组件** - 将 `defaultProps` 迁移到函数参数默认值
3. **添加错误边界** - 在关键组件添加错误边界处理
