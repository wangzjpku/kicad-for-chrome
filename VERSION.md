# KiCad Web Editor - 版本历史

## v0.4.0 [当前开发中]
**开始时间**: 2026-02-14
**状态**: AI智能项目创建完成，数据加载修复

### 本次更新内容

#### 1. AI智能项目创建
- AIProjectDialog 组件：自然语言输入
- AI电路生成服务：支持5V稳压电源、LED驱动、电容降压电路
- 原理图预览：SVG可视化显示
- 项目方案预览：器件表格、技术参数

#### 2. 数据加载修复 (关键修复)
- **API代理配置**：修改 `api.ts` baseURL 为 `/api/v1`，使用Vite代理解决CORS
- **PCB数据加载**：修复 `pcbStore.ts` 响应处理，直接使用返回数据
- **原理图数据转换**：
  - 后端 `{name, model}` → 前端 `{reference, value}`
  - pins数组格式转换
- **渲染安全检查**：添加 `position?.x` 和 `pin?.position?.x` 空值检查
- **FootprintRenderer兼容**：支持 `pad` 和 `pads` 两种字段名

#### 3. 测试通过
- Playwright E2E测试：13/13 通过 (100%)
- 测试覆盖：对话框、输入、预览、创建全流程

### 运行端口
- 前端: http://localhost:3004
- 后端: http://localhost:8000

### 核心文件变更
| 文件 | 变更 |
|------|------|
| `web/src/services/api.ts` | baseURL改为代理路径 |
| `web/src/stores/pcbStore.ts` | 修复数据加载逻辑 |
| `web/src/stores/schematicStore.ts` | 添加字段转换 |
| `web/src/editors/SchematicEditor.tsx` | 添加空值安全检查 |
| `web/src/canvas/FootprintRenderer.tsx` | 兼容pad/pads字段 |
| `agent/routes/project_routes.py` | 添加schematic存储 |
| `agent/routes/ai_routes.py` | AI电路生成逻辑 |

---

## v0.3.0 [当前开发中]
**开始时间**: 2026-02-14
**目标**: 原理图编辑器 + PCB编辑器 + 自动化测试

### 已完成功能
- ✅ Phase 0: Windows环境验证
- ✅ Phase 1: Windows本地数据架构
- ✅ Phase 2: 核心PCB编辑器前端
- ✅ Phase 3: PCB编辑功能
- ✅ Phase 4: 后端API完善
- ✅ 原理图编辑器 (Schematic Editor)
- ✅ PCB编辑器 (PCB Editor)
- ✅ Playwright 自动化测试
- ✅ 单元测试 (Vitest)

### 后续Phase
- Phase 5: DRC与导出
- Phase 6: AI辅助功能
- Phase 7: Windows优化和测试

---

## 详细架构文档 (v0.4.0)

