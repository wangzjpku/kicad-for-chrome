/**
 * Differential Pair Dialog - Phase 9
 * 差分对布线对话框
 *
 * 功能:
 * - 差分信号耦合布线
 * - 阻抗控制 (USB 90Ω, HDMI 100Ω, PCIe 85Ω)
 * - 长度匹配调谐
 */

import { useState, useCallback } from 'react';
import './DiffPairDialog.css';

type ImpedancePreset = {
  label: string;
  value: number;
  protocol: string;
};

const IMPEDANCE_PRESETS: ImpedancePreset[] = [
  { label: 'USB 2.0/3.0', value: 90, protocol: 'USB' },
  { label: 'HDMI / DP', value: 100, protocol: 'HDMI' },
  { label: 'PCIe', value: 85, protocol: 'PCIe' },
  { label: 'Ethernet', value: 100, protocol: 'ETH' },
  { label: 'SATA', value: 100, protocol: 'SATA' },
  { label: '自定义', value: 0, protocol: 'CUSTOM' },
];

interface DiffPairResult {
  success: boolean;
  pos_points: Array<{ x: number; y: number }>;
  neg_points: Array<{ x: number; y: number }>;
  pos_length: number;
  neg_length: number;
  length_mismatch: number;
  impedance: number;
  target_impedance: number;
}

interface DiffPairDialogProps {
  onClose: () => void;
  onApply: (result: DiffPairResult) => void;
}

