/**
 * Impedance Calculator Component
 *
 * Phase 4: 阻抗计算器
 * - 计算单端/差分阻抗
 * - 支持多种层叠配置
 * - 反推走线宽度
 */

import React, { useState, useEffect, useMemo } from 'react';
import './ImpedanceCalculator.css';

interface ImpedanceResult {
  impedance: number;
  traceWidth: number;
  dielectricThickness: number;
  dk: number;
  propagationDelay: number;
  coupling: string;
  diffSpacing?: number;
}

interface ImpedanceCalculatorProps {
  onCalculate?: (result: ImpedanceResult) => void;
  defaultLayer?: string;
}

const ImpedanceCalculator: React.FC<ImpedanceCalculatorProps> = ({
  onCalculate,
  defaultLayer = 'F.Cu'
}) => {
  const [mode, setMode] = useState<'calculate' | 'reverse'>('calculate');
  const [coupling, setCoupling] = useState<'single' | 'diff'>('single');
  const [traceWidth, setTraceWidth] = useState<number>(0.25);
  const [diffSpacing, setDiffSpacing] = useState<number>(0.2);
  const [dielectricThickness, setDielectricThickness] = useState<number>(0.2);
  const [dk, setDk] = useState<number>(4.5);
  const [targetImpedance, setTargetImpedance] = useState<number>(50);
  const [copperThickness, setCopperThickness] = useState<number>(0.035);

  const [result, setResult] = useState<ImpedanceResult | null>(null);

  // Calculate impedance
  const calculateImpedance = (
    w: number,
    h: number,
    er: number,
    t: number,
    isDiff: boolean,
    s?: number
  ): number => {
    // Microstrip formula (simplified)
    // Z0 = 87 / sqrt(Er+1.41) * ln(5.98H / (0.8W + T))
    const zSingle = 87 / Math.sqrt(er + 1.41) * Math.log(5.98 * h / (0.8 * w + t));

    if (isDiff && s) {
      // Differential impedance
      return 2 * zSingle * (1 - 0.48 * Math.exp(-0.96 * s / h));
    }
    return zSingle;
  };

  // Reverse calculate trace width for target impedance
  const reverseCalculate = (
    zTarget: number,
    h: number,
    er: number,
    t: number,
    isDiff: boolean,
    s?: number
  ): number => {
    // Binary search for optimal width
    let low = 0.05;
    let high = 5.0;
    let bestWidth = 0.25;

    for (let i = 0; i < 20; i++) {
      const mid = (low + high) / 2;
      const z = calculateImpedance(mid, h, er, t, isDiff, s);

      if (Math.abs(z - zTarget) < 0.5) {
        bestWidth = mid;
        break;
      }

      if (z > zTarget) {
        low = mid;
      } else {
        high = mid;
      }
      bestWidth = mid;
    }

    return Math.round(bestWidth * 1000) / 1000;
  };

  // Run calculation
  useEffect(() => {
    if (mode === 'calculate') {
      const impedance = calculateImpedance(
        traceWidth,
        dielectricThickness,
        dk,
        copperThickness,
        coupling === 'diff',
        diffSpacing
      );
      const delay = 3.34 * Math.sqrt(dk); // ps/mm

      const res: ImpedanceResult = {
        impedance: Math.round(impedance * 10) / 10,
        traceWidth,
        dielectricThickness,
        dk,
        propagationDelay: Math.round(delay * 10) / 10,
        coupling,
        diffSpacing: coupling === 'diff' ? diffSpacing : undefined
      };
      setResult(res);
      onCalculate?.(res);
    }
  }, [mode, traceWidth, dielectricThickness, dk, copperThickness, coupling, diffSpacing]);

  // Reverse calculation
  useEffect(() => {
    if (mode === 'reverse') {
      const width = reverseCalculate(
        targetImpedance,
        dielectricThickness,
        dk,
        copperThickness,
        coupling === 'diff',
        diffSpacing
      );
      const impedance = calculateImpedance(
        width,
        dielectricThickness,
        dk,
        copperThickness,
        coupling === 'diff',
        diffSpacing
      );
      const delay = 3.34 * Math.sqrt(dk);

      const res: ImpedanceResult = {
        impedance: Math.round(impedance * 10) / 10,
        traceWidth: width,
        dielectricThickness,
        dk,
        propagationDelay: Math.round(delay * 10) / 10,
        coupling,
        diffSpacing: coupling === 'diff' ? diffSpacing : undefined
      };
      setResult(res);
      onCalculate?.(res);
    }
  }, [mode, targetImpedance, dielectricThickness, dk, copperThickness, coupling, diffSpacing]);

  // Preset configurations
  const presets = [
    { name: 'USB 2.0', coupling: 'diff' as const, impedance: 90, spacing: 0.2 },
    { name: 'USB 3.0', coupling: 'diff' as const, impedance: 90, spacing: 0.15 },
    { name: 'HDMI', coupling: 'diff' as const, impedance: 100, spacing: 0.1 },
    { name: 'DDR4', coupling: 'single' as const, impedance: 40, spacing: 0 },
    { name: '以太网', coupling: 'diff' as const, impedance: 100, spacing: 0.2 },
    { name: 'RF 50Ω', coupling: 'single' as const, impedance: 50, spacing: 0 },
  ];

  const applyPreset = (preset: typeof presets[0]) => {
    setCoupling(preset.coupling);
    setTargetImpedance(preset.impedance);
    setDiffSpacing(preset.spacing);
    setMode('reverse');
  };

  return (
    <div className="impedance-calculator">
      <div className="calc-header">
        <h3>阻抗计算器</h3>
        <div className="mode-toggle">
          <button
            className={mode === 'calculate' ? 'active' : ''}
            onClick={() => setMode('calculate')}
          >
            计算阻抗
          </button>
          <button
            className={mode === 'reverse' ? 'active' : ''}
            onClick={() => setMode('reverse')}
          >
            反推线宽
          </button>
        </div>
      </div>

      {/* Presets */}
      <div className="presets-section">
        <span className="label">快捷预设:</span>
        <div className="preset-buttons">
          {presets.map((preset, idx) => (
            <button
              key={idx}
              className="preset-btn"
              onClick={() => applyPreset(preset)}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Input Parameters */}
      <div className="params-section">
        {/* Coupling Type */}
        <div className="param-row">
          <label>耦合类型</label>
          <div className="coupling-toggle">
            <button
              className={coupling === 'single' ? 'active' : ''}
              onClick={() => setCoupling('single')}
            >
              单端
            </button>
            <button
              className={coupling === 'diff' ? 'active' : ''}
              onClick={() => setCoupling('diff')}
            >
              差分
            </button>
          </div>
        </div>

        {/* Mode-specific inputs */}
        {mode === 'calculate' ? (
          <div className="param-row">
            <label>走线宽度 (mm)</label>
            <input
              type="number"
              value={traceWidth}
              onChange={(e) => setTraceWidth(parseFloat(e.target.value) || 0)}
              step="0.01"
              min="0.05"
              max="5"
            />
          </div>
        ) : (
          <div className="param-row">
            <label>目标阻抗 (Ω)</label>
            <input
              type="number"
              value={targetImpedance}
              onChange={(e) => setTargetImpedance(parseFloat(e.target.value) || 50)}
              step="1"
              min="10"
              max="200"
            />
          </div>
        )}

        {/* Differential spacing */}
        {coupling === 'diff' && (
          <div className="param-row">
            <label>差分间距 (mm)</label>
            <input
              type="number"
              value={diffSpacing}
              onChange={(e) => setDiffSpacing(parseFloat(e.target.value) || 0.2)}
              step="0.01"
              min="0.05"
              max="2"
            />
          </div>
        )}

        {/* Dielectric */}
        <div className="param-row">
          <label>介质厚度 (mm)</label>
          <input
            type="number"
            value={dielectricThickness}
            onChange={(e) => setDielectricThickness(parseFloat(e.target.value) || 0.2)}
            step="0.01"
            min="0.05"
            max="2"
          />
        </div>

        <div className="param-row">
          <label>介电常数 (Dk)</label>
          <input
            type="number"
            value={dk}
            onChange={(e) => setDk(parseFloat(e.target.value) || 4.5)}
            step="0.1"
            min="2"
            max="10"
          />
          <span className="hint">FR-4: 4.5, Rogers: 3.5</span>
        </div>

        <div className="param-row">
          <label>铜厚 (mm)</label>
          <input
            type="number"
            value={copperThickness}
            onChange={(e) => setCopperThickness(parseFloat(e.target.value) || 0.035)}
            step="0.005"
            min="0.017"
            max="0.07"
          />
          <span className="hint">1oz: 0.035, 2oz: 0.07</span>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="results-section">
          <h4>计算结果</h4>
          <div className="results-grid">
            <div className="result-item primary">
              <span className="label">
                {mode === 'calculate' ? '阻抗' : '走线宽度'}
              </span>
              <span className="value">
                {mode === 'calculate'
                  ? `${result.impedance} Ω`
                  : `${result.traceWidth} mm`}
              </span>
            </div>
            <div className="result-item">
              <span className="label">传播延迟</span>
              <span className="value">{result.propagationDelay} ps/mm</span>
            </div>
            {coupling === 'diff' && (
              <div className="result-item">
                <span className="label">差分阻抗</span>
                <span className="value">{result.impedance} Ω</span>
              </div>
            )}
          </div>

          {/* Visual representation */}
          <div className="impedance-visual">
            <div className="trace-diagram">
              <div className="trace" style={{ width: `${result.traceWidth * 40}px` }} />
              {coupling === 'diff' && (
                <>
                  <div className="spacing" style={{ width: `${diffSpacing * 20}px` }} />
                  <div className="trace" style={{ width: `${result.traceWidth * 40}px` }} />
                </>
              )}
            </div>
            <div className="diagram-labels">
              <span>走线宽度: {result.traceWidth}mm</span>
              {coupling === 'diff' && <span>间距: {diffSpacing}mm</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImpedanceCalculator;