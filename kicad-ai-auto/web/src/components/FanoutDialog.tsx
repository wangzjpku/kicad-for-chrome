/**
 * Fanout Dialog - Phase 6
 * 扇出对话框 - 自动扇出元件引脚
 */

import { useState, useCallback } from 'react';
import { phase6Api, PadInfo, ViaInfo, TraceInfo } from '../services/api';

interface FanoutDialogProps {
  onClose: () => void;
  componentId: string;
  componentReference: string;
  pads: PadInfo[];
  onApply: (vias: ViaInfo[], traces: TraceInfo[]) => void;
}

type FanoutDirection = 'spread' | 'in' | 'out' | 'auto';

const DIRECTION_LABELS: Record<FanoutDirection, string> = {
  spread: '向外扩散 (Spread)',
  in: '向内 (In)',
  out: '向外 (Out)',
  auto: '自动 (Auto)',
};

export default function FanoutDialog({
  onClose,
  componentId,
  componentReference,
  pads,
  onApply,
}: FanoutDialogProps) {
  const [direction, setDirection] = useState<FanoutDirection>('auto');
  const [pinSpacing, setPinSpacing] = useState<number>(1.27);
  const [preview, setPreview] = useState<{
    vias: ViaInfo[];
    traces: TraceInfo[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 执行扇出预览
  const handlePreview = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await phase6Api.fanout({
        component_id: componentId,
        reference: componentReference,
        pads,
        direction,
        pin_spacing: pinSpacing,
      });

      if (result.success) {
        setPreview({ vias: result.vias, traces: result.traces });
      } else {
        setError('扇出预览失败');
      }
    } catch (err) {
      console.error('Fanout preview failed:', err);
      setError('扇出请求失败');
    } finally {
      setLoading(false);
    }
  }, [componentId, componentReference, pads, direction, pinSpacing]);

  // 应用扇出
  const handleApply = () => {
    if (!preview) {
      setError('请先预览扇出结果');
      return;
    }
    onApply(preview.vias, preview.traces);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#323232',
          borderRadius: 8,
          width: 700,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #4a4a4a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <h3 style={{ margin: 0, color: '#e0e0e0', fontSize: 16 }}>
            扇出 - {componentReference}
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#a0a0a0',
              cursor: 'pointer',
              fontSize: 20,
              padding: 4,
            }}
          >
            x
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          <div style={{ display: 'flex', gap: 16 }}>
            {/* Left: Options */}
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: 16 }}>
                <label
                  style={{
                    display: 'block',
                    color: '#a0a0a0',
                    fontSize: 11,
                    marginBottom: 6,
                  }}
                >
                  元件信息
                </label>
                <div
                  style={{
                    padding: 10,
                    backgroundColor: '#2d2d2d',
                    borderRadius: 4,
                    fontSize: 12,
                    color: '#e0e0e0',
                  }}
                >
                  <div>ID: {componentId}</div>
                  <div>参考: {componentReference}</div>
                  <div>焊盘数: {pads.length}</div>
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label
                  style={{
                    display: 'block',
                    color: '#a0a0a0',
                    fontSize: 11,
                    marginBottom: 6,
                  }}
                >
                  扇出方向
                </label>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value as FanoutDirection)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    backgroundColor: '#2d2d2d',
                    border: '1px solid #4a4a4a',
                    borderRadius: 4,
                    color: '#e0e0e0',
                    fontSize: 12,
                  }}
                >
                  {(Object.keys(DIRECTION_LABELS) as FanoutDirection[]).map((d) => (
                    <option key={d} value={d}>
                      {DIRECTION_LABELS[d]}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label
                  style={{
                    display: 'block',
                    color: '#a0a0a0',
                    fontSize: 11,
                    marginBottom: 6,
                  }}
                >
                  引脚间距 (mm)
                </label>
                <input
                  type="number"
                  value={pinSpacing}
                  onChange={(e) => setPinSpacing(parseFloat(e.target.value) || 1.27)}
                  step={0.01}
                  min={0.1}
                  max={5}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    backgroundColor: '#2d2d2d',
                    border: '1px solid #4a4a4a',
                    borderRadius: 4,
                    color: '#e0e0e0',
                    fontSize: 12,
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              {/* Pads List */}
              <div>
                <label
                  style={{
                    display: 'block',
                    color: '#a0a0a0',
                    fontSize: 11,
                    marginBottom: 6,
                  }}
                >
                  焊盘列表
                </label>
                <div
                  style={{
                    maxHeight: 150,
                    overflow: 'auto',
                    backgroundColor: '#2d2d2d',
                    borderRadius: 4,
                    padding: 8,
                  }}
                >
                  {pads.map((pad, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '4px 0',
                        borderBottom: '1px solid #3d3d3d',
                        fontSize: 11,
                        color: '#e0e0e0',
                      }}
                    >
                      <span>{pad.pad_number}</span>
                      <span style={{ color: '#707070' }}>{pad.net || '(无网络)'}</span>
                      <span
                        style={{
                          padding: '1px 6px',
                          backgroundColor:
                            pad.type === 'power'
                              ? '#f44336'
                              : pad.type === 'ground'
                              ? '#795548'
                              : '#4a9eff',
                          borderRadius: 3,
                          fontSize: 10,
                          color: '#fff',
                        }}
                      >
                        {pad.type || 'signal'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {error && (
                <div
                  style={{
                    marginTop: 12,
                    padding: '8px 12px',
                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    borderRadius: 4,
                    color: '#f44336',
                    fontSize: 12,
                  }}
                >
                  {error}
                </div>
              )}
            </div>

            {/* Right: Preview */}
            <div style={{ flex: 1 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 6,
                }}
              >
                <label style={{ color: '#e0e0e0', fontSize: 13 }}>扇出预览</label>
                <button
                  onClick={handlePreview}
                  disabled={loading}
                  style={{
                    padding: '6px 14px',
                    backgroundColor: '#4a9eff',
                    border: 'none',
                    borderRadius: 4,
                    color: '#fff',
                    fontSize: 12,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? '计算中...' : '预览'}
                </button>
              </div>

              <div
                style={{
                  height: 280,
                  backgroundColor: '#2d2d2d',
                  borderRadius: 4,
                  overflow: 'auto',
                  padding: 12,
                }}
              >
                {!preview ? (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      color: '#707070',
                      fontSize: 12,
                    }}
                  >
                    点击"预览"查看扇出结果
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: '#a0a0a0' }}>
                    <div style={{ marginBottom: 12 }}>
                      <strong style={{ color: '#e0e0e0' }}>统计</strong>
                      <div>过孔数: {preview.vias.length}</div>
                      <div>走线数: {preview.traces.length}</div>
                    </div>

                    {preview.vias.length > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <strong style={{ color: '#e0e0e0' }}>过孔</strong>
                        {preview.vias.map((via, i) => (
                          <div key={i} style={{ padding: '2px 0' }}>
                            Via-{i + 1}: ({via.x.toFixed(2)}, {via.y.toFixed(2)}) {via.from_layer} → {via.to_layer}
                          </div>
                        ))}
                      </div>
                    )}

                    {preview.traces.length > 0 && (
                      <div>
                        <strong style={{ color: '#e0e0e0' }}>走线</strong>
                        {preview.traces.slice(0, 5).map((trace, i) => (
                          <div key={i} style={{ padding: '2px 0' }}>
                            {trace.net}: ({trace.start_x.toFixed(1)}, {trace.start_y.toFixed(1)}) → ({trace.end_x.toFixed(1)}, {trace.end_y.toFixed(1)}) [{trace.layer}]
                          </div>
                        ))}
                        {preview.traces.length > 5 && (
                          <div style={{ color: '#707070' }}>
                            ... 还有 {preview.traces.length - 5} 条走线
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid #4a4a4a',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 12,
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: '8px 20px',
              backgroundColor: '#3d3d3d',
              border: '1px solid #4a4a4a',
              borderRadius: 4,
              color: '#e0e0e0',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            取消
          </button>
          <button
            onClick={handleApply}
            disabled={!preview}
            style={{
              padding: '8px 20px',
              backgroundColor: preview ? '#4caf50' : '#3d3d3d',
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              fontSize: 13,
              cursor: preview ? 'pointer' : 'not-allowed',
              opacity: preview ? 1 : 0.6,
            }}
          >
            应用扇出
          </button>
        </div>
      </div>
    </div>
  );
}
