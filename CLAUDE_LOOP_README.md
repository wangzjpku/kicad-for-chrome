# Claude Code 自动化循环执行脚本

本目录包含用于自动化执行 Claude Code 开发流程的脚本，基于 [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的理念设计。

## 文件说明

| 文件 | 说明 |
|------|------|
| `run_claude_loop.sh` | Linux/macOS Shell 脚本 |
| `run_claude_loop.bat` | Windows 批处理脚本 |
| `run_test_plan.sh` | 测试方案专用脚本 |
| `.claude_loop_prompts/test_plan_prompt.md` | 测试方案 Prompt 模板 |

## 快速开始

### Linux/macOS

```bash
# 给脚本添加执行权限
chmod +x run_claude_loop.sh

# 运行 5 次迭代
./run_claude_loop.sh 5

# 运行 10 次迭代，使用自定义 prompt
./run_test_plan.sh 10
```

### Windows

```batch
REM 运行 5 次迭代
run_claude_loop.bat 5
```

## 脚本说明

### 1. run_claude_loop.sh

通用循环执行脚本，接收一个数字参数表示迭代次数。

**参数:**
- `迭代次数` (必填): Claude Code 循环执行的次数
- `初始prompt` (可选): 首次执行的 prompt

**示例:**
```bash
# 运行 5 次，使用默认 prompt
./run_claude_loop.sh 5

# 运行 10 次，使用自定义 prompt
./run_claude_loop.sh 10 "实现后端API测试"
```

**环境变量:**
- `CLAUDE_OPTS`: 额外的 Claude Code 选项
- `SKIP_COMMIT`: 设置为 1 跳过自动提交

### 2. run_test_plan.sh

专门用于执行 plan4.md 测试方案的脚本。

**参数:**
- `迭代次数` (必填): 测试迭代次数

**示例:**
```bash
# 运行 10 次测试迭代
./run_test_plan.sh 10
```

### 3. run_claude_loop.bat

Windows 版本的批处理脚本，功能与 `run_claude_loop.sh` 相同。

## 功能特性

### 日志记录

- 所有输出都会记录到 `.claude_loop_logs/` 目录
- 按时间戳命名日志文件
- 包含详细的时间戳和日志级别

### 进度跟踪

- 自动创建 `.claude_loop_progress.txt` 文件
- 记录每次迭代的状态和耗时
- 支持跨会话查看进度

### 自动提交

- 每次迭代完成后自动执行 `git add` 和 `git commit`
- 提交消息格式: "迭代 N 完成"
- 可以通过 `SKIP_COMMIT=1` 跳过

### 错误处理

- 连续失败 3 次后自动停止
- 每个会话有 30 分钟超时保护
- 详细的错误日志记录

## 配置选项

### Claude Code 选项

脚本默认使用以下选项:
- `--permission-mode=auto`: 自动处理权限
- `--dangerously-skip-permissions`: 跳过权限确认提示

可以通过设置 `CLAUDE_OPTS` 环境变量添加更多选项:
```bash
export CLAUDE_OPTS="--permission-mode=auto --dangerously-skip-permissions --mcp-allow-unsafe"
./run_claude_loop.sh 5
```

### 自定义 Prompt

可以通过命令行参数或环境变量传递自定义 prompt:
```bash
# 命令行参数
./run_claude_loop.sh 5 "请实现 XXX 功能"

# 环境变量
export INITIAL_PROMPT="请实现 XXX 功能"
./run_claude_loop.sh 5
```

## Prompt 文件结构

### test_plan_prompt.md

测试方案使用的 prompt 模板，包含:
- 背景信息
- 当前项目状态
- 测试方案目标
- 执行要求
- 具体任务列表

### 迭代 Prompt 格式

每次迭代会自动生成包含以下内容的 prompt:
```
[基础 prompt]
---
## 当前迭代信息

- 迭代次数: X/Y
- 请从 feature_list.json 中获取当前需要完成的任务
- 更新 claude-progress.txt 记录进度
- 完成后提交代码
```

## 输出文件

### 日志文件

位置: `.claude_loop_logs/session_YYYYMMDD_HHMMSS.log`

格式:
```
[2026-02-14 14:30:00] [INFO] 开始第 1 次迭代
[2026-02-14 14:30:05] [INFO] 第 1 次迭代完成
```

### 进度文件

位置: `.claude_loop_progress.txt`

格式:
```
--- Iteration: 1 ---
Status: SUCCESS
Time: 2026-02-14 14:30:00
Details: 耗时 5 分钟
```

## 与 Plan4.md 集成

本脚本与 plan4.md 测试方案完全集成:

1. **feature_list.json**: 记录所有待测试功能
2. **claude-progress.txt**: 记录每次迭代的进度
3. **自动状态更新**: 每次迭代完成后自动更新状态

### 使用测试方案脚本

```bash
# 运行测试方案（10 次迭代）
./run_test_plan.sh 10

# 查看进度
cat .claude_test_progress.txt

# 查看日志
tail -f .claude_loop_logs/test_plan_*.log
```

## 故障排查

### Claude Code 未找到

确保 Claude Code 已安装并在 PATH 中:
```bash
which claude
```

### 权限错误

如果遇到权限问题，确保:
1. 脚本有执行权限: `chmod +x run_claude_loop.sh`
2. Claude Code 有足够权限运行命令

### 超时问题

脚本默认 30 分钟超时，如果任务需要更长时间，可以修改脚本中的 `timeout_minutes` 变量。

## 参考资料

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [foramoment/agents-long-horizon-harness](https://github.com/foramoment/agents-long-horizon-harness)
- [jeffjacobsen/yokeflow2](https://github.com/jeffjacobsen/yokeflow2)
