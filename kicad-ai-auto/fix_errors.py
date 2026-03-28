# -*- coding: utf-8 -*-
import re

# 修复 pcbStore.ts
pcb_file = 'E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-ai-auto/web/src/stores/pcbStore.ts'
with open(pcb_file, 'r', encoding='utf-8') as f:
    content = f.read()

old_pcb = '''        } catch (error) {
          console.error('[PCBStore] Load PCB error:', error);
          set({ error: 'Network error', isLoading: false });
        }'''

new_pcb = '''        } catch (error) {
          // 忽略请求被取消的错误（快速切换页面时发生）
          if (error instanceof Error && error.name === 'CanceledError') {
            console.log('[PCBStore] PCB load cancelled (page navigation)');
          } else {
            console.error('[PCBStore] Load PCB error:', error);
          }
          set({ error: null, isLoading: false });
        }'''

if old_pcb in content:
    content = content.replace(old_pcb, new_pcb)
    with open(pcb_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed pcbStore.ts')
else:
    print('pcbStore.ts pattern not found')

# 修复 schematicStore.ts
sch_file = 'E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-ai-auto/web/src/stores/schematicStore.ts'
with open(sch_file, 'r', encoding='utf-8') as f:
    content = f.read()

old_sch = "console.error('Failed to load schematic data:', error);"
new_sch = """// 忽略请求被取消的错误（快速切换页面时发生）
          if (error instanceof Error && error.name !== 'CanceledError') {
            console.error('Failed to load schematic data:', error);
          }"""

if old_sch in content:
    content = content.replace(old_sch, new_sch)
    with open(sch_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed schematicStore.ts')
else:
    print('schematicStore.ts pattern not found')
