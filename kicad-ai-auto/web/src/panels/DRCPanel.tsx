/**
 * DRC 面板 (Phase 5.3)
 * 设计规则检查结果展示
 */

import React, { useState, useCallback } from 'react';
import { usePCBStore } from '../stores/pcbStore';
import { drcApi } from '../services/api';
import { DRCReport, DRCItem } from '../types';

interface DRCPanelProps {
  onDRCComplete?: (report: DRCReport | null) => void;
}

const DRCPanel: React.FC<DRCPanelProps> = ({ onDRCComplete }) => {
  const { projectId, pcbData } = usePCBStore();
  const [report, setReport] = useState<DRCReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 运行 DRC
  const runDRC = useCallback(async () => {
    if (!projectId) {
      setError('No project loaded');
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      const response = await drcApi.runDRC(projectId, pcbData);
      if (response.success && response.data) {
        setReport(response.data);
        onDRCComplete?.(response.data); // 通知父组件DRC完成
      } else {
        setError(response.error || 'DRC failed');
        onDRCComplete?.(null);
      }
    } catch {
      setError('Network error during DRC');
      onDRCComplete?.(null);
    } finally {
      setIsRunning(false);
    }
  }, [projectId, pcbData, onDRCComplete]);

  // 主题色配置
  const THEME = {
    accent: '#4a9eff',
    accentHover: '#5aaaff',
    bg: {
      card: '#2d2d2d',
      cardHover: '#333333',
      input: '#1a1a1a',
    },
    border: {
      default: '#3d3d3d',
      hover: '#4a9eff',
    },
    text: {
      primary: '#ffffff',
      secondary: '#888888',
      muted: '#666666',
    },
    error: '#ff4444',
    warning: '#ffaa00',
    success: '#4caf50',
  };

  // 获取严重性颜色
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return THEME.error;
      case 'warning':
        return THEME.warning;
      default:
        return THEME.text.muted;
    }
  };

  // 渲染单个错误项
  const renderDRCItem = (item: DRCItem, index: number) => (
    <div
      key={item.id}
      style={{
        padding: '12px 14px',
        marginBottom: '8px',
        backgroundColor: THEME.bg.card,
        borderRadius: '8px',
        border: `1px solid ${THEME.border.default}`,
        borderLeft: `4px solid ${getSeverityColor(item.severity)}`,
        transition: 'all 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = THEME.bg.cardHover;
        e.currentTarget.style.transform = 'translateX(2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = THEME.bg.card;
        e.currentTarget.style.transform = 'translateX(0)';
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            color: getSeverityColor(item.severity),
            fontSize: '10px',
            fontWeight: 600,
            textTransform: 'uppercase',
            padding: '2px 6px',
            backgroundColor: `${getSeverityColor(item.severity)}22`,
            borderRadius: '4px',
          }}>
            {item.severity === 'error' ? '✗' : '⚠'} {item.severity}
          </span>
          <span style={{ color: THEME.text.muted, fontSize: '10px' }}>
            #{index + 1}
          </span>
        </div>
        <span style={{
          color: THEME.text.muted,
          fontSize: '10px',
          backgroundColor: THEME.bg.input,
          padding: '2px 6px',
          borderRadius: '4px',
        }}>
          {item.type}
        </span>
      </div>
      <div style={{
        color: THEME.text.primary,
        fontSize: '12px',
        marginBottom: '6px',
        lineHeight: '1.4',
      }}>
        {item.message}
      </div>
      {item.position && (
        <div style={{
          color: THEME.text.muted,
          fontSize: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <span>📍</span>
          <span style={{ fontFamily: 'monospace' }}>
            ({item.position.x.toFixed(2)}, {item.position.y.toFixed(2)})
          </span>
        </div>
      )}
    </div>
  );

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题区域 */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{
          color: THEME.text.primary,
          fontSize: '16px',
          margin: '0 0 6px 0',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}>
          <span style={{ fontSize: '20px' }}>🔍</span>
          设计规则检查
        </h3>
        <p style={{
          color: THEME.text.secondary,
          fontSize: '11px',
          margin: 0,
          marginBottom: '14px',
        }}>
          检查设计是否符合制造要求
        </p>

        {/* 运行DRC按钮 */}
        <button
          onClick={runDRC}
          disabled={isRunning || !projectId}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: isRunning ? THEME.bg.card : THEME.accent,
            color: '#ffffff',
            border: 'none',
            borderRadius: '8px',
            cursor: isRunning || !projectId ? 'not-allowed' : 'pointer',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            boxShadow: isRunning ? 'none' : '0 2px 8px rgba(74, 158, 255, 0.25)',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            if (!isRunning && projectId) {
              e.currentTarget.style.backgroundColor = THEME.accentHover;
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(74, 158, 255, 0.35)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isRunning) {
              e.currentTarget.style.backgroundColor = THEME.accent;
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(74, 158, 255, 0.25)';
            }
          }}
        >
          {isRunning ? (
            <>
              <span style={{
                display: 'inline-block',
                width: '14px',
                height: '14px',
                border: '2px solid rgba(255,255,255,0.3)',
                borderTopColor: '#ffffff',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }} />
              检查中...
            </>
          ) : (
            <>
              <span>▶</span>
              运行 DRC
            </>
          )}
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{
          padding: '12px 14px',
          backgroundColor: `${THEME.error}15`,
          border: `1px solid ${THEME.error}40`,
          color: THEME.error,
          borderRadius: '8px',
          fontSize: '12px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>✗</span>
          {error}
        </div>
      )}

      {/* 检查结果报告 */}
      {report && (
        <>
          {/* 统计摘要卡片 */}
          <div style={{
            display: 'flex',
            gap: '10px',
            marginBottom: '16px',
          }}>
            {/* 错误数 */}
            <div style={{
              flex: 1,
              padding: '14px',
              backgroundColor: report.errorCount > 0 ? `${THEME.error}15` : THEME.bg.card,
              border: `1px solid ${report.errorCount > 0 ? `${THEME.error}40` : THEME.border.default}`,
              borderRadius: '10px',
              textAlign: 'center',
            }}>
              <div style={{
                color: report.errorCount > 0 ? THEME.error : THEME.success,
                fontSize: '24px',
                fontWeight: 700,
              }}>
                {report.errorCount}
              </div>
              <div style={{
                color: THEME.text.secondary,
                fontSize: '10px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                错误
              </div>
            </div>

            {/* 警告数 */}
            <div style={{
              flex: 1,
              padding: '14px',
              backgroundColor: report.warningCount > 0 ? `${THEME.warning}15` : THEME.bg.card,
              border: `1px solid ${report.warningCount > 0 ? `${THEME.warning}40` : THEME.border.default}`,
              borderRadius: '10px',
              textAlign: 'center',
            }}>
              <div style={{
                color: report.warningCount > 0 ? THEME.warning : THEME.success,
                fontSize: '24px',
                fontWeight: 700,
              }}>
                {report.warningCount}
              </div>
              <div style={{
                color: THEME.text.secondary,
                fontSize: '10px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                警告
              </div>
            </div>
          </div>

          {/* 错误列表 */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {report.errors.length === 0 && report.warnings.length === 0 ? (
              <div style={{
                padding: '30px 20px',
                backgroundColor: `${THEME.success}10`,
                border: `1px solid ${THEME.success}30`,
                borderRadius: '10px',
                textAlign: 'center',
              }}>
                <div style={{
                  fontSize: '36px',
                  marginBottom: '10px',
                }}>✓</div>
                <div style={{
                  color: THEME.success,
                  fontSize: '14px',
                  fontWeight: 600,
                }}>
                  没有发现设计规则违规！
                </div>
                <div style={{
                  color: THEME.text.secondary,
                  fontSize: '11px',
                  marginTop: '4px',
                }}>
                  您的设计符合制造要求
                </div>
              </div>
            ) : (
              <>
                {/* 错误 */}
                {report.errors.length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{
                      color: THEME.error,
                      fontSize: '12px',
                      fontWeight: 600,
                      margin: '0 0 10px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}>
                      <span>✗</span>
                      错误 ({report.errors.length})
                    </h4>
                    {report.errors.map((item, index) => renderDRCItem(item, index))}
                  </div>
                )}

                {/* 警告 */}
                {report.warnings.length > 0 && (
                  <div>
                    <h4 style={{
                      color: THEME.warning,
                      fontSize: '12px',
                      fontWeight: 600,
                      margin: '0 0 10px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}>
                      <span>⚠</span>
                      警告 ({report.warnings.length})
                    </h4>
                    {report.warnings.map((item, index) => renderDRCItem(item, index))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* 时间戳 */}
          <div style={{
            marginTop: '14px',
            paddingTop: '14px',
            borderTop: `1px solid ${THEME.border.default}`,
            color: THEME.text.muted,
            fontSize: '10px',
            textAlign: 'center',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
          }}>
            <span>🕐</span>
            最后检查: {new Date(report.timestamp).toLocaleString()}
          </div>
        </>
      )}

      {/* 空状态 */}
      {!report && !error && !isRunning && (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: THEME.text.muted,
          textAlign: 'center',
          padding: '30px',
          backgroundColor: THEME.bg.card,
          border: `1px dashed ${THEME.border.default}`,
          borderRadius: '10px',
        }}>
          <div style={{ fontSize: '40px', marginBottom: '12px' }}>🔍</div>
          <div style={{
            color: THEME.text.secondary,
            fontSize: '13px',
            fontWeight: 500,
            marginBottom: '4px',
          }}>
            尚未运行检查
          </div>
          <div style={{
            color: THEME.text.muted,
            fontSize: '11px',
          }}>
            点击"运行 DRC"按钮开始检查设计
          </div>
        </div>
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

export default DRCPanel;
