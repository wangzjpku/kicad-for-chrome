# Phase 4 设计文档 - 高质量 PCB 生成

**日期**: 2026-03-30
**版本**: 1.0
**状态**: 已批准

## 概述

Phase 4 目标：将 AI 生成的 PCB 质量从"网格排列 + L型连线"提升到接近手工设计水平。

## 设计决策

| 问题 | 选择 |
|------|------|
| 网络分类策略 | C - 综合方案（关键词 + 元器件 + 用户标注） |
| 分类时机 | B - 独立预处理步骤 |
| 电流信息获取 | D - 用户标注 > datasheet > 默认估算 |
| 铺铜策略 | D - 用户指定 + GND 默认 |
| 铺铜顺序 | A - 布线之后 |
| 走线宽度传递 | B - 预处理阶段设置 |
| KiCad 格式 | C - 完整 S-expression |

## 架构

```
原理图数据
    ↓
┌─────────────────────────────────────┐
│  1. net_classifier.py               │
│     - 关键词匹配                     │
│     - 元器件类型推断                 │
│     - 用户标注覆盖                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. current_calculator.py           │
│     - IPC-2221 载流标准              │
│     - 计算走线宽度                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. ai_routes.py                   │
│     - 智能布局                      │
│     - 智能布线（动态宽度）            │
│     - 铜箔浇注                      │
└─────────────────────────────────────┘
    ↓
KiCad S-Expression 输出
```

## 新增文件

| 文件 | 描述 |
|------|------|
| `agent/pcb/__init__.py` | 模块初始化 |
| `agent/pcb/net_classifier.py` | 网络分类器 |
| `agent/pcb/current_calculator.py` | 电流计算器 |
| `tests/test_net_classifier.py` | 分类器测试 |
| `tests/test_current_calculator.py` | 电流计算测试 |

## 修改文件

| 文件 | 修改内容 |
|------|---------|
| `agent/routes/ai_routes.py` | 集成 Phase 4 流程 |
| `agent/routing/routing_engine.py` | 支持动态走线宽度 |
| `agent/routing/copper_pour.py` | 修复并集成 |

## 网络分类规则

```python
NET_CLASS_POWER = "power"      # VCC, VDD, 5V, 3V3, 12V, VIN, VOUT, VBUS
NET_CLASS_GROUND = "ground"   # GND, AGND, DGND, SGND, EARTH
NET_CLASS_HIGH_SPEED = "high_speed"  # USB, PCIe, DDR, HDMI, ETH, MIPI
NET_CLASS_DIFF_PAIR = "diff_pair"   # USB_D+, USB_D-, ETH_TX+
NET_CLASS_SIGNAL = "signal"    # 其他
```

## 电流计算 (IPC-2221)

| 走线宽度 | 最大电流 (1oz铜, 10°C温升) |
|---------|--------------------------|
| 0.25mm | 0.5A |
| 0.5mm | 1.5A |
| 1.0mm | 3.0A |
| 2.5mm | 5.0A |

## KiCad 输出特性

- **Zone**: GND/电源 平面铺铜
- **Thermal Relief**: 4-spoke 十字花焊盘
- **Via Stitching**: 过孔阵列
- **Dynamic Width**: 根据电流自动调整

## 质量对比

| 特性 | Phase 3 | Phase 4 |
|------|---------|---------|
| 走线宽度 | 固定 0.25mm | 动态计算 |
| 铺铜 | 无 | GND + 电源 zone |
| 热焊盘 | 无 | 4-spoke thermal |
| 过孔阵列 | 单点过孔 | Via Stitching |
| 用户控制 | 无 | 电流 + 铺铜标注 |