export default function DiffPairDialog({ onClose, onApply }: DiffPairDialogProps) {
  const [preset, setPreset] = useState(0);
  const [targetZ, setTargetZ] = useState(90);
  const [customZ, setCustomZ] = useState(90);

  // Start/End points
  const [startPosX, setStartPosX] = useState(10);
  const [startPosY, setStartPosY] = useState(45);
  const [startNegX, setStartNegX] = useState(10);
  const [startNegY, setStartNegY] = useState(55);
  const [endPosX, setEndPosX] = useState(90);
  const [endPosY, setEndPosY] = useState(45);
  const [endNegX, setEndNegX] = useState(90);
  const [endNegY, setEndNegY] = useState(55);

  const [layer, setLayer] = useState('F.Cu');
  const [maxMismatch, setMaxMismatch] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiffPairResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const effectiveZ = preset < IMPEDANCE_PRESETS.length - 1 ? IMPEDANCE_PRESETS[preset].value : customZ;

  const handleRoute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/pcb/diff-pair-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_pos_x: startPosX, start_pos_y: startPosY,
          start_neg_x: startNegX, start_neg_y: startNegY,
          end_pos_x: endPosX, end_pos_y: endPosY,
          end_neg_x: endNegX, end_neg_y: endNegY,
          layer,
          target_impedance: effectiveZ,
          max_length_mismatch: maxMismatch,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Routing failed');
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [startPosX, startPosY, startNegX, startNegY, endPosX, endPosY, endNegX, endNegY, layer, effectiveZ, maxMismatch]);

  return (
    <div className="diff-pair-overlay" onClick={onClose}>
      <div className="diff-pair-dialog" onClick={e => e.stopPropagation()}>
        <div className="dpd-header">
          <h3>差分对布线</h3>
          <button className="dpd-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="dpd-body">
          {/* Impedance Presets */}
          <div className="dpd-section">
            <label className="dpd-label">阻抗预设</label>
            <div className="dpd-presets">
              {IMPEDANCE_PRESETS.map((p, i) => (
                <button
                  key={i}
                  className={`dpd-preset-btn ${preset === i ? 'active' : ''}`}
                  onClick={() => setPreset(i)}
                >
                  <span className="dpd-preset-name">{p.label}</span>
                  <span className="dpd-preset-z">{p.value > 0 ? `${p.value}Ω` : '?'}</span>
                </button>
              ))}
            </div>
            {preset === IMPEDANCE_PRESETS.length - 1 && (
              <div className="dpd-field" style={{ marginTop: 8 }}>
                <span>自定义阻抗 (Ω)</span>
                <input type="number" step="1" value={customZ} onChange={e => setCustomZ(+e.target.value)} />
              </div>
            )}
          </div>

          {/* Pin Positions */}
          <div className="dpd-section">
            <label className="dpd-label">引脚位置 (mm)</label>
            <div className="dpd-pins-grid">
              <div className="dpd-pin-header"><span></span><span>X</span><span>Y</span></div>
              <div className="dpd-pin-row">
                <span className="dpd-pin-label dpd-pos">P+</span>
                <input type="number" step="0.1" value={startPosX} onChange={e => setStartPosX(+e.target.value)} />
                <input type="number" step="0.1" value={startPosY} onChange={e => setStartPosY(+e.target.value)} />
              </div>
              <div className="dpd-pin-row">
                <span className="dpd-pin-label dpd-neg">P-</span>
                <input type="number" step="0.1" value={startNegX} onChange={e => setStartNegX(+e.target.value)} />
                <input type="number" step="0.1" value={startNegY} onChange={e => setStartNegY(+e.target.value)} />
              </div>
              <div className="dpd-pin-row">
                <span className="dpd-pin-label dpd-pos">N+</span>
                <input type="number" step="0.1" value={endPosX} onChange={e => setEndPosX(+e.target.value)} />
                <input type="number" step="0.1" value={endPosY} onChange={e => setEndPosY(+e.target.value)} />
              </div>
              <div className="dpd-pin-row">
                <span className="dpd-pin-label dpd-neg">N-</span>
                <input type="number" step="0.1" value={endNegX} onChange={e => setEndNegX(+e.target.value)} />
                <input type="number" step="0.1" value={endNegY} onChange={e => setEndNegY(+e.target.value)} />
              </div>
            </div>
          </div>

          {/* Options */}
          <div className="dpd-section">
            <div className="dpd-grid-2">
              <div className="dpd-field">
                <span>布线层</span>
                <select value={layer} onChange={e => setLayer(e.target.value)}>
                  <option value="F.Cu">F.Cu (顶层)</option>
                  <option value="B.Cu">B.Cu (底层)</option>
                  <option value="In1.Cu">In1.Cu (内层1)</option>
                </select>
              </div>
              <div className="dpd-field">
                <span>最大长度不匹配 (mm)</span>
                <input type="number" step="0.1" value={maxMismatch} onChange={e => setMaxMismatch(+e.target.value)} />
              </div>
            </div>
          </div>

          {/* Result */}
          {result && (
            <div className="dpd-result">
              <div className="dpd-result-stats">
                <div className="dpd-stat">
                  <span className="dpd-stat-value" style={{ color: result.impedance >= result.target_impedance * 0.9 && result.impedance <= result.target_impedance * 1.1 ? '#66bb6a' : '#ef5350' }}>
                    {result.impedance.toFixed(1)}Ω
                  </span>
                  <span className="dpd-stat-label">实际阻抗</span>
                </div>
                <div className="dpd-stat">
                  <span className="dpd-stat-value">{result.pos_length.toFixed(2)}mm</span>
                  <span className="dpd-stat-label">P+ 长度</span>
                </div>
                <div className="dpd-stat">
                  <span className="dpd-stat-value">{result.neg_length.toFixed(2)}mm</span>
                  <span className="dpd-stat-label">P- 长度</span>
                </div>
                <div className="dpd-stat">
                  <span className="dpd-stat-value" style={{ color: result.length_mismatch <= maxMismatch ? '#66bb6a' : '#ef5350' }}>
                    {result.length_mismatch.toFixed(3)}mm
                  </span>
                  <span className="dpd-stat-label">长度差</span>
                </div>
              </div>
            </div>
          )}

          {error && <div className="dpd-error">{error}</div>}
        </div>

        <div className="dpd-footer">
          <button className="dpd-btn dpd-btn-secondary" onClick={onClose}>取消</button>
          <button className="dpd-btn dpd-btn-primary" onClick={handleRoute} disabled={loading}>
            {loading ? '布线中...' : result ? '重新布线' : '开始布线'}
          </button>
          {result && (
            <button className="dpd-btn dpd-btn-apply" onClick={() => { onApply(result); onClose(); }}>
              应用到 PCB
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
