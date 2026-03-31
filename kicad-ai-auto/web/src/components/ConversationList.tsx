/**
 * ConversationList - 对话历史列表组件
 *
 * 功能:
 * - 查看历史对话列表
 * - 搜索对话
 * - 加载对话到 AI 助手
 * - 删除对话
 */

import React, { useState, useEffect } from 'react';
import { conversationApi, Conversation, ChatMessage } from '../services/api';
import './ConversationList.css';

interface ConversationListProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadConversation: (conversationId: string, messages: ChatMessage[]) => void;
  currentConversationId?: string;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  isOpen,
  onClose,
  onLoadConversation,
  currentConversationId,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<Conversation[] | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadConversations();
    }
  }, [isOpen]);

  const loadConversations = async () => {
    setLoading(true);
    try {
      const response = await conversationApi.list();
      if (response.success && response.data?.conversations) {
        setConversations(response.data.conversations);
      }
    } catch (error) {
      console.error('加载对话列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      setSearchResults(null);
      return;
    }

    setLoading(true);
    try {
      const response = await conversationApi.search(searchKeyword);
      if (response.success && response.data?.conversations) {
        setSearchResults(response.data.conversations);
      }
    } catch (error) {
      console.error('搜索对话失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadConversation = async () => {
    if (!selectedConversation) return;

    try {
      const response = await conversationApi.get(selectedConversation.id);
      if (response.success && response.data?.messages) {
        onLoadConversation(selectedConversation.id, response.data.messages);
        onClose();
      }
    } catch (error) {
      console.error('加载对话详情失败:', error);
      alert('加载对话失败');
    }
  };

  const handleDeleteConversation = async (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();

    if (!confirm(`确定要删除对话 "${conv.title}" 吗？此操作不可恢复。`)) {
      return;
    }

    try {
      const response = await conversationApi.delete(conv.id);
      if (response.success) {
        setConversations(conversations.filter(c => c.id !== conv.id));
        if (selectedConversation?.id === conv.id) {
          setSelectedConversation(null);
        }
      }
    } catch (error) {
      console.error('删除对话失败:', error);
      alert('删除对话失败');
    }
  };

  const displayList = searchResults ?? conversations;

  if (!isOpen) return null;

  return (
    <div className="conversation-list" onClick={onClose}>
      <div className="conversation-list-content" onClick={e => e.stopPropagation()}>
        <div className="conversation-list-header">
          <h3>对话历史</h3>
          <button className="conversation-list-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="conversation-list-body">
          {/* Search */}
          <div className="conversation-search">
            <input
              type="text"
              placeholder="搜索对话..."
              value={searchKeyword}
              onChange={e => setSearchKeyword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
          </div>

          {/* Conversation List */}
          <div className="conversation-items">
            {loading ? (
              <div className="conversation-loading">加载中...</div>
            ) : displayList.length === 0 ? (
              <div className="conversation-empty">
                <div className="conversation-empty-icon">💬</div>
                <p>{searchResults ? '没有找到匹配的对话' : '暂无对话历史'}</p>
                <p style={{ fontSize: '12px' }}>
                  {searchResults
                    ? '尝试其他关键词'
                    : '开始与 AI 助手对话来创建历史记录'}
                </p>
              </div>
            ) : (
              displayList.map(conv => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    selectedConversation?.id === conv.id ? 'selected' : ''
                  } ${currentConversationId === conv.id ? 'current' : ''}`}
                  onClick={() => setSelectedConversation(conv)}
                >
                  <div className="conversation-item-header">
                    <span className="conversation-item-title">
                      {conv.title || '无标题对话'}
                    </span>
                    <span className="conversation-item-date">
                      {new Date(conv.updated_at).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                  <div className="conversation-item-meta">
                    <span className="conversation-item-info">
                      {conv.message_count} 条消息
                    </span>
                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                      <span className="conversation-item-model">{conv.model}</span>
                      <button
                        className="conversation-btn conversation-btn-danger"
                        style={{ padding: '2px 8px', fontSize: '12px' }}
                        onClick={e => handleDeleteConversation(conv, e)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="conversation-list-footer">
          <button
            className="conversation-btn conversation-btn-secondary"
            onClick={onClose}
          >
            取消
          </button>
          <button
            className="conversation-btn conversation-btn-primary"
            onClick={handleLoadConversation}
            disabled={!selectedConversation}
          >
            加载该对话
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConversationList;
