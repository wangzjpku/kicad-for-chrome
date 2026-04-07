# PCB设计专用LLM微调方案 — KiCad AI Auto 项目专用版

## 日期
2026-04-05 (v2.0 - 项目对齐版)

## 零、项目对接说明

### 当前项目架构
本方案完全针对 `1-kicad-for-chrome/kicad-ai-auto` 项目设计，与现有系统无缝集成。

**核心对接点**:
- **数据结构**: 对齐 `schematic_data.json`, `projects_data.json`, `pcb_data.json`
- **API接口**: 对齐 `routes/ai_routes.py`, `routes/project_routes.py`
- **评分系统**: 对齐 `pcb_quality_scorer.py` 的10维度评分
- **前端渲染**: 输出格式兼容 Konva.js 渲染层

---

## 一、项目目标

### 核心目标
- **输入**: 自然语言描述电路需求 → 通过 `/api/v1/ai/analyze` 接口
- **输出**: 完整的原理图 + PCB布局 + 制造文件 → 对齐现有数据结构
- **目标分数**: 85-90分（使用 `pcb_quality_scorer.py` 评分器）

### 与现有系统的能力对照

| 能力 | 现有API路由 | 现有数据结构 | 微调目标 | 优先级 |
|------|-------------|--------------|----------|--------|
| 原理图生成 | `/api/v1/ai/generate` | `schematic_data.json` | 专业级 | P0 |
| 元件选型 | `/api/v1/symbols/search` | `components[]` | 自动匹配LCSC | P0 |
| PCB布局 | `/api/v1/projects/{id}/pcb` | `pcb_data.json` | 专业级 | P0 |
| 自动布线 | `/api/v1/pcb/fanout` | `tracks[]` | 高质量 | P1 |
| DRC修复 | `/drc/check` | `drc_status{}` | 自动修复 | P1 |
| 优化迭代 | `iteration_optimizer_v3.py` | 10维度评分 | AI驱动 | P2 |

---

## 二、模型选择

### 推荐方案

| 模型 | 参数量 | 推理速度 | 中文能力 | 推荐场景 |
|------|--------|----------|----------|----------|
| **Qwen2.5-7B-Instruct** | 7B | 快 | 优秀 | 推荐 ✅ |
| Qwen2.5-14B-Instruct | 14B | 中 | 优秀 | 更高精度 |
| Gemma2-9B-It | 9B | 中 | 一般 | 英文场景 |
| Llama3.1-8B-Instruct | 8B | 快 | 较差 | 不推荐 |

### 硬件需求

| 配置 | Qwen-7B | Qwen-14B |
|------|---------|----------|
| 微调(LoRA) | RTX 3090/4090 (24GB) | A100 (40GB) |
| 推理 | RTX 3060 (12GB) | RTX 3090 (24GB) |
| 量化推理 | RTX 2060 (8GB) | RTX 3060 (12GB) |

---

## 三、数据准备

### 3.1 数据类型总览

```
训练数据集结构:
├── stage1_pretrain/           # 阶段1: 领域预训练
│   ├── pcb_textbooks.jsonl    # PCB教材文本
│   ├── datasheets.jsonl       # 元件数据手册
│   └── app_notes.jsonl        # 应用笔记
│
├── stage2_sft/                # 阶段2: 有监督微调
│   ├── schematic_gen.jsonl    # 原理图生成
│   ├── component_select.jsonl # 元件选型
│   ├── placement.jsonl        # 布局设计
│   ├── routing.jsonl          # 布线设计
│   └── optimization.jsonl     # 优化迭代
│
├── stage3_rlhf/               # 阶段3: 强化学习(可选)
│   ├── preference.jsonl       # 偏好数据
│   └── reward_model.jsonl     # 奖励模型数据
│
└── evaluation/                # 评估数据
    ├── test_cases.jsonl       # 测试用例
    └── golden_samples.jsonl   # 金标准样本
```

### 3.2 数据格式详解 — 对齐现有项目数据结构

> **重要**: 以下格式完全对齐 `schematic_data.json`, `projects_data.json`, `pcb_data.json` 的字段定义

#### 格式1: 原理图生成 (schematic_gen.jsonl) — 对齐 `schematic_data.json`

**现有数据结构** (来自 `schematic_data.json`):
```json
{
  "project-uuid": {
    "components": [
      {"id": "R1", "reference": "R1", "model": "1K", "footprint": "Resistor_SMD:R_0603_1608Metric"}
    ],
    "wires": [...],
    "nets": [...],
    "powerSymbols": [...]
  }
}
```

