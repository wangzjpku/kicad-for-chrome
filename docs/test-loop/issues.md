# Issues Log

## [ROUND-1] [T1-AMS1117] [SEVERITY: HIGH]
- 问题ID: ISS-20260322-001
- 场景: T1-AMS1117-3.3V-LDO
- 问题描述: AI声称添加了5条走线，但实际数据库中wires数组为空
- 预期: 应有5条wire记录（VIN→C1→U1_VIN, GND→C1, GND→C2, U1_VOUT→C2, 输出网络）
- 实际: wires: [], networks: []，导线计数显示0条
- 截图/证据: round1_T1_07_schematic_view.png, API返回wires=0
- 建议修复: 检查apply_template中saveSchematicData是否正确写入wire数据
- **状态: FIXED** - 在AIChatAssistant.tsx的apply_template case中添加了wire生成逻辑，从template.nets提取连接信息生成Wire对象并调用schematicStore.addWire()

## [ROUND-1] [T1-AMS1117] [SEVERITY: MEDIUM]
- 问题ID: ISS-20260322-002
- 场景: T1-AMS1117-3.3V-LDO
- 问题描述: 电容数量不足，需求要求"输入输出滤波电容"（通常10uF+0.1uF并联），只添加了1个输入电容和1个输出电容
- 预期: 4个电容（输入10uF + 输入0.1uF + 输出10uF + 输出0.1uF）或至少标注具体容值
- 实际: 只有C1（输入电容）和C2（输出电容），无具体容值标注
- 截图/证据: API返回 C1|输入电容, C2|输出电容
- 建议修复: 模板应添加具体容值，或区分大电容和小电容
- **状态: KNOWN LIMITATION** - 当前模板只有基础电容设计，不影响基本功能

## [ROUND-1] [T1-AMS1117] [SEVERITY: MEDIUM]
- 问题ID: ISS-20260322-003
- 场景: T1-AMS1117-3.3V-LDO
- 问题描述: 无网络连接信息，电路功能不完整
- 预期: 应有3-5个命名网络（VIN, GND, VOUT, NET_C1, NET_C2）
- 实际: networks数组为空
- 截图/证据: API返回networks=0
- 建议修复: 检查saveSchematicData是否正确生成networks数据
- **状态: PARTIALLY FIXED** - wires现在包含netId，networks数组仍为空但不影响功能

## [ROUND-1] [T1-AMS1117] [SEVERITY: MEDIUM]
- 问题ID: ISS-20260322-004
- 场景: T1-AMS1117-3.3V-LDO
- 问题描述: PCB数据正确（有3个封装、5条走线）但schematic数据wires/networks为空
- 预期: 原理图和PCB应有对应的连接关系
- 实际: PCB tracks=5, schematic wires=0, networks=0
- 截图/证据: API验证
- 建议修复: apply_template时统一保存到schematic和pcb
- **状态: FIXED** - 通过修复ISS-20260322-001解决

## [ROUND-1] [T2-CH340C] [SEVERITY: MEDIUM]
- 问题ID: ISS-20260322-005
- 场景: T2-CH340C-USB-UART
- 问题描述: 空输入提交后点击发送按钮会重复应用上一个模板，inputValue未在提交后清空
- 预期: 提交后inputValue应清空，防止重复提交
- 实际: inputValue保持原值，焦点在输入框时按回车或点击发送会再次触发同一模板
- 截图/证据: 在T2测试中，关闭对话框后点击发送导致CH340C模板被应用两次（6→12个元件）
- 建议修复: 在apply_template成功后调用setInputValue('')
- **状态: FIXED** - 在apply_template case中添加setInputValue('')调用。Round2 T1验证: 提交后输入框清空，发送按钮disabled
## [BOUNDARY] [B01] [SEVERITY: MEDIUM]
- 问题ID: ISS-B01-001
- 场景: B01-超长/特殊字符输入
- 问题描述: 项目名创建时未过滤特殊字符 `/\:*?"<>|`，允许危险字符存入数据库
- 预期: 应拒绝包含Windows文件名禁止字符的项目名
- 实际: 项目"测试项目/abc:def*ghi?jkl\"mno|pqr"成功创建并持久化
- 截图/证据: B01_01_special_chars_input.png, API返回201
- 建议修复: 在ProjectCreate模型中添加field_validator过滤 `/\:*?"<>|` 字符
- **状态: FIXED** - Round 2验证: 输入`测试:abc*def?ghi`后端返回HTTP 422，特殊字符`\ / : * ? " < > |`全部被拒绝。前端显示"Failed to create project"。正常项目名创建不受影响。

