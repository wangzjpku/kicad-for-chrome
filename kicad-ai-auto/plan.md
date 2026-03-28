# 项目升级计划：从当前状态到 Flux.ai 同等能力

## 背景

当前项目 (kicad-ai-auto) 是一个基于浏览器的 KiCad AI 自动化工具，已具备基础的 AI 原理图生成能力。Flux.ai 是一个专业的 AI PCB 设计平台，具备更强大的功能和更完善的工作流。

**目标**：将当前项目升级到 Flux.ai 的功能水平，实现完整的 AI PCB 设计流程。

---

## 一、现状分析

### 1.1 当前能力

| 模块 | 状态 | 说明 |
|------|------|------|
| AI 原理图生成 | ✅ 基础 | 模板 + Kimi/GLM-4/DeepSeek 级联 |
| 知识库 | ⚠️ 118个元器件 | 需要扩展 |
| 原理图编辑器 | ✅ Konva.js | 支持拖拽、缩放、画线 |
| PCB 编辑器 | ⚠️ 基础 | 仅支持查看和手动编辑 |
| KiCad 符号库 | ✅ 解析器完成 | 可解析 .kicad_sym |
| KiCad 封装库 | ✅ 解析器完成 | 可解析 .kicad_mod |
| IPC API | ⚠️ 有限 | 需要 KiCad GUI |
| 质量验证 | ✅ 三层校验 | Tier1/2/3 + 三角验证 |

### 1.2 与 Flux.ai 差距

| 功能 | Flux.ai | 当前项目 | 差距等级 |
|------|---------|---------|---------|
| AI Copilot 多轮对话 | ✅ | ❌ | 高 |
| 原理图生成 | ✅ | ⚠️ 基础 | 中 |
| PCB 自动布局 | ✅ | ❌ | 高 |
| 自动布线 | ✅ | ❌ | 高 |
| SPICE 仿真 | ✅ | ❌ | 高 |
| 参数化设计 | ✅ | ❌ | 高 |
| 数据表解析 (PDF) | ✅ | ❌ | 高 |
| 元器件库规模 | ~百万级 | 118 | 高 |
| 模板库 | Arduino/RPi | 16 模板 | 中 |
| 多模态交互 | ✅ 图像+文本 | ❌ 纯文本 | 高 |
| 自动阻抗控制 | ✅ | ❌ | 高 |

---

## 二、优先级排序

### Phase 1: 核心问题修复 (1-2 周)

**P0 - 必须立即修复**

| # | 问题 | 文件 | 修复方案 |
|---|------|------|---------|
| 1 | DeepSeek 响应格式适配不完整 | deepseek_client.py | 完善 `_normalize_response()` 处理所有格式 |
| 2 | 部分电路返回 0 components | ai_routes.py | 修复 `bill_of_materials` 字段映射 |

### Phase 2: AI 能力提升 (2-4 周)

**P1 - 核心功能**

| # | 功能 | 说明 | 难度 |
|---|------|------|------|
| 1 | 扩展知识库到 1000+ 元器件 | 完善 component_db.json | 中 |
| 2 | AI Copilot 多轮对话 | 添加 chat 端点 + 上下文管理 | 高 |
| 3 | 扩展电路类型模板 | 从 3 种扩展到 10+ 种 | 中 |
| 4 | KiCad 符号库全文搜索 | 接入官方符号库 (~50万符号) | 中 |

### Phase 3: PCB 自动化 (4-8 周)

**P1 - 差异化功能**

| # | 功能 | 说明 | 难度 |
|---|------|------|------|
| 1 | PCB 自动布局算法 | 基于约束的元件摆放 | 高 |
| 2 | 自动布线算法 | 迷宫布线 + 推挤布线 | 高 |
| 3 | DRC 检查集成 | KiCad IPC + 规则引擎 | 中 |
| 4 | 自动阻抗控制 | 差分对 + 阻抗计算 | 高 |

### Phase 4: 高级功能 (8-16 周)

**P2 - 高级功能**

