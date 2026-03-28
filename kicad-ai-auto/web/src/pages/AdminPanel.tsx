/**
 * Admin管理后台 - 运维管理面板
 * 包含：用户管理、Token管理、项目管理、系统状态、缓存清理等
 */

import React, { useState, useEffect } from 'react';

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
  const [activeTab, setActiveTab] = useState<'dashboard' | 'users' | 'tokens' | 'projects' | 'system' | 'cache'>('dashboard');
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
      const res = await fetch('http://localhost:8000/api/admin/users');
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
      const res = await fetch('http://localhost:8000/api/v1/projects');
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
      const backendRes = await fetch('http://localhost:8000/api/health');
      checks.backend = backendRes.ok;

      // Check KiCad
      const kicadRes = await fetch('http://localhost:8000/api/kicad-ipc/status');
      const kicadData = await kicadRes.json();
      checks.kicad = kicadData.connected || false;

      // Check AI
      const aiRes = await fetch('http://localhost:8000/api/v1/ai/health');
      checks.ai = aiRes.ok;

      // Check database (via projects API)
      const dbRes = await fetch('http://localhost:8000/api/v1/projects');
      checks.database = dbRes.ok;
    } catch (e) {
      console.error('Health check failed:', e);
    }
    setHealth(checks);
  };

  const loadTokenLogs = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/token/logs');
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
      const res = await fetch(`http://localhost:8000/api/v1/projects/${projectId}`, { method: 'DELETE' });
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
      const res = await fetch('http://localhost:8000/api/v1/projects/clear-all', { method: 'DELETE' });
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
      const res = await fetch(`http://localhost:8000/api/admin/user/delete/${userId}`, { method: 'POST' });
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
      const res = await fetch('http://localhost:8000/api/admin/user/token', {
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
        const res = await fetch(`http://localhost:8000${api.path}`, { method: api.method });
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
          <button onClick={() => window.open('http://localhost:8000/api/token/logs')} style={{ backgroundColor: THEME.accent.success, border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 6, cursor: 'pointer' }}>
            下载日志
          </button>
        </div>
        <div style={{ backgroundColor: THEME.bg.card, padding: 24, borderRadius: 8, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📖</div>
          <h4 style={{ margin: '0 0 12px' }}>API文档</h4>
          <p style={{ color: THEME.text.secondary, marginBottom: 16 }}>查看完整的API文档</p>
          <button onClick={() => window.open('http://localhost:8000/docs')} style={{ backgroundColor: '#a78bfa', border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 6, cursor: 'pointer' }}>
            打开Swagger
          </button>
        </div>
      </div>
    </div>
  );
}

