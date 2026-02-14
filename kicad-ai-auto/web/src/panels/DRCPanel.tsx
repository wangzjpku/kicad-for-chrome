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
    } catch (err) {
      setError('Network error during DRC');
      onDRCComplete?.(null);
    } finally {
      setIsRunning(false);
    }
  }, [projectId, pcbData, onDRCComplete]);

  // 获取严重性颜色
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return '#ff4444';
      case 'warning':
        return '#ffaa00';
      default:
        return '#888888';
    }
  };

  // 渲染单个错误项
  const renderDRCItem = (item: DRCItem, index: number) => (
    <div
      key={item.id}
      style={{
        padding: '10px',
        marginBottom: '8px',
        backgroundColor: '#2d2d2d',
        borderRadius: '4px',
        borderLeft: `3px solid ${getSeverityColor(item.severity)}`,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '4px',
        }}
      >
        <span
          style={{
            color: getSeverityColor(item.severity),
            fontSize: '11px',
            fontWeight: 'bold',
            textTransform: 'uppercase',
          }}
        >
          {item.severity}
        </span>
        <span style={{ color: '#666666', fontSize: '10px' }}>
          {item.type}
        </span>
      </div>
      <div style={{ color: '#ffffff', fontSize: '12px', marginBottom: '4px' }}>
        {item.message}
      </div>
      {item.position && (
        <div style={{ color: '#666666', fontSize: '10px' }}>
          Position: ({item.position.x.toFixed(2)}, {item.position.y.toFixed(2)})
        </div>
      )}
    </div>
  );

  return (
    <div style={{ padding: '16px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ color: '#ffffff', fontSize: '14px', margin: '0 0 12px 0' }}>
          Design Rule Check
        </h3>
        <button
          onClick={runDRC}
          disabled={isRunning || !projectId}
          style={{
            width: '100%',
            padding: '10px',
            backgroundColor: isRunning ? '#3d3d3d' : '#4a9eff',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            cursor: isRunning || !projectId ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 'bold',
          }}
        >
          {isRunning ? 'Running DRC...' : 'Run DRC'}
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: '10px',
            backgroundColor: '#ff444422',
            color: '#ff4444',
            borderRadius: '4px',
            fontSize: '12px',
            marginBottom: '16px',
          }}
        >
          {error}
        </div>
      )}

      {report && (
        <>
          {/* 统计摘要 */}
          <div
            style={{
              display: 'flex',
              gap: '12px',
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: '#2d2d2d',
              borderRadius: '4px',
            }}
          >
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ color: '#ff4444', fontSize: '18px', fontWeight: 'bold' }}>
                {report.errorCount}
              </div>
              <div style={{ color: '#888888', fontSize: '10px' }}>Errors</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ color: '#ffaa00', fontSize: '18px', fontWeight: 'bold' }}>
                {report.warningCount}
              </div>
              <div style={{ color: '#888888', fontSize: '10px' }}>Warnings</div>
            </div>
          </div>

          {/* 错误列表 */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {report.errors.length === 0 && report.warnings.length === 0 ? (
              <div
                style={{
                  textAlign: 'center',
                  color: '#4caf50',
                  padding: '20px',
                  fontSize: '14px',
                }}
              >
                ✓ No DRC violations found!
              </div>
            ) : (
              <>
                {/* 错误 */}
                {report.errors.length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ color: '#ff4444', fontSize: '12px', margin: '0 0 8px 0' }}>
                      Errors ({report.errors.length})
                    </h4>
                    {report.errors.map((item, index) => renderDRCItem(item, index))}
                  </div>
                )}

                {/* 警告 */}
                {report.warnings.length > 0 && (
                  <div>
                    <h4 style={{ color: '#ffaa00', fontSize: '12px', margin: '0 0 8px 0' }}>
                      Warnings ({report.warnings.length})
                    </h4>
                    {report.warnings.map((item, index) => renderDRCItem(item, index))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* 时间戳 */}
          <div
            style={{
              marginTop: '12px',
              paddingTop: '12px',
              borderTop: '1px solid #3d3d3d',
              color: '#666666',
              fontSize: '10px',
              textAlign: 'center',
            }}
          >
            Last check: {new Date(report.timestamp).toLocaleString()}
          </div>
        </>
      )}

      {!report && !error && !isRunning && (
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#666666',
            fontSize: '12px',
            textAlign: 'center',
          }}
        >
          Click "Run DRC" to check your design
        </div>
      )}
    </div>
  );
};

export default DRCPanel;
