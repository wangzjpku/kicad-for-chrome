/**
 * 登录/注册对话框
 */

import React, { useState } from 'react';
import { useAuthStore, authApi } from '../stores/authStore';

interface AuthDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

// 主题
const THEME = {
  bg: { primary: '#323232', secondary: '#3d3d3d', tertiary: '#454545' },
  text: { primary: '#e0e0e0', secondary: '#a0a0a0', muted: '#707070' },
  accent: { primary: '#4a9eff', success: '#4caf50', warning: '#ff9800', error: '#f44336' },
  border: { default: '#4a4a4a' },
};

export default function AuthDialog({ isOpen, onClose, onSuccess }: AuthDialogProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let result;
      if (mode === 'login') {
        result = await authApi.login(email, password);
      } else {
        result = await authApi.register(email, password, username);
      }

      setAuth(result.user, result.token);
      onSuccess();
      onClose();
    } catch (e: any) {
      setError(e.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setError('');
  };

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
        padding: 24,
        width: 360,
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      }} onClick={(e) => e.stopPropagation()}>
        {/* 标题 */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <h2 style={{ margin: 0, color: THEME.text.primary, fontSize: 20 }}>
            {mode === 'login' ? '登录' : '注册'}
          </h2>
          <p style={{ margin: '8px 0 0', color: THEME.text.muted, fontSize: 13 }}>
            {mode === 'login' ? '登录到 DeepEDA' : '创建 DeepEDA 账号'}
          </p>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', color: THEME.text.secondary, fontSize: 12, marginBottom: 4 }}>
                用户名
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: THEME.bg.primary,
                  border: `1px solid ${THEME.border.default}`,
                  borderRadius: 4,
                  color: THEME.text.primary,
                  fontSize: 14,
                  boxSizing: 'border-box',
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', color: THEME.text.secondary, fontSize: 12, marginBottom: 4 }}>
              邮箱
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="请输入邮箱"
              required
              style={{
                width: '100%',
                padding: '10px 12px',
                backgroundColor: THEME.bg.primary,
                border: `1px solid ${THEME.border.default}`,
                borderRadius: 4,
                color: THEME.text.primary,
                fontSize: 14,
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', color: THEME.text.secondary, fontSize: 12, marginBottom: 4 }}>
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
              minLength={6}
              style={{
                width: '100%',
                padding: '10px 12px',
                backgroundColor: THEME.bg.primary,
                border: `1px solid ${THEME.border.default}`,
                borderRadius: 4,
                color: THEME.text.primary,
                fontSize: 14,
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <div style={{
              padding: '10px 12px',
              backgroundColor: 'rgba(244, 67, 54, 0.1)',
              border: `1px solid ${THEME.accent.error}`,
              borderRadius: 4,
              color: THEME.accent.error,
              fontSize: 13,
              marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: loading ? THEME.text.muted : THEME.accent.primary,
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              marginBottom: 16,
            }}
          >
            {loading ? '处理中...' : (mode === 'login' ? '登录' : '注册')}
          </button>
        </form>

        {/* 切换模式 */}
        <div style={{ textAlign: 'center', fontSize: 13, color: THEME.text.muted }}>
          {mode === 'login' ? '还没有账号？' : '已有账号？'}
          <span
            onClick={toggleMode}
            style={{
              color: THEME.accent.primary,
              cursor: 'pointer',
              marginLeft: 4,
            }}
          >
            {mode === 'login' ? '立即注册' : '立即登录'}
          </span>
        </div>

        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: 12,
            right: 12,
            background: 'none',
            border: 'none',
            color: THEME.text.muted,
            fontSize: 20,
            cursor: 'pointer',
          }}
        >
          ×
        </button>

        {/* Token 提示 */}
        <div style={{
          marginTop: 20,
          padding: 12,
          backgroundColor: THEME.bg.primary,
          borderRadius: 4,
          fontSize: 12,
          color: THEME.text.muted,
          textAlign: 'center',
        }}>
          🎁 新用户注册即送 <span style={{ color: THEME.accent.success, fontWeight: 600 }}>1000</span> Token
        </div>
      </div>
    </div>
  );
}
