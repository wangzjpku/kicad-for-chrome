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
        <span style={{ fontSize: 24 }}>🔌</span>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: '#fff', margin: 0 }}>
          KiCad AI Auto
        </h1>
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
