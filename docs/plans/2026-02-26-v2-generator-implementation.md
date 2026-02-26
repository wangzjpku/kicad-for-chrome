# V2生成器实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 启用kicad-sch-api V2生成器，移除原理图生成中的引脚硬编码问题

**Architecture:** 通过V2生成器使用kicad-sch-api官方库自动获取元件引脚位置，替代V1中的SYMBOL_PIN_POSITIONS硬编码

**Tech Stack:** kicad-sch-api, kipy, pytest

---

## Task 1: 验证V2库可用性

**Files:**
- Test: 直接在Python中验证

**Step 1: 验证kipy导入**

```bash
cd E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\agent
./venv/Scripts/python.exe -c "import kipy; print('kipy OK')"
```

Expected: 输出 "kipy OK"

**Step 2: 验证kicad-sch-api导入**

```bash
cd E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\agent
./venv/Scripts/python.exe -c "import kicad_sch_api; print('kicad_sch_api OK')"
```

Expected: 输出 "kicad_sch_api OK"

**Step 3: 检查is_v2_available函数**

```bash
cd E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\agent
./venv/Scripts/python.exe -c "from generators.schematic_v2 import is_v2_available; print('V2 available:', is_v2_available())"
```

Expected: 输出 "V2 available: True"

---

## Task 2: 创建V2生成器单元测试

**Files:**
- Create: `agent/tests/test_schematic_v2.py`

**Step 1: 写入测试文件**

```python
"""
原理图生成器V2单元测试
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generators.schematic_v2 import SchematicGeneratorV2, is_v2_available


class TestV2Availability:
    """测试V2生成器可用性"""

    def test_v2_is_available(self):
        """V2生成器应该可用"""
        assert is_v2_available() == True

    def test_v2_generator_can_be_instantiated(self):
        """V2生成器可以实例化"""
        gen = SchematicGeneratorV2()
        assert gen.version.value == "v2"


class TestV2Generation:
    """测试V2生成功能"""

    def test_generate_simple_schematic(self):
        """测试生成简单原理图"""
        gen = SchematicGeneratorV2()

        # 简单测试数据
        json_data = {
            "title": "Test Circuit",
            "components": [
                {
                    "reference": "R1",
                    "symbol_library": "Device:R",
                    "name": "Resistor",
                    "value": "10k",
                    "position": {"x": 100, "y": 100},
                    "pins": [
                        {"number": "1", "name": "1", "type": "passive"},
                        {"number": "2", "name": "2", "type": "passive"}
                    ]
                }
            ],
            "nets": [],
            "wires": [],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            assert result.success == True
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_v2_loads_symbol_from_library(self):
        """测试从符号库加载元件"""
        gen = SchematicGeneratorV2()

        # 测试数据 - 包含完整引脚信息
        json_data = {
            "title": "Test",
            "components": [
                {
                    "reference": "U1",
                    "symbol_library": "MCU_Raspberry_Pi:RP2040",
                    "name": "RP2040",
                    "value": "RP2040",
                    "position": {"x": 0, "y": 0},
                    "pins": []
                }
            ],
            "nets": [],
            "wires": [],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            # 验证生成成功
            assert result.success == True
        finally:
            Path(output_path).unlink(missing_ok=True)
```

**Step 2: 运行测试验证失败**

```bash
cd E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\agent
./venv/Scripts/python.exe -m pytest tests/test_schematic_v2.py -v
```

Expected: 测试应该通过（如果V2库正常工作）

---

## Task 3: 验证V2路由集成

**Files:**
- Modify: `agent/routes/ai_design_routes.py`

**Step 1: 检查当前路由实现**

查看 `agent/routes/ai_design_routes.py` 中的 `/api/ai/generators` 端点，确认返回V2可用状态

**Step 2: 检查创建电路时是否使用V2**

```bash
grep -n "generate" agent/routes/ai_design_routes.py | head -20
```

查找实际调用生成器的代码位置

---

## Task 4: 端到端测试

**Files:**
- Modify: 使用现有E2E测试或手动测试

**Step 1: 启动后端服务**

```bash
cd E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\agent
./venv/Scripts/python.exe main.py
```

**Step 2: 测试API端点**

```bash
curl http://localhost:8000/api/ai/generators
```

Expected: 返回包含 "v2_available": true 的JSON

**Step 3: 测试创建电路**

发送创建电路请求，验证使用V2生成

---

## Task 5: 验证引脚位置不再硬编码（可选）

**Files:**
- 检查: `agent/kicad_schematic_generator.py`

**Step 1: 确认V1仍使用硬编码**

```bash
grep -n "SYMBOL_PIN_POSITIONS" agent/kicad_schematic_generator.py
```

Expected: 仍存在（V1保留用于向后兼容）

**Step 2: 确认新请求使用V2**

在路由中添加逻辑，确保新请求使用V2生成器

---

## 验证检查点

完成所有任务后，运行以下命令验证：

```bash
# 1. V2库可用
./venv/Scripts/python.exe -c "from generators.schematic_v2 import is_v2_available; assert is_v2_available()"

# 2. V2测试通过
./venv/Scripts/python.exe -m pytest tests/test_schematic_v2.py -v

# 3. API返回V2可用
curl http://localhost:8000/api/ai/generators | grep "v2_available"
```

---

## 预期结果

- [x] Task 1: V2库已安装并可用
- [ ] Task 2: 创建V2单元测试
- [ ] Task 3: 验证路由集成
- [ ] Task 4: 端到端测试
- [ ] Task 5: 验证硬编码问题解决

**成功标准:** 新创建的电路使用V2生成器，不再依赖SYMBOL_PIN_POSITIONS硬编码
