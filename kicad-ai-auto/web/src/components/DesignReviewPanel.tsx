/**
 * Design Review Panel - Phase 10
 * 实时设计审查面板
 *
 * 多维度审查: DRC/PI/SI/DFM/Thermal/EMI
 * AI 学习: 用户修正行为反馈
 */

import { useState, useEffect, useCallback } from 'react';
import './DesignReviewPanel.css';

interface ReviewIssue {
  category: string;
  severity: 'critical' | 'warning' | 'info' | 'suggestion';
  title: string;
  description: string;
  location?: { x: number; y: number; ref?: string };
  suggestion: string;
  rule_id: string;
}

interface ReviewResult {
  success: boolean;
  score: number;
  issues: ReviewIssue[];
  summary: {
    critical: number;
    warning: number;
    info: number;
    suggestion: number;
    total: number;
  };
  duration_s: number;
  board_stats: Record<string, number>;
}

interface LearningStats {
  total_corrections: number;
  accepted: number;
  dismissed: number;
}

interface DesignReviewPanelProps {
  visible: boolean;
  pcbData?: Record<string, unknown>;
  onClose: () => void;
}

const SEVERITY_CONFIG = {
  critical: { label: '严重', color: '#ef5350', icon: '🔴' },
  warning: { label: '警告', color: '#ff9800', icon: '🟡' },
  info: { label: '信息', color: '#42a5f5', icon: '🔵' },
  suggestion: { label: '建议', color: '#66bb6a', icon: '🟢' },
};

const CATEGORY_LABELS: Record<string, string> = {
  drc: '设计规则',
  schematic: '原理图',
  layout: '布局',
  routing: '布线',
  manufacturing: '可制造性',
  signal_integrity: '信号完整性',
  emi: 'EMI',
  thermal: '热管理',
  power: '电源',
};

export default function DesignReviewPanel({
  visible,
  pcbData,
  onClose,
}: DesignReviewPanelProps) {
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [expandedIssue, setExpandedIssue] = useState<string | null>(null);
  const [learningStats, setLearningStats] = useState<LearningStats | null>(null);

  const runReview = useCallback(async () => {
    if (!pcbData) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/review/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pcb_data: pcbData, include_suggestions: true }),
      });
      const data = await response.json();
      if (response.ok) setResult(data);
    } catch (err) {
      console.error('Review failed:', err);
    } finally {
      setLoading(false);
    }
  }, [pcbData]);

  const recordAction = useCallback(async (ruleId: string, action: string) => {
    try {
      await fetch('/api/v1/review/correction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_id: ruleId, action, details: '' }),
      });
    } catch {}
  }, []);

  useEffect(() => {
    if (visible && pcbData) {
      runReview();
    }
  }, [visible, pcbData]);

  useEffect(() => {
    if (visible) {
      fetch('/api/v1/review/learning-stats')
        .then(r => r.json())
        .then(setLearningStats)
        .catch(() => {});
    }
  }, [visible]);

  if (!visible) return null;

  const filteredIssues = result?.issues.filter(
    i => filter === 'all' || i.severity === filter
  ) ?? [];

  const scoreColor = result
    ? result.score >= 80 ? '#66bb6a'
      : result.score >= 60 ? '#ff9800'
      : '#ef5350'
    : '#888';

  return (
    <div className="review-panel">
      {/* Header */}
      <div className="rp-header">
        <h3>设计审查</h3>
        <div className="rp-header-actions">
          <button className="rp-run-btn" onClick={runReview} disabled={loading}>
            {loading ? '审查中...' : '重新审查'}
          </button>
          <button className="rp-close-btn" onClick={onClose}>✕</button>
        </div>
      </div>

      {/* Score */}
      {result && (
        <div className="rp-score-section">
          <div className="rp-score-ring" style={{ borderColor: scoreColor }}>
            <span className="rp-score-value" style={{ color: scoreColor }}>
              {result.score.toFixed(0)}
            </span>
          </div>
          <div className="rp-summary-chips">
            {(['critical', 'warning', 'info', 'suggestion'] as const).map(sev => {
              const cfg = SEVERITY_CONFIG[sev];
              const count = result.summary[sev] || 0;
              return (
                <button
                  key={sev}
                  className={`rp-chip ${filter === sev ? 'active' : ''}`}
                  style={{ borderColor: count > 0 ? cfg.color : '#333' }}
                  onClick={() => setFilter(filter === sev ? 'all' : sev)}
                >
                  {cfg.icon} {cfg.label}: {count}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Issues List */}
      <div className="rp-issues">
        {filteredIssues.length === 0 && !loading && (
          <div className="rp-empty">
            {result ? '没有发现设计问题!' : '点击"重新审查"开始检查'}
          </div>
        )}
        {filteredIssues.map((issue, idx) => {
          const cfg = SEVERITY_CONFIG[issue.severity];
          const isExpanded = expandedIssue === issue.rule_id;
          return (
            <div
              key={`${issue.rule_id}-${idx}`}
              className={`rp-issue rp-issue-${issue.severity}`}
              onClick={() => setExpandedIssue(isExpanded ? null : issue.rule_id)}
            >
              <div className="rp-issue-header">
                <span className="rp-issue-severity" style={{ color: cfg.color }}>
                  {cfg.icon}
                </span>
                <span className="rp-issue-title">{issue.title}</span>
                <span className="rp-issue-category">
                  {CATEGORY_LABELS[issue.category] || issue.category}
                </span>
              </div>
              {isExpanded && (
                <div className="rp-issue-detail">
                  <p className="rp-issue-desc">{issue.description}</p>
                  {issue.suggestion && (
                    <div className="rp-issue-suggestion">
                      <span className="rp-suggestion-label">建议:</span>
                      <span>{issue.suggestion}</span>
                    </div>
                  )}
                  <div className="rp-issue-actions">
                    <button
                      className="rp-action-btn rp-accept"
                      onClick={e => { e.stopPropagation(); recordAction(issue.rule_id, 'accepted'); }}
                    >
                      接受
                    </button>
                    <button
                      className="rp-action-btn rp-dismiss"
                      onClick={e => { e.stopPropagation(); recordAction(issue.rule_id, 'dismissed'); }}
                    >
                      忽略
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Learning Stats */}
      {learningStats && learningStats.total_corrections > 0 && (
        <div className="rp-learning">
          <span className="rp-learning-label">AI 学习</span>
          <span className="rp-learning-stat">
            {learningStats.total_corrections} 次反馈
          </span>
        </div>
      )}

      {/* Board Stats */}
      {result?.board_stats && (
        <div className="rp-board-stats">
          {Object.entries(result.board_stats).map(([key, val]) => (
            <span key={key} className="rp-stat-item">{key}: {val}</span>
          ))}
        </div>
      )}
    </div>
  );
}
