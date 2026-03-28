# 更新日志 (Changelog)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.9.12] - 2026-03-25

### Fixed
- 版本号统一: 所有文件（VERSION.md, package.json, main.py, CLAUDE.md）统一为 v0.9.12
- 技术债务: 20+ 处裸异常处理修复为带日志的精确异常捕获

## [0.9.11] - 2026-02-26

### Added
- AI电路智能识别系统
  - ESP32/Arduino/STM32单片机自动识别
  - 电源模块自动识别
  - 传感器模块自动识别
- 标准原理图生成器
  - 自动元件布局
  - 自动网络连接
  - 电源符号生成
- PCB自动生成
  - 从原理图自动转换
  - 自动封装分配
  - 自动走线规划
- 前端AI项目创建对话框
  - 需求输入界面
  - 澄清问题功能
  - 方案预览和编辑
  - 项目创建流程

### Fixed
- 修复了AI返回模板而非动态生成的问题
- 修复了原理图数据未正确传递的问题
- 修复了PCB数据为空的问题

### Changed
- 优化了电路类型检测优先级（ESP32/Arduino/STM32优先于通用模板）
- 改进了API响应格式处理

---

## [0.8.0] - 早期版本

### Added
- FastAPI后端服务
- React前端界面 (Vite + TypeScript)
- KiCad IPC API集成 (kicad-python)
- WebSocket实时通信
- 项目管理API
- 原理图编辑器
- PCB编辑器

### Changed
- 支持Docker部署
- 支持Windows本地运行
- 支持Linux容器化运行

---

## [0.1.0] - 项目初始版本

### Added
- 基础项目结构
- Docker配置
- Playwright测试框架
