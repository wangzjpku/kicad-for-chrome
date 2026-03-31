/**
 * Design Progress Panel - Phase 7E
 * 多步设计 Agent 进度面板
 *
 * 显示 10 步设计流水线的实时进度:
 * 需求分析 → 模板匹配 → 原理图生成 → ERC验证 → 自动修复
 * → PCB布局 → PCB布线 → DRC检查 → 铺铜 → 最终验证
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import './DesignProgressPanel.css';

// 步骤定义
const STEPS = [
  { key: 'requirements_analysis', label: '需求分析', icon: '🔍' },
  { key: 'template_matching', label: '模板匹配', icon: '📋' },
  { key: 'schematic_generation', label: '原理图生成', icon: '📐' },
  { key: 'erc_validation', label: 'ERC 验证', icon: '✓' },
  { key: 'auto_fix', label: '自动修复', icon: '🔧' },
  { key: 'pcb_layout', label: 'PCB 布局', icon: '📦' },
  { key: 'pcb_routing', label: 'PCB 布线', icon: '〰' },
  { key: 'drc_check', label: 'DRC 检查', icon: '⚠' },
  { key: 'copper_pour', label: '铺铜', icon: '🟫' },
  { key: 'final_validation', label: '最终验证', icon: '🏆' },
] as const;

type StepKey = (typeof STEPS)[number]['key'];

interface StepState {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  message?: string;
  duration_s?: number;
  data?: Record<string, unknown>;
  errors?: string[];
  warnings?: string[];
}

interface DesignProgressPanelProps {
  /** 是否显示面板 */
  visible: boolean;
  /** 任务 ID (启动设计后获得) */
  taskId: string | null;
  /** 设计需求描述 */
  requirements?: string;
  /** 关闭回调 */
  onClose: () => void;
  /** 设计完成回调 */
  onCompleted?: (result: DesignResult) => void;
}

export interface DesignResult {
  task_id: string;
  success: boolean;
  steps: Array<{
    step_type: string;
    status: string;
    message: string;
    duration_s: number;
    data?: Record<string, unknown>;
    errors: string[];
    warnings: string[];
  }>;
  total_duration_s: number;
  iterations: number;
  error_message: string;
  schematic?: Record<string, unknown>;
  pcb?: Record<string, unknown>;
  drc_result?: Record<string, unknown>;
  bom?: Array<Record<string, unknown>>;
}

const STEP_STATUS_ICONS: Record<StepState['status'], string> = {
  pending: '○',
  running: '◉',
  completed: '●',
  failed: '✕',
  skipped: '—',
};

