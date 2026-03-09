/**
 * AppMenu 组件
 * 应用菜单栏
 */

import React, { useState } from 'react';

interface MenuItem {
  id: string;
  label: string;
  shortcut?: string;
  action?: string;
  separator?: boolean;
  disabled?: boolean;
}

interface MenuCategory {
  id: string;
  label: string;
  items: MenuItem[];
}

interface AppMenuProps {
  onAction: (action: string) => void;
}

// 菜单配置
const menuCategories: MenuCategory[] = [
  {
    id: 'file',
    label: '文件',
    items: [
      { id: 'new-project', label: '新建项目', shortcut: 'Ctrl+N', action: 'newProject' },
      { id: 'open-project', label: '打开项目', shortcut: 'Ctrl+O', action: 'openProject' },
      { id: 'sep1', label: '', separator: true },
      { id: 'save', label: '保存', shortcut: 'Ctrl+S', action: 'save' },
      { id: 'export-gerber', label: '导出 Gerber', action: 'exportGerber' },
      { id: 'export-bom', label: '导出 BOM', action: 'exportBOM' },
    ],
  },
  {
    id: 'edit',
    label: '编辑',
    items: [
      { id: 'undo', label: '撤销', shortcut: 'Ctrl+Z', action: 'undo' },
      { id: 'redo', label: '重做', shortcut: 'Ctrl+Y', action: 'redo' },
      { id: 'sep1', label: '', separator: true },
      { id: 'select-all', label: '全选', shortcut: 'Ctrl+A', action: 'selectAll' },
      { id: 'delete', label: '删除', shortcut: 'Delete', action: 'delete' },
    ],
  },
  {
    id: 'view',
    label: '视图',
    items: [
      { id: 'zoom-in', label: '放大', shortcut: 'Ctrl++', action: 'zoomIn' },
      { id: 'zoom-out', label: '缩小', shortcut: 'Ctrl+-', action: 'zoomOut' },
      { id: 'zoom-fit', label: '适应窗口', shortcut: 'Ctrl+0', action: 'zoomFit' },
      { id: 'sep1', label: '', separator: true },
      { id: 'view-2d', label: '2D 视图', action: 'view2D' },
      { id: 'view-3d', label: '3D 视图', action: 'view3D' },
    ],
  },
  {
    id: 'tools',
    label: '工具',
    items: [
      { id: 'run-drc', label: '运行 DRC', shortcut: 'F9', action: 'runDRC' },
      { id: 'run-erc', label: '运行 ERC', shortcut: 'F8', action: 'runERC' },
      { id: 'sep1', label: '', separator: true },
      { id: 'auto-route', label: '自动布线', shortcut: 'A', action: 'autoRoute' },
    ],
  },
  {
    id: 'help',
    label: '帮助',
    items: [
      { id: 'about', label: '关于', action: 'about' },
    ],
  },
];

const AppMenu: React.FC<AppMenuProps> = ({ onAction }) => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  const handleMenuClick = (menuId: string) => {
    setActiveMenu(activeMenu === menuId ? null : menuId);
  };

  const handleItemClick = (action?: string) => {
    if (action) {
      onAction(action);
    }
    setActiveMenu(null);
  };

  return (
    <div
      style={{
        height: 28,
        backgroundColor: '#252526',
        borderBottom: '1px solid #333',
        display: 'flex',
        alignItems: 'center',
        padding: '0 4px',
      }}
    >
      {menuCategories.map((category) => (
        <div key={category.id} style={{ position: 'relative' }}>
          {/* 菜单按钮 */}
          <button
            onClick={() => handleMenuClick(category.id)}
            onMouseEnter={() => activeMenu && setActiveMenu(category.id)}
            style={{
              padding: '4px 12px',
              backgroundColor: activeMenu === category.id ? '#333' : 'transparent',
              border: 'none',
              color: '#ccc',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {category.label}
          </button>

          {/* 下拉菜单 */}
          {activeMenu === category.id && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                minWidth: 200,
                backgroundColor: '#252526',
                border: '1px solid #444',
                borderRadius: 4,
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                zIndex: 1000,
              }}
            >
              {category.items.map((item) =>
                item.separator ? (
                  <div
                    key={item.id}
                    style={{ height: 1, backgroundColor: '#444', margin: '4px 8px' }}
                  />
                ) : (
                  <button
                    key={item.id}
                    onClick={() => handleItemClick(item.action)}
                    disabled={item.disabled}
                    style={{
                      width: '100%',
                      padding: '8px 16px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: item.disabled ? '#666' : '#ccc',
                      cursor: item.disabled ? 'not-allowed' : 'pointer',
                      fontSize: 13,
                      display: 'flex',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                    }}
                  >
                    <span>{item.label}</span>
                    {item.shortcut && (
                      <span style={{ color: '#666', fontSize: 11 }}>{item.shortcut}</span>
                    )}
                  </button>
                )
              )}
            </div>
          )}
        </div>
      ))}

      {/* 点击外部关闭菜单 */}
      {activeMenu && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 999,
          }}
          onClick={() => setActiveMenu(null)}
        />
      )}
    </div>
  );
};

export default AppMenu;
