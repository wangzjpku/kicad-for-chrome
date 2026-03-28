# 嘉立创开源项目测试方案

基于图像识别和浏览器自动化的测试方案，使用真实的嘉立创开源KiCad项目作为测试案例。

## 测试架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      测试框架 (Pytest)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │  案例1: 元件库   │  │  案例2: DRC验证  │  │ 案例3: 导出流程 │ │
│  │  加载测试       │  │  测试           │  │ 测试           │ │
│  └────────┬────────┘  └────────┬────────┘  └───────┬────────┘ │
│           │                   │                    │           │
│           ▼                   ▼                    ▼           │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              图像识别引擎 (OpenCV)                        │  │
│  │  • 模板匹配    • 边缘检测    • 轮廓分析    • 直方图对比  │  │
│  └────────────────────────────┬────────────────────────────┘  │
│                               │                               │
│                               ▼                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           浏览器自动化 (Playwright)                      │  │
│  │  • 页面导航  • 元素交互  • 截图采集  • 状态验证         │  │
│  └────────────────────────────┬────────────────────────────┘  │
│                               │                               │
│                               ▼                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           待测系统: KiCad AI Automation                  │  │
│  │  • 前端 (React): http://localhost:3000                  │  │
│  │  • 后端 (FastAPI): http://localhost:8000                 │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 测试案例详情

### 案例1: JLCPCB元件库加载测试

**目标项目**: CDFER/JLCPCB-Kicad-Library

**测试目标**:
- 验证系统能正确加载JLCPCB元件库
- 验证AI能生成包含JLC元件的原理图
- 验证原理图渲染正确性

**测试步骤**:
1. 打开AI对话对话框
2. 输入需求: "创建一个简单的电源电路，使用JLCPCB库中的AMS1117-3.3稳压芯片"
3. 提交给AI生成
4. 等待生成完成
5. 截图验证原理图内容
6. 图像分析检测原理图元素

**验证指标**:
- 原理图成功生成
- 包含预期元件（稳压芯片、电容等）
- 渲染无明显错误

### 案例2: DRC规则验证测试

**目标项目**: tinfever/KiCAD-Custom-DRC-Rules-for-JLCPCB

**测试目标**:
- 验证JLCPCB 4层板DRC规则正确加载
- 验证DRC检查功能正常工作
- 验证错误检测和报告

**测试步骤**:
1. 打开一个有潜在DRC问题的PCB
2. 打开AI对话框
3. 输入: "检查当前PCB的DRC错误，确保符合JLCPCB 4层板规则"
4. 提交给AI分析
5. 等待分析完成
6. 检查错误报告

**验证指标**:
- DRC检查完成
- 正确识别DRC错误
- 错误信息清晰可读

### 案例3: 导出工作流测试

**测试目标**:
- 验证Gerber导出功能
- 验证BOM导出功能
- 验证坐标文件导出功能

**测试步骤**:
1. 打开一个PCB设计
2. 打开AI对话框
3. 输入: "导出Gerber文件、BOM和坐标文件，用于JLCPCB贴片"
4. 提交导出请求
5. 等待导出完成
6. 检查输出文件

**验证指标**:
- 导出成功完成
- 文件数量正确
- 文件格式正确

## 图像识别技术

### 使用的OpenCV技术

| 技术 | 用途 |
|------|------|
| 模板匹配 | 查找UI按钮、图标 |
| Canny边缘检测 | 检测PCB走线、元件边界 |
| 轮廓检测 | 识别元件、焊盘 |
| 直方图对比 | 比较渲染结果相似度 |
| 形态学操作 | 去除噪声、增强特征 |

### 视觉验证流程

```python
# 1. 截图当前状态
screenshot = await page.screenshot()

# 2. 加载为OpenCV图像
img = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)

# 3. 检测边缘
edges = cv2.Canny(gray, 50, 150)

# 4. 查找轮廓
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 5. 分析元素
for cnt in contours:
    area = cv2.contourArea(cnt)
    # 判断是否为元件、走线等
```

## 运行测试

### 前置条件

1. 启动后端服务:
```bash
cd kicad-ai-auto/agent
./venv/Scripts/python.exe main.py
```

2. 启动前端服务:
```bash
cd kicad-ai-auto/web
npm run dev
```

3. 安装依赖:
```bash
pip install opencv-python pillow numpy
playwright install chromium
```

### 运行所有测试

```bash
cd kicad-ai-auto/playwright-tests
pytest test_jlc_open_source.py -v
```

### 运行单个测试

```bash
pytest test_jlc_open_source.py::test_jlc_library_loading -v
```

### 生成HTML报告

```bash
pytest test_jlc_open_source.py -v --html=report.html --self-contained-html
```

## 测试输出

### 目录结构

```
playwright-tests/
├── test_outputs/
│   └── jlc_tests/
│       ├── screenshots/
│       │   ├── test_case_1_library_loading_result.png
│       │   ├── test_case_1_library_loading_error.png
│       │   ├── test_case_2_drc_validation_result.png
│       │   └── ...
│       └── test_report.json
└── test_jlc_open_source.py
```

### 测试报告示例

```json
{
  "test_date": "2026-03-10",
  "total_tests": 3,
  "passed": 2,
  "failed": 1,
  "results": [
    {
      "test_name": "test_case_1_library_loading",
      "passed": true,
      "duration_ms": 45000,
      "metrics": {
        "elements_detected": {...},
        "image_size": [1080, 1920]
      }
    }
  ]
}
```

## 扩展测试

### 添加新测试案例

```python
async def test_case_4_your_feature(self) -> TestResult:
    """测试案例4: 新功能测试"""
    test_name = "test_case_4_your_feature"
    # 实现测试逻辑...
    return TestResult(test_name=test_name, passed=True)
```

### 视觉回归测试

```python
async def test_visual_regression():
    """视觉回归测试 - 对比基准图像"""
    # 1. 加载基准图像
    baseline = cv2.imread("baseline/schematic.png")

    # 2. 截图当前状态
    current = await capture_screenshot()

    # 3. 对比差异
    result = ImageAnalyzer.compare_images(baseline, current, "diff.png")

    # 4. 验证相似度
    assert result.similarity > 0.95, f"相似度不足: {result.similarity}"
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 测试框架 | Pytest |
| 浏览器自动化 | Playwright |
| 图像识别 | OpenCV |
| 图像处理 | Pillow, NumPy |
| 异步支持 | asyncio |

## 注意事项

1. **图像识别依赖**: 确保OpenCV正确安装
2. **浏览器驱动**: Playwright会自动下载 Chromium
3. **服务依赖**: 需要先启动前后端服务
4. **超时设置**: 复杂操作可能需要较长超时时间
