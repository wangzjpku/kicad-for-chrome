# Power-Pico 需求测试报告

**测试日期**: 2026-03-29
**测试目标**: 验证 AI 对复杂硬件产品需求的生成质量和稳定性
**测试工具**: Playwright 自动化测试

## 产品需求

Power-Pico 是一款便携测量工具：
- 测量 uA 级别微小电流
- STM32F411CEU6 主控
- INA190 电流采样差分运算电路
- FUSB302 PPS 快充协议诱骗
- ST7789 SPI LCD 显示屏
- Type-C 接口，USB 高速数据传输

## 测试结果

### 问题发现：组件生成失败

**严重程度**: 高
**问题描述**: AI 生成空组件列表

```json
{
  "spec": {
    "name": "",
    "description": "一款基于树莓派Pico...", // 描述生成正常
    "components": [],  // ← 空数组！
    "parameters": [...] // 参数生成正常
  },
  "schematic": {
    "components": [],  // ← 空数组！
    "wires": [],
    "nets": [...]
  }
}
```

### 现象

1. ✅ AI 能够理解需求并生成详细描述
2. ✅ 技术参数生成完整（测量范围、精度、采样率等）
3. ❌ **器件清单为空**（0 个组件）
4. ❌ **原理图为空**（无器件、无导线）
5. ❌ **项目名称为空字符串**

### 根本原因分析

1. **AI 能力限制**: DeepSeek 对复杂需求无法确定具体器件型号
2. **Prompt 缺陷**: 系统提示词未强制要求必须生成 components
3. **缺少后处理**: 未在 AI 返回空组件时使用知识库推断
4. **缺失质量检查**: 返回前未验证组件数量

### 对比测试

| 需求类型 | 组件生成 | 质量 |
|---------|---------|------|
| ESP32 智能控制器（简单） | ✅ 13 个器件 | 良好 |
| 5V 稳压电源（模板） | ✅ 有器件 | 良好 |
| Power-Pico（复杂定制） | ❌ 0 个器件 | **不合格** |

### 建议修复方案

#### 方案 1: 优化 Prompt（短期）

在 `deepseek_client.py` 的 system prompt 中添加：

```python
"""
【强制要求】:
- components 字段必须包含至少 5 个器件
- 每个器件必须包含: name, model, package, quantity
- 如果无法确定具体型号，使用常见型号替代
- 禁止返回空的 components 列表
"""
```

#### 方案 2: 知识库推断（中期）

在 `ai_routes.py` 中添加后处理：

```python
def infer_components_from_requirements(requirements: str) -> List[ComponentSpec]:
    """当 AI 返回空组件时，从知识库推断"""
    components = []

    # 提取关键词并匹配知识库
    if "STM32" in requirements:
        components.append(ComponentSpec(name="MCU", model="STM32F411CEU6", ...))
    if "INA190" in requirements:
        components.append(ComponentSpec(name="Current Sensor", model="INA190", ...))
    if "FUSB302" in requirements:
        components.append(ComponentSpec(name="PD Controller", model="FUSB302", ...))
    # ...

    return components
```

#### 方案 3: 质量检查机制（长期）

在 `ai_quality_check.py` 中添加：

```python
class ComponentQualityCheck:
    def check_components_non_empty(self, components: List) -> QualityResult:
        if not components:
            return QualityResult(
                passed=False,
                severity=Severity.CRITICAL,
                message="AI 返回空组件列表"
            )
        return QualityResult(passed=True)
```

### 结论

**当前状态**: Power-Pico 复杂需求无法生成有效设计
**建议**: 立即实施方案 1（Prompt 优化），中期实施方案 2（知识库推断）

### 截图证据

- `power_pico_empty_components.png` - 空组件列表截图

---

测试执行: Claude Code (Playwright)
测试环境: Windows 10, Chrome
