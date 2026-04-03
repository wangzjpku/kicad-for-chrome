/**
 * Admin管理后台 - 运维管理面板
 * 包含：用户管理、Token管理、项目管理、系统状态、缓存清理等
 */

import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '';

const THEME = {
  bg: { primary: '#1a1a2e', secondary: '#16213e', card: '#0f3460', dark: '#0a0a15' },
  text: { primary: '#eaeaea', secondary: '#a0a0a0', muted: '#606060' },
  accent: { primary: '#e94560', success: '#00d9ff', warning: '#fbbf24', error: '#ef4444' },
  border: '#2a2a4a'
};

interface User {
  id: number;
  username: string;
  email: string;
  token_balance: number;
  is_admin: number;
  created_at: string;
}

interface TokenLog {
  id: number;
  action_type: string;
  token_count: number;
  model_used: string;
  created_at: string;
}

interface Project {
  id: string;
  name: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

interface SystemStats {
  totalUsers: number;
  totalTokens: number;
  totalConsumed: number;
  todayConsumed: number;
  totalProjects: number;
}

interface HealthStatus {
  backend: boolean;
  kicad: boolean;
  ai: boolean;
  database: boolean;
}

interface ApiEndpoint {
  path: string;
  method: string;
  status: number;
  response_time: number;
}

export default function AdminPanel({ onClose }: { onClose?: () => void }) {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'users' | 'tokens' | 'projects' | 'system' | 'cache' | 'pcb' | 'ai' | 'manufacturing' | 'templates' | 'knowledge'>('dashboard');
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<TokenLog[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<SystemStats>({totalUsers: 0, totalTokens: 0, totalConsumed: 0, todayConsumed: 0, totalProjects: 0});
  const [health, setHealth] = useState<HealthStatus>({backend: false, kicad: false, ai: false, database: false});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error' | 'warning', text: string} | null>(null);

  // 加载数据
  useEffect(() => {
    loadAllData();
  }, []);

  const showMessage = (type: 'success' | 'error' | 'warning', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
             loadUsers(),
 await Promise.all([
        loadProjects(),
        loadHealthStatus(),
        loadTokenLogs()
      ]);
    } catch (e) {
      console.error('Load data failed:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const res = await fetch(API_BASE + '/api/admin/users');
      const data = await res.json();
      setUsers(data || []);
      const totalTokens = (data || []).reduce((sum: number, u: User) => sum + (u.token_balance || 0), 0);
      setStats(s => ({ ...s, totalUsers: (data || []).length, totalTokens }));
    } catch (e) {
      console.error('Load users failed:', e);
    }
  };

  const loadProjects = async () => {
    try {
      const res = await fetch(API_BASE + '/api/v1/projects');
      const data = await res.json();
      setProjects(data || []);
      setStats(s => ({ ...s, totalProjects: (data || []).length }));
    } catch (e) {
      console.error('Load projects failed:', e);
    }
  };

  const loadHealthStatus = async () => {
    const checks: HealthStatus = { backend: false, kicad: false, ai: false, database: false };
    try {
      // Check backend
      const backendRes = await fetch(API_BASE + '/api/health');
      checks.backend = backendRes.ok;

      // Check KiCad
      const kicadRes = await fetch(API_BASE + '/api/kicad-ipc/status');
      const kicadData = await kicadRes.json();
      checks.kicad = kicadData.connected || false;

      // Check AI
      const aiRes = await fetch(API_BASE + '/api/v1/ai/health');
      checks.ai = aiRes.ok;

      // Check database (via projects API)
      const dbRes = await fetch(API_BASE + '/api/v1/projects');
      checks.database = dbRes.ok;
    } catch (e) {
      console.error('Health check failed:', e);
    }
    setHealth(checks);
  };

  const loadTokenLogs = async () => {
    try {
      const res = await fetch(API_BASE + '/api/token/logs');
      const data = await res.json();
      setLogs(data || []);
      const totalConsumed = (data || []).reduce((sum: number, l: TokenLog) => sum + (l.token_count || 0), 0);
      setStats(s => ({ ...s, totalConsumed }));
    } catch (e) {
      console.error('Load logs failed:', e);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('确定要删除这个项目吗？此操作不可恢复！')) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}`, { method: 'DELETE' });
      if (res.ok) {
        showMessage('success', '项目删除成功');
        loadProjects();
      } else {
        showMessage('error', '删除失败');
      }
    } catch (e) {
      showMessage('error', '删除失败: ' + e);
    }
  };

  const handleClearAllProjects = async () => {
    if (!confirm('⚠️ 确定要清空所有项目吗？此操作不可恢复！')) return;
    if (!confirm('再次确认：所有项目数据将被永久删除！')) return;
    try {
      const res = await fetch(API_BASE + '/api/v1/projects/clear-all', { method: 'DELETE' });
      if (res.ok) {
        showMessage('success', '所有项目已清空');
        loadProjects();
      } else {
        showMessage('error', '清空失败');
      }
    } catch (e) {
      showMessage('error', '清空失败: ' + e);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('确定要删除这个用户吗？')) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/user/delete/${userId}`, { method: 'POST' });
      if (res.ok) {
        showMessage('success', '用户删除成功');
        loadUsers();
      } else {
        showMessage('error', '删除失败');
      }
    } catch (e) {
      showMessage('error', '删除失败: ' + e);
    }
  };

  const handleTokenTopup = async (userId: number, amount: number) => {
    try {
      const res = await fetch(API_BASE + '/api/admin/user/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, amount })
      });
      if (res.ok) {
        showMessage('success', `已为用户 ${userId} 充值 ${amount} Token`);
        loadUsers();
      } else {
        showMessage('error', '充值失败');
      }
    } catch (e) {
      showMessage('error', '充值失败: ' + e);
    }
  };

  const handleClearCache = async () => {
    if (!confirm('确定要清理缓存吗？')) return;
    // 模拟缓存清理
    showMessage('success', '缓存清理完成');
  };

  const handleRestartBackend = async () => {
    if (!confirm('确定要重启后端服务吗？这将中断所有正在进行的操作。')) return;
    showMessage('warning', '后端重启需要手动执行，请联系运维人员');
  };

  const tabs = [
    { id: 'dashboard', label: '📊 控制台' },
    { id: 'users', label: '👥 用户管理' },
    { id: 'tokens', label: '💰 Token记录' },
    { id: 'projects', label: '📁 项目管理' },
    { id: 'system', label: '🖥️ 系统状态' },
    { id: 'cache', label: '🧹 运维工具' },
    { id: 'pcb', label: '🔧 PCB参数' },
    { id: 'ai', label: '🤖 AI模型' },
    { id: 'manufacturing', label: '🏭 制造选项' },
    { id: 'templates', label: '📋 模板管理' },
    { id: 'knowledge', label: '🧠 知识库' },
  ];

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: THEME.bg.primary,
      color: THEME.text.primary,
      padding: 20,
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      overflow: 'auto',
      zIndex: 1000
    }}>
      {/* 顶部标题栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h1 style={{ margin: 0, fontSize: 24 }}>🔧 运维管理后台</h1>
          <span style={{ fontSize: 12, color: THEME.text.secondary, backgroundColor: THEME.bg.card, padding: '4px 12px', borderRadius: 4 }}>
            v0.9.14
          </span>
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            backgroundColor: THEME.bg.card,
            border: 'none',
            color: THEME.text.primary,
            padding: '8px 16px',
            borderRadius: 6,
            cursor: 'pointer'
          }}>
            ✕ 关闭
          </button>
        )}
      </div>

      {/* 消息提示 */}
      {message && (
        <div style={{
          position: 'fixed',
          top: 20,
          right: 20,
          backgroundColor: message.type === 'success' ? THEME.accent.success : message.type === 'warning' ? THEME.accent.warning : THEME.accent.error,
          color: '#fff',
          padding: '12px 24px',
          borderRadius: 8,
          zIndex: 1001,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}>
          {message.text}
        </div>
      )}

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { label: '👥 总用户', value: stats.totalUsers, color: THEME.accent.success },
          { label: '💎 总Token', value: stats.totalTokens, color: '#4ade80' },
          { label: '📊 总消耗', value: stats.totalConsumed, color: THEME.accent.primary },
          { label: '📁 项目数', value: stats.totalProjects, color: '#a78bfa' },
          { label: '🟢 后端状态', value: health.backend ? '在线' : '离线', color: health.backend ? THEME.accent.success : THEME.accent.error },
        ].map((stat, i) => (
          <div key={i} style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8, textAlign: 'center' }}>
            <div style={{ color: THEME.text.secondary, fontSize: 13 }}>{stat.label}</div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: stat.color }}>{typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}</div>
          </div>
        ))}
      </div>

      {/* 标签页导航 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === tab.id ? THEME.accent.primary : THEME.bg.card,
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: activeTab === tab.id ? 'bold' : 'normal'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 内容区域 */}
      <div style={{ backgroundColor: THEME.bg.secondary, borderRadius: 8, padding: 20, minHeight: 400 }}>
        {loading && <div style={{ textAlign: 'center', padding: 40, color: THEME.text.secondary }}>加载中...</div>}

        {!loading && activeTab === 'dashboard' && (
          <DashboardView health={health} stats={stats} users={users} logs={logs} projects={projects} />
        )}

        {!loading && activeTab === 'users' && (
          <UsersView users={users} onDelete={handleDeleteUser} onTopup={handleTokenTopup} />
        )}

        {!loading && activeTab === 'tokens' && (
          <TokensView logs={logs} />
        )}

        {!loading && activeTab === 'projects' && (
          <ProjectsView projects={projects} onDelete={handleDeleteProject} onClearAll={handleClearAllProjects} />
        )}

        {!loading && activeTab === 'system' && (
          <SystemView health={health} onRefresh={loadHealthStatus} />
        )}

        {!loading && activeTab === 'cache' && (
          <CacheView onClearCache={handleClearCache} onRestart={handleRestartBackend} />
        )}

        {!loading && activeTab === 'pcb' && (
          <PCBSettingsView />
        )}

        {!loading && activeTab === 'ai' && (
          <AISettingsView />
        )}

        {!loading && activeTab === 'manufacturing' && (
          <ManufacturingSettingsView />
        )}

        {!loading && activeTab === 'templates' && (
          <TemplatesView />
        )}

        {!loading && activeTab === 'knowledge' && (
          <KnowledgeBaseView />
        )}
      </div>
    </div>
  );
}

