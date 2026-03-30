/**
 * DRC Report Component
 *
 * Phase 3: DRC检查报告显示
 * - 显示DRC违规列表
 * - 按类型/严重程度分组
 * - 支持定位到具体位置
 */

import React, { useState, useMemo } from 'react';
import './DRCReport.css';

interface DRCViolation {
  ruleName: string;
  ruleType: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  net1?: string;
  net2?: string;
  component?: string;
  x?: number;
  y?: number;
  expected?: number;
  actual?: number;
  layer?: string;
}

interface DRCReportProps {
  violations: DRCViolation[];
  onViolationClick?: (violation: DRCViolation) => void;
  compact?: boolean;
}

const DRCReport: React.FC<DRCReportProps> = ({
  violations,
  onViolationClick,
  compact = false
}) => {
  const [filter, setFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all');
  const [sortBy, setSortBy] = useState<'severity' | 'type'>('severity');

  const stats = useMemo(() => {
    const errorCount = violations.filter(v => v.severity === 'error').length;
    const warningCount = violations.filter(v => v.severity === 'warning').length;
    const infoCount = violations.filter(v => v.severity === 'info').length;
    return { errorCount, warningCount, infoCount, total: violations.length };
  }, [violations]);

  const filteredViolations = useMemo(() => {
    let result = violations;
    if (filter !== 'all') {
      result = result.filter(v => v.severity === filter);
    }

    // Sort
    const severityOrder = { error: 0, warning: 1, info: 2 };
    return [...result].sort((a, b) => {
      if (sortBy === 'severity') {
        return severityOrder[a.severity] - severityOrder[b.severity];
      }
      return a.ruleType.localeCompare(b.ruleType);
    });
  }, [violations, filter, sortBy]);

  const groupedByType = useMemo(() => {
    const groups: Record<string, DRCViolation[]> = {};
    filteredViolations.forEach(v => {
      const type = v.ruleType || 'other';
      if (!groups[type]) groups[type] = [];
      groups[type].push(v);
    });
    return groups;
  }, [filteredViolations]);

  const getSeverityIcon = (severity: string): string => {
    switch (severity) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '•';
    }
  };

  const getSeverityClass = (severity: string): string => {
    return `severity-${severity}`;
  };

  const getRuleTypeName = (type: string): string => {
    const names: Record<string, string> = {
      'clearance': '间距',
      'track_width': '线宽',
      'via_size': '过孔',
      'differential_pair': '差分对',
      'net_class': '网络类',
      'manufacturing': '制造',
      'high_speed': '高速信号'
    };
    return names[type] || type;
  };

  if (compact) {
    return (
      <div className="drc-report-compact">
        <div className="stats-row">
          <span className="stat error">
            <span className="dot" /> {stats.errorCount} 错误
          </span>
          <span className="stat warning">
            <span className="dot" /> {stats.warningCount} 警告
          </span>
        </div>
        {stats.errorCount === 0 && stats.warningCount === 0 && (
          <div className="pass-message">
            ✅ DRC检查通过
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="drc-report">
      {/* Header Stats */}
      <div className="report-header">
        <h3>DRC检查报告</h3>
        <div className="stats-pills">
          <span className={`pill ${stats.errorCount > 0 ? 'has-error' : ''}`}>
            ❌ {stats.errorCount}
          </span>
          <span className={`pill ${stats.warningCount > 0 ? 'has-warning' : ''}`}>
            ⚠️ {stats.warningCount}
          </span>
          <span className="pill info">
            ℹ️ {stats.infoCount}
          </span>
        </div>
      </div>

      {/* Pass/Fail Status */}
      {stats.errorCount === 0 ? (
        <div className="status-pass">
          <span className="icon">✅</span>
          <span>设计规则检查通过</span>
        </div>
      ) : (
        <div className="status-fail">
          <span className="icon">❌</span>
          <span>发现 {stats.errorCount} 个错误需要修复</span>
        </div>
      )}

      {/* Filters */}
      <div className="report-controls">
        <div className="filter-buttons">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            全部 ({stats.total})
          </button>
          <button
            className={filter === 'error' ? 'active' : ''}
            onClick={() => setFilter('error')}
          >
            错误 ({stats.errorCount})
          </button>
          <button
            className={filter === 'warning' ? 'active' : ''}
            onClick={() => setFilter('warning')}
          >
            警告 ({stats.warningCount})
          </button>
          <button
            className={filter === 'info' ? 'active' : ''}
            onClick={() => setFilter('info')}
          >
            信息 ({stats.infoCount})
          </button>
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'severity' | 'type')}
          className="sort-select"
        >
          <option value="severity">按严重程度</option>
          <option value="type">按规则类型</option>
        </select>
      </div>

      {/* Violations List */}
      <div className="violations-list">
        {sortBy === 'type' ? (
          // Grouped by type
          Object.entries(groupedByType).map(([type, viols]) => (
            <div key={type} className="violation-group">
              <div className="group-header">
                <span className="group-type">{getRuleTypeName(type)}</span>
                <span className="group-count">{viols.length}</span>
              </div>
              <div className="group-items">
                {viols.map((v, idx) => (
                  <div
                    key={idx}
                    className={`violation-item ${getSeverityClass(v.severity)}`}
                    onClick={() => onViolationClick?.(v)}
                  >
                    <span className="severity-icon">
                      {getSeverityIcon(v.severity)}
                    </span>
                    <div className="violation-content">
                      <span className="violation-message">{v.message}</span>
                      {v.x !== undefined && v.y !== undefined && (
                        <span className="violation-location">
                          位置: ({v.x.toFixed(2)}, {v.y.toFixed(2)})
                        </span>
                      )}
                    </div>
                    {v.expected !== undefined && v.actual !== undefined && (
                      <div className="violation-values">
                        <span className="expected">期望: {v.expected}</span>
                        <span className="actual">实际: {v.actual}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))
        ) : (
          // Flat list sorted by severity
          filteredViolations.map((v, idx) => (
            <div
              key={idx}
              className={`violation-item ${getSeverityClass(v.severity)}`}
              onClick={() => onViolationClick?.(v)}
            >
              <span className="severity-icon">
                {getSeverityIcon(v.severity)}
              </span>
              <div className="violation-content">
                <div className="violation-header">
                  <span className="rule-name">{v.ruleName}</span>
                  <span className="rule-type">{getRuleTypeName(v.ruleType)}</span>
                </div>
                <span className="violation-message">{v.message}</span>
                <div className="violation-meta">
                  {v.x !== undefined && v.y !== undefined && (
                    <span>📍 ({v.x.toFixed(2)}, {v.y.toFixed(2)})</span>
                  )}
                  {v.layer && <span>📐 {v.layer}</span>}
                  {v.net1 && <span>🔌 {v.net1}</span>}
                </div>
              </div>
              {v.expected !== undefined && v.actual !== undefined && (
                <div className="violation-values">
                  <span className="expected">期望: {v.expected}</span>
                  <span className="actual">实际: {v.actual}</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Empty State */}
      {filteredViolations.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">✅</span>
          <span>没有发现{filter !== 'all' ? `${filter === 'error' ? '错误' : filter === 'warning' ? '警告' : '信息'}` : ''}问题</span>
        </div>
      )}
    </div>
  );
};

export default DRCReport;
export type { DRCViolation, DRCReportProps };