**训练数据格式** (对齐上述结构):
```json
{
  "id": "sch_001",
  "instruction": "设计一个STM32F103C8T6最小系统原理图，包含电源、复位、晶振、调试接口",
  "input": {
    "requirements": {
      "mcu": "STM32F103C8T6",
      "power": {"input": "5V USB", "output": "3.3V", "max_current": "500mA"},
      "crystal": "8MHz",
      "debug": "SWD",
      "constraints": {"cost_target": "50元以内", "size": "紧凑"}
    }
  },
  "output": {
    "schematic": {
      "components": [
        {
          "id": "U1",
          "reference": "U1",
          "name": "STM32F103C8T6",
          "model": "STM32F103C8T6",
          "value": "STM32F103C8T6",
          "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
          "lcsc": "C8734",
          "position": {"x": 0, "y": 0},
          "pins": [
            {"number": 1, "name": "VBAT", "type": "power_in"},
            {"number": 2, "name": "PC13", "type": "bidirectional"}
          ],
          "nets": ["VCC", "GND"]
        },
        {
          "id": "U2",
          "reference": "U2",
          "name": "AMS1117-3.3",
          "model": "AMS1117-3.3",
          "value": "AMS1117-3.3",
          "footprint": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
          "lcsc": "C6186",
          "position": {"x": -50, "y": 30},
          "pins": [
            {"number": 1, "name": "GND", "type": "power_in"},
            {"number": 2, "name": "VOUT", "type": "power_out"},
            {"number": 3, "name": "VIN", "type": "power_in"}
          ]
        }
      ],
      "wires": [
        {"start": {"x": -50, "y": 30}, "end": {"x": 0, "y": 0}, "net": "VCC"},
        {"start": {"x": -50, "y": 25}, "end": {"x": 0, "y": -5}, "net": "GND"}
      ],
      "nets": [
        {"name": "VCC", "type": "power"},
        {"name": "GND", "type": "ground"},
        {"name": "NRST", "type": "signal"},
        {"name": "OSC_IN", "type": "signal"}
      ],
      "powerSymbols": [
        {"type": "VCC", "position": {"x": -50, "y": 35}},
        {"type": "GND", "position": {"x": -50, "y": 20}}
      ],
      "labels": [
        {"text": "STM32F103C8T6最小系统", "position": {"x": 0, "y": 50}}
      ],
      "designRules": {
        "min_clearance": 0.15,
        "min_track_width": 0.15
      },
      "title": "STM32F103C8T6最小系统",
      "date": "2026-04-05",
      "revision": "1.0",
      "company": "KiCad AI Auto"
    },
    "explanation": "STM32最小系统包含: 1) AMS1117-3.3 LDO 2) 8MHz晶振 3) 去耦电容 4) SWD接口"
  },
  "quality_score": 92,
  "quality_dimensions": {
    "电气正确性": 14.5,
    "完整性": 14.0,
    "可读性": 9.5,
    "规范性": 9.0
  }
}
```

#### 格式2: PCB布局 (placement.jsonl) — 对齐 `pcb_data.json` + 评分维度

**现有PCB数据结构字段** (来自 `pcb_quality_scorer.py` 评估逻辑):
```python
# PCB评分依赖的字段:
pcb_data = {
    "footprints": [...],      # 组件/封装
    "tracks": [...],          # 走线
    "vias": [...],            # 过孔
    "zones": [...],           # 铺铜区域
    "nets": [...],            # 网络
    "texts": [...],           # 丝印文字
    "design_rules": {...},    # 设计规则
    "drc_status": {...},      # DRC状态
    "boardWidth": 100,        # 板宽
    "boardHeight": 80         # 板高
}
```

