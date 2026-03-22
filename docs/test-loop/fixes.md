# Fixes Log

<!-- Append fixes here -->

## FIX-20260322-001: 原理图导线未生成
- 问题ID: ISS-20260322-001, ISS-20260322-004
- 修复文件: `kicad-ai-auto/web/src/components/AIChatAssistant.tsx`
- 修复位置: `apply_template` case (约641-677行)
- 修复内容: 在生成schematic符号后，添加从template.nets提取连接信息生成Wire对象并调用`schematicStore.addWire()`的逻辑
- 验证: API确认schematic wires=5, netIds=[VIN, GND, GND, GND, VOUT]

## FIX-20260322-002: 空输入重复提交模板
- 问题ID: ISS-20260322-005
- 修复文件: `kicad-ai-auto/web/src/components/AIChatAssistant.tsx`
- 修复位置: `apply_template` case (约667-671行)
- 修复内容: 在模板应用成功后调用`setInputValue('')`清空输入框
- 验证: 重现测试：点击发送后输入框应保持清空状态

## FIX-20260322-003: PCB保存时机竞态条件
- 问题ID: ISS-20260322-006
- 修复文件: `kicad-ai-auto/web/src/components/AIChatAssistant.tsx`
- 修复位置: `executeModifications` (约684-690行)
- 修复内容: 在savePCBData()前添加`await new Promise(resolve => setTimeout(resolve, 0))`确保React状态更新完成
- 验证: T4和T5测试确认PCB footprints正确保存 (PCB 7/8和5/7)

## FIX-20260322-005: validate_name strip()顺序安全问题
- 问题ID: ISS-B06-001
- 修复文件: `kicad-ai-auto/agent/routes/project_routes.py`
- 修复位置: `ProjectCreate.validate_name` (约676-690行)
- 修复内容: 调整验证顺序，禁止字符检查在trim之前，防止`" <script> "`通过trim绕过检查
- 验证: `<script>` 即使包裹空格也被422拒绝，正常名称自动trim存储 ✅


## FIX-20260322-004: 模板匹配优先级错误
- 问题ID: ISS-20260322-007
- 修复文件: `kicad-ai-auto/web/src/components/AIChatAssistant.tsx`
- 修复位置: `preprocessMessage` 中的 `templatePatterns` 数组
- 修复内容: 将精确芯片型号模式（ESP32, STM32）放在通用关键词（最小系统）之前，防止误匹配
- 验证: 需要重新测试T4（ESP32）以确认正确匹配esp32-minimal模板