### 一、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (React)                          │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │  ProjectList  │  │  PCBEditor    │  │ SchematicEditor  │   │
│  └──────┬───────┘  └───────┬────────┘  └────────┬─────────┘   │
│         │                  │                     │              │
│  ┌──────▼─────────────────▼─────────────────────▼─────────┐   │
│  │              Zustand State Management                     │   │
│  │  PCBStore          │        SchematicStore               │   │
│  └──────────────────────────┬────────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────┘
                              │ /api/v1/* (Vite Proxy)
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                   │
│  /api/v1/projects       - Project CRUD                        │
│  /api/v1/projects/{id}/pcb/design  - PCB数据                │
│  /api/v1/projects/{id}/schematic   - 原理图数据              │
│  /api/v1/ai/generate  - AI生成电路                           │
└────────────────────────────────────────────────────────────────┘
```

### 二、前端项目结构

```
kicad-ai-auto/web/
├── src/
│   ├── App.tsx                     # 主应用组件
│   ├── pages/ProjectList.tsx       # 项目列表页面
│   ├── editors/
│   │   ├── PCBEditor.tsx          # PCB编辑器 (Konva)
│   │   └── SchematicEditor.tsx     # 原理图编辑器 (Konva)
│   ├── components/AIProjectDialog.tsx  # AI创建项目对话框
│   ├── stores/
│   │   ├── pcbStore.ts            # PCB状态管理
│   │   └── schematicStore.ts      # 原理图状态管理
│   ├── services/api.ts            # API客户端
│   ├── canvas/                    # Konva渲染组件
│   │   ├── FootprintRenderer.tsx
│   │   ├── TrackRenderer.tsx
│   │   └── ViaRenderer.tsx
│   └── types/index.ts             # TypeScript类型定义
└── vite.config.ts                 # Vite配置 (代理设置)
```

### 三、核心数据流

#### AI创建项目流程
```
用户输入需求 → AIProjectDialog → API POST /ai/generate
    → ai_service.py 解析需求 → 返回 components/wires/nets
    → 创建Project + 存储原理图 + 生成PCB封装
    → 打开项目编辑器
```

#### 项目数据加载流程
```
用户点击Open → App.setCurrentProject
    → PCBStore.loadPCBData(projectId) → GET /pcb/design
    → SchematicStore.loadSchematicData(projectId) → GET /schematic
```

### 四、关键数据结构

```typescript
// PCB数据
interface PCBData {
  id: string;
  projectId: string;
  footprints: Footprint[];  // 封装列表 (后端返回pad字段)
  tracks: Track[];
  vias: Via[];
  nets: Net[];
}

// 封装 (后端返回pad，不是pads)
interface Footprint {
  id: string;
  reference: string;  // 位号 R1, C1...
  value: string;      // 型号
  position: { x: number; y: number };
  pad: Pad[];        // 注意：后端返回pad
}

// 原理图元件 (字段转换)
interface SchematicComponent {
  id: string;
  reference: string;   // 由后端name转换而来
  value: string;       // 由后端model转换而来
  position: { x: number; y: number };
  pins: SchematicPin[];
}
```

### 五、Zustand状态管理

#### PCBStore
- `pcbData`: PCB数据
- `projectId`: 当前项目ID
- `selectedIds`: 选中的元素
- `currentTool`: 当前工具 (select/move/route/place_footprint/place_via)
- `zoom/pan/gridSize`: 画布状态
- `loadPCBData/savePCBData`: 数据操作
- `undo/redo`: 历史记录

#### SchematicStore
- `schematicData`: 原理图数据
- `projectId`: 当前项目ID
- `currentTool`: 当前工具 (select/place_symbol/place_wire/place_label)
- `loadSchematicData`: 数据加载

### 六、AI电路生成

支持的电路类型及关键词：
- **5V稳压电源**: "5v", "稳压", "电源"
- **LED驱动电路**: "驱动", "灯具", "led"
- **电容降压电路**: "电容降压"

### 七、启动命令

```bash
# 后端
cd agent && python main.py

# 前端
cd web && npm run dev

# 测试
python ralph_ai_dialog_test.py
```

### 八、已知问题修复记录

1. **API代理**: api.ts baseURL改为 `/api/v1`
2. **数据加载**: 直接使用返回数据，不用 response.success 检查
3. **字段转换**: schematicStore 中 name→reference, model→value
4. **空值检查**: 组件渲染时添加可选链 `position?.x`
5. **字段兼容**: FootprintRenderer 支持 pad/pads

---

## v0.2.0 [已完成]
**完成时间**: 2026-02-13
**状态**: Windows环境验证完成

### 已完成内容
- ✅ KiCad 9.0 IPC API 验证
- ✅ 后端依赖安装
- ✅ 前端依赖安装
- ✅ 前后端连通验证

---

## v0.1.0 [已完成]
**完成时间**: 2026-02-12
**状态**: 基础架构完成

### 已完成内容
- ✅ 系统架构设计 (plan2.txt)
- ✅ 原子化执行计划 (ToDo2.txt)
- ✅ 后端FastAPI框架
- ✅ 数据库模型设计 (20+实体)
- ✅ IPC引擎封装
- ✅ 前端React项目结构
- ✅ TypeScript类型定义
- ✅ Zustand状态管理Store
- ✅ PCB画布引擎基础
- ✅ 层管理面板
- ✅ DRC报告面板

### 代码统计
- 后端: ~2,500行
- 前端: ~2,500行
- 总计: ~5,000行
- 文件: 30+

### 备份位置
`versions/v0.1.0/`

---
