/**
 * * DRC Dashboard - Phase 7A
 * * Unified design rule check dashboard combining DRC, Safety, SI, and EMI analysis
 * */

import React, { useState, useCallback } from 'react';
import { drcApi } from '../services/api';

interface Tab {
  id: string;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: 'drc', label: 'DRC 规则', icon: '🔍' },
  { id: 'safety', label: '安全规则', icon: '🛡️' },
  { id: 'si', label: 'SI 分析', icon: '📈' },
  { id: 'emi', label: 'EMI 分析', icon: '📡' },
];

interface DRCDashboardProps {
  projectId: string;
  pcbData?: any;
  onViolationClick?: (x: number, y: number) => void;
}

const DRCDashboard: React.FC<DRCDashboardProps> = ({
  projectId,
  pcbData,
  onViolationClick,
}) => {
  const [activeTab, setActiveTab] = useState<string>('drc');
  const [results, setResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runCheck = useCallback(async (type: string) => {
    setLoading(type);
    setError(null);
    try {
      let result;
      switch (type) {
        case 'drc':
          result = await drcApi.runDRC(projectId, pcbData);
          break;
        case 'safety':
          result = await drcApi.runAdvancedDRC(projectId, pcbData, 'jlcpcb', 'standard');
          break;
        case 'si':
          result = await drcApi.runSIAnalysis(pcbData);
          break;
        case 'emi':
          result = await drcApi.runEMIAnalysis(pcbData, 'medium');
          break;
      }
      setResults((prev) => ({ ...prev, [type]: result }));
    } catch (err: any) {
      setError(err?.message || 'Check failed');
    } finally {
      setLoading(null);
    }
  }, [projectId, pcbData]);

  const runAllChecks = useCallback(async () => {
    for (const tab of TABS) {
      await runCheck(tab.id);
    }
  }, [runCheck]);

  const currentResult = results[activeTab];

  const getPassedInfo = (data: any) => {
    if (!data) return { passed: false, errors: 0, warnings: 0 };
    return {
      passed: data.passed ?? data.success ?? false,
      errors: data.error_count ?? data.errorCount ?? 0,
      warnings: data.warning_count ?? data.warningCount ?? 0,
    };
  };

  const info = getPassedInfo(currentResult);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#1e1e1e',
      color: '#e0e0e0',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid #333',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px', fontWeight: 600 }}>DRC Dashboard</span>
          {Object.keys(results).length > 0 && (
            <span style={{
              fontSize: '10px',
              padding: '2px 8px',
              borderRadius: '10px',
              backgroundColor: info.passed ? '#2e7d3220' : '#ff444420',
              color: info.passed ? '#4caf50' : '#ff4444',
            }}>
              {info.passed ? 'PASS' : 'FAIL'}
            </span>
          )}
        </div>
        <button
          onClick={runAllChecks}
          disabled={loading !== null}
          style={{
            padding: '6px 14px',
            backgroundColor: '#4a9eff',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'wait' : 'pointer',
            fontSize: '11px',
            fontWeight: 500,
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? 'Running...' : 'Run All Checks'}
        </button>
      </div>

      {/* Tab Bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid #333',
      }}>
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          const tabResult = results[tab.id];
          const tabInfo = getPassedInfo(tabResult);
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (!results[tab.id]) runCheck(tab.id);
              }}
              style={{
                flex: 1,
                padding: '10px 8px',
                border: 'none',
                borderBottom: isActive ? '2px solid #4a9eff' : '2px solid transparent',
                backgroundColor: 'transparent',
                color: isActive ? '#4a9eff' : '#888',
                cursor: 'pointer',
                fontSize: '11px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
              }}
            >
              <span>{tab.icon}</span>
              <span style={{ fontSize: '10px' }}>{tab.label}</span>
              {tabResult && (
                <span style={{
                  fontSize: '9px',
                  padding: '1px 4px',
                  borderRadius: '6px',
                  backgroundColor: tabInfo.errors > 0 ? '#ff444420' : tabInfo.warnings > 0 ? '#ffaa0020' : '#4caf5020',
                  color: tabInfo.errors > 0 ? '#ff4444' : tabInfo.warnings > 0 ? '#ffaa00' : '#4caf50',
                }}>
                  {tabInfo.errors > 0 ? `${tabInfo.errors}E` : tabInfo.warnings > 0 ? `${tabInfo.warnings}W` : 'OK'}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
        {loading === activeTab && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: '8px',
            color: '#888',
          }}>
            <div style={{
              width: '16px',
              height: '16px',
              border: '2px solid #444',
              borderTopColor: '#4a9eff',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }} />
            Checking...
          </div>
        )}

        {error && activeTab !== 'drc' && (
          <div style={{
            padding: '12px',
            backgroundColor: '#ff444415',
            border: '1px solid #ff444440',
            borderRadius: '8px',
            color: '#ff4444',
            fontSize: '12px',
          }}>
            {error}
          </div>
        )}

        {currentResult && loading !== activeTab && (
          _renderResult(currentResult, activeTab, onViolationClick)
        )}

        {!currentResult && loading !== activeTab && (
          <div style={{
            textAlign: 'center',
            color: '#666',
            padding: '40px',
          }}>
            Click a tab to run the check
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

function _renderResult(
  data: any,
  type: string,
  onViolationClick?: (x: number, y: number) => void,
) {
  const violations = data?.violations || data?.errors || data?.warnings || [];
  const isPassed = data?.passed ?? data?.success ?? false;

  const errorCount = data?.error_count ?? data?.errorCount ?? 0;
  const warningCount = data?.warning_count ?? data?.warningCount ?? 0;
  const stats = data?.statistics || data?.duration_ms;

 null;

  if (isPassed && errorCount === 0 && warningCount === 0) {
    return (
      <div style={{
        padding: '24px',
        backgroundColor: '#4caf5010',
        border: '1px solid #4caf5030',
        borderRadius: '10px',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>✓</div>
        <div style={{ color: '#4caf50', fontWeight: 600, fontSize: '14px' }}>
          All checks passed!
        </div>
        {stats && (
          <div style={{ color: '#888', fontSize: '11px', marginTop: '8px' }}>
            {stats.components_checked || 0} components, {stats.tracks_checked || 0} tracks,
stats.vias_checked || 0} vias
 {' | '}
            {typeof stats.duration_ms === 'number' && (
              <span> | {stats.duration_ms.toFixed(0)}ms</span>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      {/* Summary */}
      <div style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '12px',
      }}>
        {errorCount > 0 && (
          <div style={{
            flex: 1,
            padding: '10px',
            backgroundColor: '#ff444410',
            border: '1px solid #ff444440',
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            <div style={{ color: '#ff4444', fontSize: '20px', fontWeight: 700 }}>{errorCount}</div>
            <div style={{ color: '#ff6666', fontSize: '10px' }}>Errors</div>
          </div>
        )}
        {warningCount > 0 && (
          <div style={{
            flex: 1,
            padding: '10px',
            backgroundColor: '#ffaa0010',
            border: '1px solid #ffaa0040',
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            <div style={{ color: '#ffaa00', fontSize: '20px', fontWeight: 700 }}>{warningCount}</div>
            <div style={{ color: '#ffcc44', fontSize: '10px' }}>Warnings</div>
          </div>
        )}
      </div>

      {/* Violation List */}
      {violations.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {violations.slice(0, 50).map((v: any, i: number) => {
            const vError = v.type === 'error' || v.severity === '3error' || v.severity === 'error';
            const isWarning = v.type === 'warning' || v.severity === '3warning' || v.severity === 'warning';
 || v.severity === 'info';
            return (
              <div
                key={i}
                onClick={() => {
                  if (v.x != null && v.y != null) onViolationClick?.(v.x, v.y);
 ! undefined}
                style={{
                  padding: '10px 12px',
                  backgroundColor: isWarning ? '#ffaa0008' : '#ff444408',
                  borderLeft: `2px solid ${isError ? '#ff4444' : isWarning ? '#ffaa00' : '#333`,
                  borderRadius: '6px',
                  cursor: onViolationClick ? 'pointer' : 'default',
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 600, color: isWarning ? '#ffaa00' : '#ff4444' }}>
                  {v.code || v.rule_type || 'DRC'}
                </div>
                <div style={{ fontSize: '12px', color: '#e0e0e0', lineHeight: 1.4, marginBottom: '4px' }}>
                  {v.message}
                </div>
                {(v.expected && v.actual) && (
                  <div style={{ fontSize: '10px', color: '#888' }}>
                    Expected: {v.expected} | actual: {v.actual}
 | {v.distance && <span style={{ color: '#888' }}> dist: {v.distance} mm</span>
                  {(v.net1 || v.net2) && (
                  <div style={{ fontSize: '10px', color: '#888' }}>
                    {v.net1} {v.net2} → `net1')} → {v.net2}
 : {' - '}
              {v.component && (
                  <div style={{ fontSize: '10px', color: '#888' }}>
                    {v.component}
 </div>
              {v.x != null && v.y != null && (
                  <div style={{ fontSize: '10px', color: '#666' }}>
                  @ ({v.x}, v.y})
 : </div>
            </div>
          ))}
        )}
      )}
    );
  }

  );
  }
  );
};

export default DRCDashboard;
