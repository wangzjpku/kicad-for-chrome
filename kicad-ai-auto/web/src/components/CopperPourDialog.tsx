/**
 * Copper Pour Dialog - Phase 7C
 * 铜皮/铺铜配置对话框
 *
 * 支持功能:
 * - 选择铺铜类型 (实心/网格)
 * - 选择网络 (GND/电源)
 * - 热焊盘样式
 * - 缝合过孔
 * - 层选择
 */

import { useState, useCallback } from 'react';
import { phase6Api } from '../services/api';
import './CopperPourDialog.css';

type PourStyle = 'solid' | 'hatched';
type ThermalStyle = 'four_spoke' | 'two_spoke' | 'diagonal';

interface CopperPourResult {
  success: boolean;
  results: Array<{
    net: string;
    layer: string;
    zone: boolean;
    stitching_vias: number;
  }>;
  total_zones: number;
  drc_check?: {
    passed: boolean | null;
    total_violations: number;
    copper_violations: number;
    violations: Array<{ rule: string; message: string }>;
  };
}

interface CopperPourDialogProps {
  onClose: () => void;
  onApply: (result: CopperPourResult) => void;
  /** 可用网络列表 */
  availableNets?: string[];
  /** 可用层列表 */
  availableLayers?: string[];
}

const DEFAULT_NETS = ['GND', 'VCC', '3V3', '5V', 'VIN'];
const DEFAULT_LAYERS = ['F.Cu', 'B.Cu', 'In1.Cu', 'In2.Cu'];

