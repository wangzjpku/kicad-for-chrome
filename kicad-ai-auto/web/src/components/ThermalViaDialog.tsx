/**
 * Thermal Via Dialog - Phase 8
 * 热过孔阵列生成对话框
 *
 * 为功率元件生成散热过孔:
 * - 自动计算所需过孔数量
 * - 网格排列避让信号引脚
 * - 支持自定义热阻目标
 */

import { useState, useCallback } from 'react';
import './ThermalViaDialog.css';

interface ThermalViaPosition {
  x: number;
  y: number;
  drill: number;
  size: number;
}

interface ThermalViaResult {
  success: boolean;
  via_count: number;
  estimated_rth: number;
  target_rth: number;
  grid_rows: number;
  grid_cols: number;
  vias: ThermalViaPosition[];
  kicad_output: string;
}

interface ThermalViaDialogProps {
  onClose: () => void;
  /** 预填充的元件信息 */
  component?: {
    x: number;
    y: number;
    width: number;
    height: number;
    reference: string;
  };
  onApply: (result: ThermalViaResult) => void;
}

export default function ThermalViaDialog({
  onClose,
  component,
  onApply,
}: ThermalViaDialogProps) {
  const [compX, setCompX] = useState(component?.x ?? 50);
  const [compY, setCompY] = useState(component?.y ?? 50);
  const [compW, setCompW] = useState(component?.width ?? 10);
  const [compH, setCompH] = useState(component?.height ?? 10);
  const [targetRth, setTargetRth] = useState(15);
  const [viaDrill, setViaDrill] = useState(0.3);
  const [viaSize, setViaSize] = useState(0.6);
  const [spacing, setSpacing] = useState(1.0);
  const [net, setNet] = useState('GND');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ThermalViaResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/pcb/thermal-vias', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          component_x: compX,
          component_y: compY,
          component_width: compW,
          component_height: compH,
          target_rth: targetRth,
          via_drill: viaDrill,
          via_size: viaSize,
          spacing,
          net,
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
  }, [compX, compY, compW, compH, targetRth, viaDrill, viaSize, spacing, net]);

  return (
    <div className="thermal-via-overlay" onClick={onClose}>
      <div className="thermal-via-dialog" onClick={e => e.stopPropagation()}>
        <div className="tvd-header">
          <h3>热过孔阵列生成</h3>
          {component && <span className="tvd-ref">{component.reference}</span>}
          <button className="tvd-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="tvd-body">
          {/* Component Position */}
          <div className="tvd-section">
            <label className="tvd-label">元件位置与尺寸</label>
            <div className="tvd-grid-4">
              <div className="tvd-field">
                <span>X (mm)</span>
                <input type="number" step="0.1" value={compX} onChange={e => setCompX(+e.target.value)} />
              </div>
              <div className="tvd-field">
                <span>Y (mm)</span>
                <input type="number" step="0.1" value={compY} onChange={e => setCompY(+e.target.value)} />
              </div>
              <div className="tvd-field">
                <span>宽 (mm)</span>
                <input type="number" step="0.1" value={compW} onChange={e => setCompW(+e.target.value)} />
              </div>
              <div className="tvd-field">
                <span>高 (mm)</span>
                <input type="number" step="0.1" value={compH} onChange={e => setCompH(+e.target.value)} />
              </div>
            </div>
          </div>

          {/* Thermal Parameters */}
          <div className="tvd-section">
            <label className="tvd-label">热参数</label>
            <div className="tvd-grid-3">
              <div className="tvd-field">
                <span>目标热阻 (°C/W)</span>
                <input type="number" step="1" value={targetRth} onChange={e => setTargetRth(+e.target.value)} />
              </div>
              <div className="tvd-field">
                <span>过孔钻径 (mm)</span>
                <input type="number" step="0.05" value={viaDrill} onChange={e => setViaDrill(+e.target.value)} />
              </div>
              <div className="tvd-field">
                <span>过孔外径 (mm)</span>
                <input type="number" step="0.05" value={viaSize} onChange={e => setViaSize(+e.target.value)} />
              </div>
            </div>
          </div>

          {/* Options */}
          <div className="tvd-section">
            <div className="tvd-grid-2">
              <div className="tvd-field">
                <span>间距 (mm)</span>
                <input type="number" step="0.1" value={spacing} onChange={e => setSpacing(+e.target.value)} />
              </div>
              <div className="tvd-field">
                <span>网络</span>
                <input type="text" value={net} onChange={e => setNet(e.target.value)} />
              </div>
            </div>
          </div>

          {/* Result Preview */}
          {result && (
            <div className="tvd-result">
              <div className="tvd-result-stats">
                <div className="tvd-stat">
                  <span className="tvd-stat-value">{result.via_count}</span>
                  <span className="tvd-stat-label">过孔数</span>
                </div>
                <div className="tvd-stat">
                  <span className="tvd-stat-value">{result.estimated_rth.toFixed(1)}</span>
                  <span className="tvd-stat-label">估计热阻 °C/W</span>
                </div>
                <div className="tvd-stat">
                  <span className="tvd-stat-value">{result.grid_rows}x{result.grid_cols}</span>
                  <span className="tvd-stat-label">网格</span>
                </div>
              </div>
            </div>
          )}

          {error && <div className="tvd-error">{error}</div>}
        </div>

        <div className="tvd-footer">
          <button className="tvd-btn tvd-btn-secondary" onClick={onClose}>取消</button>
          <button
            className="tvd-btn tvd-btn-primary"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? '生成中...' : result ? '重新生成' : '生成热过孔'}
          </button>
          {result && (
            <button
              className="tvd-btn tvd-btn-apply"
              onClick={() => { onApply(result); onClose(); }}
            >
              应用到 PCB
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
