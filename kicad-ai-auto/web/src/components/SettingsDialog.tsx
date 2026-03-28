/**
 * 设置对话框 - 用户设置、Token管理、消费记录
 */

import React, { useState, useEffect } from 'react';
import { useAuthStore, authApi } from '../stores/authStore';

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

// 主题
const THEME = {
  bg: { primary: '#323232', secondary: '#3d3d3d', tertiary: '#454545' },
  text: { primary: '#e0e0e0', secondary: '#a0a0a0', muted: '#707070' },
  accent: { primary: '#4a9eff', success: '#4caf50', warning: '#ff9800', error: '#f44336' },
  border: { default: '#4a4a4a' },
};

type TabType = 'profile' | 'token' | 'logs';

export default function SettingsDialog({ isOpen, onClose }: SettingsDialogProps) {
  const { user, token, updateBalance } = useAuthStore();
  const [activeTab, setActiveTab] = useState<TabType>('profile');
  const [logs, setLogs] = useState<any[]>([]);
  const [modelInfo, setModelInfo] = useState<any>(null);
  const [topupAmount, setTopupAmount] = useState('');
  const [topupLoading, setTopupLoading] = useState(false);
  const [topupMsg, setTopupMsg] = useState('');

  useEffect(() => {
    if (isOpen && token) {
      loadData();
    }
  }, [isOpen, token]);

  const loadData = async () => {
    if (!token) return;
    try {
      const [logsData, info] = await Promise.all([
        authApi.getLogs(token),
        authApi.getModelInfo(token),
      ]);
      setLogs(logsData);
      setModelInfo(info);
    } catch (e) {
      console.error('Failed to load data:', e);
    }
  };

  const handleTopup = async () => {
    if (!token || !topupAmount) return;
    const amount = parseInt(topupAmount);
    if (isNaN(amount) || amount <= 0) {
      setTopupMsg('请输入有效的充值数量');
      return;
    }

    setTopupLoading(true);
    setTopupMsg('');
    try {
      const result = await authApi.topup(token, amount);
      updateBalance(result.new_balance);
      setTopupMsg(`充值成功！当前余额: ${result.new_balance}`);
      setTopupAmount('');
      loadData();
    } catch (e: any) {
      setTopupMsg(e.message || '充值失败');
    } finally {
      setTopupLoading(false);
    }
  };

  if (!isOpen) return null;

  const tabs = [
    { id: 'profile' as TabType, label: '👤 账户信息' },
    { id: 'token' as TabType, label: '💰 Token管理' },
    { id: 'logs' as TabType, label: '📋 消费记录' },
  ];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
    }} onClick={onClose}>
      <div style={{
        backgroundColor: THEME.bg.secondary,
        borderRadius: 8,
        width: 600,
        maxHeight: '80vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      }} onClick={(e) => e.stopPropagation()}>
        {/* 标题栏 */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: `1px solid ${THEME.border.default}`,
        }}>
          <h2 style={{ margin: 0, color: THEME.text.primary, fontSize: 18 }}>
            ⚙️ 设置
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: THEME.text.muted,
              fontSize: 24,
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Tab 切换 */}
        <div style={{
          display: 'flex',
          borderBottom: `1px solid ${THEME.border.default}`,
        }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                padding: '12px',
                backgroundColor: activeTab === tab.id ? THEME.bg.tertiary : 'transparent',
                border: 'none',
                borderBottom: activeTab === tab.id ? `2px solid ${THEME.accent.primary}` : 'none',
                color: activeTab === tab.id ? THEME.text.primary : THEME.text.muted,
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 内容区域 */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {/* 账户信息 Tab */}
          {activeTab === 'profile' && (
            <div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '100px 1fr',
                gap: 12,
                marginBottom: 20,
              }}>
                <div style={{ color: THEME.text.muted, fontSize: 13 }}>用户名:</div>
                <div style={{ color: THEME.text.primary, fontSize: 13 }}>{user?.username}</div>

                <div style={{ color: THEME.text.muted, fontSize: 13 }}>邮箱:</div>
                <div style={{ color: THEME.text.primary, fontSize: 13 }}>{user?.email}</div>

                <div style={{ color: THEME.text.muted, fontSize: 13 }}>注册时间:</div>
                <div style={{ color: THEME.text.primary, fontSize: 13 }}>
                  {user?.created_at ? new Date(user.created_at).toLocaleString('zh-CN') : '-'}
                </div>

                <div style={{ color: THEME.text.muted, fontSize: 13 }}>账户类型:</div>
                <div style={{ fontSize: 13 }}>
                  {user?.is_admin ? (
                    <span style={{ color: THEME.accent.warning }}>管理员</span>
                  ) : (
                    <span style={{ color: THEME.text.secondary }}>普通用户</span>
                  )}
                </div>
              </div>

              {/* 模型信息 */}
              {modelInfo && (
                <div style={{
                  padding: 16,
                  backgroundColor: THEME.bg.primary,
                  borderRadius: 6,
                  marginTop: 16,
                }}>
                  <h4 style={{ margin: '0 0 12px', color: THEME.text.primary, fontSize: 14 }}>
                    🤖 DeepEDA 大模型信息
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
                    <div>
                      <span style={{ color: THEME.text.muted }}>虚拟模型:</span>
                      <span style={{ color: THEME.text.primary, marginLeft: 8 }}>{modelInfo.virtual_model}</span>
                    </div>
                    <div>
                      <span style={{ color: THEME.text.muted }}>实际接入:</span>
                      <span style={{ color: THEME.text.primary, marginLeft: 8 }}>{modelInfo.actual_model}</span>
                    </div>
                    <div>
                      <span style={{ color: THEME.text.muted }}>单次消耗:</span>
                      <span style={{ color: THEME.accent.primary, marginLeft: 8 }}>{modelInfo.model_cost} Token</span>
                    </div>
                    <div>
                      <span style={{ color: THEME.text.muted }}>模式:</span>
                      <span style={{
                        color: modelInfo.is_test_mode ? THEME.accent.warning : THEME.accent.success,
                        marginLeft: 8,
                      }}>
                        {modelInfo.is_test_mode ? '测试模式' : '正式模式'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Token 管理 Tab */}
          {activeTab === 'token' && (
            <div>
              {/* 余额卡片 */}
              <div style={{
                padding: 24,
                backgroundColor: THEME.bg.primary,
                borderRadius: 8,
                textAlign: 'center',
                marginBottom: 20,
              }}>
                <div style={{ color: THEME.text.muted, fontSize: 13, marginBottom: 8 }}>
                  当前余额
                </div>
                <div style={{
                  fontSize: 48,
                  fontWeight: 700,
                  color: THEME.accent.success,
                }}>
                  {user?.token_balance ?? 0}
                </div>
                <div style={{ color: THEME.text.muted, fontSize: 12, marginTop: 8 }}>
                  Token
                </div>
                {modelInfo?.is_test_mode && (
                  <div style={{
                    display: 'inline-block',
                    marginTop: 12,
                    padding: '4px 12px',
                    backgroundColor: THEME.accent.warning,
                    borderRadius: 4,
                    fontSize: 12,
                    color: '#000',
                  }}>
                    ⚠️ 测试模式 - 不真实扣费
                  </div>
                )}
              </div>

              {/* 充值区域 */}
              <div style={{
                padding: 16,
                backgroundColor: THEME.bg.tertiary,
                borderRadius: 6,
              }}>
                <h4 style={{ margin: '0 0 12px', color: THEME.text.primary, fontSize: 14 }}>
                  💳 充值 Token
                </h4>
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  <input
                    type="number"
                    value={topupAmount}
                    onChange={(e) => setTopupAmount(e.target.value)}
                    placeholder="输入充值数量"
                    style={{
                      flex: 1,
                      padding: '10px 12px',
                      backgroundColor: THEME.bg.primary,
                      border: `1px solid ${THEME.border.default}`,
                      borderRadius: 4,
                      color: THEME.text.primary,
                      fontSize: 14,
                    }}
                  />
                  <button
                    onClick={handleTopup}
                    disabled={topupLoading}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: topupLoading ? THEME.text.muted : THEME.accent.primary,
                      border: 'none',
                      borderRadius: 4,
                      color: '#fff',
                      fontSize: 14,
                      cursor: topupLoading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {topupLoading ? '处理中...' : '充值'}
                  </button>
                </div>
                {topupMsg && (
                  <div style={{
                    padding: '8px 12px',
                    backgroundColor: topupMsg.includes('成功') ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)',
                    borderRadius: 4,
                    color: topupMsg.includes('成功') ? THEME.accent.success : THEME.accent.error,
                    fontSize: 13,
                  }}>
                    {topupMsg}
                  </div>
                )}
                <div style={{ color: THEME.text.muted, fontSize: 11, marginTop: 8 }}>
                  * 充值功能预留接口，当前为测试充值
                </div>
              </div>
            </div>
          )}

          {/* 消费记录 Tab */}
          {activeTab === 'logs' && (
            <div>
              {logs.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: 40,
                  color: THEME.text.muted,
                }}>
                  暂无消费记录
                </div>
              ) : (
                <div style={{ fontSize: 13 }}>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 100px 80px 80px',
                    gap: 8,
                    padding: '8px 12px',
                    backgroundColor: THEME.bg.primary,
                    borderRadius: 4,
                    color: THEME.text.muted,
                    fontWeight: 600,
                    marginBottom: 8,
                  }}>
                    <div>时间</div>
                    <div>操作</div>
                    <div>Token</div>
                    <div>模型</div>
                  </div>
                  {logs.map((log) => (
                    <div key={log.id} style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 100px 80px 80px',
                      gap: 8,
                      padding: '10px 12px',
                      borderBottom: `1px solid ${THEME.border.default}`,
                      color: THEME.text.secondary,
                    }}>
                      <div>{new Date(log.created_at).toLocaleString('zh-CN')}</div>
                      <div>{log.action_type}</div>
                      <div style={{ color: log.is_test ? THEME.accent.warning : THEME.accent.primary }}>
                        -{log.token_count}
                        {log.is_test && <span style={{ fontSize: 10 }}>(测)</span>}
                      </div>
                      <div>{log.model_used}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
