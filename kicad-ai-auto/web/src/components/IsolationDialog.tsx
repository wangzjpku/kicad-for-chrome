/**
 * Isolation Dialog - Phase 8
 * 安全隔离生成对话框
 *
 * 功能:
 * - IEC 60950-1 / IEC 62368-1 标准爬电距离
 * - 隔离槽 (Edge.Cuts) 生成
 * - 锯齿形爬电屏障
 * - KiCad S-expression 输出
 */

import { useState, useCallback } from 'react';
import './ThermalViaDialog.css';  // 共享样式

interface IsolationResult {
  success: boolean;
  slot: {
    x: number;
    y: number;
    width: number;
    height: number;
    voltage_label: string;
    standard: string;
  };
  min_creepage_mm: number;
  barriers_count: number;
  kicad_output: string;
}

interface IsolationDialogProps {
  onClose: () => void;
  boardWidth?: number;
  boardHeight?: number;
  onApply: (result: IsolationResult) => void;
}

export default function IsolationDialog({
  onClose,
  boardWidth = 100,
  boardHeight = 80,
  onApply,
}: IsolationDialogProps) {
  const [bw, setBw] = useState(boardWidth);
  const [bh, setBh] = useState(boardHeight);
  const [primaryZone, setPrimaryZone] = useState([0, 0, 40, 80]);
  const [secondaryZone, setSecondaryZone] = useState([60, 0, 40, 80]);
  const [voltage, setVoltage] = useState(220);
  const [standard, setStandard] = useState('IEC 60950-1');
  const [voltageLabel, setVoltageLabel] = useState('220V AC');
  const [addBarriers, setAddBarriers] = useState(true);
  const [numBarriers, setNumBarriers] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IsolationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/pcb/isolation-generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board_width: bw,
          board_height: bh,
          primary_zone: primaryZone,
          secondary_zone: secondaryZone,
          voltage,
          voltage_label: voltageLabel,
          standard,
          add_barriers: addBarriers,
          num_barriers: numBarriers,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Generation failed');
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [bw, bh, primaryZone, secondaryZone, voltage, voltageLabel, standard, addBarriers, numBarriers]);

  const updateZone = (
    setter: React.Dispatch<React.SetStateAction<number[]>>,
    index: number,
    value: number
  ) => {
    setter(prev => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  return (
    <div className="isolation-overlay" onClick={onClose}>
      <div className="isolation-dialog" onClick={e => e.stopPropagation()}>
        <div className="iso-header">
          <h3>安全隔离生成</h3>
          <button className="iso-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="iso-body">
          {/* Board Size */}
          <div className="iso-section">
            <label className="iso-label">板子尺寸</label>
            <div className="iso-grid-2">
              <div className="iso-field">
                <span>宽 (mm)</span>
                <input type="number" value={bw} onChange={e => setBw(+e.target.value)} />
              </div>
              <div className="iso-field">
                <span>高 (mm)</span>
                <input type="number" value={bh} onChange={e => setBh(+e.target.value)} />
              </div>
            </div>
          </div>

          {/* Primary Zone */}
          <div className="iso-section">
            <label className="iso-label">初级区域 (高压侧)</label>
            <div className="iso-grid-4">
              <div className="iso-field">
                <span>X</span>
                <input type="number" step="0.1" value={primaryZone[0]}
                  onChange={e => updateZone(setPrimaryZone, 0, +e.target.value)} />
              </div>
              <div className="iso-field">
                <span>Y</span>
                <input type="number" step="0.1" value={primaryZone[1]}
                  onChange={e => updateZone(setPrimaryZone, 1, +e.target.value)} />
              </div>
              <div className="iso-field">
                <span>宽</span>
                <input type="number" step="0.1" value={primaryZone[2]}
                  onChange={e => updateZone(setPrimaryZone, 2, +e.target.value)} />
              </div>
              <div className="iso-field">
                <span>高</span>
                <input type="number" step="0.1" value={primaryZone[3]}
                  onChange={e => updateZone(setPrimaryZone, 3, +e.target.value)} />
              </div>
            </div>
          </div>

          {/* Secondary Zone */}
          <div className="iso-section">
            <label className="iso-label">次级区域 (安全侧)</label>
            <div className="iso-grid-4">
              <div className="iso-field">
                <span>X</span>
                <input type="number" step="0.1" value={secondaryZone[0]}
                  onChange={e => updateZone(setSecondaryZone, 0, +e.target.value)} />
              </div>
              <div className="iso-field">
                <span>Y</span>
                <input type="number" step="0.1" value={secondaryZone[1]}
                  onChange={e => updateZone(setSecondaryZone, 1, +e.target.value)} />
              </div>
              <div className="iso-field">
                <span>宽</span>
                <input type="number" step="0.1" value={secondaryZone[2]}
                  onChange={e => updateZone(setSecondaryZone, 2, +e.target.value)} />
              </div>
              <div className="iso-field">
                <span>高</span>
                <input type="number" step="0.1" value={secondaryZone[3]}
                  onChange={e => updateZone(setSecondaryZone, 3, +e.target.value)} />
              </div>
            </div>
          </div>

          {/* Voltage & Standard */}
          <div className="iso-section">
            <label className="iso-label">电压与标准</label>
            <div className="iso-grid-4">
              <div className="iso-field">
                <span>电压 (V)</span>
                <input type="number" value={voltage} onChange={e => setVoltage(+e.target.value)} />
              </div>
              <div className="iso-field">
                <span>标签</span>
                <input type="text" value={voltageLabel} onChange={e => setVoltageLabel(e.target.value)} />
              </div>
              <div className="iso-field">
                <span>标准</span>
                <select value={standard} onChange={e => setStandard(e.target.value)}>
                  <option value="IEC 60950-1">IEC 60950-1</option>
                  <option value="IEC 62368-1">IEC 62368-1</option>
                </select>
              </div>
              <div className="iso-field">
                <span>屏障数</span>
                <input type="number" min="0" max="10" value={numBarriers}
                  onChange={e => setNumBarriers(+e.target.value)} />
              </div>
            </div>
            <label className="iso-option" style={{ marginTop: 6 }}>
              <input type="checkbox" checked={addBarriers}
                onChange={e => setAddBarriers(e.target.checked)} />
              <span style={{ fontSize: 12, color: '#ccc' }}>添加锯齿形爬电屏障</span>
            </label>
          </div>

          {/* Result */}
          {result && (
            <div className="iso-result">
              <div className="iso-result-row">
                <span className="iso-result-label">隔离槽位置</span>
                <span className="iso-result-value">
                  ({result.slot.x.toFixed(1)}, {result.slot.y.toFixed(1)})
                  {result.slot.width.toFixed(1)}x{result.slot.height.toFixed(1)} mm
                </span>
              </div>
              <div className="iso-result-row">
                <span className="iso-result-label">最小爬电距离</span>
                <span className="iso-result-value">{result.min_creepage_mm.toFixed(1)} mm</span>
              </div>
              <div className="iso-result-row">
                <span className="iso-result-label">爬电屏障</span>
                <span className="iso-result-value">{result.barriers_count} 个</span>
              </div>
              <div className="iso-result-row">
                <span className="iso-result-label">安全标准</span>
                <span className="iso-result-value">{result.slot.standard}</span>
              </div>
            </div>
          )}

          {error && <div className="iso-error">{error}</div>}
        </div>

        <div className="iso-footer">
          <button className="iso-btn iso-btn-secondary" onClick={onClose}>取消</button>
          <button
            className="iso-btn iso-btn-primary"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? '生成中...' : result ? '重新生成' : '生成隔离'}
          </button>
          {result && (
            <button className="iso-btn iso-btn-apply" onClick={() => { onApply(result); onClose(); }}>
              应用到 PCB
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
