/**
 * App.tsx - Professional PCB Editor UI
 * 采用专业 PCB 软件设计风格 (KiCad/Altium)
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import PCBEditor from './editors/PCBEditor';
import SchematicEditor from './editors/SchematicEditor';
import ProjectList from './pages/ProjectList';
import AIChatAssistant from './components/AIChatAssistant';
import { Project } from './types';
import { usePCBStore } from './stores/pcbStore';
import { useSchematicStore } from './stores/schematicStore';
import { exportApi, drcApi } from './services/api';

type EditorType = 'pcb' | 'schematic';
type ViewType = 'project-list' | 'editor';

// 专业配色方案 - KiCad 风格
const THEME = {
  // 主色调
  bg: {
    primary: '#323232',      // 主背景深灰
    secondary: '#3d3d3d',    // 次要背景
    tertiary: '#454545',      // 第三级背景
    toolbar: '#2d2d2d',     // 工具栏
    panel: '#383838',         // 面板
    canvas: '#1e1e1e',       // 画布背景
  },
  // 边框色
  border: {
    default: '#4a4a4a',
    light: '#555555',
    dark: '#333333',
  },
  // 文字色
  text: {
    primary: '#e0e0e0',
    secondary: '#a0a0a0',
    muted: '#707070',
    accent: '#4a9eff',
  },
  // 强调色
  accent: {
    primary: '#4a9eff',    // 蓝色 - 主要按钮
    success: '#4caf50',     // 绿色 - 成功
    warning: '#ff9800',     // 橙色 - 警告
    error: '#f44336',      // 红色 - 错误
  },
  // 交互状态
  hover: {
    default: '#4a4a4a',
    active: '#555555',
  }
};

function App() {
  const [currentView, setCurrentView] = useState<ViewType>('project-list');
  const [editorType, setEditorType] = useState<EditorType>('pcb');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(true);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const {
    setCurrentProject: setPCBProject,
    loadPCBData,
    savePCBData,
    undo: pcbUndo,
    redo: pcbRedo,
    currentTool: pcbCurrentTool,
    setCurrentTool: setPcbCurrentTool,
    zoom: pcbZoom,
    setZoom: setPcbZoom,
    gridSize: pcbGridSize,
    setGridSize: setPcbGridSize,
    snapToGrid: pcbSnapToGrid,
    setSnapToGrid: setPcbSnapToGrid,
    rotateSelectedFootprints: rotatePCBSelected,
    mirrorSelectedFootprints: mirrorPCBSelected,
    selectedIds: pcbSelectedIds
  } = usePCBStore();
  const {
    setCurrentProject: setSchematicProject,
    loadSchematicData,
    currentTool: schematicCurrentTool,
    setCurrentTool: setSchematicCurrentTool,
    zoom: schematicZoom,
    setZoom: setSchematicZoom,
    undo: schematicUndo,
    redo: schematicRedo,
    rotateSelectedComponents: rotateSchematicSelected,
    mirrorSelectedComponents: mirrorSchematicSelected,
    selectedIds: schematicSelectedIds
  } = useSchematicStore();

  // 根据当前编辑器类型获取对应的工具和操作方法
  const currentTool = editorType === 'pcb' ? pcbCurrentTool : schematicCurrentTool;
  const setCurrentTool = editorType === 'pcb' ? setPcbCurrentTool : setSchematicCurrentTool;
  const zoom = editorType === 'pcb' ? pcbZoom : schematicZoom;
  const setZoom = editorType === 'pcb' ? setPcbZoom : setSchematicZoom;
  const gridSize = editorType === 'pcb' ? pcbGridSize : 1;
  const setGridSize = editorType === 'pcb' ? setPcbGridSize : () => {};
  const snapToGrid = editorType === 'pcb' ? pcbSnapToGrid : false;
  const setSnapToGrid = editorType === 'pcb' ? setPcbSnapToGrid : () => {};
  const undo = editorType === 'pcb' ? pcbUndo : schematicUndo;
  const redo = editorType === 'pcb' ? pcbRedo : schematicRedo;

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleOpenProject = async (project: Project) => {
    setPCBProject(project);
    setSchematicProject(project);
    setCurrentProject(project);
    setCurrentView('editor');

    // 加载PCB和原理图数据
    if (project.id) {
      await loadPCBData(project.id);
      await loadSchematicData(project.id);
    }
  };

  const handleBackToList = () => {
    setCurrentView('project-list');
    setCurrentProject(null);
  };

  const handleSwitchEditor = (type: EditorType) => {
    setEditorType(type);
  };

  // 剪切板状态
  const [clipboard, setClipboard] = useState<any>(null);

  // 底部面板标签状态
  const [activeBottomTab, setActiveBottomTab] = useState<'messages' | 'drc' | 'erc' | 'bom'>('messages');
  const [bottomPanelMessages, setBottomPanelMessages] = useState<string[]>(['[20:25:00] 系统就绪', '[20:25:01] 等待 KiCad 连接...']);

  // 添加消息到底部面板
  const addMessage = useCallback((msg: string) => {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    setBottomPanelMessages(prev => [...prev.slice(-49), `[${timestamp}] ${msg}`]);
  }, []);

  // 菜单操作处理
  const handleMenuAction = useCallback(async (action: string) => {
    setActiveMenu(null);

    switch (action) {
      case 'new':
        handleBackToList();
        addMessage('新建项目');
        break;
      case 'open':
        handleBackToList();
        addMessage('打开项目');
        break;
      case 'save':
        if (currentProject?.id) {
          await savePCBData();
          addMessage('项目已保存');
        }
        break;
      case 'saveas':
        addMessage('另存为功能开发中...');
        alert('另存为功能开发中');
        break;
      case 'undo':
        undo();
        addMessage('撤销操作');
        break;
      case 'redo':
        redo();
        addMessage('重做操作');
        break;
      case 'cut':
        if (editorType === 'pcb') {
          const { selectedIds, pcbData } = usePCBStore.getState();
          if (selectedIds.length > 0 && pcbData) {
            const selectedFootprints = pcbData.footprints.filter(fp => selectedIds.includes(fp.id));
            setClipboard({ type: 'footprints', data: selectedFootprints });
            usePCBStore.getState().removeSelectedElements();
            addMessage(`剪切 ${selectedIds.length} 个元素`);
          }
        } else {
          const { selectedIds, schematicData } = useSchematicStore.getState();
          if (selectedIds.length > 0 && schematicData) {
            const selectedComponents = schematicData.components.filter(c => selectedIds.includes(c.id));
            setClipboard({ type: 'components', data: selectedComponents });
            useSchematicStore.getState().removeSelectedElements();
            addMessage(`剪切 ${selectedIds.length} 个元素`);
          }
        }
        break;
      case 'copy':
        if (editorType === 'pcb') {
          const { selectedIds, pcbData } = usePCBStore.getState();
          if (selectedIds.length > 0 && pcbData) {
            const selectedFootprints = pcbData.footprints.filter(fp => selectedIds.includes(fp.id));
            setClipboard({ type: 'footprints', data: selectedFootprints });
            addMessage(`复制 ${selectedIds.length} 个元素`);
          }
        } else {
          const { selectedIds, schematicData } = useSchematicStore.getState();
          if (selectedIds.length > 0 && schematicData) {
            const selectedComponents = schematicData.components.filter(c => selectedIds.includes(c.id));
            setClipboard({ type: 'components', data: selectedComponents });
            addMessage(`复制 ${selectedIds.length} 个元素`);
          }
        }
        break;
      case 'paste':
        if (clipboard?.type === 'footprints') {
          const { addFootprint, pcbData } = usePCBStore.getState();
          const newIds: string[] = [];
          clipboard.data.forEach((fp: any, idx: number) => {
            const newId = `FP${Date.now()}_${idx}`;
            newIds.push(newId);
            addFootprint({
              ...fp,
              id: newId,
              reference: `${fp.reference}_copy`,
              position: { x: fp.position.x + 10, y: fp.position.y + 10 }
            });
          });
          usePCBStore.getState().setSelectedIds(newIds);
          addMessage(`粘贴 ${clipboard.data.length} 个封装`);
        } else if (clipboard?.type === 'components') {
          const { addComponent } = useSchematicStore.getState();
          const newIds: string[] = [];
          clipboard.data.forEach((comp: any, idx: number) => {
            const newId = `comp-${Date.now()}_${idx}`;
            newIds.push(newId);
            addComponent({
              ...comp,
              id: newId,
              reference: `${comp.reference}_copy`,
              position: { x: comp.position.x + 10, y: comp.position.y + 10 }
            });
          });
          useSchematicStore.getState().setSelectedIds(newIds);
          addMessage(`粘贴 ${clipboard.data.length} 个元件`);
        }
        break;
      case 'delete':
        if (editorType === 'pcb') {
          const { selectedIds, removeSelectedElements } = usePCBStore.getState();
          if (selectedIds.length > 0) {
            removeSelectedElements();
            addMessage(`删除 ${selectedIds.length} 个元素`);
          }
        } else {
          const { selectedIds, removeSelectedElements } = useSchematicStore.getState();
          if (selectedIds.length > 0) {
            removeSelectedElements();
            addMessage(`删除 ${selectedIds.length} 个元素`);
          }
        }
        break;
      case 'zoom_in':
        setZoom(Math.min(zoom * 1.2, 10));
        addMessage('放大视图');
        break;
      case 'zoom_out':
        setZoom(Math.max(zoom / 1.2, 0.1));
        addMessage('缩小视图');
        break;
      case 'zoom_fit':
        setZoom(1);
        if (editorType === 'pcb') {
          usePCBStore.getState().setPan({ x: 0, y: 0 });
        } else {
          useSchematicStore.getState().setPan({ x: 100, y: 50 });
        }
        addMessage('适应窗口');
        break;
      case 'toggle_left':
        setSidebarCollapsed(!sidebarCollapsed);
        addMessage(sidebarCollapsed ? '显示左侧面板' : '隐藏左侧面板');
        break;
      case 'toggle_right':
        setRightPanelCollapsed(!rightPanelCollapsed);
        addMessage(rightPanelCollapsed ? '显示右侧面板' : '隐藏右侧面板');
        break;
      case 'place_footprint':
        setCurrentTool('place_footprint');
        addMessage('放置封装模式');
        break;
      case 'route':
        setCurrentTool('route');
        addMessage('布线模式');
        break;
      case 'place_via':
        setCurrentTool('place_via');
        addMessage('放置过孔模式');
        break;
      case 'place_zone':
        addMessage('放置铜区功能开发中...');
        alert('放置铜区功能开发中');
        break;
      case 'place_text':
        addMessage('放置文本功能开发中...');
        alert('放置文本功能开发中');
        break;
      case 'drc':
        if (currentProject?.id) {
          try {
            setActiveBottomTab('drc');
            const result = await drcApi.runDRC(currentProject.id);
            console.log('DRC Result:', result);
            addMessage(`DRC检查完成: ${result.data?.errorCount || 0} 错误, ${result.data?.warningCount || 0} 警告`);
            alert(`DRC检查完成: ${result.data?.errorCount || 0} 错误, ${result.data?.warningCount || 0} 警告`);
          } catch (e) {
            console.error('DRC failed:', e);
            addMessage('DRC检查失败');
          }
        }
        break;
      case 'refill':
        addMessage('重新灌铜功能开发中...');
        alert('重新灌铜功能开发中');
        break;
      case 'gerber':
        if (currentProject?.id) {
          try {
            setActiveBottomTab('bom');
            const result = await exportApi.exportGerber(currentProject.id);
            console.log('Gerber export:', result);
            addMessage('Gerber导出成功');
            alert('Gerber导出成功！');
          } catch (e) {
            console.error('Gerber export failed:', e);
            addMessage('Gerber导出失败');
          }
        }
        break;
      case 'bom':
        if (currentProject?.id) {
          try {
            setActiveBottomTab('bom');
            const result = await exportApi.exportBOM(currentProject.id);
            console.log('BOM export:', result);
            addMessage('BOM导出成功');
            alert('BOM导出成功！');
          } catch (e) {
            console.error('BOM export failed:', e);
            addMessage('BOM导出失败');
          }
        }
        break;
      case 'dxf':
        addMessage('导出DXF功能开发中...');
        alert('导出DXF功能开发中');
        break;
      case 'manual':
        addMessage('打开使用手册...');
        window.open('https://docs.kicad.org/', '_blank');
        break;
      case 'about':
        addMessage('关于 KiCad Web Editor');
        alert('KiCad Web Editor v0.9.0\n基于 KiCad 的在线 PCB 设计工具');
        break;
    }
  }, [currentProject, savePCBData, undo, redo, editorType, clipboard, zoom, sidebarCollapsed, rightPanelCollapsed]);

  // 菜单配置
  const menus = [
    {
      label: '文件',
      key: 'file',
      items: [
        { label: '新建项目', action: 'new', shortcut: 'Ctrl+N' },
        { label: '打开项目', action: 'open', shortcut: 'Ctrl+O' },
        { divider: true },
        { label: '保存', action: 'save', shortcut: 'Ctrl+S' },
        { label: '另存为...', action: 'saveas' },
      ]
    },
    {
      label: '编辑',
      key: 'edit',
      items: [
        { label: '撤销', action: 'undo', shortcut: 'Ctrl+Z' },
        { label: '重做', action: 'redo', shortcut: 'Ctrl+Y' },
        { divider: true },
        { label: '剪切', action: 'cut', shortcut: 'Ctrl+X' },
        { label: '复制', action: 'copy', shortcut: 'Ctrl+C' },
        { label: '粘贴', action: 'paste', shortcut: 'Ctrl+V' },
        { divider: true },
        { label: '删除', action: 'delete', shortcut: 'Del' },
      ]
    },
    {
      label: '视图',
      key: 'view',
      items: [
        { label: '放大', action: 'zoom_in', shortcut: 'Ctrl+=' },
        { label: '缩小', action: 'zoom_out', shortcut: 'Ctrl+-' },
        { label: '适应窗口', action: 'zoom_fit', shortcut: 'Ctrl+0' },
        { divider: true },
        { label: '切换左侧面板', action: 'toggle_left' },
        { label: '切换右侧面板', action: 'toggle_right' },
      ]
    },
    {
      label: '放置',
      key: 'place',
      items: [
        { label: '放置封装', action: 'place_footprint' },
        { label: '绘制走线', action: 'route' },
        { label: '放置过孔', action: 'place_via' },
        { label: '放置铜区', action: 'place_zone' },
        { label: '放置文本', action: 'place_text' },
      ]
    },
    {
      label: '工具',
      key: 'tools',
      items: [
        { label: '设计规则检查', action: 'drc', shortcut: 'F5' },
        { label: '重新灌铜', action: 'refill' },
        { divider: true },
        { label: '导出Gerber...', action: 'gerber' },
        { label: '导出BOM...', action: 'bom' },
        { label: '导出DXF...', action: 'dxf' },
      ]
    },
    {
      label: '帮助',
      key: 'help',
      items: [
        { label: '使用手册', action: 'manual' },
        { label: '关于', action: 'about' },
      ]
    },
  ];

  // ===== 项目列表视图 =====
  if (currentView === 'project-list') {
    return (
      <div style={{
        width: '100vw',
        height: '100vh',
        backgroundColor: THEME.bg.primary,
        color: THEME.text.primary,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}>
        {/* 顶部导航栏 */}
        <header style={{
          height: 48,
          backgroundColor: THEME.bg.toolbar,
          borderBottom: `1px solid ${THEME.border.default}`,
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          justifyContent: 'space-between',
        }}>
          {/* 左侧 Logo + 标题 */}
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
              K
            </div>
            <span style={{
              fontSize: 15,
              fontWeight: 600,
              color: THEME.text.primary,
              letterSpacing: '-0.3px',
            }}>
              KiCad Web Editor
            </span>
          </div>

          {/* 右侧状态 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 12, color: THEME.text.muted }}>
              后端服务: <span style={{ color: THEME.accent.success }}>●</span> 已连接
            </span>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              backgroundColor: THEME.bg.tertiary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              color: THEME.text.secondary,
            }}>
              U
            </div>
          </div>
        </header>

        {/* 主内容区 */}
        <div style={{
          height: 'calc(100vh - 48px)',
          overflow: 'auto',
          padding: 32,
        }}>
          <ProjectList onOpenProject={handleOpenProject} />
        </div>
      </div>
    );
  }

  // ===== 编辑器视图 =====
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      backgroundColor: THEME.bg.primary,
      color: THEME.text.primary,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* ===== 顶部菜单栏 ===== */}
      <header
        ref={menuRef}
        style={{
          height: 32,
          backgroundColor: THEME.bg.toolbar,
          borderBottom: `1px solid ${THEME.border.default}`,
          display: 'flex',
          alignItems: 'center',
          padding: '0 8px',
        }}
      >
        {/* 菜单项 */}
        {menus.map((menu) => (
          <div key={menu.key} style={{ position: 'relative' }}>
            <button
              onClick={() => setActiveMenu(activeMenu === menu.key ? null : menu.key)}
              onMouseEnter={() => activeMenu && setActiveMenu(menu.key)}
              style={{
                padding: '4px 12px',
                backgroundColor: activeMenu === menu.key ? THEME.hover.default : 'transparent',
                border: 'none',
                color: activeMenu === menu.key ? THEME.text.primary : THEME.text.secondary,
                fontSize: 13,
                cursor: 'pointer',
                borderRadius: 4,
                transition: 'all 0.15s',
              }}
            >
              {menu.label}
            </button>
            {/* 下拉菜单 */}
            {activeMenu === menu.key && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                backgroundColor: THEME.bg.secondary,
                border: `1px solid ${THEME.border.default}`,
                borderRadius: 4,
                minWidth: 180,
                zIndex: 1000,
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                padding: '4px 0',
              }}>
                {menu.items.map((item, idx) => (
                  'divider' in item ? (
                    <div key={idx} style={{ height: 1, backgroundColor: THEME.border.default, margin: '4px 8px' }} />
                  ) : (
                    <div
                      key={item.action}
                      onClick={() => handleMenuAction(item.action)}
                      style={{
                        padding: '8px 16px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: 13,
                        color: THEME.text.secondary,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = THEME.hover.default;
                        e.currentTarget.style.color = THEME.text.primary;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.color = THEME.text.secondary;
                      }}
                    >
                      <span>{item.label}</span>
                      {'shortcut' in item && <span style={{ fontSize: 11, color: THEME.text.muted, marginLeft: 16 }}>{item.shortcut}</span>}
                    </div>
                  )
                ))}
              </div>
            )}
          </div>
        ))}

        {/* 右侧空白区域 */}
        <div style={{ flex: 1 }} />

        {/* 右侧操作 */}
        <button
          onClick={handleBackToList}
          style={{
            padding: '4px 12px',
            backgroundColor: 'transparent',
            border: 'none',
            color: THEME.text.secondary,
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          ← 返回项目列表
        </button>
      </header>

      {/* ===== 工具栏 ===== */}
      <div style={{
        height: 40,
        backgroundColor: THEME.bg.secondary,
        borderBottom: `1px solid ${THEME.border.default}`,
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        gap: 4,
      }}>
        {/* 编辑器切换 */}
        <div style={{ display: 'flex', gap: 4, paddingRight: 8, borderRight: `1px solid ${THEME.border.default}` }}>
          {[
            { id: 'schematic', label: '原理图', icon: '⚡' },
            { id: 'pcb', label: 'PCB', icon: '🔲' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleSwitchEditor(tab.id as EditorType)}
              style={{
                padding: '6px 14px',
                backgroundColor: editorType === tab.id ? THEME.accent.primary : 'transparent',
                border: 'none',
                borderRadius: 4,
                color: editorType === tab.id ? '#fff' : THEME.text.secondary,
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* 工具分组 */}
        <div style={{ display: 'flex', gap: 2, paddingLeft: 8 }}>
          {[
            { label: '选择', icon: '↖', toolType: 'select' },
            { label: '移动', icon: '✥', toolType: 'move' },
          ].map((tool) => (
            <button
              key={tool.label}
              title={tool.label}
              onClick={() => setCurrentTool(tool.toolType as any)}
              style={{
                width: 32,
                height: 28,
                backgroundColor: currentTool === tool.toolType ? THEME.accent.primary : 'transparent',
                border: 'none',
                borderRadius: 4,
                color: currentTool === tool.toolType ? '#fff' : THEME.text.secondary,
                fontSize: 14,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => {
                if (currentTool !== tool.toolType) {
                  e.currentTarget.style.backgroundColor = THEME.hover.default;
                }
              }}
              onMouseLeave={(e) => {
                if (currentTool !== tool.toolType) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {tool.icon}
            </button>
          ))}
          {/* 旋转按钮 */}
          <button
            title="旋转选中元件 (90°)"
            onClick={() => {
              if (editorType === 'pcb' && pcbSelectedIds.length > 0) {
                rotatePCBSelected(90);
                addMessage(`旋转 ${pcbSelectedIds.length} 个封装 90°`);
              } else if (editorType === 'schematic' && schematicSelectedIds.length > 0) {
                rotateSchematicSelected(90);
                addMessage(`旋转 ${schematicSelectedIds.length} 个元件 90°`);
              } else {
                addMessage('请先选择要旋转的元件');
              }
            }}
            style={{
              width: 32,
              height: 28,
              backgroundColor: 'transparent',
              border: 'none',
              borderRadius: 4,
              color: THEME.text.secondary,
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = THEME.hover.default;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            ↻
          </button>
          {/* 镜像按钮 */}
          <button
            title="镜像选中元件"
            onClick={() => {
              if (editorType === 'pcb' && pcbSelectedIds.length > 0) {
                mirrorPCBSelected('x');
                addMessage(`镜像 ${pcbSelectedIds.length} 个封装`);
              } else if (editorType === 'schematic' && schematicSelectedIds.length > 0) {
                mirrorSchematicSelected();
                addMessage(`镜像 ${schematicSelectedIds.length} 个元件`);
              } else {
                addMessage('请先选择要镜像的元件');
              }
            }}
            style={{
              width: 32,
              height: 28,
              backgroundColor: 'transparent',
              border: 'none',
              borderRadius: 4,
              color: THEME.text.secondary,
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = THEME.hover.default;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            ⇆
          </button>
        </div>

        {/* 分隔线 */}
        <div style={{ width: 1, height: 24, backgroundColor: THEME.border.default, margin: '0 8px' }} />

        {/* 放置工具 */}
        <div style={{ display: 'flex', gap: 2 }}>
          {[
            { label: '封装', icon: '□', toolType: 'place_footprint' },
            { label: '走线', icon: '⬡', toolType: 'route' },
            { label: '过孔', icon: '◎', toolType: 'place_via' },
            { label: '铜区', icon: '▣', toolType: 'place_zone' },
            { label: '文本', icon: 'A', toolType: 'place_text' },
          ].map((tool) => (
            <button
              key={tool.label}
              title={tool.label}
              onClick={() => setCurrentTool(tool.toolType as any)}
              style={{
                width: 32,
                height: 28,
                backgroundColor: currentTool === tool.toolType ? THEME.accent.primary : 'transparent',
                border: 'none',
                borderRadius: 4,
                color: currentTool === tool.toolType ? '#fff' : THEME.text.secondary,
                fontSize: 14,
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                if (currentTool !== tool.toolType) {
                  e.currentTarget.style.backgroundColor = THEME.hover.default;
                }
              }}
              onMouseLeave={(e) => {
                if (currentTool !== tool.toolType) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {tool.icon}
            </button>
          ))}
        </div>

        {/* 分隔线 */}
        <div style={{ width: 1, height: 24, backgroundColor: THEME.border.default, margin: '0 8px' }} />

        {/* 视图工具 */}
        <div style={{ display: 'flex', gap: 2 }}>
          {[
            {
              label: '放大',
              icon: '🔍+',
              action: () => setZoom(Math.min(zoom * 1.2, 10))
            },
            {
              label: '缩小',
              icon: '🔍-',
              action: () => setZoom(Math.max(zoom / 1.2, 0.1))
            },
            {
              label: '适应',
              icon: '⊞',
              action: () => setZoom(1)
            },
            {
              label: snapToGrid ? '网格(开)' : '网格(关)',
              icon: '▦',
              action: () => setSnapToGrid(!snapToGrid),
              active: snapToGrid
            },
          ].map((tool) => (
            <button
              key={tool.label}
              title={tool.label}
              onClick={tool.action}
              style={{
                width: 32,
                height: 28,
                backgroundColor: tool.active ? THEME.accent.primary : 'transparent',
                border: 'none',
                borderRadius: 4,
                color: tool.active ? '#fff' : THEME.text.secondary,
                fontSize: 14,
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                if (!tool.active) {
                  e.currentTarget.style.backgroundColor = THEME.hover.default;
                }
              }}
              onMouseLeave={(e) => {
                if (!tool.active) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {tool.icon}
            </button>
          ))}
        </div>
      </div>

      {/* ===== 主内容区 ===== */}
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
        minWidth: 600,
      }}>
        {/* ===== 左侧边栏 ===== */}
        <div style={{
          width: sidebarCollapsed ? 32 : 200,
          minWidth: 32,
          maxWidth: 200,
          backgroundColor: THEME.bg.panel,
          borderRight: `1px solid ${THEME.border.default}`,
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.2s',
          flexShrink: 0,
        }}>
          {/* 边栏折叠按钮 */}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            style={{
              width: '100%',
              height: 32,
              backgroundColor: 'transparent',
              border: 'none',
              borderBottom: `1px solid ${THEME.border.dark}`,
              color: THEME.text.muted,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
            }}
          >
            {sidebarCollapsed ? '▶' : '◀'}
          </button>

          {!sidebarCollapsed && (
            <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
              {/* 图层面板 */}
              <div style={{ marginBottom: 16 }}>
                <div style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: THEME.text.muted,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: 8,
                  padding: '0 4px',
                }}>
                  图层
                </div>
                {[
                  { name: 'F.Cu', color: '#ff6b6b', visible: true },
                  { name: 'B.Cu', color: '#6bff6b', visible: true },
                  { name: 'F.SilkS', color: '#ffff6b', visible: true },
                  { name: 'B.SilkS', color: '#6bffff', visible: false },
                  { name: 'F.Mask', color: '#6b6bff', visible: true },
                  { name: 'Edge.Cuts', color: '#ff6bff', visible: true },
                ].map((layer) => (
                  <div
                    key={layer.name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '6px 8px',
                      borderRadius: 4,
                      cursor: 'pointer',
                      opacity: layer.visible ? 1 : 0.5,
                    }}
                  >
                    <div style={{
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      backgroundColor: layer.color,
                    }} />
                    <span style={{ fontSize: 12, color: THEME.text.secondary }}>
                      {layer.name}
                    </span>
                  </div>
                ))}
              </div>

              {/* 过滤器 */}
              <div>
                <div style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: THEME.text.muted,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: 8,
                  padding: '0 4px',
                }}>
                  过滤器
                </div>
                {['封装', '走线', '过孔', '文本', '标注'].map((item) => (
                  <div
                    key={item}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '6px 8px',
                      borderRadius: 4,
                      cursor: 'pointer',
                    }}
                  >
                    <input type="checkbox" defaultChecked />
                    <span style={{ fontSize: 12, color: THEME.text.secondary }}>
                      {item}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ===== 中间区域（画布80% + 底部10%） ===== */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 400,
          height: '100%',  // 关键：确保子元素百分比高度有效
          overflow: 'hidden',
        }}>
          {/* 画布区域 - 80%高度 */}
          <div style={{
            flex: '0 0 80%',
            backgroundColor: THEME.bg.canvas,
            position: 'relative',
            display: 'flex',
            overflow: 'hidden',
          }}>
            {editorType === 'pcb' ? <PCBEditor /> : <SchematicEditor />}
          </div>

          {/* 底部区域 - 10%高度（输出面板 + 状态栏） */}
          <div style={{
            flex: '0 0 10%',
            minHeight: 60,
            backgroundColor: THEME.bg.panel,
            borderTop: `1px solid ${THEME.border.default}`,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}>
            {/* 面板标签 */}
            <div style={{
              height: 24,
              backgroundColor: THEME.bg.secondary,
              display: 'flex',
              alignItems: 'center',
              padding: '0 8px',
              borderBottom: `1px solid ${THEME.border.dark}`,
              flexShrink: 0,
            }}>
              {[
                { id: 'messages', label: '消息' },
                { id: 'drc', label: 'DRC' },
                { id: 'erc', label: 'ERC' },
                { id: 'bom', label: 'BOM' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveBottomTab(tab.id as any)}
                  style={{
                    padding: '2px 10px',
                    backgroundColor: activeBottomTab === tab.id ? THEME.bg.panel : 'transparent',
                    border: 'none',
                    borderBottom: activeBottomTab === tab.id ? `2px solid ${THEME.accent.primary}` : 'none',
                    color: activeBottomTab === tab.id ? THEME.text.primary : THEME.text.muted,
                    fontSize: 10,
                    cursor: 'pointer',
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            {/* 面板内容 */}
            <div style={{
              flex: 1,
              padding: '4px 8px',
              overflow: 'auto',
              fontSize: 10,
              fontFamily: 'Consolas, Monaco, monospace',
              color: THEME.text.secondary,
            }}>
              {activeBottomTab === 'messages' && bottomPanelMessages.map((msg, idx) => (
                <div key={idx}>{msg}</div>
              ))}
              {activeBottomTab === 'drc' && (
                <div style={{ padding: '8px 0' }}>
                  <div style={{ color: THEME.accent.primary, marginBottom: 4 }}>DRC 检查结果</div>
                  <div>点击菜单「工具 → 设计规则检查」运行 DRC</div>
                </div>
              )}
              {activeBottomTab === 'erc' && (
                <div style={{ padding: '8px 0' }}>
                  <div style={{ color: THEME.accent.primary, marginBottom: 4 }}>ERC 电气规则检查</div>
                  <div>ERC 功能开发中...</div>
                </div>
              )}
              {activeBottomTab === 'bom' && (
                <div style={{ padding: '8px 0' }}>
                  <div style={{ color: THEME.accent.primary, marginBottom: 4 }}>BOM 物料清单</div>
                  <div>点击菜单「工具 → 导出BOM」导出物料清单</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ===== 右侧边栏 ===== */}
        <div style={{
          width: rightPanelCollapsed ? 32 : 200,
          minWidth: 32,
          maxWidth: 200,
          backgroundColor: THEME.bg.panel,
          borderLeft: `1px solid ${THEME.border.default}`,
          transition: 'width 0.2s',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}>
          <button
            onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
            style={{
              width: '100%',
              height: 32,
              backgroundColor: 'transparent',
              border: 'none',
              borderBottom: `1px solid ${THEME.border.dark}`,
              color: THEME.text.muted,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
            }}
          >
            {rightPanelCollapsed ? '◀' : '▶'}
          </button>

          {!rightPanelCollapsed && (
            <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
              {/* 属性面板 */}
              <div style={{ marginBottom: 16 }}>
                <div style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: THEME.text.muted,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: 12,
                }}>
                  属性
                </div>
                {[
                  { label: '位置 X', value: '0.000 mm' },
                  { label: '位置 Y', value: '0.000 mm' },
                  { label: '旋转', value: '0°' },
                  { label: '层', value: 'F.Cu' },
                ].map((prop) => (
                  <div key={prop.label} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '6px 0',
                    borderBottom: `1px solid ${THEME.border.dark}`,
                  }}>
                    <span style={{ fontSize: 11, color: THEME.text.muted }}>
                      {prop.label}
                    </span>
                    <span style={{ fontSize: 11, color: THEME.text.primary }}>
                      {prop.value}
                    </span>
                  </div>
                ))}
              </div>

              {/* 常用操作 */}
              <div>
                <div style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: THEME.text.muted,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: 12,
                }}>
                  常用操作
                </div>
                <button
                  onClick={async () => {
                    if (currentProject?.id) {
                      try {
                        setActiveBottomTab('drc');
                        addMessage('开始运行 DRC 检查...');
                        const result = await drcApi.runDRC(currentProject.id);
                        addMessage(`DRC检查完成: ${result.data?.errorCount || 0} 错误, ${result.data?.warningCount || 0} 警告`);
                        alert(`DRC检查完成: ${result.data?.errorCount || 0} 错误, ${result.data?.warningCount || 0} 警告`);
                      } catch (e) {
                        console.error('DRC failed:', e);
                        addMessage('DRC检查失败');
                      }
                    }
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: THEME.accent.primary,
                    border: 'none',
                    borderRadius: 4,
                    color: '#fff',
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: 'pointer',
                    marginBottom: 8,
                  }}
                >
                  运行 DRC
                </button>
                <button
                  onClick={async () => {
                    if (currentProject?.id) {
                      try {
                        setActiveBottomTab('bom');
                        addMessage('开始导出 Gerber...');
                        const result = await exportApi.exportGerber(currentProject.id);
                        addMessage('Gerber导出成功');
                        alert('Gerber导出成功！');
                      } catch (e) {
                        console.error('Gerber export failed:', e);
                        addMessage('Gerber导出失败');
                      }
                    }
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: THEME.bg.tertiary,
                    border: `1px solid ${THEME.border.default}`,
                    borderRadius: 4,
                    color: THEME.text.primary,
                    fontSize: 12,
                    cursor: 'pointer',
                    marginBottom: 8,
                  }}
                >
                  导出 Gerber
                </button>
                <button
                  onClick={async () => {
                    if (currentProject?.id) {
                      try {
                        setActiveBottomTab('bom');
                        addMessage('开始导出 BOM...');
                        const result = await exportApi.exportBOM(currentProject.id);
                        addMessage('BOM导出成功');
                        alert('BOM导出成功！');
                      } catch (e) {
                        console.error('BOM export failed:', e);
                        addMessage('BOM导出失败');
                      }
                    }
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: THEME.bg.tertiary,
                    border: `1px solid ${THEME.border.default}`,
                    borderRadius: 4,
                    color: THEME.text.primary,
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  导出 BOM
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===== AI 聊天助手 (浮动组件 - fixed定位不影响布局) ===== */}
      <div style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        zIndex: 1000,
      }}>
        <AIChatAssistant
          schematicData={currentProject}
          projectSpec={currentProject}
          defaultExpanded={false}
        />
      </div>
    </div>
  );
}

export default App;
