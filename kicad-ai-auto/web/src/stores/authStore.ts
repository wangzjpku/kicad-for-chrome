/**
 * 用户认证状态管理
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: number;
  email: string;
  username: string;
  token_balance: number;
  is_test_mode: boolean;
  is_admin: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  updateBalance: (balance: number) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      setAuth: (user, token) => set({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
      }),

      logout: () => set({
        user: null,
        token: null,
        isAuthenticated: false,
      }),

      updateBalance: (balance) => set((state) => ({
        user: state.user ? { ...state.user, token_balance: balance } : null,
      })),

      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: 'deepeda-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// API 调用（使用相对路径，通过 Vite 代理访问后端）
const API_BASE = import.meta.env.VITE_API_URL || '';

export const authApi = {
  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '登录失败');
    }
    const data = await res.json();
    return { user: data.user, token: data.token };
  },

  async register(email: string, password: string, username?: string): Promise<{ user: User; token: string }> {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '注册失败');
    }
    const data = await res.json();
    return { user: data.user, token: data.token };
  },

  async getProfile(token: string): Promise<User> {
    const res = await fetch(`${API_BASE}/api/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('获取用户信息失败');
    return res.json();
  },

  async getBalance(token: string): Promise<{ balance: number; is_test_mode: boolean }> {
    const res = await fetch(`${API_BASE}/api/token/balance`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('获取余额失败');
    return res.json();
  },

  async getLogs(token: string): Promise<any[]> {
    const res = await fetch(`${API_BASE}/api/token/logs?limit=20`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('获取记录失败');
    return res.json();
  },

  async getModelInfo(token: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/deepeda/model-info`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('获取模型信息失败');
    return res.json();
  },

  async topup(token: string, amount: number): Promise<{ new_balance: number }> {
    const res = await fetch(`${API_BASE}/api/token/topup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ amount, payment_method: 'manual' }),
    });
    if (!res.ok) throw new Error('充值失败');
    return res.json();
  },
};