| # | 功能 | 说明 | 难度 |
|---|------|------|------|
| 1 | SPICE 仿真集成 | ngspice 或外部服务 | 高 |
| 2 | PDF 数据表解析 | 提取元器件参数 | 中 |
| 3 | 多模态交互 | 图像识别 + 原理图 OCR | 高 |
| 4 | 参数化设计 | 参数化元件模型 | 高 |

---

## 三、详细实施方案

### 3.1 Phase 1: 核心问题修复

#### Issue #1: DeepSeek 响应格式适配

**问题**: DeepSeek 返回多种格式，`_normalize_response()` 未覆盖所有情况。

**文件**: `agent/deepseek_client.py`

**修复方案**: 扩展 `_normalize_response()` 函数

```python
def _normalize_response(project_spec, usage):
    """归一化 DeepSeek 的各种响应格式"""
    # 1. 处理 project_scheme 包装
    if "project_scheme" in project_spec:
        scheme = project_spec["project_scheme"]
        return {
            "name": scheme.get("name", ""),
            "description": scheme.get("description", ""),
            "components": scheme.get("components_list", scheme.get("components", [])),
            "parameters": scheme.get("technical_parameters", scheme.get("parameters", [])),
            "schematic": scheme.get("schematic_layout", scheme.get("schematic", {})),
            "usage": usage,
        }

    # 2. 处理 project + bill_of_materials 格式
    if "project" in project_spec:
        proj = project_spec["project"]
        return {
            "name": proj.get("name", ""),
            "description": proj.get("description", ""),
            "components": project_spec.get("bill_of_materials",
                proj.get("bill_of_materials",
                proj.get("components_list", []))),
            "parameters": project_spec.get("technical_parameters",
                proj.get("technical_parameters", [])),
            "schematic": project_spec.get("schematic_layout",
                proj.get("schematic_layout",
                proj.get("schematic", {}))),
            "usage": usage,
        }

    # 3. 直接返回（已是标准格式）
    return {**project_spec, "usage": usage}
```

#### Issue #2: 修复 ai_routes.py 中的 bill_of_materials 映射

**问题**: `components` 字段为空，因为 `bill_of_materials` 未被正确提取。

**文件**: `agent/routes/ai_routes.py`

**修复位置**: 约行 2823-2825

```python
# 当前代码
comp_list = project_spec.get("components", []) or []

# 应改为
comp_list = (
    project_spec.get("components", []) or
    project_spec.get("bill_of_materials", []) or
    project_spec.get("components_list", []) or
    []
)
```

---

### 3.2 Phase 2: AI 能力提升

#### Feature #1: 扩展知识库到 1000+ 元器件

**目标**: 从 118 个扩展到 1000+ 个常用元器件

**文件**: `agent/component_knowledge/component_db.json`

**实施步骤**:

1. **自动化抓取常用元器件**
   - STMicroelectronics MCU (STM32F0/F1/F4系列)
   - Espressif WiFi/蓝牙芯片 (ESP32系列)
   - 常用 USB 芯片 (CH340, FT232, CP2102)
   - 电源管理芯片 (AMS1117, LM7805, LM317, TPS系列)
   - 运算放大器 (LM358, TL072, NE5532)

2. **添加元器件数据结构**
```json
{
  "STM32F401CCU6": {
    "category": "mcu",
    "manufacturer": "STMicroelectronics",
    "symbol_library": "MCU_ST_STM32F4",
    "symbol_name": "STM32F401xCx",
    "datasheet_url": "https://www.st.com/resource/en/datasheet/stm32f401cc.pdf",
    "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
    "pins": [...],
    "required_circuits": ["decoupling", "crystal_oscillator"],
    "typical_circuits": ["uart", "spi", "i2c"],
    "power_pins": ["VDD", "VSS", "VDDA", "VSSA"]
  }
}
```

3. **创建脚本自动填充**
   - `scripts/expand_knowledge_base.py`

#### Feature #2: AI Copilot 多轮对话

**目标**: 实现 Flux.ai 风格的 AI Copilot，支持上下文对话

**文件**: `agent/routes/ai_routes.py` (新建 chat 端点)

