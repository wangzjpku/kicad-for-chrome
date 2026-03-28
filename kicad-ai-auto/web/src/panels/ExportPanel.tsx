/**
 * 导出面板 (Phase 5.4)
 */

import React, { useState } from 'react';
import { usePCBStore } from '../stores/pcbStore';
import { exportApi, ApiResponse, ExportResultData } from '../services/api';

interface ExportPanelProps {
  onClose?: () => void;
}

const ExportPanel: React.FC<ExportPanelProps> = ({ onClose }) => {
  const { projectId } = usePCBStore();
  const [exporting, setExporting] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const [exportPath, setExportPath] = useState<string>('C:\\KiCadWebEditor\\output\\');
  const [isEditingPath, setIsEditingPath] = useState(false);

  const handleExport = async (type: string, exportFn: () => Promise<ApiResponse<ExportResultData>>) => {
    if (!projectId) {
      setResults(prev => ({
        ...prev,
        [type]: { success: false, message: 'No project loaded' }
      }));
      return;
    }

    setExporting(type);
    try {
      const response = await exportFn();
      if (response.success) {
        setResults(prev => ({
          ...prev,
          [type]: { success: true, message: 'Export successful' }
        }));
      } else {
        setResults(prev => ({
          ...prev,
          [type]: { success: false, message: response.error || 'Export failed' }
        }));
      }
    } catch {
      setResults(prev => ({
        ...prev,
        [type]: { success: false, message: 'Network error' }
      }));
    } finally {
      setExporting(null);
    }
  };

  const exportFormats = [
    {
      id: 'gerber',
      name: 'Gerber Files',
      description: 'Standard PCB manufacturing format',
      icon: '📄',
      action: () => handleExport('gerber', () => exportApi.exportGerber(projectId!))
    },
    {
      id: 'drill',
      name: 'Drill Files',
      description: 'NC drill and route files',
      icon: '🔩',
      action: () => handleExport('drill', () => exportApi.exportDrill(projectId!))
    },
    {
      id: 'bom',
      name: 'Bill of Materials',
      description: 'CSV format component list',
      icon: '📋',
      action: () => handleExport('bom', () => exportApi.exportBOM(projectId!))
    },
    {
      id: 'step',
      name: '3D Model (STEP)',
      description: '3D mechanical model',
      icon: '🧊',
      action: () => handleExport('step', () => exportApi.exportSTEP(projectId!))
    }
  ];

  // 主题色配置
  const THEME = {
    accent: '#4a9eff',
    accentHover: '#5aaaff',
    bg: {
      card: '#2d2d2d',
      cardHover: '#333333',
      input: '#1a1a1a',
      button: '#3d3d3d',
    },
    border: {
      default: '#3d3d3d',
      hover: '#4a9eff',
      active: '#4a9eff',
    },
    text: {
      primary: '#ffffff',
      secondary: '#888888',
      muted: '#666666',
    },
    success: '#4caf50',
    error: '#ff4444',
  };

  return (
    <div style={{ padding: '20px', maxWidth: '500px' }}>
      {/* 标题区域 */}
      <div style={{
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: `1px solid ${THEME.border.default}`,
      }}>
        <h2 style={{
          color: THEME.text.primary,
          margin: '0 0 8px 0',
          fontSize: '18px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}>
          <span style={{ fontSize: '22px' }}>📦</span>
          导出项目
        </h2>
        <p style={{
          color: THEME.text.secondary,
          margin: 0,
          fontSize: '12px',
          lineHeight: '1.5',
        }}>
          选择需要的导出格式，文件将保存到输出目录
        </p>
      </div>

      {/* 导出格式列表 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {exportFormats.map(format => (
          <div
            key={format.id}
            onMouseEnter={() => setHoveredItem(format.id)}
            onMouseLeave={() => setHoveredItem(null)}
            style={{
              padding: '14px 16px',
              backgroundColor: hoveredItem === format.id ? THEME.bg.cardHover : THEME.bg.card,
              borderRadius: '10px',
              border: `1px solid ${hoveredItem === format.id ? THEME.border.hover : THEME.border.default}`,
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              transition: 'all 0.2s ease',
              cursor: 'default',
              boxShadow: hoveredItem === format.id ? '0 4px 12px rgba(0,0,0,0.2)' : 'none',
            }}
          >
            {/* 图标 */}
            <div style={{
              fontSize: '28px',
              width: '44px',
              height: '44px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: THEME.bg.input,
              borderRadius: '10px',
              border: `1px solid ${hoveredItem === format.id ? THEME.border.hover : THEME.border.default}`,
              transition: 'all 0.2s ease',
            }}>
              {format.icon}
            </div>

            {/* 内容 */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                color: THEME.text.primary,
                fontSize: '14px',
                fontWeight: 600,
                marginBottom: '3px',
              }}>
                {format.name}
              </div>
              <div style={{
                color: THEME.text.secondary,
                fontSize: '11px',
                lineHeight: '1.4',
              }}>
                {format.description}
              </div>

              {/* 导出结果状态 */}
              {results[format.id] && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  marginTop: '6px',
                  padding: '4px 8px',
                  backgroundColor: results[format.id].success ? 'rgba(76, 175, 80, 0.15)' : 'rgba(255, 68, 68, 0.15)',
                  borderRadius: '4px',
                  width: 'fit-content',
                }}>
                  <span style={{
                    fontSize: '10px',
                    color: results[format.id].success ? THEME.success : THEME.error,
                    fontWeight: 500,
                  }}>
                    {results[format.id].success ? '✓' : '✗'} {results[format.id].message}
                  </span>
                </div>
              )}
            </div>

            {/* 导出按钮 - 小巧尺寸 */}
            <button
              onClick={format.action}
              disabled={exporting === format.id || !projectId}
              style={{
                padding: '4px 10px',
                backgroundColor: exporting === format.id
                  ? THEME.bg.button
                  : hoveredItem === format.id
                    ? THEME.accentHover
                    : THEME.accent,
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                cursor: exporting === format.id || !projectId ? 'not-allowed' : 'pointer',
                fontSize: '11px',
                fontWeight: 500,
                minWidth: '56px',
                transition: 'all 0.2s ease',
              }}
            >
              {exporting === format.id ? (
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}>
                  <span style={{
                    display: 'inline-block',
                    width: '10px',
                    height: '10px',
                    border: '2px solid rgba(255,255,255,0.3)',
                    borderTopColor: '#ffffff',
                    borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite',
                  }} />
                </span>
              ) : (
                '导出'
              )}
            </button>
          </div>
        ))}
      </div>

      {/* 导出路径设置 */}
      <div style={{
        marginTop: '20px',
        padding: '16px',
        backgroundColor: THEME.bg.card,
        borderRadius: '10px',
        border: `1px solid ${THEME.border.default}`,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '10px',
        }}>
          <div style={{
            color: THEME.text.primary,
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span>📁</span>
            导出路径
          </div>
          {!isEditingPath && (
            <button
              onClick={() => setIsEditingPath(true)}
              style={{
                padding: '4px 10px',
                backgroundColor: 'transparent',
                border: `1px solid ${THEME.border.default}`,
                borderRadius: '4px',
                color: THEME.text.secondary,
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = THEME.accent;
                e.currentTarget.style.color = THEME.accent;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = THEME.border.default;
                e.currentTarget.style.color = THEME.text.secondary;
              }}
            >
              修改
            </button>
          )}
        </div>

        {isEditingPath ? (
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={exportPath}
              onChange={(e) => setExportPath(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                backgroundColor: THEME.bg.input,
                border: `1px solid ${THEME.accent}`,
                borderRadius: '6px',
                color: THEME.text.primary,
                fontSize: '12px',
                fontFamily: 'monospace',
                outline: 'none',
              }}
              placeholder="输入导出路径..."
              autoFocus
            />
            <button
              onClick={() => setIsEditingPath(false)}
              style={{
                padding: '8px 14px',
                backgroundColor: THEME.accent,
                border: 'none',
                borderRadius: '6px',
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              确认
            </button>
          </div>
        ) : (
          <div style={{
            padding: '10px 12px',
            backgroundColor: THEME.bg.input,
            borderRadius: '6px',
            border: `1px solid ${THEME.border.default}`,
          }}>
            <div style={{
              color: THEME.text.secondary,
              fontSize: '12px',
              fontFamily: 'monospace',
              wordBreak: 'break-all',
            }}>
              {exportPath}
            </div>
          </div>
        )}

        {/* 提示 */}
        <div style={{
          marginTop: '10px',
          padding: '8px 10px',
          backgroundColor: 'rgba(74, 158, 255, 0.08)',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <span style={{ fontSize: '12px' }}>💡</span>
          <span style={{
            color: THEME.text.muted,
            fontSize: '11px',
          }}>
            导出的文件将保存到此目录
          </span>
        </div>
      </div>

      {/* 关闭按钮 */}
      {onClose && (
        <button
          onClick={onClose}
          style={{
            marginTop: '20px',
            width: '100%',
            padding: '12px',
            backgroundColor: THEME.bg.button,
            color: THEME.text.primary,
            border: `1px solid ${THEME.border.default}`,
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: 500,
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#4a4a4a';
            e.currentTarget.style.borderColor = THEME.border.hover;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = THEME.bg.button;
            e.currentTarget.style.borderColor = THEME.border.default;
          }}
        >
          关闭
        </button>
      )}

      {/* CSS动画 */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default ExportPanel;
