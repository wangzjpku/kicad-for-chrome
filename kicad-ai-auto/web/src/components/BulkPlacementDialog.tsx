/**
 * Bulk Placement Dialog - Phase 6
 * 批量放置对话框 - 从 BOM 批量添加元件
 */

import { useState, useCallback } from 'react';
import { phase6Api, PlacedComponent, BulkPlacementRequest } from '../services/api';

interface BulkPlacementDialogProps {
  onClose: () => void;
  onApply: (components: PlacedComponent[]) => void;
}

type PlacementStrategy = 'grid' | 'horizontal' | 'vertical' | 'auto';

const STRATEGY_LABELS: Record<PlacementStrategy, string> = {
  grid: '网格排列',
  horizontal: '水平排列',
  vertical: '垂直排列',
  auto: '自动选择',
};

export default function BulkPlacementDialog({ onClose, onApply }: BulkPlacementDialogProps) {
  const [bomText, setBomText] = useState(`Reference,Value,Footprint
R1,10k,0805
R2,10k,0805
C1,100nF,0805
C2,100nF,0805
U1,STM32F103C8,LQFP-48`);
  const [strategy, setStrategy] = useState<PlacementStrategy>('auto');
  const [startX, setStartX] = useState(100);
  const [startY, setStartY] = useState(100);
  const [spacingX, setSpacingX] = useState(50);
  const [spacingY, setSpacingY] = useState(30);
  const [maxCols, setMaxCols] = useState(10);
  const [preview, setPreview] = useState<PlacedComponent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 预览放置结果
  const handlePreview = useCallback(async () => {
    if (!bomText.trim()) {
      setError('请输入 BOM 数据');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request: BulkPlacementRequest = {
        bom_text: bomText,
        strategy,
        start_x: startX,
        start_y: startY,
        spacing_x: spacingX,
        spacing_y: spacingY,
        max_cols: maxCols,
      };

      const result = await phase6Api.bulkPlace(request);
      if (result.success) {
        setPreview(result.components);
      } else {
        setError('预览失败');
      }
    } catch (err) {
      console.error('Bulk placement preview failed:', err);
      setError('预览请求失败');
    } finally {
      setLoading(false);
    }
  }, [bomText, strategy, startX, startY, spacingX, spacingY, maxCols]);

  // 应用放置
  const handleApply = () => {
    if (preview.length === 0) {
      setError('请先预览放置结果');
      return;
    }
    onApply(preview);
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
          width: 900,
          maxHeight: '85vh',
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
            批量放置元件
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
            {/* Left: BOM Input */}
            <div style={{ flex: 1 }}>
              <label
                style={{
                  display: 'block',
                  color: '#e0e0e0',
                  fontSize: 13,
                  marginBottom: 6,
                }}
              >
                BOM 数据 (CSV 格式)
              </label>
              <textarea
                value={bomText}
                onChange={(e) => setBomText(e.target.value)}
                placeholder="Reference,Value,Footprint&#10;R1,10k,0805&#10;C1,100nF,0805"
                style={{
                  width: '100%',
                  height: 200,
                  padding: 10,
                  backgroundColor: '#2d2d2d',
                  border: '1px solid #4a4a4a',
                  borderRadius: 4,
                  color: '#e0e0e0',
                  fontSize: 12,
                  fontFamily: 'monospace',
                  resize: 'vertical',
                  boxSizing: 'border-box',
                }}
              />

              {/* Options */}
              <div
                style={{
                  marginTop: 16,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: 12,
                }}
              >
                <div>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 4 }}>
                    放置策略
                  </label>
                  <select
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value as PlacementStrategy)}
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
                    {(Object.keys(STRATEGY_LABELS) as PlacementStrategy[]).map((s) => (
                      <option key={s} value={s}>
                        {STRATEGY_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 4 }}>
                    最大列数
                  </label>
                  <input
                    type="number"
                    value={maxCols}
                    onChange={(e) => setMaxCols(parseInt(e.target.value) || 10)}
                    min={1}
                    max={20}
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

                <div>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 4 }}>
                    起始 X (mm)
                  </label>
                  <input
                    type="number"
                    value={startX}
                    onChange={(e) => setStartX(parseFloat(e.target.value) || 0)}
                    step={0.1}
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

                <div>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 4 }}>
                    起始 Y (mm)
                  </label>
                  <input
                    type="number"
                    value={startY}
                    onChange={(e) => setStartY(parseFloat(e.target.value) || 0)}
                    step={0.1}
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

                <div>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 4 }}>
                    X 间距 (mm)
                  </label>
                  <input
                    type="number"
                    value={spacingX}
                    onChange={(e) => setSpacingX(parseFloat(e.target.value) || 0)}
                    step={0.1}
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

                <div>
                  <label style={{ display: 'block', color: '#a0a0a0', fontSize: 11, marginBottom: 4 }}>
                    Y 间距 (mm)
                  </label>
                  <input
                    type="number"
                    value={spacingY}
                    onChange={(e) => setSpacingY(parseFloat(e.target.value) || 0)}
                    step={0.1}
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
                <label style={{ color: '#e0e0e0', fontSize: 13 }}>
                  放置预览
                </label>
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
                  {loading ? '预览中...' : '预览'}
                </button>
              </div>

              <div
                style={{
                  height: 320,
                  backgroundColor: '#2d2d2d',
                  borderRadius: 4,
                  overflow: 'auto',
                  padding: 12,
                }}
              >
                {preview.length === 0 ? (
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
                    点击"预览"查看放置结果
                  </div>
                ) : (
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: 11,
                    }}
                  >
                    <thead>
                      <tr style={{ color: '#a0a0a0' }}>
                        <th style={{ textAlign: 'left', padding: '4px 6px' }}>参考</th>
                        <th style={{ textAlign: 'left', padding: '4px 6px' }}>符号</th>
                        <th style={{ textAlign: 'left', padding: '4px 6px' }}>X</th>
                        <th style={{ textAlign: 'left', padding: '4px 6px' }}>Y</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.map((comp, i) => (
                        <tr
                          key={i}
                          style={{ color: '#e0e0e0' }}
                        >
                          <td style={{ padding: '4px 6px' }}>{comp.reference}</td>
                          <td style={{ padding: '4px 6px' }}>{comp.symbol_name}</td>
                          <td style={{ padding: '4px 6px' }}>{comp.x.toFixed(1)}</td>
                          <td style={{ padding: '4px 6px' }}>{comp.y.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div
                style={{
                  marginTop: 8,
                  color: '#707070',
                  fontSize: 11,
                }}
              >
                共 {preview.length} 个元件
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
            disabled={preview.length === 0}
            style={{
              padding: '8px 20px',
              backgroundColor: '#4caf50',
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              fontSize: 13,
              cursor: preview.length === 0 ? 'not-allowed' : 'pointer',
              opacity: preview.length === 0 ? 0.6 : 1,
            }}
          >
            应用放置
          </button>
        </div>
      </div>
    </div>
  );
}