**API 设计**:
```python
@router.post("/chat")
async def ai_chat(request: ChatRequest):
    """
    AI Copilot 多轮对话

    ChatRequest:
    - session_id: str (对话会话ID)
    - message: str (用户消息)
    - context: Optional[Dict] (当前设计上下文)
    - attachments: Optional[List] (附件)

    返回:
    - response: str (AI 回复)
    - suggestions: List[str] (建议操作)
    - updated_context: Dict (更新后的上下文)
    """
```

**Copilot 能力**:

1. **设计建议**: 根据当前原理图提出改进建议
2. **元器件替换**: 推荐性价比更高的替代芯片
3. **电路分析**: 解释电路工作原理
4. **问题诊断**: 分析 PCB 布局问题
5. **BOM 优化**: 建议更低成本的方案

#### Feature #3: 扩展电路类型模板

**目标**: 从 3 种 (general, power_supply, mcu) 扩展到 10+ 种

**文件**: `agent/schematic_generator.py`

**新增电路类型**:

```python
CIRCUIT_TYPES = {
    "general": "通用电路",
    "power_supply": "电源电路",
    "mcu": "单片机最小系统",
    "usb_device": "USB 设备",
    "wireless_sensor": "无线传感器",
    "audio_amplifier": "音频放大器",
    "motor_control": "电机控制",
    "display_interface": "显示接口",
    "communication": "通信接口",
    "iot_gateway": "物联网网关",
    "power_amplifier": "功率放大器",
    "signal_conditioning": "信号调理",
}
```

#### Feature #4: KiCad 符号库全文搜索

**目标**: 接入 KiCad 官方符号库 (~50万符号)

**文件**: `agent/symbol_lib_parser.py`

**API 端点**:
```
GET /api/v1/symbols/search?query=STM32&limit=20
GET /api/v1/symbols/search?query=USB&category=connector
```

---

### 3.3 Phase 3: PCB 自动化

#### Feature #5: PCB 自动布局算法

**目标**: 基于约束的元件自动摆放

**文件**: `agent/pcb_layout_optimizer.py` (新建)

**策略**:
1. 分离电源/模拟/数字区域
2. 相关元件靠近放置
3. 最小化连线长度
4. 遵守 DFM 规则

#### Feature #6: 自动布线算法

**目标**: 实现 PCB 自动布线

**文件**: `agent/pcb_router.py` (新建)

**策略**:
1. 迷宫布线 (Lee algorithm) - 简单网络
2. 推挤布线 (maze router + rip-up) - 复杂网络
3. 差分对布线 - USB/以太网

#### Feature #7: DRC 检查集成

**目标**: 集成 KiCad DRC 规则检查

**文件**: `agent/routes/drc_routes.py` (新建)

---

### 3.4 Phase 4: 高级功能

#### Feature #8: SPICE 仿真集成

**目标**: 内置电路仿真

**文件**: `agent/simulator/spice_simulator.py` (新建)

**集成方式**:
1. 本地 ngspice (Windows/Linux)
2. 远程仿真服务 (如 AWS)

**API 端点**:
```
POST /api/v1/simulate
{
    "schematic": {...},
    "analysis": "tran",
    "parameters": {"tstop": 1, "tstep": 0.001}
}
```

#### Feature #9: PDF 数据表解析

**目标**: 上传 PDF 数据表，AI 提取元器件参数

**文件**: `agent/services/datasheet_parser.py` (新建)

**API 端点**:
```
POST /api/v1/datasheet/parse
Content-Type: multipart/form-data
file: <pdf_file>
```

#### Feature #10: 多模态交互

**目标**: 支持图像输入（截图、手绘原理图）

**文件**: `agent/services/vision_analyzer.py` (新建)

**能力**:
1. 原理图 OCR - 识别元件和连接
2. PCB 截图分析 - 识别布局问题
3. 手绘草图转原理图

**API 端点**:
```
POST /api/v1/vision/analyze-schematic
Content-Type: multipart/form-data
image: <image_file>
```

---

## 四、关键文件清单

### 4.1 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `agent/deepseek_client.py` | 完善响应格式归一化 |
| `agent/routes/ai_routes.py` | 修复 bill_of_materials 映射，添加 chat 端点 |
| `agent/component_knowledge/component_db.json` | 扩展到 1000+ 元器件 |
| `agent/schematic_generator.py` | 扩展电路类型模板 |

