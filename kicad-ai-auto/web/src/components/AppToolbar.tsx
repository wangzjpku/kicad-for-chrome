/**
 * AppToolbar 组件
 * 应用工具栏
 */

import React from 'react';

interface ToolbarButton {
  id: string;
  icon: string;
  label: string;
  action: string;
}

interface AppToolbarProps {
  currentTool: string;
  onToolChange: (tool: string) => void;
  onAction: (action: string) => void;
}

const toolbarButtons: ToolbarButton[] = [
  { id: 'select', icon: '⬚', label: '选择', action: 'select' },
  { id: 'move', icon: '✋', label: '移动', action: 'move' },
  { id: 'route', icon: '📍', label: '布线', action: 'route' },
  { id: 'via', icon: '⚫', label: '过孔', action: 'via' },
  { id: 'zone', icon: '🟩', label: '铺铜', action: 'zone' },
  { id: 'measure', icon: '📏', label: '测量', action: 'measure' },
  { id: 'annotation', icon: '🔢', label: '标注', action: 'annotation' },
];

const AppToolbar: React.FC<AppToolbarProps> = ({
  currentTool,
  onToolChange,
  onAction
}) => {
  return (
    <div
      style={{
        height: 40,
        backgroundColor: '#252526',
        borderBottom: '1px solid #333',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        gap: 4,
      }}
    >
      {toolbarButtons.map((btn) => (
        <button
          key={btn.id}
          onClick={() => {
            onToolChange(btn.id);
            onAction(btn.action);
          }}
          title={btn.label}
          style={{
            width: 32,
            height: 32,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: currentTool === btn.id ? '#4a9eff' : 'transparent',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 16,
            color: currentTool === btn.id ? '#fff' : '#ccc',
          }}
        >
          {btn.icon}
        </button>
      ))}

      {/* 分隔线 */}
      <div style={{ width: 1, height: 24, backgroundColor: '#444', margin: '0 8px' }} />

      {/* 视图切换 */}
      <button
        onClick={() => onAction('view2d')}
        title="2D 视图"
        style={{
          padding: '4px 12px',
          backgroundColor: '#2d2d2d',
          border: '1px solid #444',
          borderRadius: 4,
          color: '#ccc',
          cursor: 'pointer',
          fontSize: 12,
        }}
      >
        2D
      </button>
      <button
        onClick={() => onAction('view3d')}
        title="3D 视图"
        style={{
          padding: '4px 12px',
          backgroundColor: '#2d2d2d',
          border: '1px solid #444',
          borderRadius: 4,
          color: '#ccc',
          cursor: 'pointer',
          fontSize: 12,
        }}
      >
        3D
      </button>
    </div>
  );
};

export default AppToolbar;
