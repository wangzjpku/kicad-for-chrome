/**
 * 菜单配置
 * 从 App.tsx 中提取的菜单定义
 */

export interface MenuItem {
  id: string;
  label: string;
  shortcut?: string;
  action?: string;
  submenu?: MenuItem[];
  separator?: boolean;
  disabled?: boolean;
}

export interface MenuCategory {
  id: string;
  label: string;
  items: MenuItem[];
}

// 菜单栏配置
export const menuCategories: MenuCategory[] = [
  {
    id: 'file',
    label: '文件',
    items: [
      { id: 'new-project', label: '新建项目', shortcut: 'Ctrl+N', action: 'newProject' },
      { id: 'open-project', label: '打开项目', shortcut: 'Ctrl+O', action: 'openProject' },
      { id: 'separator1', label: '', separator: true },
      { id: 'save', label: '保存', shortcut: 'Ctrl+S', action: 'save' },
      { id: 'save-as', label: '另存为', shortcut: 'Ctrl+Shift+S', action: 'saveAs' },
      { id: 'separator2', label: '', separator: true },
      { id: 'export-gerber', label: '导出 Gerber', action: 'exportGerber' },
      { id: 'export-bom', label: '导出 BOM', action: 'exportBOM' },
      { id: 'export-step', label: '导出 STEP', action: 'exportSTEP' },
      { id: 'separator3', label: '', separator: true },
      { id: 'exit', label: '退出', shortcut: 'Alt+F4', action: 'exit' },
    ],
  },
  {
    id: 'edit',
    label: '编辑',
    items: [
      { id: 'undo', label: '撤销', shortcut: 'Ctrl+Z', action: 'undo' },
      { id: 'redo', label: '重做', shortcut: 'Ctrl+Y', action: 'redo' },
      { id: 'separator1', label: '', separator: true },
      { id: 'cut', label: '剪切', shortcut: 'Ctrl+X', action: 'cut' },
      { id: 'copy', label: '复制', shortcut: 'Ctrl+C', action: 'copy' },
      { id: 'paste', label: '粘贴', shortcut: 'Ctrl+V', action: 'paste' },
      { id: 'delete', label: '删除', shortcut: 'Delete', action: 'delete' },
      { id: 'separator2', label: '', separator: true },
      { id: 'select-all', label: '全选', shortcut: 'Ctrl+A', action: 'selectAll' },
    ],
  },
  {
    id: 'view',
    label: '视图',
    items: [
      { id: 'zoom-in', label: '放大', shortcut: 'Ctrl++', action: 'zoomIn' },
      { id: 'zoom-out', label: '缩小', shortcut: 'Ctrl+-', action: 'zoomOut' },
      { id: 'zoom-fit', label: '适应窗口', shortcut: 'Ctrl+0', action: 'zoomFit' },
      { id: 'separator1', label: '', separator: true },
      { id: 'view-2d', label: '2D 视图', shortcut: 'F2', action: 'view2D' },
      { id: 'view-3d', label: '3D 视图', shortcut: 'F3', action: 'view3D' },
      { id: 'separator2', label: '', separator: true },
      { id: 'toggle-grid', label: '切换网格', shortcut: 'G', action: 'toggleGrid' },
      { id: 'toggle-rats', label: '切换鼠线', shortcut: 'R', action: 'toggleRats' },
    ],
  },
  {
    id: 'tools',
    label: '工具',
    items: [
      { id: 'run-drc', label: '运行 DRC', shortcut: 'F9', action: 'runDRC' },
      { id: 'run-erc', label: '运行 ERC', shortcut: 'F8', action: 'runERC' },
      { id: 'separator1', label: '', separator: true },
      { id: 'auto-route', label: '自动布线', shortcut: 'A', action: 'autoRoute' },
      { id: 'clear-routes', label: '清除布线', action: 'clearRoutes' },
      { id: 'separator2', label: '', separator: true },
      { id: 'design-rules', label: '设计规则', action: 'designRules' },
      { id: 'board-setup', label: '板材设置', action: 'boardSetup' },
    ],
  },
  {
    id: 'help',
    label: '帮助',
    items: [
      { id: 'documentation', label: '文档', action: 'documentation' },
      { id: 'about', label: '关于', action: 'about' },
    ],
  },
];

// 工具栏按钮配置
export interface ToolbarButton {
  id: string;
  icon: string;
  label: string;
  action: string;
  disabled?: boolean;
}

export const toolbarButtons: ToolbarButton[] = [
  { id: 'new', icon: '📄', label: '新建', action: 'newProject' },
  { id: 'open', icon: '📂', label: '打开', action: 'openProject' },
  { id: 'save', icon: '💾', label: '保存', action: 'save' },
  { id: 'separator1', icon: '', label: '', action: '' },
  { id: 'undo', icon: '↩️', label: '撤销', action: 'undo' },
  { id: 'redo', icon: '↪️', label: '重做', action: 'redo' },
  { id: 'separator2', icon: '', label: '', action: '' },
  { id: 'select', icon: '⬚', label: '选择', action: 'select' },
  { id: 'route', icon: '📍', label: '布线', action: 'route' },
  { id: 'via', icon: '⚫', label: '过孔', action: 'via' },
  { id: 'zone', icon: '🟩', label: '铺铜', action: 'zone' },
  { id: 'separator3', icon: '', label: '', action: '' },
  { id: 'drc', icon: '✅', label: 'DRC', action: 'runDRC' },
  { id: 'export', icon: '📤', label: '导出', action: 'export' },
];

export default {
  menuCategories,
  toolbarButtons,
};
