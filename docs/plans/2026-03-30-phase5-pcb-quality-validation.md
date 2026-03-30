# Phase 5 设计文档 - PCB 质量验证与制造输出

**日期**: 2026-03-30
**版本**: 1.0
**状态**: 已完成

## 概述

Phase 5 实现了三个方向的功能：

1. **高级 DRC + SI 分析** - 将阻抗计算主动集成到 DRC 引擎
2. **自动制造输出** - 增强 Gerber/BOM/装配图生成
3. **KiCad 原生集成测试** - 端到端验证 PCB 文件可被 KiCad 打开

## 架构

```
原理图数据
    ↓
┌─────────────────────────────────────┐
│  1. SI 分析器 (si_analyzer.py)      │
│     - 阻抗控制分析                   │
│     - 差分对阻抗                     │
│     - 传输线损耗                   │
│     - 串扰估算                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. 制造检查 (manufacturing_checker) │
│     - JLCPCB 规则                   │
│     - PCBWay 规则                   │
│     - 费用估算                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. 导出模块 (export/)              │
│     - Gerber 生成                    │
│     - BOM 生成                      │
│     - 装配图                        │
└─────────────────────────────────────┘
    ↓
KiCad S-Expression / Gerber / BOM
```

## 新增文件

| 文件 | 描述 |
|------|------|
| `agent/drc/si_analyzer.py` | 信号完整性分析器 |
| `agent/export/__init__.py` | 导出包初始化 |
| `agent/export/gerber_generator.py` | 多层板 Gerber 生成器 |
| `agent/export/bom_generator.py` | LCSC 料号 BOM 生成器 |
| `agent/export/manufacturing_checker.py` | 制造可行性检查器 |
| `agent/tests/test_kicad_e2e.py` | KiCad E2E 测试 |

## 修改文件

| 文件 | 修改内容 |
|------|---------|
| `agent/routes/drc_routes.py` | 添加 `/si/analyze` 端点 |

## SI 分析器 (SIAnalyzer)

### 功能

| 方法 | 描述 |
|------|------|
| `analyze_impedance()` | 计算单线阻抗，与目标值对比 |
| `analyze_diff_pair()` | 分析差分对：阻抗、耦合、长度匹配 |
| `analyze_transmission_loss()` | 传输线损耗分析 |
| `calculate_crosstalk_simple()` | 串扰系数估算 |
| `analyze_all()` | 分析所有网络 |

### 阻抗目标

| 接口 | 目标阻抗 | 容差 |
|------|----------|------|
| USB | 90Ω 差分 | ±10% |
| Ethernet | 100Ω 差分 | ±10% |
| HDMI | 100Ω 差分 | ±10% |
| PCIe | 85Ω 差分 | ±10% |
| DDR | 50Ω 单端 | ±10% |
| LVDS | 100Ω 差分 | ±10% |
| RS485/CAN | 120Ω 差分 | ±10% |

## 制造检查器 (ManufacturingChecker)

### JLCPCB 规则

| 参数 | 最小值 |
|------|--------|
| 线宽 | 0.127mm |
| 间距 | 0.127mm |
| 过孔钻孔 | 0.3mm |
| 过孔外径 | 0.45mm |
| 焊环 | 0.15mm |
| 板厚 | 0.4-3.2mm |
| 厚径比 | ≤8:1 |

### 费用估算

```python
{
    "manufacturer": "jlcpcb",
    "dimensions": "100x80mm",
    "layers": 2,
    "thickness": "1.6mm",
    "quantity": 5,
    "unit_price_usd": 2.50,
    "total_price_usd": 12.50
}
```

## 导出模块

### Gerber 生成器 (EnhancedGerberGenerator)

生成层:
- 铜层: F.Cu, B.Cu, In1.Cu, In2.Cu...
- 阻焊层: F.Mask, B.Mask...
- 丝印层: F.SilkS, B.SilkS
- 锡膏层: F.Paste, B.Paste
- 板框: Edge.Cuts

### BOM 生成器 (BOMGenerator)

导出格式:
- CSV (扁平/分组)
- JSON
- XML (KiCad 格式)

字段:
- Reference, Value, Footprint, Symbol
- LCSC Part, Manufacturer Part, Manufacturer
- Datasheet

## API 端点

### SI 分析

```
POST /drc/si/analyze
{
    "pcb_data": {...},
    "include_impedance": true,
    "include_crosstalk": true,
    "include_loss": true
}
```

响应:
```json
{
    "success": true,
    "passed": true,
    "impedance_violations": [...],
    "crosstalk_warnings": [...],
    "loss_warnings": [...],
    "summary": {
        "total_nets": 10,
        "critical_violations": 0,
        "warnings": 2
    }
}
```

## 测试

| 测试文件 | 测试数量 | 覆盖范围 |
|----------|---------|----------|
| `test_kicad_e2e.py` | 18 | PCB 生成、导出、制造、SI 分析 |

测试结果: **624 passed, 4 skipped**

## 质量对比

| 特性 | Phase 3 | Phase 5 |
|------|---------|---------|
| 阻抗控制检查 | 无 | ✅ 微带线/带状线 |
| 差分对分析 | 无 | ✅ 90/100Ω 目标 |
| 传输损耗 | 无 | ✅ 导体/介质损耗 |
| 串扰估算 | 无 | ✅ 简化模型 |
| Gerber 生成 | KiCad 导出 | ✅ 多层板生成 |
| BOM 生成 | 基本 CSV | ✅ LCSC 料号 |
| 制造检查 | 无 | ✅ JLCPCB/PCBWay |
| 费用估算 | 无 | ✅ 自动计算 |
| E2E 测试 | 原理图 | ✅ PCB + 制造 |

## 后续工作

1. **真实 KiCad E2E 测试** - 需要 KiCad GUI 运行环境
2. **ODB++ 导出** - 高级制造文件格式
3. **IPC-2221 进阶** - 更多铜厚/温升选项
4. **EMI 热点可视化** - 在 PCB 编辑器中高亮问题区域
