/**
 * 用户栏组件 - 右上角用户信息和设置
 */

import React, { useState, useEffect } from 'react';
import { useAuthStore, authApi } from '../stores/authStore';
import AuthDialog from './AuthDialog';
import SettingsDialog from './SettingsDialog';

interface UserBarProps {
  onOpenSettings?: () => void;
  onOpenLogin?: () => void;
  onOpenAdmin?: () => void;
}

// 主题
const THEME = {
  bg: { primary: '#323232', secondary: '#3d3d3d', toolbar: '#2d2d2d' },
  text: { primary: '#e0e0e0', secondary: '#a0a0a0', muted: '#707070', accent: '#4a9eff' },
  accent: { primary: '#4a9eff', success: '#4caf50', warning: '#ff9800', error: '#f44336' },
  border: { default: '#4a4a4a' },
};

export default function UserBar({ onOpenSettings, onOpenLogin, onOpenAdmin }: UserBarProps) {
  const { user, token, isAuthenticated, logout, updateBalance } = useAuthStore();
  const [showDropdown, setShowDropdown] = useState(false);
  const [modelInfo, setModelInfo] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  // 本地对话框状态 - 如果外部没有提供回调，则使用本地状态
  const [localShowAuthDialog, setLocalShowAuthDialog] = useState(false);
  const [localShowSettingsDialog, setLocalShowSettingsDialog] = useState(false);

  // 刷新余额
  const refreshBalance = async () => {
    if (!token) return;
    setRefreshing(true);
    try {
      const info = await authApi.getModelInfo(token);
      setModelInfo(info);
      updateBalance(info.token_balance);
    } catch (e) {
      console.error('Failed to refresh:', e);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && token) {
      refreshBalance();
      const interval = setInterval(refreshBalance, 30000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, token]);

  // 退出登录
  const handleLogout = () => {
    logout();
    setShowDropdown(false);
    window.location.reload();
  };

  // 处理登录按钮点击
  const handleLoginClick = () => {
    if (onOpenLogin) {
      onOpenLogin();
    } else {
      // 使用本地状态
      setLocalShowAuthDialog(true);
    }
  };

  // 处理设置按钮点击
  const handleSettingsClick = () => {
    if (onOpenSettings) {
      onOpenSettings();
    } else {
      setLocalShowSettingsDialog(true);
    }
  };

  // 处理管理按钮点击
  const handleAdminClick = () => {
    if (onOpenAdmin) {
      onOpenAdmin();
    }
    setShowDropdown(false);
  };

  // 未登录状态
  if (!isAuthenticated) {
    return (
      <>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleLoginClick}
            style={{
              padding: '4px 12px',
              backgroundColor: THEME.accent.primary,
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              fontSize: 12,
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            登录 / 注册
          </button>
        </div>
        {/* 本地登录对话框 */}
        <AuthDialog
          isOpen={localShowAuthDialog}
          onClose={() => setLocalShowAuthDialog(false)}
          onSuccess={() => {
            setLocalShowAuthDialog(false);
          }}
        />
      </>
    );
  }

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Token 余额显示 */}
        <div
          onClick={refreshBalance}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 10px',
            backgroundColor: THEME.bg.secondary,
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
          }}
          title="点击刷新"
        >
          <span style={{ color: THEME.text.muted }}>Token:</span>
          <span style={{ color: THEME.accent.success, fontWeight: 600 }}>
            {refreshing ? '...' : user?.token_balance ?? 0}
          </span>
          {modelInfo?.is_test_mode && (
            <span style={{
              padding: '1px 4px',
              backgroundColor: THEME.accent.warning,
              borderRadius: 2,
              fontSize: 10,
              color: '#000',
            }}>
              测试
            </span>
          )}
        </div>

        {/* 模型信息 */}
        <div style={{
          fontSize: 11,
          color: THEME.text.muted,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}>
          <span>🤖</span>
          <span>{modelInfo?.virtual_model || 'DeepEDA大模型'}</span>
        </div>

        {/* 用户下拉菜单 */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 8px',
              backgroundColor: 'transparent',
              border: `1px solid ${THEME.border.default}`,
              borderRadius: 4,
              color: THEME.text.primary,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <span>👤</span>
            <span>{user?.username || user?.email}</span>
            <span style={{ fontSize: 10 }}>▼</span>
          </button>

          {showDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              marginTop: 4,
              backgroundColor: THEME.bg.secondary,
              border: `1px solid ${THEME.border.default}`,
              borderRadius: 4,
              minWidth: 150,
              zIndex: 1000,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              overflow: 'hidden',
            }}>
              <div
                onClick={() => { handleSettingsClick(); setShowDropdown(false); }}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: THEME.text.secondary,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.bg.primary}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                ⚙️ 设置
              </div>
              {user?.is_admin && (
                <div
                  onClick={handleAdminClick}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    fontSize: 12,
                    color: THEME.accent.warning,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.bg.primary}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  🔧 管理后台
                </div>
              )}
              <div
                onClick={handleLogout}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: THEME.accent.error,
                  borderTop: `1px solid ${THEME.border.default}`,
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.bg.primary}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                🚪 退出登录
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 本地设置对话框 */}
      <SettingsDialog
        isOpen={localShowSettingsDialog}
        onClose={() => setLocalShowSettingsDialog(false)}
      />
    </>
  );
}