export default function CopperPourDialog({
  onClose,
  onApply,
  availableNets = DEFAULT_NETS,
  availableLayers = DEFAULT_LAYERS,
}: CopperPourDialogProps) {
  const [nets, setNets] = useState<string[]>(['GND']);
  const [layers, setLayers] = useState<string[]>(['B.Cu']);
  const [style, setStyle] = useState<PourStyle>('solid');
  const [thermalRelief, setThermalRelief] = useState(true);
  const [stitchVias, setStitchVias] = useState(true);
  const [stitchSpacing, setStitchSpacing] = useState(1.0);
  const [clearance, setClearance] = useState(0.3);
  const [hatchWidth, setHatchWidth] = useState(1.0);
  const [hatchGap, setHatchGap] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<CopperPourResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggleNet = useCallback((net: string) => {
    setNets(prev =>
      prev.includes(net) ? prev.filter(n => n !== net) : [...prev, net]
    );
  }, []);

  const toggleLayer = useCallback((layer: string) => {
    setLayers(prev =>
      prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]
    );
  }, []);

  const handlePreview = useCallback(async () => {
    if (nets.length === 0 || layers.length === 0) {
      setError('请至少选择一个网络和一层');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await phase6Api.copperPour({
        nets,
        layers,
        style,
        thermal_relief: thermalRelief,
        stitch_vias: stitchVias,
        stitch_spacing: stitchSpacing,
        clearance,
        hatch_width: hatchWidth,
        hatch_gap: hatchGap,
      });
      setPreview(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '预览失败');
    } finally {
      setLoading(false);
    }
  }, [nets, layers, style, thermalRelief, stitchVias, stitchSpacing, clearance, hatchWidth, hatchGap]);

  const handleApply = useCallback(() => {
    if (preview) {
      onApply(preview);
      onClose();
    }
  }, [preview, onApply, onClose]);

  return (
    <div className="copper-pour-overlay" onClick={onClose}>
      <div className="copper-pour-dialog" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="cpd-header">
          <h3>铜皮/铺铜设置</h3>
          <button className="cpd-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Body */}
        <div className="cpd-body">
          {/* Pour Style */}
          <div className="cpd-section">
            <label className="cpd-label">铺铜类型</label>
            <div className="cpd-style-toggle">
              <button
                className={`cpd-style-btn ${style === 'solid' ? 'active' : ''}`}
                onClick={() => setStyle('solid')}
              >
                实心铺铜
              </button>
              <button
                className={`cpd-style-btn ${style === 'hatched' ? 'active' : ''}`}
                onClick={() => setStyle('hatched')}
              >
                网格铺铜
              </button>
            </div>
          </div>

          {/* Net Selection */}
          <div className="cpd-section">
            <label className="cpd-label">目标网络</label>
            <div className="cpd-chips">
              {availableNets.map(net => (
                <button
                  key={net}
                  className={`cpd-chip ${nets.includes(net) ? 'active' : ''}`}
                  onClick={() => toggleNet(net)}
                >
                  {net}
                </button>
              ))}
            </div>
          </div>

          {/* Layer Selection */}
          <div className="cpd-section">
            <label className="cpd-label">铺铜层</label>
            <div className="cpd-chips">
              {availableLayers.map(layer => (
                <button
                  key={layer}
                  className={`cpd-chip ${layers.includes(layer) ? 'active' : ''}`}
                  onClick={() => toggleLayer(layer)}
                >
                  {layer}
                </button>
              ))}
            </div>
          </div>

          {/* Options Grid */}
          <div className="cpd-options-grid">
            <div className="cpd-option">
              <label>
                <input
                  type="checkbox"
                  checked={thermalRelief}
                  onChange={e => setThermalRelief(e.target.checked)}
                />
                热焊盘散热连接
              </label>
            </div>
            <div className="cpd-option">
              <label>
                <input
                  type="checkbox"
                  checked={stitchVias}
                  onChange={e => setStitchVias(e.target.checked)}
                />
                缝合过孔
              </label>
            </div>
          </div>

          {/* Numeric Parameters */}
          <div className="cpd-params">
            <div className="cpd-param">
              <label>间距 (mm)</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="2.0"
                value={clearance}
                onChange={e => setClearance(parseFloat(e.target.value) || 0.3)}
              />
            </div>
            {stitchVias && (
              <div className="cpd-param">
                <label>缝合间距 (mm)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="5.0"
                  value={stitchSpacing}
                  onChange={e => setStitchSpacing(parseFloat(e.target.value) || 1.0)}
                />
              </div>
            )}
            {style === 'hatched' && (
              <>
                <div className="cpd-param">
                  <label>网格线宽 (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.2"
                    max="3.0"
                    value={hatchWidth}
                    onChange={e => setHatchWidth(parseFloat(e.target.value) || 1.0)}
                  />
                </div>
                <div className="cpd-param">
                  <label>网格间隙 (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.2"
                    max="3.0"
                    value={hatchGap}
                    onChange={e => setHatchGap(parseFloat(e.target.value) || 0.5)}
                  />
                </div>
              </>
            )}
          </div>

          {/* Preview Results */}
          {preview && (
            <div className="cpd-preview">
              <h4>预览结果</h4>
              <div className="cpd-preview-stats">
                <span>区域数: {preview.total_zones}</span>
                <span>缝合过孔: {preview.results.reduce((s, r) => s + r.stitching_vias, 0)}</span>
              </div>
              {preview.drc_check && (
                <div className={`cpd-drc ${preview.drc_check.passed ? 'pass' : 'fail'}`}>
                  DRC: {preview.drc_check.passed ? '通过' : `有 ${preview.drc_check.copper_violations} 个违规`}
                </div>
              )}
            </div>
          )}

          {/* Error */}
          {error && <div className="cpd-error">{error}</div>}
        </div>

        {/* Footer */}
        <div className="cpd-footer">
          <button className="cpd-btn cpd-btn-secondary" onClick={onClose}>
            取消
          </button>
          <button
            className="cpd-btn cpd-btn-secondary"
            onClick={handlePreview}
            disabled={loading || nets.length === 0}
          >
            {loading ? '预览中...' : '预览'}
          </button>
          <button
            className="cpd-btn cpd-btn-primary"
            onClick={handleApply}
            disabled={!preview || loading}
          >
            应用铺铜
          </button>
        </div>
      </div>
    </div>
  );
}