**训练数据格式**:
```json
{
  "id": "pcb_001",
  "instruction": "为STM32最小系统设计PCB布局，双层板，50x50mm",
  "input": {
    "schematic": {
      "components": [...],
      "nets": [...]
    },
    "constraints": {
      "boardWidth": 50,
      "boardHeight": 50,
      "layers": 2,
      "min_trace_width": 0.15,
      "min_clearance": 0.15,
      "manufacturing": "JLCPCB经济版"
    }
  },
  "output": {
    "pcb": {
      "footprints": [
        {
          "reference": "U1",
          "name": "STM32F103C8T6",
          "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
          "position": {"x": 25, "y": 25},
          "rotation": 0,
          "layer": "F.Cu",
          "pads": [
            {"number": 1, "name": "VBAT", "net": "VCC"},
            {"number": 5, "name": "VSS", "net": "GND"}
          ],
          "placement_reason": "MCU放在中心，便于周围元件布局和布线"
        },
        {
          "reference": "U2",
          "name": "AMS1117-3.3",
          "footprint": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
          "position": {"x": 10, "y": 40},
          "rotation": 0,
          "layer": "F.Cu",
          "pads": [
            {"number": 1, "name": "GND", "net": "GND"},
            {"number": 2, "name": "VOUT", "net": "VCC"},
            {"number": 3, "name": "VIN", "net": "VIN"}
          ],
          "placement_reason": "LDO放在边缘靠近电源输入，散热良好"
        }
      ],
      "tracks": [],
      "vias": [],
      "zones": [
        {
          "name": "GND_Top",
          "net": "GND",
          "layer": "F.Cu",
          "outline": [{"x": 5, "y": 5}, {"x": 45, "y": 5}, {"x": 45, "y": 45}, {"x": 5, "y": 45}],
          "purpose": "顶层GND铺铜，EMC评分提升"
        },
        {
          "name": "GND_Bottom",
          "net": "GND",
          "layer": "B.Cu",
          "outline": [{"x": 3, "y": 3}, {"x": 47, "y": 3}, {"x": 47, "y": 47}, {"x": 3, "y": 47}],
          "purpose": "底层GND铺铜，完整参考平面"
        }
      ],
      "texts": [
        {"text": "U1", "layer": "F.SilkS", "position": {"x": 25, "y": 25}},
        {"text": "STM32_Min", "layer": "F.SilkS", "position": {"x": 25, "y": 5}}
      ],
      "nets": [
        {"name": "VCC"}, {"name": "GND"}, {"name": "VIN"}
      ],
      "design_rules": {
        "min_clearance": 0.15,
        "min_track_width": 0.15,
        "min_via_size": 0.4,
        "min_via_drill": 0.2
      },
      "boardWidth": 50,
      "boardHeight": 50
    },
    "design_rules_applied": [
      "去耦电容紧靠IC电源引脚",
      "晶振远离高速信号",
      "电源路径短而宽",
      "GND铺铜完整"
    ]
  },
  "quality_score": 88,
  "quality_dimensions": {
    "功能正确性": 12.0,
    "可制造性": 9.0,
    "信号完整性": 8.0,
    "热设计": 4.0,
    "EMC合规": 4.5,
    "美学评估": 4.0
  }
}
```

#### 格式3: 布线设计 (routing.jsonl) — 对齐评分器检测逻辑

**评分器检测字段** (`pcb_quality_scorer.py`):
```python
# 布线相关评分依赖:
tracks = [{
    "net": "VCC",           # 网络名称
    "start": {"x": 0, "y": 0},  # 起点
    "end": {"x": 10, "y": 10},  # 终点
    "width": 0.3,           # 线宽
    "layer": "F.Cu"         # 层
}]
vias = [{
    "net": "GND",
    "x": 15, "y": 35,
    "size": 0.6,
    "drill": 0.3,
    "thermal": false        # 是否热过孔
}]
```

**训练数据格式**:
```json
{
  "id": "route_001",
  "instruction": "完成STM32最小系统的PCB布线",
  "input": {
    "placement": {...},
    "nets": [...],
    "constraints": {
      "power_nets": ["VCC", "3V3", "5V"],
      "signal_nets": ["OSC_IN", "OSC_OUT", "SWDIO", "SWCLK"],
      "high_speed": [],
      "differential_pairs": []
    }
  },
  "output": {
    "routing": {
      "tracks": [
        {
          "id": "T001",
          "net": "VCC",
          "layer": "F.Cu",
          "width": 0.3,
          "start": {"x": 10, "y": 40},
          "end": {"x": 25, "y": 25},
          "purpose": "电源走线加宽 (可制造性:线宽检查)"
        },
        {
          "id": "T002",
          "net": "OSC_IN",
          "layer": "F.Cu",
          "width": 0.15,
          "start": {"x": 20, "y": 18},
          "end": {"x": 22, "y": 20},
          "purpose": "晶振信号走线短而直 (信号完整性)"
        }
      ],
      "vias": [
        {
          "id": "V001",
          "net": "GND",
          "x": 15,
          "y": 35,
          "size": 0.6,
          "drill": 0.3,
          "thermal": false,
          "purpose": "GND过孔连接上下层 (EMC合规:回路面积)"
        },
        {
          "id": "V002",
          "net": "GND",
          "x": 8,
          "y": 38,
          "size": 0.6,
          "drill": 0.3,
          "thermal": true,
          "purpose": "LDO热过孔 (热设计:thermal_vias)"
        }
      ]
    },
    "routing_strategy": {
      "power_first": true,
      "signal_grouping": "by_function",
      "layer_assignment": "signals_on_top,ground_on_bottom"
    }
  },
  "quality_score": 85,
  "quality_dimensions": {
    "功能正确性": 14.0,
    "可制造性": 8.5,
    "信号完整性": 7.5,
    "EMC合规": 4.0
  }
}
```