export default function DesignProgressPanel({
  visible,
  taskId,
  requirements,
  onClose,
  onCompleted,
}: DesignProgressPanelProps) {
  const [steps, setSteps] = useState<Record<StepKey, StepState>>(
    () => Object.fromEntries(STEPS.map(s => [s.key, { status: 'pending' as const }])) as Record<StepKey, StepState>
  );
  const [overallProgress, setOverallProgress] = useState(0);
  const [overallStatus, setOverallStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [totalDuration, setTotalDuration] = useState(0);
  const [logMessages, setLogMessages] = useState<string[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // 添加日志消息
  const addLog = useCallback((msg: string) => {
    setLogMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  // 轮询进度
  useEffect(() => {
    if (!visible || !taskId) return;

    setOverallStatus('running');
    setLogMessages([]);
    addLog(`设计任务已启动: ${taskId}`);
    if (requirements) addLog(`需求: ${requirements.slice(0, 80)}...`);

    pollRef.current = setInterval(async () => {
      try {
        // Fetch progress
        const progressRes = await fetch(`/api/v1/agent/progress/${taskId}`);
        if (!progressRes.ok) return;
        const progress = await progressRes.json();

        setOverallProgress(progress.progress_pct);

        // Update current step
        const currentStep = progress.current_step as StepKey;
        if (currentStep) {
          setSteps(prev => ({
            ...prev,
            [currentStep]: { status: 'running', message: `正在执行...` },
          }));
        }

        // Mark earlier steps as completed based on step_index
        const stepIndex = progress.step_index;
        for (let i = 0; i < stepIndex && i < STEPS.length; i++) {
          const stepKey = STEPS[i].key;
          setSteps(prev => {
            if (prev[stepKey].status === 'pending' || prev[stepKey].status === 'running') {
              return { ...prev, [stepKey]: { status: 'completed' } };
            }
            return prev;
          });
        }

        // If completed or failed, fetch final result
        if (progress.status === 'completed' || progress.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);

          try {
            const resultRes = await fetch(`/api/v1/agent/result/${taskId}`);
            if (resultRes.ok) {
              const result: DesignResult = await resultRes.json();
              setOverallStatus(result.success ? 'completed' : 'failed');
              setTotalDuration(result.total_duration_s);

              // Update all steps from result
              const newSteps = { ...steps };
              for (const step of result.steps) {
                const key = step.step_type as StepKey;
                if (key in newSteps) {
                  newSteps[key] = {
                    status: step.status as StepState['status'],
                    message: step.message,
                    duration_s: step.duration_s,
                    data: step.data,
                    errors: step.errors,
                    warnings: step.warnings,
                  };
                }
              }
              setSteps(newSteps);
              setOverallProgress(100);

              result.steps.forEach(s => {
                const icon = s.status === 'completed' ? '✓' : s.status === 'failed' ? '✕' : '→';
                addLog(`${icon} ${s.step_type}: ${s.message}`);
              });

              addLog(result.success
                ? `设计完成! 总耗时 ${result.total_duration_s.toFixed(1)}s`
                : `设计失败: ${result.error_message}`
              );

              onCompleted?.(result);
            }
          } catch {
            // result not ready yet
          }
        }
      } catch (err) {
        // Polling error - network issue, keep trying
        console.warn('Progress poll error:', err);
      }
    }, 1000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [visible, taskId]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logMessages]);

  if (!visible) return null;

  const completedCount = Object.values(steps).filter(s => s.status === 'completed').length;
  const failedCount = Object.values(steps).filter(s => s.status === 'failed').length;

  return (
    <div className="design-progress-panel">
      {/* Header */}
      <div className="dpp-header">
        <h3>AI 设计流水线</h3>
        <div className="dpp-header-stats">
          <span className={`dpp-status-badge dpp-status-${overallStatus}`}>
            {overallStatus === 'idle' && '等待中'}
            {overallStatus === 'running' && '运行中'}
            {overallStatus === 'completed' && '已完成'}
            {overallStatus === 'failed' && '失败'}
          </span>
          {overallStatus === 'running' && (
            <span className="dpp-progress-text">{overallProgress.toFixed(0)}%</span>
          )}
          {totalDuration > 0 && (
            <span className="dpp-duration">{totalDuration.toFixed(1)}s</span>
          )}
        </div>
        <button className="dpp-close-btn" onClick={onClose} title="关闭">✕</button>
      </div>

      {/* Progress Bar */}
      <div className="dpp-progress-bar-container">
        <div
          className={`dpp-progress-bar ${failedCount > 0 ? 'dpp-progress-has-errors' : ''}`}
          style={{ width: `${overallProgress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="dpp-steps">
        {STEPS.map((step, idx) => {
          const state = steps[step.key];
          return (
            <div
              key={step.key}
              className={`dpp-step dpp-step-${state.status}`}
            >
              <div className="dpp-step-indicator">
                <span className="dpp-step-icon">
                  {state.status === 'running' ? '◉' : STEP_STATUS_ICONS[state.status]}
                </span>
                {idx < STEPS.length - 1 && (
                  <div className={`dpp-step-connector ${state.status === 'completed' ? 'connected' : ''}`} />
                )}
              </div>
              <div className="dpp-step-content">
                <div className="dpp-step-header">
                  <span className="dpp-step-label">
                    <span className="dpp-step-emoji">{step.icon}</span>
                    {step.label}
                  </span>
                  {state.duration_s !== undefined && state.duration_s > 0 && (
                    <span className="dpp-step-duration">{state.duration_s.toFixed(1)}s</span>
                  )}
                </div>
                {state.message && (
                  <div className="dpp-step-message">{state.message}</div>
                )}
                {state.errors && state.errors.length > 0 && (
                  <div className="dpp-step-errors">
                    {state.errors.map((e, i) => (
                      <div key={i} className="dpp-error-item">{e}</div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary */}
      {(overallStatus === 'completed' || overallStatus === 'failed') && (
        <div className={`dpp-summary dpp-summary-${overallStatus}`}>
          {overallStatus === 'completed' ? (
            <>
              <span>设计完成! {completedCount}/{STEPS.length} 步骤成功</span>
              {totalDuration > 0 && <span> · 耗时 {totalDuration.toFixed(1)}s</span>}
            </>
          ) : (
            <>
              <span>设计未完成: {failedCount} 步骤失败</span>
            </>
          )}
        </div>
      )}

      {/* Log */}
      <div className="dpp-log">
        <div className="dpp-log-title">执行日志</div>
        <div className="dpp-log-content">
          {logMessages.map((msg, i) => (
            <div key={i} className="dpp-log-line">{msg}</div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
