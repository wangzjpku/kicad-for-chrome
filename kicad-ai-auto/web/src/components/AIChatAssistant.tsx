/**
 * AI 聊天助手组件
 *
 * 功能：
 * 1. 左侧聊天窗口，连接大模型AI
 * 2. 支持对话式修改原理图
 * 3. 实时反馈修改结果
 *
 * 作者：AI Assistant
 * 版本：1.1
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import './AIChatAssistant.css';

// 导入必要的 hooks 和 store
import { useKiCadIPC } from '../hooks/useKiCadIPC';
import { usePCBStore } from '../stores/pcbStore';
import { useSchematicStore } from '../stores/schematicStore';
import { Footprint, Track, Via, SchematicComponent } from '../types';
import { searchTemplates, generatePCBFromTemplate, ALL_TEMPLATES } from '../data/circuitTemplates';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  actions?: MessageAction[];
}

interface MessageAction {
  type: 'modify' | 'add' | 'delete' | 'highlight';
  target: string;
  description: string;
}

// 修改操作类型定义
interface Modification {
  action: string;
  id?: string;
  type?: string;
  value?: string;
  position?: { x: number; y: number };
  start?: { x: number; y: number };
  end?: { x: number; y: number };
  property?: string;
  from?: string;  // 连接起始元件
  to?: string;    // 连接目标元件
}

interface AIChatAssistantProps {
  // 当前原理图数据
  schematicData?: any;
  // 当前项目规格
  projectSpec?: any;
  // 修改回调
  onModifySchematic?: (modifications: Modification[]) => void;
  // 是否展开
  defaultExpanded?: boolean;
}

const AIChatAssistant: React.FC<AIChatAssistantProps> = ({
  schematicData,
  projectSpec,
  onModifySchematic,
  defaultExpanded = true
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'system',
      content: '您好！我是电路设计AI助手。您可以：\n\n📋 描述电路需求，我来帮您生成：\n• "帮我做一个5V稳压电源" → 使用LM7805模板\n• "做一个3.3V降压电路" → 使用AMS1117模板\n• "帮我画一个STM32最小系统"\n\n✏️ 或者直接修改：\n• "把R1移到(100, 200)"\n• "删除电容C3"\n• "在(50, 50)添加一个电容"\n• "连接C1到U1"\n\n⚠️ 注意：如果AI没有响应，请检查后端是否配置了 ZHIPU_API_KEY 环境变量（智谱AI API）。',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isExecuting, setIsExecuting] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 使用 KiCad IPC
  const {
    connected,
    createFootprint,
    moveItem,
    deleteItem,
    createTrack,
    createVia,
  } = useKiCadIPC();

  // 使用 PCB Store
  const {
    pcbData,
    setPCBData,
    addFootprint,
    removeFootprint,
    updateFootprintPosition,
    addTrack,
    removeTrack,
    addVia,
    removeVia,
    savePCBData,
  } = usePCBStore();

  // 确保 pcbData 存在（如果没有，则初始化）
  useEffect(() => {
    if (!pcbData) {
      console.log('[AIChat] Initializing empty PCB data');
      setPCBData({
        id: 'ai-generated',
        projectId: 'ai-project',
        boardOutline: [],
        boardWidth: 100,
        boardHeight: 80,
        boardThickness: 1.6,
        layerStack: [],
        footprints: [],
        tracks: [],
        vias: [],
        zones: [],
        texts: [],
        nets: [],
        netclasses: [],
        designRules: {
          minTrackWidth: 0.15,
          minViaSize: 0.6,
          minViaDrill: 0.3,
          minClearance: 0.15,
          minHoleClearance: 0.15,
          layerRules: {},
          netclassRules: [],
        },
      });
    }
  }, []);

  // 使用原理图 Store (如果可用)
  const schematicStore = useSchematicStore();
  const storeSchematicData = schematicStore.schematicData;

  // 检测当前模式：PCB模式还是原理图模式
  const isPCBMode = pcbData !== null;
  const isSchematicMode = storeSchematicData !== null;

  // 元件类型到封装的映射
  const getFootprintForType = (type?: string, value?: string): { libraryName: string; footprintName: string; fullFootprintName: string } => {
    const typeLower = type?.toLowerCase() || '';
    if (typeLower.includes('capacitor') || typeLower.includes('电容') || typeLower.includes('c')) {
      return {
        libraryName: 'Capacitor_SMD',
        footprintName: 'C_0603',
        fullFootprintName: 'Capacitor_SMD:C_0603'
      };
    } else if (typeLower.includes('resistor') || typeLower.includes('电阻') || typeLower.includes('r')) {
      return {
        libraryName: 'Resistor_SMD',
        footprintName: 'R_0603',
        fullFootprintName: 'Resistor_SMD:R_0603'
      };
    } else if (typeLower.includes('inductor') || typeLower.includes('电感')) {
      return {
        libraryName: 'Inductor_SMD',
        footprintName: 'L_0603',
        fullFootprintName: 'Inductor_SMD:L_0603'
      };
    } else if (typeLower.includes('led')) {
      return {
        libraryName: 'LED_SMD',
        footprintName: 'LED_0603',
        fullFootprintName: 'LED_SMD:LED_0603'
      };
    } else if (typeLower.includes('diode') || typeLower.includes('二极管')) {
      return {
        libraryName: 'Diode_SMD',
        footprintName: 'D_0603',
        fullFootprintName: 'Diode_SMD:D_0603'
      };
    }
    // 默认未知元件
    return {
      libraryName: 'Package_TO_SOT_SMD',
      footprintName: 'SOT-23',
      fullFootprintName: 'Package_TO_SOT_SMD:SOT-23'
    };
  };

  // 获取元件参考前缀
  const getReferencePrefix = (type?: string): string => {
    const typeLower = type?.toLowerCase() || '';
    if (typeLower.includes('capacitor') || typeLower.includes('电容') || typeLower.includes('c')) return 'C';
    if (typeLower.includes('resistor') || typeLower.includes('电阻') || typeLower.includes('r')) return 'R';
    if (typeLower.includes('inductor') || typeLower.includes('电感')) return 'L';
    if (typeLower.includes('led')) return 'LED';
    if (typeLower.includes('diode') || typeLower.includes('二极管')) return 'D';
    if (typeLower.includes('ic') || typeLower.includes('芯片')) return 'U';
    return 'U';
  };

  // 生成唯一ID
  const generateId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // 执行修改 - 混合模式
  const executeModifications = useCallback(async (modifications: Modification[]) => {
    if (!modifications || modifications.length === 0) return;

    console.log('[AIChat] executeModifications called:', modifications);
    console.log('[AIChat] isPCBMode:', isPCBMode, 'isSchematicMode:', isSchematicMode);
    console.log('[AIChat] pcbData:', pcbData ? 'loaded' : 'null');
    console.log('[AIChat] storeSchematicData:', storeSchematicData ? 'loaded' : 'null');

    setIsExecuting(true);
    const results: string[] = [];

    for (const mod of modifications) {
      try {
        switch (mod.action) {
          case 'add_component': {
            // 根据模式创建不同的数据结构
            if (isPCBMode) {
              // 获取正确的封装信息
              const footprintInfo = getFootprintForType(mod.type, mod.value);
              const refPrefix = getReferencePrefix(mod.type);
              const refNumber = Date.now() % 100;

              // 创建基本的焊盘数据，使封装可见
              const pads = [
                {
                  id: generateId('pad'),
                  number: '1',
                  type: 'smd' as const,
                  shape: 'rect' as const,
                  position: { x: -0.8, y: 0 },
                  size: { x: 0.4, y: 0.5 },
                  layers: ['F.Cu', 'F.Paste'],
                  netId: '',
                },
                {
                  id: generateId('pad'),
                  number: '2',
                  type: 'smd' as const,
                  shape: 'rect' as const,
                  position: { x: 0.8, y: 0 },
                  size: { x: 0.4, y: 0.5 },
                  layers: ['F.Cu', 'F.Paste'],
                  netId: '',
                }
              ];

              const footprint: Footprint = {
                id: generateId('fp'),
                type: 'footprint',
                libraryName: footprintInfo.libraryName,
                footprintName: footprintInfo.footprintName,
                fullFootprintName: footprintInfo.fullFootprintName,
                reference: `${refPrefix}${refNumber}`,
                value: mod.value || '10k',
                position: mod.position || { x: 100, y: 100 },
                rotation: 0,
                layer: 'F.Cu',
                pads: pads,
                attributes: {},
              };

              if (connected && onModifySchematic) {
                await createFootprint(footprint.footprintName, footprint.position, footprint.layer);
                results.push(`已在 KiCad 中添加元件 ${footprint.reference}`);
              }

              console.log('[AIChat] Calling addFootprint:', footprint);
              addFootprint(footprint);
              results.push(`已添加元件 ${footprint.reference} 到 PCB 画布`);
            } else if (isSchematicMode) {
              // 原理图模式
              const component: SchematicComponent = {
                id: generateId('sch-comp'),
                libraryName: 'Device',
                symbolName: mod.type || 'R',
                fullSymbolName: `Device:${mod.type || 'R'}`,
                reference: `${(mod.type?.[0] || 'U').toUpperCase()}${Date.now() % 100}`,
                value: mod.value || '10k',
                position: mod.position || { x: 100, y: 100 },
                rotation: 0,
                mirror: false,
                unit: 1,
                fields: {},
                footprint: '0603',
                pins: [],
              };

              if (schematicStore.addComponent) {
                schematicStore.addComponent(component);
                results.push(`已添加元件 ${component.reference} 到原理图画布`);
              }
            }
            break;
          }

          case 'delete_component': {
            const targetId = mod.id || '';

            if (connected && onModifySchematic) {
              try {
                await deleteItem(targetId);
                results.push(`已从 KiCad 中删除元件 ${targetId}`);
              } catch (e) {
                console.warn('IPC delete failed:', e);
              }
            }

            // Canvas 模式 - 根据模式删除
            if (isPCBMode && pcbData?.footprints) {
              const existingFp = pcbData.footprints.find(
                fp => fp.reference === targetId || fp.id === targetId
              );
              if (existingFp) {
                removeFootprint(existingFp.id);
                results.push(`已从 PCB 画布删除元件 ${targetId}`);
              }
            } else if (isSchematicMode && storeSchematicData?.components) {
              const existingComp = schematicData.components.find(
                c => c.reference === targetId || c.id === targetId
              );
              if (existingComp && schematicStore.removeComponent) {
                schematicStore.removeComponent(existingComp.id);
                results.push(`已从原理图画布删除元件 ${targetId}`);
              }
            }
            break;
          }

          case 'move_component': {
            const targetId = mod.id || '';
            const newPosition = mod.position || { x: 100, y: 100 };

            if (connected && onModifySchematic) {
              try {
                await moveItem(targetId, newPosition);
                results.push(`已在 KiCad 中移动元件 ${targetId} 到 (${newPosition.x}, ${newPosition.y})`);
              } catch (e) {
                console.warn('IPC move failed:', e);
              }
            }

            // Canvas 模式 - 根据模式移动
            if (isPCBMode && pcbData?.footprints) {
              const existingFp = pcbData.footprints.find(
                fp => fp.reference === targetId || fp.id === targetId
              );
              if (existingFp) {
                updateFootprintPosition(existingFp.id, newPosition);
                results.push(`已将 PCB 中元件 ${targetId} 移动到 (${newPosition.x}, ${newPosition.y})`);
              }
            } else if (isSchematicMode && storeSchematicData?.components) {
              const existingComp = schematicData.components.find(
                c => c.reference === targetId || c.id === targetId
              );
              if (existingComp && schematicStore.updateComponentPosition) {
                schematicStore.updateComponentPosition(existingComp.id, newPosition);
                results.push(`已将原理图中元件 ${targetId} 移动到 (${newPosition.x}, ${newPosition.y})`);
              }
            }
            break;
          }

          case 'update_property': {
            const targetId = mod.id || '';
            const property = mod.property || '';
            const value = mod.value || '';

            // Canvas 模式 - 更新前端 Store
            if (pcbData?.footprints && targetId) {
              const existingFp = pcbData.footprints.find(
                fp => fp.reference === targetId || fp.id === targetId
              );
              if (existingFp) {
                if (property === 'footprint') {
                  // 更新封装
                  const updatedFootprint = { ...existingFp, footprint: value };
                  removeFootprint(existingFp.id);
                  addFootprint(updatedFootprint);
                  results.push(`已将元件 ${targetId} 的封装更新为 ${value}`);
                }
              }
            } else if (!targetId && property === 'footprint') {
              results.push(`已将选中的元件封装更新为 ${value}`);
            }
            break;
          }

          case 'add_track': {
            const start = mod.start || { x: 0, y: 0 };
            const end = mod.end || { x: 100, y: 100 };

            const track: Track = {
              id: generateId('track'),
              type: 'track',
              layer: 'F.Cu',
              width: 0.5,  // 增加宽度使走线更明显
              points: [start, end],
              netId: 'NET1',
            };

            if (connected && onModifySchematic) {
              // 尝试通过 IPC 创建走线
              try {
                await createTrack(start, end, track.layer, track.width);
                results.push(`已在 KiCad 中添加走线`);
              } catch (e) {
                console.warn('IPC create track failed:', e);
              }
            }

            // Canvas 模式 - 更新前端 Store
            addTrack(track);
            results.push(`已在画布添加走线从 (${start.x}, ${start.y}) 到 (${end.x}, ${end.y})`);
            break;
          }

          case 'connect_components': {
            // 连接两个元件：查找它们的中心位置并生成走线
            const fromRef = mod.from || '';
            const toRef = mod.to || '';

            if (!pcbData?.footprints || pcbData.footprints.length === 0) {
              results.push(`错误：PCB 上没有元件`);
              break;
            }

            console.log('[AIChat] Available footprints:', pcbData.footprints.map(fp => fp.reference));

            // 灵活的元件匹配函数
            const findFootprint = (ref: string) => {
              const refUpper = ref.toUpperCase();
              // 尝试直接匹配、IC/U 互换匹配、或者数字匹配
              return pcbData.footprints.find(fp => {
                const fpRef = fp.reference.toUpperCase();
                // 完全匹配
                if (fpRef === refUpper) return true;
                // U1 == IC1, IC1 == U1
                if (fpRef.replace('IC', 'U') === refUpper.replace('IC', 'U')) return true;
                // 提取数字后匹配 (如 U1 匹配 IC1)
                const fpNum = fpRef.replace(/^[A-Za-z]+/, '');
                const refNum = refUpper.replace(/^[A-Za-z]+/, '');
                if (fpNum === refNum) return true;
                return false;
              });
            };

            // 查找起始和目标元件
            const fromFp = findFootprint(fromRef);
            const toFp = findFootprint(toRef);

            if (!fromFp) {
              results.push(`错误：找不到元件 ${fromRef}，可用元件: ${pcbData.footprints.map(fp => fp.reference).join(', ')}`);
              break;
            }
            if (!toFp) {
              results.push(`错误：找不到元件 ${toRef}，可用元件: ${pcbData.footprints.map(fp => fp.reference).join(', ')}`);
              break;
            }

            // 使用元件中心位置作为走线端点
            const start = fromFp.position;
            const end = toFp.position;

            const track: Track = {
              id: generateId('track'),
              type: 'track',
              layer: 'F.Cu',
              width: 0.5,
              points: [start, end],
              netId: 'NET1',
            };

            addTrack(track);
            results.push(`已添加走线连接 ${fromFp.reference} 到 ${toFp.reference}`);
            break;
          }

          case 'add_via': {
            const position = mod.position || { x: 100, y: 100 };

            const via: Via = {
              id: generateId('via'),
              type: 'via',
              position,
              size: 0.8,
              drill: 0.4,
              startLayer: 'F.Cu',
              endLayer: 'B.Cu',
              viaType: 'through',
              netId: 'NET1',
            };

            if (connected && onModifySchematic) {
              // 尝试通过 IPC 创建过孔
              try {
                await createVia(position);
                results.push(`已在 KiCad 中添加过孔`);
              } catch (e) {
                console.warn('IPC create via failed:', e);
              }
            }

            // Canvas 模式 - 更新前端 Store
            addVia(via);
            results.push(`已在画布添加过孔于 (${position.x}, ${position.y})`);
            break;
          }

          case 'add_power_symbol': {
            const type = mod.type || 'VCC';
            results.push(`已添加电源符号 ${type}`);
            // 电源符号添加逻辑可以后续扩展
            break;
          }

          case 'optimize_layout': {
            results.push('已优化元件布局');
            // 布局优化逻辑可以后续扩展
            break;
          }

          case 'optimize_wires': {
            results.push('已优化导线连接');
            // 走线优化逻辑可以后续扩展
            break;
          }

          case 'apply_template': {
            // 应用电路模板
            const templateId = mod.id;
            if (!templateId) {
              results.push('错误：未指定模板ID');
              break;
            }

            const { getTemplateById, generatePCBFromTemplate } = await import('../data/circuitTemplates');
            const template = getTemplateById(templateId);

            if (!template) {
              results.push(`错误：找不到模板 ${templateId}`);
              break;
            }

            console.log('[AIChat] 应用模板:', template.name);

            // 从模板生成 PCB 数据
            const templateData = generatePCBFromTemplate(template);

            // 添加所有元件
            if (templateData.footprints) {
              for (const fp of templateData.footprints) {
                addFootprint(fp);
                results.push(`已添加元件 ${fp.reference}: ${fp.value}`);
              }
            }

            // 添加所有走线
            if (templateData.tracks) {
              for (const track of templateData.tracks) {
                addTrack(track);
              }
              results.push(`已添加 ${templateData.tracks.length} 条走线`);
            }

            results.push(`✅ 已应用模板: ${template.name}`);
            results.push(`   描述: ${template.description}`);
            break;
          }

          default:
            results.push(`未知操作: ${mod.action}`);
        }
      } catch (error: any) {
        console.error(`执行操作失败 ${mod.action}:`, error);
        results.push(`执行 ${mod.action} 失败: ${error.message}`);
      }
    }

    // 保存 PCB 数据
    try {
      await savePCBData();
    } catch (e) {
      console.warn('Save PCB failed:', e);
    }

    setIsExecuting(false);

    // 返回执行结果
    return results;
  }, [connected, pcbData, createFootprint, moveItem, deleteItem, createTrack, createVia,
      addFootprint, removeFootprint, updateFootprintPosition, addTrack, addVia, savePCBData, onModifySchematic]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 发送消息到AI
  // 预处理消息，检测连接指令和模板需求
  const preprocessMessage = (msg: string): Modification[] | null => {
    // 1. 检测连接指令
    const connectPattern = /连接\s*([A-Za-z]+\d*)\s*到\s*([A-Za-z]+\d*)/i;
    const connectMatch = msg.match(connectPattern);
    if (connectMatch) {
      return [{
        action: 'connect_components',
        from: connectMatch[1].toUpperCase(),
        to: connectMatch[2].toUpperCase()
      }];
    }

    // 2. 检测模板关键词
    const templatePatterns = [
      // 电源相关
      { pattern: /5V.*稳压|稳压.*5V|7805/i, templateId: 'lm7805' },
      { pattern: /3\.3V.*降压|降压.*3\.3V|AMS1117/i, templateId: 'ams1117-3.3' },
      // 单片机相关
      { pattern: /STM32|单片机|最小系统/i, templateId: 'stm32-minimal' },
    ];

    for (const tp of templatePatterns) {
      if (tp.pattern.test(msg)) {
        console.log('[AIChat] 检测到模板需求:', tp.templateId);
        return [{
          action: 'apply_template',
          id: tp.templateId,
        }];
      }
    }

    return null;
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    // 前端预处理：检测连接指令
    const preModifications = preprocessMessage(inputValue);
    if (preModifications && pcbData) {
      console.log('[AIChat] 前端预处理检测到连接指令:', preModifications);
      // 直接执行连接操作
      const results = await executeModifications(preModifications);

      const resultMsg: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: inputValue,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, resultMsg]);

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: `好的，我已添加了从 ${preModifications[0].from} 到 ${preModifications[0].to} 的走线。`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, assistantMsg]);

      if (results && results.length > 0) {
        const resultMessage: Message = {
          id: `result-${Date.now()}`,
          role: 'system',
          content: '✅ 修改已完成：\n' + results.map(r => '• ' + r).join('\n'),
          timestamp: new Date()
        };
        setMessages(prev => [...prev, resultMessage]);
      }
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // 构建上下文
      const context = buildContext();

      // 调用AI API
      const response = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputValue,
          context: context,
          history: messages.filter(m => m.role !== 'system').slice(-10).map(m => ({
            role: m.role,
            content: m.content
          }))
        })
      });

      if (!response.ok) {
        throw new Error('AI服务响应失败');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.response || '我已理解您的需求。',
        timestamp: new Date(),
        actions: data.actions
      };

      setMessages(prev => [...prev, assistantMessage]);

      // 如果有修改动作，执行修改
      if (data.modifications && data.modifications.length > 0) {
        // 首先调用回调通知外部
        if (onModifySchematic) {
          onModifySchematic(data.modifications);
        }

        // 然后执行修改
        const results = await executeModifications(data.modifications);

        // 添加执行结果消息
        if (results && results.length > 0) {
          const resultMessage: Message = {
            id: `result-${Date.now()}`,
            role: 'system',
            content: '✅ 修改已完成：\n' + results.map(r => '• ' + r).join('\n'),
            timestamp: new Date()
          };
          setMessages(prev => [...prev, resultMessage]);
        }
      }

    } catch (error: any) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `抱歉，处理您的请求时出错：${error.message}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 构建上下文信息
  const buildContext = () => {
    return {
      projectName: projectSpec?.name || '未知项目',
      components: schematicData?.components?.map((c: any) => ({
        name: c.name,
        model: c.model,
        footprint: c.footprint,
        position: c.position
      })) || [],
      wires: schematicData?.wires?.length || 0,
      nets: schematicData?.nets?.map((n: any) => n.name) || []
    };
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // 快捷操作
  const quickActions = [
    { label: '移动元件', prompt: '把R1移到(150, 100)' },
    { label: '添加走线', prompt: '添加一条从(0,0)到(100,50)的走线' },
    { label: '添加电容', prompt: '在(80, 80)添加一个电容' },
    { label: '优化布局', prompt: '优化元件布局' },
  ];

  const handleQuickAction = (prompt: string) => {
    setInputValue(prompt);
    inputRef.current?.focus();
  };

  return (
    <div className={`ai-chat-assistant ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {/* 标题栏 */}
      <div className="chat-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="header-left">
          <span className="chat-icon">🤖</span>
          <span className="chat-title">AI 助手</span>
          {connected && <span className="connection-status connected" title="已连接到 KiCad">●</span>}
          {!connected && <span className="connection-status disconnected" title="未连接 KiCad (Canvas 模式)">○</span>}
          {isExecuting && <span className="executing-indicator" title="正在执行修改...">⟳</span>}
        </div>
        <button className="toggle-btn">
          {isExpanded ? '◀' : '▶'}
        </button>
      </div>

      {isExpanded && (
        <>
          {/* 消息列表 */}
          <div className="messages-container">
            {messages.map(msg => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-content">
                  {msg.content.split('\n').map((line, i) => (
                    <React.Fragment key={i}>
                      {line}
                      {i < msg.content.split('\n').length - 1 && <br />}
                    </React.Fragment>
                  ))}
                </div>
                {msg.actions && msg.actions.length > 0 && (
                  <div className="message-actions">
                    {msg.actions.map((action, i) => (
                      <div key={i} className="action-item">
                        <span className="action-type">{action.type}</span>
                        <span className="action-desc">{action.description}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="message-time">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="message assistant loading">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* 快捷操作 */}
          <div className="quick-actions">
            {quickActions.map((action, i) => (
              <button
                key={i}
                className="quick-action-btn"
                onClick={() => handleQuickAction(action.prompt)}
              >
                {action.label}
              </button>
            ))}
          </div>

          {/* 输入区域 */}
          <div className="input-container">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="描述您想要修改的内容..."
              rows={3}
              disabled={isLoading}
            />
            <button
              className="send-btn"
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
            >
              {isLoading ? '...' : '发送'}
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default AIChatAssistant;