#### 格式4: 优化迭代 (optimization.jsonl) — 对齐 `iteration_optimizer_v3.py` 维度

**评分器10维度定义** (来自 `pcb_quality_scorer.py`):
```python
# 原理图维度 (50分)
SCHEMATIC_DIMENSIONS = {
    "电气正确性": {"max": 15, "weight": 2.0},  # ERC/悬浮引脚/电源/短路
    "完整性": {"max": 15, "weight": 1.5},       # 元件值/封装/网络/BOM/规则
    "可读性": {"max": 10, "weight": 1.0},       # 间距/标签/交叉/模块化
    "规范性": {"max": 10, "weight": 1.0},       # 命名/网络/引脚/注释
}

# PCB维度 (50分)
PCB_DIMENSIONS = {
    "功能正确性": {"max": 15, "weight": 2.5},  # DRC/布线/LVS
    "可制造性": {"max": 10, "weight": 1.5},   # 线宽/间距/过孔/焊盘/丝印
    "信号完整性": {"max": 10, "weight": 1.8},  # 阻抗/差分/串扰/参考面
    "热设计": {"max": 5, "weight": 1.3},       # 铺铜/热过孔/分布
    "EMC合规": {"max": 5, "weight": 1.5},       # 回路/地平面/去耦
    "美学评估": {"max": 5, "weight": 0.8}        # 角度/一致性/对齐
}
```

**训练数据格式**:
```json
{
  "id": "opt_001",
  "instruction": "当前PCB评分75分，优化到85分以上",
  "input": {
    "current_design": {
      "schematic": {...},
      "pcb": {...}
    },
    "current_score": 75,
    "score_breakdown": {
      "功能正确性": 12.0,
      "可制造性": 8.5,
      "信号完整性": 6.0,
      "热设计": 2.5,
      "EMC合规": 3.0,
      "美学评估": 3.0
    },
    "target_score": 85
  },
  "output": {
    "optimizations": [
      {
        "action": "add_thermal_vias",
        "target_dimension": "热设计",
        "target": "U2",
        "reason": "LDO发热，需要热过孔散热 (热设计当前2.5/5.0)",
        "expected_improvement": 2.0,
        "modifications": [
          {
            "type": "add_via",
            "net": "GND",
            "x": 8,
            "y": 38,
            "size": 0.6,
            "drill": 0.3,
            "thermal": true
          },
          {
            "type": "add_via",
            "net": "GND",
            "x": 12,
            "y": 38,
            "size": 0.6,
            "drill": 0.3,
            "thermal": true
          }
        ]
      },
      {
        "action": "add_gnd_zone",
        "target_dimension": "EMC合规",
        "reason": "EMC评分3.0/5.0，需要完整GND平面",
        "expected_improvement": 2.0,
        "modifications": [
          {
            "type": "add_zone",
            "net": "GND",
            "layer": "B.Cu",
            "outline": [{"x": 3, "y": 3}, {"x": 47, "y": 3}, {"x": 47, "y": 47}, {"x": 3, "y": 47}]
          }
        ]
      }
    ],
    "expected_final_score": 88,
    "action_priority": ["add_thermal_vias", "add_gnd_zone"]
  }
}
```

#### 格式5: 元件选型 (component_select.jsonl)

