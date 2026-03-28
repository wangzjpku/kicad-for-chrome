/**
 * ERC 检查面板
 * 显示电气规则检查结果
 */

import React, { useEffect, useState } from 'react';
import { useSchematicStore } from '../stores/schematicStore';
import { generateNetlist, NetlistResult, ERCError } from '../services/netlistService';

interface ERCPanelProps {
  onErrorClick?: (error: ERCError) => void;
}

const THEME = {
  bg: {
    panel: '#2d2d2d',
    card: '#333333',
    input: '#1a1a1a',
  },
  border: {
    default: '#3d3d3d',
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

const ERCPanel: React.FC<ERCPanelProps> = ({ onErrorClick }) => {
  const { schematicData, setSelectedIds } = useSchematicStore();
  const [result, setResult] = useState<NetlistResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [lastCheckTime, setLastCheckTime] = useState<Date | null>(null);

  // 运行ERC检查
  const runERC = () => {
    setIsRunning(true);

    // 使用setTimeout让UI有机会更新
    setTimeout(() => {
      const ercResult = generateNetlist(schematicData);
      setResult(ercResult);
      setLastCheckTime(new Date());
      setIsRunning(false);
    }, 100);
  };

  // 组件挂载时自动运行一次
  useEffect(() => {
    runERC();
  }, [schematicData]);

  // 处理错误点击
  const handleErrorClick = (error: ERCError) => {
    if (error.elementId) {
      setSelectedIds([error.elementId]);
    }
    onErrorClick?.(error);
  };

  // 渲染错误/警告项
  const renderERCItem = (item: ERCError, index: number) => {
    const isError = item.type === 'error';
    const color = isError ? THEME.error : THEME.warning;
    const icon = isError ? '✗' : '⚠';

    return (
      <div
        key={`${item.id}-${index}`}
        onClick={() => handleErrorClick(item)}
        style={{
          padding: '10px 12px',
          marginBottom: '8px',
          backgroundColor: THEME.bg.card,
          borderRadius: '6px',
          border: `1px solid ${THEME.border.default}`,
          borderLeft: `4px solid ${color}`,
          cursor: item.elementId ? 'pointer' : 'default',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#3a3a3a';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = THEME.bg.card;
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
          <span style={{ color, fontSize: '14px', fontWeight: 'bold' }}>
            {icon}
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '12px', color: THEME.text.primary, marginBottom: '2px' }}>
              {item.message}
            </div>
            <div style={{ fontSize: '10px', color: THEME.text.muted }}>
              {item.category === 'unconnected_pin' && '未连接引脚'}
              {item.category === 'no_power' && '电源网络'}
              {item.category === 'no_ground' && '地网络'}
              {item.category === 'short_circuit' && '短路'}
              {item.category === 'floating_net' && '悬空网络'}
              {item.position && ` - 位置: (${item.position.x.toFixed(1)}, ${item.position.y.toFixed(1)})`}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: '16px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题区域 */}
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{
          color: THEME.text.primary,
          fontSize: '16px',
          margin: '0 0 8px 0',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>🔍</span>
          ERC 电气规则检查
        </h3>

        {/* 运行按钮 */}
        <button
          onClick={runERC}
          disabled={isRunning}
          style={{
            width: '100%',
            padding: '10px',
            backgroundColor: isRunning ? THEME.bg.card : '#4a9eff',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
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
              运行 ERC
            </>
          )}
        </button>
      </div>

      {/* 统计摘要 */}
      {result && (
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '16px',
        }}>
          <div style={{
            flex: 1,
            padding: '12px',
            backgroundColor: result.errors.length > 0 ? `${THEME.error}15` : `${THEME.success}15`,
            border: `1px solid ${result.errors.length > 0 ? `${THEME.error}40` : `${THEME.success}40`}`,
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            <div style={{
              color: result.errors.length > 0 ? THEME.error : THEME.success,
              fontSize: '20px',
              fontWeight: 700,
            }}>
              {result.errors.length}
            </div>
            <div style={{ color: THEME.text.secondary, fontSize: '10px' }}>错误</div>
          </div>

          <div style={{
            flex: 1,
            padding: '12px',
            backgroundColor: result.warnings.length > 0 ? `${THEME.warning}15` : `${THEME.success}15`,
            border: `1px solid ${result.warnings.length > 0 ? `${THEME.warning}40` : `${THEME.success}40`}`,
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            <div style={{
              color: result.warnings.length > 0 ? THEME.warning : THEME.success,
              fontSize: '20px',
              fontWeight: 700,
            }}>
              {result.warnings.length}
            </div>
            <div style={{ color: THEME.text.secondary, fontSize: '10px' }}>警告</div>
          </div>

          <div style={{
            flex: 1,
            padding: '12px',
            backgroundColor: THEME.bg.card,
            border: `1px solid ${THEME.border.default}`,
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            <div style={{ color: THEME.text.primary, fontSize: '20px', fontWeight: 700 }}>
              {result.nets.length}
            </div>
            <div style={{ color: THEME.text.secondary, fontSize: '10px' }}>网络</div>
          </div>
        </div>
      )}

      {/* 连接统计 */}
      {result && (
        <div style={{
          padding: '10px',
          backgroundColor: THEME.bg.card,
          borderRadius: '6px',
          marginBottom: '16px',
          fontSize: '11px',
          color: THEME.text.secondary,
        }}>
          <div>元件: {result.componentCount} 个</div>
          <div>引脚: {result.connectedPinCount}/{result.pinCount} 已连接</div>
          {result.unconnectedPinCount > 0 && (
            <div style={{ color: THEME.warning }}>
              {result.unconnectedPinCount} 个引脚未连接
            </div>
          )}
        </div>
      )}

      {/* 错误列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {result?.errors.length === 0 && result?.warnings.length === 0 ? (
          <div style={{
            padding: '30px 20px',
            backgroundColor: `${THEME.success}10`,
            border: `1px solid ${THEME.success}30`,
            borderRadius: '10px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '32px', marginBottom: '10px' }}>✓</div>
            <div style={{ color: THEME.success, fontSize: '14px', fontWeight: 600 }}>
              没有发现电气规则违规！
            </div>
            <div style={{ color: THEME.text.secondary, fontSize: '11px', marginTop: '4px' }}>
              您的设计通过ERC检查
            </div>
          </div>
        ) : (
          <>
            {result?.errors.map((error, index) => renderERCItem(error, index))}
            {result?.warnings.map((warning, index) => renderERCItem(warning, index))}
          </>
        )}
      </div>

      {/* 时间戳 */}
      {lastCheckTime && (
        <div style={{
          marginTop: '12px',
          paddingTop: '12px',
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
          最后检查: {lastCheckTime.toLocaleTimeString()}
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default ERCPanel;
