# Todo 3: AI 智能项目创建对话框

## 任务列表

### Phase 1: UI 对话框开发

- [x] **T3.1.1** 设计 AI 对话框 UI 原型
  - 位置: kicad-ai-auto/web/src/components/
  - 描述: 设计对话框布局、输入区域、按钮样式

- [x] **T3.1.2** 创建 AIProjectDialog 组件
  - 位置: kicad-ai-auto/web/src/components/AIProjectDialog.tsx
  - 描述: 实现模态对话框，包含输入框、提交按钮、进度显示

- [x] **T3.1.3** 集成到项目列表页面
  - 位置: kicad-ai-auto/web/src/pages/ProjectList.tsx
  - 描述: 添加 "AI 创建" 按钮，打开 AI 对话框

- [x] **T3.1.4** 添加对话框样式
  - 位置: kicad-ai-auto/web/src/components/AIProjectDialog.css
  - 描述: 现代化对话框样式，支持暗色主题

### Phase 2: 后端 API 开发

- [x] **T3.2.1** 创建 AI 路由模块
  - 位置: kicad-ai-auto/agent/routes/ai_routes.py
  - 描述: 创建 /api/v1/ai/* 路由

- [x] **T3.2.2** 实现需求分析 API
  - 位置: ai_routes.py - analyze_requirements()
  - 描述: 解析自然语言输入，提取技术参数

- [x] **T3.2.3** 实现原理图生成 API
  - 位置: ai_routes.py - generate_schematic()
  - 描述: 生成 KiCad 兼容的 JSON 指令

- [ ] **T3.2.4** 集成 Claude/OpenAI API
  - 位置: kicad-ai-auto/agent/services/ai_service.py
  - 描述: 创建 AI 服务封装 (当前使用模拟数据)

### Phase 3: 原理图生成引擎

- [ ] **T3.3.1** 创建系统提示词模板
  - 位置: kicad-ai-auto/agent/prompts/schematic_generator.txt
  - 描述: 基于对话框模板.txt 优化

- [ ] **T3.3.2** 实现 JSON 指令生成器
  - 位置: kicad-ai-auto/agent/services/schematic_generator.py
  - 描述: 将 AI 输出转换为 KiCad 指令

- [ ] **T3.3.3** 器件库匹配模块
  - 位置: kicad-ai-auto/agent/services/component_library.py
  - 描述: 根据需求匹配器件

- [ ] **T3.3.4** 方案文档生成器
  - 位置: kicad-ai-auto/agent/services/spec_generator.py
  - 描述: 生成 Markdown 格式项目方案

### Phase 4: 前端预览和渲染

- [ ] **T3.4.1** 创建方案预览组件
  - 位置: kicad-ai-auto/web/src/components/ProjectSpecViewer.tsx
  - 描述: 渲染 Markdown 项目方案

- [ ] **T3.4.2** 创建原理图预览组件
  - 位置: kicad-ai-auto/web/src/components/SchematicPreview.tsx
  - 描述: 渲染 JSON 指令生成的原理图

- [ ] **T3.4.3** 添加确认和编辑功能
  - 位置: AIProjectDialog.tsx
  - 描述: 支持用户确认或修改 AI 生成的方案

- [ ] **T3.4.4** 集成到创建流程
  - 位置: ProjectList.tsx
  - 描述: AI 生成的方案直接创建项目

### Phase 5: 测试和优化

- [ ] **T3.5.1** 单元测试
  - 描述: 测试需求解析、JSON 生成等核心功能

- [ ] **T3.5.2** 集成测试
  - 描述: 测试完整流程：输入 → AI → 预览 → 创建

- [ ] **T3.5.3** UI 测试
  - 描述: 测试对话框交互、预览渲染

- [ ] **T3.5.4** 性能优化
  - 描述: 优化 AI 响应时间、预览渲染速度

## 验收标准

1. 用户可以通过自然语言描述项目需求
2. AI 能够生成结构化的项目方案文档
3. 原理图指令可以正确渲染
4. 用户可以预览、编辑和确认方案
5. 确认后自动创建项目并打开编辑器
6. 单元测试覆盖核心功能
7. 集成测试通过

## 优先级

| 优先级 | 任务 |
|--------|------|
| P0 | T3.1.1, T3.1.2, T3.1.3 - UI 对话框 |
| P0 | T3.2.1, T3.2.2 - 后端 API |
| P1 | T3.2.3, T3.2.4 - AI 集成 |
| P1 | T3.3.1, T3.3.2 - 原理图生成 |
| P2 | T3.4.1 - T3.4.4 - 预览和渲染 |
| P2 | T3.5.1 - T3.5.3 - 测试 |
| P3 | T3.5.4 - 优化 |

## 资源需求

- 前端开发: 1 人
- 后端开发: 1 人
- AI 集成: 1 人
- 测试: 0.5 人
- 总计: ~3.5 人/周

## 测试结果

### Playwright 测试通过率: 13/13 (100%)

| 测试用例 | 状态 |
|---------|------|
| T3.1.1 页面加载 | ✓ PASS |
| T3.1.1 AI创建按钮点击 | ✓ PASS |
| T3.1.1 对话框打开 | ✓ PASS |
| T3.1.1 标题显示 | ✓ PASS |
| T3.1.3 输入区域 | ✓ PASS |
| T3.1.4 提交按钮 | ✓ PASS |
| T3.2.2 预览模式 | ✓ PASS |
| T3.4.1 项目名称 | ✓ PASS |
| T3.4.1 器件列表 | ✓ PASS |
| T3.5.1 原理图预览 | ✓ PASS |
| T3.6.1 确认创建 | ✓ PASS |
| T3.6.1 项目创建 | ✓ PASS |
| T3.10 截图保存 | ✓ PASS |
