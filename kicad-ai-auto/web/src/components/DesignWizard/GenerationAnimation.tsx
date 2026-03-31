/**
 * GenerationAnimation.tsx - Animated progress indicator for design generation
 *
 * Shows a multi-stage animation with rotating icons, progress bar,
 * and descriptive text for each generation phase.
 */

import React, { useEffect, useState, useMemo } from 'react';

interface GenerationAnimationProps {
  stage: string;
  progress?: number; // 0-100
  message?: string;
  substeps?: string[];
}

const STAGE_ICONS: Record<string, { icon: string; color: string; label: string }> = {
  analyzing: { icon: '🔍', color: '#4a9eff', label: '分析需求' },
  generating: { icon: '⚡', color: '#ff9800', label: '生成原理图' },
  placing: { icon: '📐', color: '#8bc34a', label: '元件布局' },
  routing: { icon: '🔌', color: '#ab47bc', label: '自动布线' },
  checking: { icon: '✅', color: '#4caf50', label: '质量检查' },
  exporting: { icon: '📦', color: '#42a5f5', label: '导出文件' },
  default: { icon: '⚙️', color: '#78909c', label: '处理中' },
};

export const GenerationAnimation: React.FC<GenerationAnimationProps> = ({
  stage,
  progress = 0,
  message = '',
  substeps = [],
}) => {
  const [dots, setDots] = useState('');
  const [activeSubstep, setActiveSubstep] = useState(0);

  const config = useMemo(() => STAGE_ICONS[stage] || STAGE_ICONS.default, [stage]);

  // Animate dots
  useEffect(() => {
    const timer = setInterval(() => {
      setDots(d => d.length >= 3 ? '' : d + '.');
    }, 400);
    return () => clearInterval(timer);
  }, []);

  // Cycle through substeps
  useEffect(() => {
    if (substeps.length === 0) return;
    const timer = setInterval(() => {
      setActiveSubstep(s => (s + 1) % substeps.length);
    }, 1500);
    return () => clearInterval(timer);
  }, [substeps]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 32,
      minHeight: 200,
    }}>
      {/* Spinning icon */}
      <div style={{
        fontSize: 56,
        marginBottom: 20,
        animation: 'gen-spin 2s ease-in-out infinite',
        filter: `drop-shadow(0 0 12px ${config.color}44)`,
      }}>
        {config.icon}
      </div>

      {/* Stage label */}
      <div style={{
        fontSize: 16,
        fontWeight: 600,
        color: config.color,
        marginBottom: 8,
      }}>
        {config.label}{dots}
      </div>

      {/* Progress bar */}
      <div style={{
        width: 240,
        height: 4,
        backgroundColor: '#333',
        borderRadius: 2,
        overflow: 'hidden',
        marginBottom: 16,
      }}>
        <div style={{
          width: `${progress}%`,
          height: '100%',
          backgroundColor: config.color,
          borderRadius: 2,
          transition: 'width 0.3s ease',
          boxShadow: `0 0 8px ${config.color}66`,
        }} />
      </div>

      {/* Message */}
      {message && (
        <div style={{
          fontSize: 12,
          color: '#a0a0a0',
          textAlign: 'center',
          maxWidth: 300,
          marginBottom: 12,
        }}>
          {message}
        </div>
      )}

      {/* Substeps */}
      {substeps.length > 0 && (
        <div style={{
          display: 'flex',
          gap: 8,
          marginTop: 8,
        }}>
          {substeps.map((step, i) => (
            <div
              key={i}
              style={{
                padding: '4px 10px',
                borderRadius: 10,
                fontSize: 10,
                fontFamily: 'monospace',
                backgroundColor: i === activeSubstep ? `${config.color}22` : 'transparent',
                border: `1px solid ${i === activeSubstep ? config.color : '#444'}`,
                color: i === activeSubstep ? config.color : '#666',
                transition: 'all 0.3s',
              }}
            >
              {step}
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes gen-spin {
          0%, 100% { transform: rotate(0deg) scale(1); }
          25% { transform: rotate(90deg) scale(1.1); }
          50% { transform: rotate(180deg) scale(1); }
          75% { transform: rotate(270deg) scale(1.1); }
        }
      `}</style>
    </div>
  );
};

export default GenerationAnimation;
