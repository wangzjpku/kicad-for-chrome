/**
 * AppHeader 组件
 * 应用顶部标题栏
 */

import React from 'react';

interface AppHeaderProps {
  backendConnected: boolean;
  onToggleConnection: () => void;
}

const AppHeader: React.FC<AppHeaderProps> = ({
  backendConnected,
  onToggleConnection
}) => {
  return (
    <header
      style={{
        height: 48,
        backgroundColor: '#1e1e1e',
        borderBottom: '1px solid #333',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
      }}
    >
      {/* 左侧：Logo 和标题 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 28,
          height: 28,
          background: 'linear-gradient(135deg, #4a9eff 0%, #2563eb 100%)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: 14,
          color: '#fff',
        }}>
          智
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ fontSize: 16, fontWeight: 600, color: '#fff', margin: 0 }}>
            智板工具
          </h1>
          <span style={{ fontSize: 10, color: '#888' }}>
            北京懿建达出品
          </span>
        </div>
      </div>

      {/* 右侧：状态指示 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <button
          onClick={onToggleConnection}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 12px',
            backgroundColor: '#2d2d2d',
            border: '1px solid #444',
            borderRadius: 4,
            color: '#ccc',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: backendConnected ? '#4caf50' : '#f44336',
            }}
          />
          {backendConnected ? '已连接' : '未连接'}
        </button>
      </div>
    </header>
  );
};

export default AppHeader;
