/**
 * DRC Dashboard - Phase 7A
 * Unified design rule check dashboard combining DRC, Safety, SI, and EMI analysis
 */

import React, { useState, useCallback } from 'react';
import { drcApi } from '../services/api';
import { PCBData, DRCItem } from '../types';

interface Tab {
  id: string;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: 'drc', label: 'DRC', icon: '🔍' },
  { id: 'safety', label: 'Safety', icon: '🛡️' },
  { id: 'si', label: 'SI', icon: '📈' },
  { id: 'emi', label: 'EMI', icon: '📡' },
];

/** DRC violation item */
interface DRCViolation {
  code?: string;
  rule_type?: string;
  message: string;
  severity?: 'error' | 'warning' | 'info';
  type?: 'error' | 'warning' | 'info';
  x?: number;
  y?: number;
  expected?: number | string;
  actual?: number | string;
  distance?: number;
  net1?: string;
  net2?: string;
  component?: string;
}

/** DRC result data */
interface DRCResultData {
  passed?: boolean;
  success?: boolean;
  error_count?: number;
  errorCount?: number;
  warning_count?: number;
  warningCount?: number;
  violations?: DRCViolation[];
  errors?: DRCViolation[];
  warnings?: DRCViolation[];
  statistics?: {
    total_checks?: number;
    passed_checks?: number;
    failed_checks?: number;
    components_checked?: number;
    tracks_checked?: number;
    vias_checked?: number;
    duration_ms?: number;
    [key: string]: number | undefined;
  };
  [key: string]: unknown;
}

interface DRCDashboardProps {
  projectId: string;
  pcbData?: PCBData;
  onViolationClick?: (x: number, y: number) => void;
}

/* ========== Violation Card ========== */

function ViolationCard({ v, onViolationClick }: { v: DRCViolation; onViolationClick?: (x: number, y: number) => void }) {
  const isError = v.type === 'error' || v.severity === 'error';
  const isWarning = v.type === 'warning' || v.severity === 'warning';

  return (
    <div
      onClick={() => {
        if (v.x != null && v.y != null && onViolationClick) {
          onViolationClick(v.x, v.y);
        }
      }}
      style={{
        padding: '8px 12px',
        backgroundColor: isError ? '#ff444408' : '#ffaa0008',
        borderLeft: `3px solid ${isError ? '#ff4444' : isWarning ? '#ffaa00' : '#444'}`,
        borderRadius: '6px',
        cursor: v.x != null && v.y != null && onViolationClick ? 'pointer' : 'default',
      }}
    >
      <div style={{ fontSize: '11px', fontWeight: 600, color: isError ? '#ff6666' : isWarning ? '#ffaa00' : '#aaa' }}>
        {v.code || v.rule_type || 'DRC'}
      </div>
      <div style={{ fontSize: '12px', color: '#e0e0e0', lineHeight: 1.4, marginBottom: '4px' }}>
        {v.message}
      </div>
      {v.expected != null && v.actual != null && (
        <div style={{ fontSize: '10px', color: '#888' }}>
          Expected: {v.expected} | Actual: {v.actual}
        </div>
      )}
      {v.distance != null && (
        <div style={{ fontSize: '10px', color: '#888' }}>
          Distance: {v.distance} mm
        </div>
      )}
      {(v.net1 || v.net2) && (
        <div style={{ fontSize: '10px', color: '#888' }}>
          Nets: {v.net1 || '-'} ↔ {v.net2 || '-'}
        </div>
      )}
      {v.component && (
        <div style={{ fontSize: '10px', color: '#888' }}>
          Component: {v.component}
        </div>
      )}
      {v.x != null && v.y != null && (
        <div style={{ fontSize: '10px', color: '#666' }}>
          @ ({Number(v.x).toFixed(2)}, {Number(v.y).toFixed(2)})
        </div>
      )}
    </div>
  );
}

/* ========== Result Panel ========== */

function ResultPanel({
  data,
  onViolationClick,
}: {
  data: DRCResultData;
  type: string;
  onViolationClick?: (x: number, y: number) => void;
}) {
  const violations: DRCViolation[] = (data?.violations || data?.errors || data?.warnings || []) as DRCViolation[];
  const isPassed = data?.passed ?? data?.success ?? false;
  const errorCount = data?.error_count ?? data?.errorCount ?? 0;
  const warningCount = data?.warning_count ?? data?.warningCount ?? 0;
  const stats = data?.statistics;

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
            {stats.components_checked || 0} components, {stats.tracks_checked || 0} tracks, {stats.vias_checked || 0} vias
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
      {/* Error/Warning Summary */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
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
          {violations.slice(0, 50).map((v, i) => (
            <ViolationCard key={i} v={v} onViolationClick={onViolationClick} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ========== Main Dashboard Component ========== */

const DRCDashboard: React.FC<DRCDashboardProps> = ({
  projectId,
  pcbData,
  onViolationClick,
}) => {
  const [activeTab, setActiveTab] = useState<string>('drc');
  const [results, setResults] = useState<Record<string, DRCResultData>>({});
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
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Check failed';
      setError(errorMessage);
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

  const getPassedInfo = (data: DRCResultData | undefined) => {
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
      <div style={{ display: 'flex', borderBottom: '1px solid #333' }}>
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

        {error && (
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
          <ResultPanel data={currentResult} type={activeTab} onViolationClick={onViolationClick} />
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

export default DRCDashboard;
