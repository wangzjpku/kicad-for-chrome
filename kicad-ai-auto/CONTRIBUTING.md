# 贡献指南

感谢您对 KiCad AI Auto 的关注！本项目欢迎各种形式的贡献。

## 贡献方式

### 1. 报告问题
- 在 GitHub Issues 中提交 Bug 报告
- 提供复现步骤、环境信息和预期/实际行为
- 使用 `/api/health` 端点获取系统状态信息

### 2. 代码贡献

#### 开发环境
```bash
# 克隆仓库
git clone <repo-url>
cd kicad-for-chrome/kicad-ai-auto

# 后端开发
cd agent
pip install -r requirements.txt
./venv/Scripts/python.exe main.py

# 前端开发
cd ../web
npm install
npm run dev
```

#### 代码规范

**Python (后端)**
- 使用 `logging.getLogger(__name__)` 进行日志记录
- 所有异常处理必须捕获具体异常类型，使用 `logger.debug()` 记录
- 避免使用裸 `except: pass`
- 遵循 PEP 8 规范

**TypeScript/React (前端)**
- 使用 Vitest 进行单元测试
- 遵循项目的 ESLint 配置
- 组件添加 JSDoc 注释

#### 提交规范
```
feat: 新功能
fix: Bug 修复
docs: 文档更新
test: 测试相关
refactor: 代码重构
chore: 构建/工具更新
```

### 3. 测试

```bash
# 后端测试
cd agent
pytest tests/ -v

# 前端测试
cd web
npm run test -- --run

# 带覆盖率
pytest tests/ --cov=. --cov-report=html
npm run test:coverage
```

### 4. 提交 Pull Request

1. Fork 仓库并创建分支
2. 确保所有测试通过
3. 更新相关文档
4. 提交 PR 并描述变更内容

## 项目结构

```
kicad-ai-auto/
├── agent/           # FastAPI 后端
│   ├── routes/      # API 路由 (14个路由文件)
│   ├── kb_quality/ # 知识库质量保障
│   └── generators/ # 电路生成器
├── web/             # React 前端
│   └── src/
│       ├── editors/    # PCB/原理图编辑器
│       ├── canvas/     # Konva.js 画布组件
│       └── stores/     # Zustand 状态管理
└── playwright-tests/  # Playwright E2E 测试
```

## 分支策略

- `master` - 主分支，稳定版本
- 功能开发使用特性分支

## 许可

贡献的代码将使用与项目相同的 [GPL-3.0](LICENSE) 许可证。