```json
{
  "id": "comp_001",
  "instruction": "为5V转3.3V/500mA电源选择合适的LDO",
  "input": {
    "requirements": {
      "input_voltage": "5V",
      "output_voltage": "3.3V",
      "max_current": "500mA",
      "constraints": {
        "cost": "低",
        "footprint": "小型SMD",
        "manufacturer": "国内可采购"
      }
    }
  },
  "output": {
    "recommendations": [
      {
        "name": "AMS1117-3.3",
        "manufacturer": "高级/台康",
        "lcsc": "C6186",
        "footprint": "SOT-223",
        "price": "0.15元",
        "specs": {
          "vin_max": "15V",
          "vout": "3.3V",
          "iout_max": "1A",
          "dropout": "1.3V",
          "accuracy": "±1%"
        },
        "score": 95,
        "reason": "性价比高，电流裕量大，国内易采购"
      },
      {
        "name": "RT9193-33GB",
        "manufacturer": "立锜",
        "lcsc": "C117613",
        "footprint": "SOT-23-5",
        "price": "0.35元",
        "specs": {
          "vin_max": "5.5V",
          "vout": "3.3V",
          "iout_max": "300mA",
          "dropout": "0.35V",
          "accuracy": "±2%"
        },
        "score": 85,
        "reason": "低压差，体积小，但电流裕量小"
      }
    ],
    "selected": "AMS1117-3.3",
    "required_components": [
      {"type": "capacitor", "value": "10uF", "position": "input", "lcsc": "C15850"},
      {"type": "capacitor", "value": "22uF", "position": "output", "lcsc": "C45783"}
    ]
  }
}
```

---

## 四、数据规模要求

### 4.1 最小可行数据集 (MVP)

| 数据类型 | 最少数量 | 建议数量 | 来源 |
|----------|----------|----------|------|
| 原理图生成 | 500 | 2000 | 人工标注 |
| PCB布局 | 300 | 1000 | 人工标注 |
| 布线设计 | 200 | 500 | 人工标注 |
| 优化迭代 | 500 | 2000 | 自动生成+人工校验 |
| 元件选型 | 1000 | 5000 | LCSC数据+规则 |
| 领域知识 | 10000 | 50000 | 教材/数据手册 |

### 4.2 数据来源

```
数据来源优先级:
1. 人工标注 (质量最高，成本最高)
   - 内部工程师标注
   - 外包标注团队

2. 半自动生成 (质量中等，成本中等)
   - 模板+参数化生成
   - 规则系统+人工校验

3. 公开数据 (质量参差，成本低)
   - KiCad官方示例
   - 开源硬件项目(Arduino/ESP32等)
   - 数据手册自动提取

4. 合成数据 (需要严格质量过滤)
   - GPT-4生成 + 人工校验
   - 规则系统生成
```

---

## 五、接口定义

### 5.1 模型输入接口

```python
# 标准化输入格式
class ModelInput(BaseModel):
    task_type: str  # "schematic" | "placement" | "routing" | "optimization"
    instruction: str  # 自然语言指令
    context: Dict  # 上下文信息
    constraints: Dict  # 约束条件

# 示例调用
input_data = ModelInput(
    task_type="schematic",
    instruction="设计一个ESP32 WiFi模块的最小系统",
    context={
        "mcu": "ESP32-WROOM-32",
        "required_interfaces": ["WiFi", "UART", "GPIO"],
        "power": "3.3V"
    },
    constraints={
        "board_size": "40x30mm",
        "layers": 2,
        "cost_target": "30元"
    }
)
```

### 5.2 模型输出接口

```python
# 标准化输出格式
class ModelOutput(BaseModel):
    success: bool
    result: Dict  # 任务结果
    confidence: float  # 置信度
    explanation: str  # 设计解释
    alternatives: List[Dict]  # 备选方案

    # 质量预测
    predicted_score: float
    score_breakdown: Dict[str, float]
```

### 5.3 评估接口

```python
class EvaluationResult(BaseModel):
    # 自动评估
    syntax_valid: bool  # 语法正确
    drc_errors: int  # DRC错误数
    connectivity: float  # 连通性 (0-1)

    # 功能评估
    functionality_score: float  # 功能分数

    # 质量评估 (规则评分器)
    quality_score: float  # 总分
    dimensions: Dict[str, float]  # 各维度分数

    # 综合评价
    overall_score: float  # 综合分
    pass_rate: bool  # 是否达标
```

---

## 六、评估指标

### 6.1 模型能力评估

| 指标 | 计算方式 | 目标值 |
|------|----------|--------|
| **生成成功率** | 有效输出/总请求 | >95% |
| **语法正确率** | JSON解析成功/总输出 | >98% |
| **功能正确率** | DRC通过/总生成 | >80% |
| **平均质量分** | 规则评分器分数 | >75 |
| **达标率** | 分数>85的比例 | >50% |

### 6.2 业务价值评估