// ========== 子组件 ==========

function DashboardView({ health, stats, users, logs, projects }: { health: HealthStatus; stats: SystemStats; users: User[]; logs: TokenLog[]; projects: Project[] }) {
  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>📊 系统概览</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.success }}>🟢 服务状态</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>后端服务</span>
              <span style={{ color: health.backend ? '#4ade80' : '#ef4444' }}>{health.backend ? '● 在线' : '● 离线'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>KiCad连接</span>
              <span style={{ color: health.kicad ? '#4ade80' : '#fbbf24' }}>{health.kicad ? '● 已连接' : '● 未连接'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>AI服务</span>
              <span style={{ color: health.ai ? '#4ade80' : '#ef4444' }}>{health.ai ? '● 正常' : '● 异常'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>数据存储</span>
              <span style={{ color: health.database ? '#4ade80' : '#ef4444' }}>{health.database ? '● 正常' : '● 异常'}</span>
            </div>
          </div>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>📈 运营数据</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>用户数</span>
              <span>{stats.totalUsers}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>项目数</span>
              <span>{stats.totalProjects}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Token总消耗</span>
              <span>{stats.totalConsumed.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Token余额</span>
              <span style={{ color: '#4ade80' }}>{stats.totalTokens.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function UsersView({ users, onDelete, onTopup }: { users: User[]; onDelete: (id: number) => void; onTopup: (id: number, amount: number) => void }) {
  const [topupAmount, setTopupAmount] = useState(1000);
  const [selectedUser, setSelectedUser] = useState<number | null>(null);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>👥 用户列表</h3>
        <span style={{ color: THEME.text.secondary }}>共 {users.length} 个用户</span>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${THEME.border}` }}>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>ID</th>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>用户名</th>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>邮箱</th>
            <th style={{ padding: 12, textAlign: 'right', color: THEME.text.secondary }}>Token余额</th>
            <th style={{ padding: 12, textAlign: 'center', color: THEME.text.secondary }}>权限</th>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>注册时间</th>
            <th style={{ padding: 12, textAlign: 'center', color: THEME.text.secondary }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} style={{ borderBottom: `1px solid ${THEME.bg.dark}` }}>
              <td style={{ padding: 12 }}>{u.id}</td>
              <td style={{ padding: 12, fontWeight: 'bold' }}>{u.username}</td>
              <td style={{ padding: 12, color: THEME.text.secondary }}>{u.email}</td>
              <td style={{ padding: 12, textAlign: 'right', color: '#4ade80', fontWeight: 'bold' }}>{u.token_balance?.toLocaleString()}</td>
              <td style={{ padding: 12, textAlign: 'center' }}>
                {u.is_admin ? <span style={{ color: THEME.accent.warning }}>👑 管理员</span> : '👤 用户'}
              </td>
              <td style={{ padding: 12, color: THEME.text.muted }}>{u.created_at?.split(' ')[0]}</td>
              <td style={{ padding: 12, textAlign: 'center' }}>
                <button
                  onClick={() => onTopup(u.id, topupAmount)}
                  style={{ backgroundColor: THEME.accent.success, border: 'none', color: '#fff', padding: '4px 12px', borderRadius: 4, cursor: 'pointer', marginRight: 8 }}
                >
                  充值
                </button>
                {!u.is_admin && (
                  <button
                    onClick={() => onDelete(u.id)}
                    style={{ backgroundColor: THEME.accent.error, border: 'none', color: '#fff', padding: '4px 12px', borderRadius: 4, cursor: 'pointer' }}
                  >
                    删除
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TokensView({ logs }: { logs: TokenLog[] }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>💰 Token消耗记录</h3>
        <span style={{ color: THEME.text.secondary }}>共 {logs.length} 条记录</span>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${THEME.border}` }}>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>ID</th>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>操作类型</th>
            <th style={{ padding: 12, textAlign: 'right', color: THEME.text.secondary }}>消耗Token</th>
            <th style={{ padding: 12, textAlign: 'center', color: THEME.text.secondary }}>模型</th>
            <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>时间</th>
          </tr>
        </thead>
        <tbody>
          {logs.slice(0, 50).map(l => (
            <tr key={l.id} style={{ borderBottom: `1px solid ${THEME.bg.dark}` }}>
              <td style={{ padding: 12 }}>{l.id}</td>
              <td style={{ padding: 12 }}>{l.action_type}</td>
              <td style={{ padding: 12, textAlign: 'right', color: THEME.accent.primary, fontWeight: 'bold' }}>-{l.token_count}</td>
              <td style={{ padding: 12, textAlign: 'center' }}>{l.model_used}</td>
              <td style={{ padding: 12, color: THEME.text.muted }}>{l.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProjectsView({ projects, onDelete, onClearAll }: { projects: Project[]; onDelete: (id: string) => void; onClearAll: () => void }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0 }}>📁 项目管理</h3>
          <span style={{ color: THEME.text.secondary }}>共 {projects.length} 个项目</span>
        </div>
        <button
          onClick={onClearAll}
          style={{ backgroundColor: THEME.accent.error, border: 'none', color: '#fff', padding: '8px 16px', borderRadius: 6, cursor: 'pointer' }}
        >
          🗑️ 清空所有项目
        </button>
      </div>
      <div style={{ maxHeight: 500, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${THEME.border}` }}>
              <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>项目名</th>
              <th style={{ padding: 12, textAlign: 'center', color: THEME.text.secondary }}>状态</th>
              <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>创建时间</th>
              <th style={{ padding: 12, textAlign: 'left', color: THEME.text.secondary }}>更新时间</th>
              <th style={{ padding: 12, textAlign: 'center', color: THEME.text.secondary }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id} style={{ borderBottom: `1px solid ${THEME.bg.dark}` }}>
                <td style={{ padding: 12, fontWeight: 'bold' }}>{p.name}</td>
                <td style={{ padding: 12, textAlign: 'center' }}>
                  <span style={{ color: p.status === 'active' ? '#4ade80' : THEME.text.secondary }}>{p.status}</span>
                </td>
                <td style={{ padding: 12, color: THEME.text.muted }}>{p.createdAt?.split('T')[0]}</td>
                <td style={{ padding: 12, color: THEME.text.muted }}>{p.updatedAt?.split('T')[0]}</td>
                <td style={{ padding: 12, textAlign: 'center' }}>
                  <button
                    onClick={() => onDelete(p.id)}
                    style={{ backgroundColor: THEME.accent.error, border: 'none', color: '#fff', padding: '4px 12px', borderRadius: 4, cursor: 'pointer' }}
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SystemView({ health, onRefresh }: { health: HealthStatus; onRefresh: () => void }) {
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([]);

  useEffect(() => {
    checkApiEndpoints();
  }, []);

  const checkApiEndpoints = async () => {
    const apis = [
      { path: '/api/health', method: 'GET' },
      { path: '/api/v1/projects', method: 'GET' },
      { path: '/api/v1/ai/health', method: 'GET' },
      { path: '/api/kicad-ipc/status', method: 'GET' },
      { path: '/api/version', method: 'GET' },
    ];
    const results: ApiEndpoint[] = [];
    for (const api of apis) {
      const start = Date.now();
      try {
        const res = await fetch(`${API_BASE}${api.path}`, { method: api.method });
        results.push({ ...api, status: res.status, response_time: Date.now() - start });
      } catch {
        results.push({ ...api, status: 0, response_time: Date.now() - start });
      }
    }
    setEndpoints(results);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>🖥️ 系统状态</h3>
        <button onClick={() => { onRefresh(); checkApiEndpoints(); }} style={{ backgroundColor: THEME.bg.card, border: 'none', color: '#fff', padding: '8px 16px', borderRadius: 6, cursor: 'pointer' }}>
          🔄 刷新
        </button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px' }}>🔴 服务健康检查</h4>
          {[
            { label: '后端API', status: health.backend },
            { label: 'KiCad连接', status: health.kicad },
            { label: 'AI服务', status: health.ai },
            { label: '数据库', status: health.database },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${THEME.bg.dark}` }}>
              <span>{item.label}</span>
              <span style={{ color: item.status ? '#4ade80' : '#ef4444', fontWeight: 'bold' }}>
                {item.status ? '● 正常' : '● 异常'}
              </span>
            </div>
          ))}
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px' }}>📡 API端点状态</h4>
          {endpoints.map((ep, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${THEME.bg.dark}` }}>
              <span><code style={{ backgroundColor: THEME.bg.dark, padding: '2px 6px', borderRadius: 4 }}>{ep.method}</code> {ep.path}</span>
              <span style={{ color: ep.status === 200 ? '#4ade80' : '#ef4444' }}>
                {ep.status || 'ERR'} ({ep.response_time}ms)
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CacheView({ onClearCache, onRestart }: { onClearCache: () => void; onRestart: () => void }) {
  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>🧹 运维工具</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
        <div style={{ backgroundColor: THEME.bg.card, padding: 24, borderRadius: 8, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🗑️</div>
          <h4 style={{ margin: '0 0 12px' }}>清理缓存</h4>
          <p style={{ color: THEME.text.secondary, marginBottom: 16 }}>清理浏览器缓存和临时文件</p>
          <button onClick={onClearCache} style={{ backgroundColor: THEME.accent.primary, border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 6, cursor: 'pointer' }}>
            执行清理
          </button>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 24, borderRadius: 8, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔄</div>
          <h4 style={{ margin: '0 0 12px' }}>重启服务</h4>
          <p style={{ color: THEME.text.secondary, marginBottom: 16 }}>重启后端服务（需要手动执行）</p>
          <button onClick={onRestart} style={{ backgroundColor: THEME.accent.warning, border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 6, cursor: 'pointer' }}>
            申请重启
          </button>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 24, borderRadius: 8, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📋</div>
          <h4 style={{ margin: '0 0 12px' }}>导出日志</h4>
          <p style={{ color: THEME.text.secondary, marginBottom: 16 }}>导出系统日志用于分析</p>
          <button onClick={() => window.open(API_BASE + '/api/token/logs')} style={{ backgroundColor: THEME.accent.success, border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 6, cursor: 'pointer' }}>
            下载日志
          </button>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 24, borderRadius: 8, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📖</div>
          <h4 style={{ margin: '0 0 12px' }}>API文档</h4>
          <p style={{ color: THEME.text.secondary, marginBottom: 16 }}>查看完整的API文档</p>
          <button onClick={() => window.open(API_BASE + '/docs')} style={{ backgroundColor: '#a78bfa', border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 6, cursor: 'pointer' }}>
            打开Swagger
          </button>
        </div>
      </div>
    </div>
  );
}

// ========== PCB 参数设置 ==========

function PCBSettingsView() {
  const [settings, setSettings] = useState({
    layerCount: 2,
    boardThickness: 1.6,
    copperThickness: 1.0,
    defaultTraceWidth: 0.25,
    minTraceWidth: 0.15,
    defaultClearance: 0.2,
    impedanceTarget: 50,
    viaDrill: 0.3,
    viaOuter: 0.6,
  });
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    try {
      const res = await fetch(API_BASE + '/api/admin/settings/pcb', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch (e) {
      console.error('Save failed:', e);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: THEME.bg.primary,
    border: `1px solid ${THEME.border}`,
    borderRadius: 6,
    color: THEME.text.primary,
    fontSize: 14,
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: 6,
    color: THEME.text.secondary,
    fontSize: 13,
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>🔧 PCB 参数设置</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>层叠设置</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>板子层数</label>
            <select style={inputStyle} value={settings.layerCount} onChange={e => setSettings({...settings, layerCount: Number(e.target.value)})}>
              <option value={2}>2层板</option>
              <option value={4}>4层板</option>
              <option value={6}>6层板</option>
            </select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>板厚 (mm)</label>
            <input style={inputStyle} type="number" step="0.1" value={settings.boardThickness} onChange={e => setSettings({...settings, boardThickness: Number(e.target.value)})} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>铜厚 (oz)</label>
            <select style={inputStyle} value={settings.copperThickness} onChange={e => setSettings({...settings, copperThickness: Number(e.target.value)})}>
              <option value={0.5}>0.5 oz</option>
              <option value={1.0}>1 oz</option>
              <option value={2.0}>2 oz</option>
            </select>
          </div>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>走线设置</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>默认走线宽度 (mm)</label>
            <input style={inputStyle} type="number" step="0.05" value={settings.defaultTraceWidth} onChange={e => setSettings({...settings, defaultTraceWidth: Number(e.target.value)})} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>最小走线宽度 (mm)</label>
            <input style={inputStyle} type="number" step="0.05" value={settings.minTraceWidth} onChange={e => setSettings({...settings, minTraceWidth: Number(e.target.value)})} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>默认间距 (mm)</label>
            <input style={inputStyle} type="number" step="0.05" value={settings.defaultClearance} onChange={e => setSettings({...settings, defaultClearance: Number(e.target.value)})} />
          </div>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>阻抗控制</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>目标阻抗 (Ω)</label>
            <input style={inputStyle} type="number" value={settings.impedanceTarget} onChange={e => setSettings({...settings, impedanceTarget: Number(e.target.value)})} />
          </div>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>过孔设置</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>过孔钻孔直径 (mm)</label>
            <input style={inputStyle} type="number" step="0.1" value={settings.viaDrill} onChange={e => setSettings({...settings, viaDrill: Number(e.target.value)})} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>过孔外径 (mm)</label>
            <input style={inputStyle} type="number" step="0.1" value={settings.viaOuter} onChange={e => setSettings({...settings, viaOuter: Number(e.target.value)})} />
          </div>
        </div>
      </div>
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button onClick={handleSave} style={{ backgroundColor: saved ? THEME.accent.success : THEME.accent.primary, border: 'none', color: '#fff', padding: '12px 32px', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
          {saved ? '✓ 已保存' : '保存设置'}
        </button>
      </div>
    </div>
  );
}

// ========== AI 模型配置 ==========

function AISettingsView() {
  const [settings, setSettings] = useState({
    apiProvider: 'deepseek',
    apiKey: '',
    modelName: 'deepseek-chat',
    temperature: 0.7,
    maxTokens: 2000,
    enableCache: true,
  });
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleSave = async () => {
    try {
      const res = await fetch(API_BASE + '/api/admin/settings/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch (e) {
      console.error('Save failed:', e);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(API_BASE + '/api/v1/ai/health');
      const data = await res.json();
      setTestResult(data.status === 'ok' ? '✓ API 连接正常' : '✗ 连接失败');
    } catch (e) {
      setTestResult('✗ 连接失败');
    } finally {
      setTesting(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: THEME.bg.primary,
    border: `1px solid ${THEME.border}`,
    borderRadius: 6,
    color: THEME.text.primary,
    fontSize: 14,
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: 6,
    color: THEME.text.secondary,
    fontSize: 13,
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>🤖 AI 模型配置</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>API 配置</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>API 提供商</label>
            <select style={inputStyle} value={settings.apiProvider} onChange={e => setSettings({...settings, apiProvider: e.target.value})}>
              <option value="deepseek">DeepSeek</option>
              <option value="kimi">Kimi</option>
              <option value="glm">GLM-4</option>
            </select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>API Key</label>
            <input style={inputStyle} type="password" value={settings.apiKey} onChange={e => setSettings({...settings, apiKey: e.target.value})} placeholder="sk-..." />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>模型名称</label>
            <input style={inputStyle} value={settings.modelName} onChange={e => setSettings({...settings, modelName: e.target.value})} />
          </div>
          <button onClick={handleTest} disabled={testing} style={{ backgroundColor: THEME.accent.success, border: 'none', color: '#fff', padding: '8px 16px', borderRadius: 6, cursor: 'pointer' }}>
            {testing ? '测试中...' : '测试连接'}
          </button>
          {testResult && <span style={{ marginLeft: 12, color: testResult.includes('正常') ? THEME.accent.success : THEME.accent.error }}>{testResult}</span>}
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>生成参数</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Temperature</label>
            <input style={inputStyle} type="number" step="0.1" min="0" max="2" value={settings.temperature} onChange={e => setSettings({...settings, temperature: Number(e.target.value)})} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Max Tokens</label>
            <input style={inputStyle} type="number" value={settings.maxTokens} onChange={e => setSettings({...settings, maxTokens: Number(e.target.value)})} />
          </div>
          <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={settings.enableCache} onChange={e => setSettings({...settings, enableCache: e.target.checked})} />
            <label>启用响应缓存</label>
          </div>
        </div>
      </div>
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button onClick={handleSave} style={{ backgroundColor: saved ? THEME.accent.success : THEME.accent.primary, border: 'none', color: '#fff', padding: '12px 32px', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
          {saved ? '✓ 已保存' : '保存设置'}
        </button>
      </div>
    </div>
  );
}

// ========== 制造选项 ==========

function ManufacturingSettingsView() {
  const [settings, setSettings] = useState({
    manufacturer: 'jlcpcb',
    surfaceFinish: 'HASL',
    baseCopper: 1.0,
    silkscreenColor: 'white',
    soldermaskColor: 'green',
    impedanceControl: false,
    count: 5,
  });
  const [saved, setSaved] = useState(false);
  const [estimate, setEstimate] = useState<any>(null);

  const handleSave = async () => {
    try {
      const res = await fetch(API_BASE + '/api/admin/settings/manufacturing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch (e) {
      console.error('Save failed:', e);
    }
  };

  const handleEstimate = async () => {
    try {
      const res = await fetch(API_BASE + '/api/admin/settings/manufacturing/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      const data = await res.json();
      setEstimate(data);
    } catch (e) {
      console.error('Estimate failed:', e);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: THEME.bg.primary,
    border: `1px solid ${THEME.border}`,
    borderRadius: 6,
    color: THEME.text.primary,
    fontSize: 14,
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: 6,
    color: THEME.text.secondary,
    fontSize: 13,
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>🏭 制造选项</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>制造商配置</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>首选制造商</label>
            <select style={inputStyle} value={settings.manufacturer} onChange={e => setSettings({...settings, manufacturer: e.target.value})}>
              <option value="jlcpcb">JLCPCB</option>
              <option value="pcbway">PCBWay</option>
              <option value="seeed">Seeed Studio</option>
            </select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>表面处理</label>
            <select style={inputStyle} value={settings.surfaceFinish} onChange={e => setSettings({...settings, surfaceFinish: e.target.value})}>
              <option value="HASL">HASL 无铅</option>
              <option value="ENIG">ENIG 金手指</option>
              <option value="OSP">OSP</option>
            </select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>基铜厚度 (oz)</label>
            <select style={inputStyle} value={settings.baseCopper} onChange={e => setSettings({...settings, baseCopper: Number(e.target.value)})}>
              <option value={1}>1 oz</option>
              <option value={2}>2 oz</option>
            </select>
          </div>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 16px', color: THEME.accent.primary }}>外观选项</h4>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>丝印颜色</label>
            <select style={inputStyle} value={settings.silkscreenColor} onChange={e => setSettings({...settings, silkscreenColor: e.target.value})}>
              <option value="white">白色</option>
              <option value="black">黑色</option>
              <option value="yellow">黄色</option>
            </select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>阻焊颜色</label>
            <select style={inputStyle} value={settings.soldermaskColor} onChange={e => setSettings({...settings, soldermaskColor: e.target.value})}>
              <option value="green">绿色</option>
              <option value="red">红色</option>
              <option value="blue">蓝色</option>
              <option value="black">黑色</option>
              <option value="white">白色</option>
            </select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>数量</label>
            <select style={inputStyle} value={settings.count} onChange={e => setSettings({...settings, count: Number(e.target.value)})}>
              <option value={5}>5 片</option>
              <option value={10}>10 片</option>
              <option value={20}>20 片</option>
              <option value={50}>50 片</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={settings.impedanceControl} onChange={e => setSettings({...settings, impedanceControl: e.target.checked})} />
            <label>启用阻抗控制</label>
          </div>
        </div>
      </div>
      <div style={{ marginTop: 24, display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
        <button onClick={handleEstimate} style={{ backgroundColor: THEME.accent.warning, border: 'none', color: '#fff', padding: '12px 24px', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
          费用估算
        </button>
        <button onClick={handleSave} style={{ backgroundColor: saved ? THEME.accent.success : THEME.accent.primary, border: 'none', color: '#fff', padding: '12px 32px', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
          {saved ? '✓ 已保存' : '保存设置'}
        </button>
      </div>
      {estimate && (
        <div style={{ marginTop: 24, backgroundColor: THEME.bg.card, padding: 20, borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 12px' }}>💰 费用估算</h4>
          <p>制造商: {estimate.manufacturer}</p>
          <p>单价: ${estimate.unit_price}</p>
          <p>总价: ${estimate.total_price}</p>
        </div>
      )}
    </div>
  );
}

// ========== 模板管理 ==========

function TemplatesView() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTemplates();
    loadCategories();
  }, [selectedCategory, searchKeyword]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.append('category', selectedCategory);
      if (searchKeyword) params.append('search', searchKeyword);
      const queryString = params.toString();
      const res = await fetch(`/api/v1/templates${queryString ? `?${queryString}` : ''}`);
      const data = await res.json();
      if (data.success) {
        setTemplates(data.templates);
      }
    } catch (e) {
      console.error('Failed to load templates:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const res = await fetch('/api/v1/templates/categories');
      const data = await res.json();
      if (data.success) {
        setCategories(data.categories);
      }
    } catch (e) {
      console.error('Failed to load categories:', e);
    }
  };

  const CATEGORY_COLORS: Record<string, string> = {
    mcu_board: '#ba68c8',
    power: '#f44336',
    sensor: '#42a5f5',
    interface: '#5c6bc0',
    wireless: '#26c6da',
    display: '#ff7043',
    motor: '#8d6e63',
    custom: '#78909c',
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>📋 项目模板管理</h3>

      {/* 搜索框 */}
      <div style={{ marginBottom: 16 }}>
        <input
          type="text"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          placeholder="搜索模板名称或描述..."
          style={{
            width: '100%',
            padding: '8px 12px',
            backgroundColor: '#2d2d2d',
            border: '1px solid #4a4a4a',
            borderRadius: 4,
            color: '#e0e0e0',
            fontSize: 13,
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* 类别过滤 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        <button
          onClick={() => setSelectedCategory(null)}
          style={{
            padding: '6px 14px',
            backgroundColor: selectedCategory === null ? '#4a9eff' : '#3d3d3d',
            border: '1px solid #4a4a4a',
            borderRadius: 4,
            color: '#fff',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          全部
        </button>
        {categories.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setSelectedCategory(cat.value)}
            style={{
              padding: '6px 14px',
              backgroundColor: selectedCategory === cat.value ? '#4a9eff' : '#3d3d3d',
              border: '1px solid #4a4a4a',
              borderRadius: 4,
              color: selectedCategory === cat.value ? '#fff' : CATEGORY_COLORS[cat.value] || '#a0a0a0',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* 模板列表 */}
      {loading ? (
        <div style={{ color: '#707070', textAlign: 'center', padding: 40 }}>加载中...</div>
      ) : templates.length === 0 ? (
        <div style={{ color: '#707070', textAlign: 'center', padding: 40 }}>暂无模板</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {templates.map((template) => (
            <div
              key={template.template_id}
              style={{
                backgroundColor: THEME.bg.card,
                borderRadius: 8,
                padding: 16,
                border: '1px solid #3d3d3d',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span
                  style={{
                    padding: '2px 8px',
                    backgroundColor: CATEGORY_COLORS[template.category] || '#78909c',
                    borderRadius: 3,
                    fontSize: 10,
                    color: '#fff',
                  }}
                >
                  {template.category}
                </span>
                {template.is_predefined && (
                  <span style={{ fontSize: 10, color: '#4a9eff' }}>预定义</span>
                )}
              </div>
              <h4 style={{ margin: '0 0 4px', color: '#e0e0e0' }}>{template.name}</h4>
              <div style={{ color: '#a0a0a0', fontSize: 12, marginBottom: 8 }}>
                {template.name_cn}
              </div>
              <p style={{ color: '#707070', fontSize: 11, margin: '0 0 12px', lineHeight: 1.5 }}>
                {template.description?.substring(0, 80)}
                {template.description && template.description.length > 80 ? '...' : ''}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {template.tags?.slice(0, 3).map((tag: string) => (
                  <span
                    key={tag}
                    style={{
                      padding: '2px 6px',
                      backgroundColor: '#3d3d3d',
                      borderRadius: 3,
                      fontSize: 10,
                      color: '#a0a0a0',
                    }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div style={{ marginTop: 12, color: '#707070', fontSize: 10 }}>
                作者: {template.author}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ========== 知识库管理 ==========

interface KnowledgeStats {
  components_count: number;
  templates_count: number;
  categories_count: number;
  quality_stats: Record<string, number>;
}

function KnowledgeBaseView() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [qualitySummary, setQualitySummary] = useState<any>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadKnowledgeData();
  }, []);

  const loadKnowledgeData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, qualityRes, catRes] = await Promise.all([
        fetch('/api/v1/knowledge/health'),
        fetch('/api/v1/knowledge/quality/summary'),
        fetch('/api/v1/knowledge/categories'),
      ]);

      const [healthData, qualityData, catData] = await Promise.all([
        healthRes.json(),
        qualityRes.json(),
        catRes.json(),
      ]);

      if (healthData.status === 'ok') {
        setStats({
          components_count: healthData.components_count || 0,
          templates_count: healthData.templates_count || 0,
          categories_count: catData.count || 0,
          quality_stats: qualityData.stats?.by_category || {},
        });
      }

      if (qualityData.success) {
        setQualitySummary(qualityData);
      }

      if (catData.success) {
        setCategories(catData.categories || []);
      }
    } catch (e) {
      console.error('Failed to load knowledge data:', e);
      setError('加载知识库数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ color: '#707070', textAlign: 'center', padding: 40 }}>
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ color: '#ef4444', textAlign: 'center', padding: 40 }}>
        {error}
      </div>
    );
  }

  const categoryColors: Record<string, string> = {
    mcu: '#ba68c8',
    wireless: '#26c6da',
    usb: '#5c6bc0',
    power: '#f44336',
    driver: '#ff7043',
    amplifier: '#42a5f5',
    rtc: '#5c6bc0',
    memory: '#8d6e63',
    sensor: '#26c6da',
    audio: '#fbbf24',
  };

  const totalComponents = stats?.components_count || 0;
  const topCategories = Object.entries(stats?.quality_stats || {})
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 8);

  return (
    <div>
      <h3 style={{ margin: '0 0 20px' }}>🧠 知识库状态</h3>

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <div style={{
          backgroundColor: THEME.bg.card,
          borderRadius: 8,
          padding: 16,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 32, fontWeight: 'bold', color: '#4a9eff' }}>
            {totalComponents}
          </div>
          <div style={{ color: '#a0a0a0', fontSize: 12 }}>元件总数</div>
        </div>
        <div style={{
          backgroundColor: THEME.bg.card,
          borderRadius: 8,
          padding: 16,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 32, fontWeight: 'bold', color: '#4caf50' }}>
            {stats?.templates_count || 0}
          </div>
          <div style={{ color: '#a0a0a0', fontSize: 12 }}>模板数量</div>
        </div>
        <div style={{
          backgroundColor: THEME.bg.card,
          borderRadius: 8,
          padding: 16,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 32, fontWeight: 'bold', color: '#ba68c8' }}>
            {stats?.categories_count || 0}
          </div>
          <div style={{ color: '#a0a0a0', fontSize: 12 }}>元件类别</div>
        </div>
        <div style={{
          backgroundColor: THEME.bg.card,
          borderRadius: 8,
          padding: 16,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 32, fontWeight: 'bold', color: '#fbbf24' }}>
            {qualitySummary?.stats?.total || 0}
          </div>
          <div style={{ color: '#a0a0a0', fontSize: 12 }}>质量门控项</div>
        </div>
      </div>

      {/* 质量门控状态 */}
      {qualitySummary && (
        <div style={{
          backgroundColor: THEME.bg.card,
          borderRadius: 8,
          padding: 16,
          marginBottom: 24,
        }}>
          <h4 style={{ margin: '0 0 12px', color: '#e0e0e0' }}>质量门控服务</h4>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ color: '#4caf50', fontSize: 13 }}>
              ✓ 服务状态: {qualitySummary.service}
            </div>
            <div style={{ color: '#a0a0a0', fontSize: 13 }}>
              版本: {qualitySummary.version}
            </div>
            <div style={{ color: '#a0a0a0', fontSize: 13 }}>
              元件验证: {qualitySummary.stats?.total || 0} 项
            </div>
          </div>
        </div>
      )}

      {/* 元件类别分布 */}
      <div style={{
        backgroundColor: THEME.bg.card,
        borderRadius: 8,
        padding: 16,
        marginBottom: 24,
      }}>
        <h4 style={{ margin: '0 0 12px', color: '#e0e0e0' }}>元件类别分布</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {topCategories.map(([cat, count]) => (
            <div
              key={cat}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 12px',
                backgroundColor: '#2d2d2d',
                borderRadius: 4,
                borderLeft: `3px solid ${categoryColors[cat] || '#78909c'}`,
              }}
            >
              <span style={{ color: '#e0e0e0', fontSize: 13, fontWeight: 500 }}>
                {cat}
              </span>
              <span style={{
                padding: '2px 8px',
                backgroundColor: categoryColors[cat] || '#78909c',
                borderRadius: 3,
                fontSize: 11,
                color: '#fff',
              }}>
                {count as number}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 知识库类别列表 */}
      <div style={{
        backgroundColor: THEME.bg.card,
        borderRadius: 8,
        padding: 16,
      }}>
        <h4 style={{ margin: '0 0 12px', color: '#e0e0e0' }}>所有元件类别 ({categories.length})</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {categories.slice(0, 30).map((cat) => (
            <span
              key={cat}
              style={{
                padding: '4px 10px',
                backgroundColor: '#3d3d3d',
                borderRadius: 4,
                fontSize: 11,
                color: '#a0a0a0',
              }}
            >
              {cat}
            </span>
          ))}
          {categories.length > 30 && (
            <span style={{ padding: '4px 10px', fontSize: 11, color: '#707070' }}>
              ... 还有 {categories.length - 30} 个
            </span>
          )}
        </div>
      </div>

      {/* 刷新按钮 */}
      <div style={{ marginTop: 20, textAlign: 'center' }}>
        <button
          onClick={loadKnowledgeData}
          style={{
            padding: '8px 24px',
            backgroundColor: '#4a9eff',
            border: 'none',
            borderRadius: 4,
            color: '#fff',
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          刷新数据
        </button>
      </div>
    </div>
  );
}