### 4.2 需要新建的文件

| 文件 | 功能 |
|------|------|
| `agent/pcb_layout_optimizer.py` | PCB 自动布局算法 |
| `agent/pcb_router.py` | PCB 自动布线算法 |
| `agent/routes/drc_routes.py` | DRC 检查 API |
| `agent/simulator/spice_simulator.py` | SPICE 仿真器 |
| `agent/services/datasheet_parser.py` | PDF 数据表解析器 |
| `agent/services/vision_analyzer.py` | 多模态视觉分析器 |
| `agent/routes/chat_routes.py` | AI Copilot 对话 API |
| `scripts/expand_knowledge_base.py` | 知识库扩展脚本 |

---

## 五、验证计划

### 5.1 单元测试

```bash
# 测试 DeepSeek 格式适配
pytest tests/test_deepseek_client.py -v

# 测试知识库
pytest tests/test_knowledge_base.py -v

# 测试原理图生成器
pytest tests/test_schematic_generator.py -v
```

### 5.2 集成测试

```bash
# 端到端 AI 生成测试
pytest tests/test_ai_flow.py -v

# PCB 布局测试
pytest tests/test_pcb_layout.py -v
```

### 5.3 Playwright E2E 测试

```javascript
// 测试 AI Copilot 多轮对话
async function testAIChat() {
    await page.click('button:has-text("AI Copilot")');
    await page.fill('textarea', '设计一个 STM32 最小系统');
    await page.click('button:has-text("发送")');
    // 验证 AI 响应
}

// 测试 PCB 自动布局
async function testAutoLayout() {
    await page.click('button:has-text("自动布局")');
    // 验证布局结果
}
```

---

## 六、里程碑计划

| 里程碑 | 内容 | 时间 |
|--------|------|------|
| M1 | 修复 DeepSeek 适配问题 | 第 1 周 |
| M2 | 知识库扩展到 300+ 元器件 | 第 2 周 |
| M3 | AI Copilot 多轮对话 | 第 3-4 周 |
| M4 | KiCad 符号库全文搜索 | 第 4 周 |
| M5 | 电路类型模板扩展到 10 种 | 第 5-6 周 |
| M6 | PCB 自动布局算法 | 第 7-10 周 |
| M7 | PCB 自动布线算法 | 第 10-14 周 |
| M8 | DRC 检查集成 | 第 14-16 周 |
| M9 | SPICE 仿真集成 | 第 17-20 周 |
| M10 | PDF 数据表解析 | 第 20-22 周 |
| M11 | 多模态交互 | 第 22-24 周 |

---

## 七、风险与依赖

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| KiCad IPC 不稳定 | PCB 操作失败 | 添加重试机制和超时处理 |
| AI API 响应慢 | 用户体验差 | 添加流式响应和进度提示 |
| 布局算法复杂度 | 性能问题 | 使用高效的数据结构和并行计算 |

### 7.2 依赖项

| 依赖 | 用途 | 备选方案 |
|------|------|---------|
| kicad-python (kipy) | KiCad IPC 通信 | PyAutoGUI 降级 |
| ngspice | SPICE 仿真 | 远程仿真服务 |
| PyMuPDF | PDF 解析 | pdfplumber |
| EasyOCR | OCR 识别 | Tesseract OCR |

---

## 八、总结

本计划通过 6 个月的分阶段开发，将当前项目升级到 Flux.ai 同等水平。重点包括：

1. **核心修复** (1-2 周): 解决 DeepSeek 适配等紧迫问题
2. **AI 能力提升** (2-4 周): 扩展知识库、实现 Copilot 多轮对话
3. **PCB 自动化** (4-8 周): 自动布局布线算法
4. **高级功能** (8-16 周): 仿真、数据表解析、多模态交互

**关键成功指标**:
- 知识库元器件数量: 118 → 1000+
- 支持电路类型: 3 → 10+
- AI Copilot 对话轮次: 0 → 10+
- PCB 自动布线完成率: 0% → 80%+