| 指标 | 当前基线 | 目标 | 计算方式 |
|------|----------|------|----------|
| 设计时间 | 4小时 | 30分钟 | 人工vsAI |
| 迭代次数 | 10次 | 3次 | 达到85分的迭代数 |
| 成功率 | 20% | 60% | 一次成功比例 |
| 成本节约 | 0 | 70% | 人力成本对比 |

### 6.3 评估流程

```
┌─────────────────────────────────────────────────────────────────┐
│                       评估流程                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 自动评估 (100%)                                               │
│     ├── JSON语法检查                                             │
│     ├── KiCad DRC检查                                            │
│     ├── 规则评分器打分                                            │
│     └── 连通性检查                                                │
│                                                                  │
│  2. 人工抽检 (10%)                                                │
│     ├── 设计合理性                                                │
│     ├── 可制造性                                                  │
│     └── 潜在问题                                                  │
│                                                                  │
│  3. 实际验证 (1%)                                                 │
│     ├── 打板测试                                                  │
│     ├── 功能验证                                                  │
│     └── 可靠性测试                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、训练配置

### 7.1 LoRA微调配置

```yaml
# 训练配置文件
model:
  name: "Qwen/Qwen2.5-7B-Instruct"
  max_length: 8192

lora:
  r: 64
  alpha: 128
  dropout: 0.05
  target_modules:
    - q_proj
    - k_proj
    - v_proj
    - o_proj
    - gate_proj
    - up_proj
    - down_proj

training:
  batch_size: 4
  gradient_accumulation: 4
  learning_rate: 2e-4
  epochs: 3
  warmup_ratio: 0.05
  lr_scheduler: "cosine"

optimization:
  optimizer: "adamw_torch"
  weight_decay: 0.01
  max_grad_norm: 1.0

# 预计训练时间: RTX 4090上约24小时
```

### 7.2 训练资源需求

| 配置项 | 最低配置 | 推荐配置 |
|--------|----------|----------|
| GPU | RTX 3090 (24GB) | A100 (40GB) |
| CPU | 16核 | 32核 |
| 内存 | 64GB | 128GB |
| 存储 | 500GB SSD | 1TB NVMe |
| 训练时间 | 48小时 | 24小时 |

---

## 八、里程碑规划

### Phase 1: 数据准备 (2-3周)

| 任务 | 时间 | 产出 |
|------|------|------|
| 数据格式定义 | 3天 | 本文档 |
| 数据采集脚本 | 5天 | 采集工具 |
| 模板库构建 | 7天 | 50+电路模板 |
| 人工标注 | 10天 | 1000+高质量样本 |

### Phase 2: 基础微调 (1-2周)

| 任务 | 时间 | 产出 |
|------|------|------|
| 环境搭建 | 2天 | 训练环境 |
| 数据预处理 | 3天 | 训练数据集 |
| 模型微调 | 5天 | 基础模型 |
| 评估测试 | 2天 | 评估报告 |

### Phase 3: 迭代优化 (2-4周)

| 任务 | 时间 | 产出 |
|------|------|------|
| 模型评估 | 3天 | 问题分析 |
| 数据增强 | 5天 | 扩展数据集 |
| 模型优化 | 7天 | 优化模型 |
| 集成测试 | 3天 | 端到端测试 |

### 目标时间线

```
Week 1-2:   数据准备 (模板+人工标注)
Week 3:     基础微调 + 初步评估
Week 4-5:   迭代优化 + 数据增强
Week 6:     最终评估 + 部署准备

关键里程碑:
- Week 2: 1000条训练数据就绪
- Week 3: 第一版模型完成 (目标>65分)
- Week 5: 优化版模型完成 (目标>75分)
- Week 6: 最终版模型完成 (目标>80分)
```

---

## 九、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 数据质量不足 | 高 | 高 | 多轮人工审核 + 自动质量过滤 |
| 模型过拟合 | 中 | 中 | 留出测试集 + 正则化 |
| 评分器不准 | 中 | 高 | 改进规则评分器 + 人工校验 |
| 训练资源不足 | 低 | 高 | 云GPU租用 + 模型量化 |
| 进度延期 | 中 | 中 | 分阶段交付 + 优先级管理 |

---

## 十、下一步行动

### 立即开始

1. **确认模型选择**: Qwen2.5-7B vs 14B
2. **准备GPU资源**: 购买/租用训练卡
3. **启动数据标注**: 内部团队 + 外包
4. **构建模板库**: 从常见电路开始

### 本周目标

- [ ] 确定10个核心电路模板
- [ ] 完成100条原理图生成样本
- [ ] 搭建训练环境
- [ ] 编写数据采集脚本

