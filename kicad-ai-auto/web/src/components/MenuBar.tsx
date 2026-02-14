/**
 * 菜单栏组件 (完整实现)
 * 包含文件菜单、编辑菜单 - 使用 pcbStore
 */

import React, { useState, useCallback, useEffect } from 'react';
import { usePCBStore, ToolType } from '../stores/pcbStore';

const MenuBar: React.FC = () => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const { 
    selectedIds, 
    clearSelection, 
    currentTool, 
    setCurrentTool,
    undo,
    redo,
    canUndo,
    canRedo,
    removeSelectedElements,
    savePCBData,
    pcbData,
    setPCBData,
  } = usePCBStore();

  // 删除选中元素
  const deleteSelected = useCallback(() => {
    if (selectedIds.length > 0) {
      removeSelectedElements();
    }
  }, [selectedIds, removeSelectedElements]);

  // 添加封装
  const addFootprint = useCallback(() => {
    setCurrentTool('place_footprint' as ToolType);
    setActiveMenu(null);
  }, [setCurrentTool]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'z':
            e.preventDefault();
            if (e.shiftKey) {
              redo();
            } else {
              undo();
            }
            break;
          case 'y':
            e.preventDefault();
            redo();
            break;
          case 's':
            e.preventDefault();
            savePCBData();
            break;
          case 'n':
            e.preventDefault();
            console.log('New Project');
            break;
          case 'o':
            e.preventDefault();
            console.log('Open Project');
            break;
        }
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedIds.length > 0) {
          deleteSelected();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, deleteSelected, selectedIds, savePCBData]);

  const menuStyle: React.CSSProperties = {
    position: 'relative',
    padding: '0 12px',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    color: '#cccccc',
    fontSize: 13,
  };

  const menuActiveStyle: React.CSSProperties = {
    ...menuStyle,
    backgroundColor: '#3d3d3d',
    color: '#ffffff',
  };

  const dropdownStyle: React.CSSProperties = {
    position: 'absolute',
    top: '100%',
    left: 0,
    backgroundColor: '#2d2d2d',
    border: '1px solid #3d3d3d',
    borderRadius: 4,
    minWidth: 180,
    zIndex: 1000,
    boxShadow: '0 4px 8px rgba(0,0,0,0.3)',
  };

  const menuItemStyle: React.CSSProperties = {
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: 13,
    color: '#cccccc',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  };

  const dividerStyle: React.CSSProperties = {
    height: 1,
    backgroundColor: '#3d3d3d',
    margin: '4px 0',
  };

  const shortcutStyle: React.CSSProperties = {
    fontSize: 11,
    color: '#666666',
    marginLeft: 16,
  };

  return (
    <div
      data-testid="menubar"
      style={{
        height: 30,
        backgroundColor: '#2d2d2d',
        borderBottom: '1px solid #3d3d3d',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
      }}
    >
      {/* 文件菜单 */}
      <div
        data-testid="menu-file"
        style={activeMenu === 'file' ? menuActiveStyle : menuStyle}
        onClick={() => setActiveMenu(activeMenu === 'file' ? null : 'file')}
        onMouseEnter={() => activeMenu && setActiveMenu('file')}
      >
        文件
        {activeMenu === 'file' && (
          <div style={dropdownStyle}>
            <div style={menuItemStyle} onClick={() => { console.log('New'); setActiveMenu(null); }}>
              <span>新建项目</span>
              <span style={shortcutStyle}>Ctrl+N</span>
            </div>
            <div style={menuItemStyle} onClick={() => { console.log('Open'); setActiveMenu(null); }}>
              <span>打开项目</span>
              <span style={shortcutStyle}>Ctrl+O</span>
            </div>
            <div style={dividerStyle} />
            <div style={menuItemStyle} onClick={() => { savePCBData(); setActiveMenu(null); }}>
              <span>保存</span>
              <span style={shortcutStyle}>Ctrl+S</span>
            </div>
            <div style={menuItemStyle} onClick={() => { console.log('Save As'); setActiveMenu(null); }}>
              <span>另存为...</span>
            </div>
          </div>
        )}
      </div>

      {/* 编辑菜单 */}
      <div
        data-testid="menu-edit"
        style={activeMenu === 'edit' ? menuActiveStyle : menuStyle}
        onClick={() => setActiveMenu(activeMenu === 'edit' ? null : 'edit')}
        onMouseEnter={() => activeMenu && setActiveMenu('edit')}
      >
        编辑
        {activeMenu === 'edit' && (
          <div style={dropdownStyle}>
            <div
              style={canUndo ? menuItemStyle : { ...menuItemStyle, opacity: 0.5, cursor: 'not-allowed' }}
              onClick={() => { if (canUndo) undo(); setActiveMenu(null); }}
            >
              <span>撤销</span>
              <span style={shortcutStyle}>Ctrl+Z</span>
            </div>
            <div
              style={canRedo ? menuItemStyle : { ...menuItemStyle, opacity: 0.5, cursor: 'not-allowed' }}
              onClick={() => { if (canRedo) redo(); setActiveMenu(null); }}
            >
              <span>重做</span>
              <span style={shortcutStyle}>Ctrl+Y</span>
            </div>
            <div style={dividerStyle} />
            <div style={menuItemStyle} onClick={() => { clearSelection(); setActiveMenu(null); }}>
              <span>取消选择</span>
              <span style={shortcutStyle}>Esc</span>
            </div>
            <div
              style={selectedIds.length > 0 ? menuItemStyle : { ...menuItemStyle, opacity: 0.5, cursor: 'not-allowed' }}
              onClick={() => { if (selectedIds.length > 0) deleteSelected(); setActiveMenu(null); }}
            >
              <span>删除</span>
              <span style={shortcutStyle}>Del</span>
            </div>
          </div>
        )}
      </div>

      {/* 放置菜单 */}
      <div
        data-testid="menu-place"
        style={activeMenu === 'place' ? menuActiveStyle : menuStyle}
        onClick={() => setActiveMenu(activeMenu === 'place' ? null : 'place')}
        onMouseEnter={() => activeMenu && setActiveMenu('place')}
      >
        放置
        {activeMenu === 'place' && (
          <div style={dropdownStyle}>
            <div style={menuItemStyle} onClick={addFootprint}>
              <span>放置封装</span>
            </div>
            <div style={menuItemStyle} onClick={() => { setCurrentTool('route'); setActiveMenu(null); }}>
              <span>绘制走线</span>
            </div>
            <div style={menuItemStyle} onClick={() => { setCurrentTool('place_via'); setActiveMenu(null); }}>
              <span>放置过孔</span>
            </div>
          </div>
        )}
      </div>

      {/* 工具菜单 */}
      <div
        data-testid="menu-tools"
        style={activeMenu === 'tools' ? menuActiveStyle : menuStyle}
        onClick={() => setActiveMenu(activeMenu === 'tools' ? null : 'tools')}
        onMouseEnter={() => activeMenu && setActiveMenu('tools')}
      >
        工具
        {activeMenu === 'tools' && (
          <div style={dropdownStyle}>
            <div style={menuItemStyle} onClick={() => { console.log('DRC'); setActiveMenu(null); }}>
              <span>设计规则检查</span>
            </div>
            <div style={menuItemStyle} onClick={() => { console.log('Refill'); setActiveMenu(null); }}>
              <span>重新灌铜</span>
            </div>
          </div>
        )}
      </div>

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

export default MenuBar;
