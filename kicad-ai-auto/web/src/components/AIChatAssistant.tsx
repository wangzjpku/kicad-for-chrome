/**
 * AI 聊天助手组件
 *
 * 功能：
 * 1. 左侧聊天窗口，连接大模型AI
 * 2. 支持对话式修改原理图
 * 3. 实时反馈修改结果
 *
 * 作者：AI Assistant
 * 版本：1.0
 */

import React, { useState, useRef, useEffect } from 'react';
import './AIChatAssistant.css';

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

interface AIChatAssistantProps {
  // 当前原理图数据
  schematicData?: any;
  // 当前项目规格
  projectSpec?: any;
  // 修改回调
  onModifySchematic?: (modifications: any) => void;
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
      content: '您好！我是电路设计AI助手。如果您发现原理图有任何问题，请直接告诉我，我会帮您修改。\n\n例如：\n• "电源符号应该在上方"\n• "这个电阻值太大了，改成10k"\n• "添加一个去耦电容"\n• "导线交叉了，请调整"',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 发送消息到AI
  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

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
      if (data.modifications && onModifySchematic) {
        onModifySchematic(data.modifications);
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
    { label: '检查封装', prompt: '请检查所有元器件的封装是否正确' },
    { label: '优化布局', prompt: '请优化元件布局，减少交叉线' },
    { label: '添加电源符号', prompt: '请添加标准的VCC和GND电源符号' },
    { label: '检查ERC', prompt: '请检查原理图的电气规则' },
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