## [ROUND-2] [B06] [SEVERITY: LOW]
- 问题ID: ISS-B06-001
- 场景: B06-前后空格边界
- 问题描述: validate_name中 `v.strip()` 在 `invalid_chars.search(v)` 之前执行，导致先trim后检查
- 预期: 应先检查禁止字符再trim，防止trim绕过安全检查
- 实际: `"  <script>alert(1)</script>  "` → strip后仍含<> → 被拒绝(巧合正确)
- 建议修复: 调整验证器顺序: 1)空检查 2)禁止字符检查 3)长度检查 4)trim
- **状态: FIXED** - 调整validate_name顺序：1)禁止字符检查 2)trim 3)空检查 4)长度检查 5)返回。修复后禁止字符即使被空格包裹也能被检测到（`<script>` → 422）

## [ROUND-N] [SCENARIO-TX] [SEVERITY: HIGH/MEDIUM/LOW]
- 问题ID: ISS-YYYYMMDD-NNN
- 场景: T1/T2/...
- 问题描述: [具体描述]
- 预期: [期望的行为]
- 实际: [实际观察到的]
- 截图/证据: [说明]
- 建议修复: [具体的修复建议]
-->

## [ROUND-1] [T3-NE555] [SEVERITY: HIGH]
- 问题ID: ISS-20260322-006
- 场景: T3-NE555-Oscillator
- 问题描述: PCB footprints未被持久化，AutoSave在模板修改完成前捕获了空状态并覆盖了正确数据
- 预期: 6个footprints (U1/NE555, R1/R2/上拉/定时电阻, C1/C2/电容, J1/电源接口)
- 实际: pcb_data.json中只有1个footprint (被测试curl覆盖后的状态)
- 截图/证据: Browser logs显示addFootprint 6次完成, STAGE RENDER显示footprints=6, 但pcb_data.json只有1个
- 根本原因: AutoSave的useEffect在模板修改的setState完成前触发，捕获了空的pcbData.footprints
- 建议修复: 在executeModifications完成后调用savePCBData，或在savePCBData中添加重试机制
- **状态: FIXED** - 在AIChatAssistant.tsx的executeModifications中添加`setTimeout(0)`延迟确保React状态更新完成后再保存PCB。Round2验证: T1 AMS1117(3 footprints+5 tracks), T4 ESP32(6 footprints+7 tracks)均正确保存

## [ROUND-1] [T4-ESP32] [SEVERITY: MEDIUM]
- 问题ID: ISS-20260322-007
- 场景: T4-ESP32-MinSys
- 问题描述: 模板匹配错误，输入ESP32需求但应用了STM32模板
- 预期: 应匹配esp32最小系统模板
- 实际: 匹配到stm32-minimal模板，生成STM32F103C8T6系统而非ESP32
- 截图/证据: AI响应"已应用模板: STM32 最小系统"而非ESP32模板
- 根本原因: preprocessMessage中regex优先级问题，"最小系统"关键词优先于"ESP32"关键词
- 建议修复: 调整模板匹配优先级，精确芯片型号优先于通用关键词
- **状态: FIXED** - 在templatePatterns中将ESP32模式移到"最小系统"模式之前。Round2验证: T4-ESP32-Round2正确匹配esp32-minimal模板（AI日志确认: 检测到模板需求: esp32-minimal），生成ESP32-WROOM-32组件
- **状态: FIXED** - 在templatePatterns中将ESP32模式移到"最小系统"模式之前
