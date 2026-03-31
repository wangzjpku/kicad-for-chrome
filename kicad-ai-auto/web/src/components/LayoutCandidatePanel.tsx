/**
 * LayoutCandidatePanel - Compare and select layout strategies
 *
 * Phase 9C: Displays 3 layout candidates (compact/balanced/thermal)
 * with score comparison and one-click selection.
 */

import React, { useState, useCallback } from 'react';
import { agentApi } from '../services/api';

interface Component {
  reference: string;
  footprint: string;
  value: string;
  width: number;
  height: number;
}

interface CandidateScores {
  overall: number;
  utilization: number;
  wire_length: number;
  thermal: number;
  routing: number;
}

interface LayoutCandidate {
  strategy: string;
  positions: Record<string, { x: number; y: number; rotation: number }>;
  scores: CandidateScores;
  description: string;
}

interface Props {
  boardWidth: number;
  boardHeight: number;
  components: Component[];
  onSelect: (strategy: string, positions: Record<string, { x: number; y: number; rotation: number }>) => void;
  onClose: () => void;
}

const STRATEGY_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  compact: { label: '紧凑布局', icon: '⊞', color: '#3b82f6' },
  balanced: { label: '均衡布局', icon: '◫', color: '#10b981' },
  thermal: { label: '散热优先', icon: '❋', color: '#f59e0b' },
};

const LayoutCandidatePanel: React.FC<Props> = ({
  boardWidth,
  boardHeight,
  components,
  onSelect,
  onClose,
}) => {
  const [candidates, setCandidates] = useState<LayoutCandidate[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommended, setRecommended] = useState<string | null>(null);

  const generateCandidates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await agentApi.generateLayoutCandidates({
        board_width: boardWidth,
        board_height: boardHeight,
        components,
      });
      setCandidates(result.candidates);
      setRecommended(result.recommended);
      // Auto-select recommended
      const recIdx = result.candidates.findIndex(c => c.strategy === result.recommended);
      if (recIdx >= 0) setSelectedIdx(recIdx);
    } catch (err: any) {
      setError(err.message || 'Failed to generate candidates');
    } finally {
      setLoading(false);
    }
  }, [boardWidth, boardHeight, components]);

  const handleApply = () => {
    if (selectedIdx !== null && candidates[selectedIdx]) {
      const c = candidates[selectedIdx];
      onSelect(c.strategy, c.positions);
    }
  };

  return (
    <div style={{ padding: 16, background: '#1e1e2e', borderRadius: 8, color: '#cdd6f4', maxWidth: 600 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>Layout Strategy Selector</h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#a6adc8', cursor: 'pointer', fontSize: 18 }}>x</button>
      </div>

      {candidates.length === 0 && !loading && (
        <button
          onClick={generateCandidates}
          style={{
            width: '100%', padding: 10, background: '#3b82f6', color: '#fff',
            border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14,
          }}
        >
          Generate 3 Layout Candidates
        </button>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: 20, color: '#a6adc8' }}>
          Generating layout candidates...
        </div>
      )}

      {error && (
        <div style={{ padding: 8, background: '#45232e', borderRadius: 4, color: '#f38ba8', marginBottom: 8 }}>
          {error}
        </div>
      )}

      {candidates.length > 0 && (
        <>
          {/* Candidate cards */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {candidates.map((c, idx) => {
              const meta = STRATEGY_LABELS[c.strategy] || { label: c.strategy, icon: '?', color: '#a6adc8' };
              const isSelected = selectedIdx === idx;
              return (
                <div
                  key={c.strategy}
                  onClick={() => setSelectedIdx(idx)}
                  style={{
                    flex: 1,
                    padding: 10,
                    background: isSelected ? '#313244' : '#181825',
                    border: isSelected ? `2px solid ${meta.color}` : '2px solid #313244',
                    borderRadius: 6,
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: 14, fontWeight: 600, color: meta.color, marginBottom: 4 }}>
                    {meta.icon} {meta.label}
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: '#cdd6f4' }}>
                    {c.scores.overall.toFixed(0)}
                  </div>
                  <div style={{ fontSize: 10, color: '#a6adc8' }}>score</div>
                  {recommended === c.strategy && (
                    <div style={{ fontSize: 10, color: '#a6e3a1', marginTop: 4 }}>Recommended</div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Selected candidate details */}
          {selectedIdx !== null && (
            <div style={{ background: '#181825', borderRadius: 6, padding: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#a6adc8', marginBottom: 8 }}>
                {candidates[selectedIdx].description}
              </div>

              {/* Score bars */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {[
                  ['Area', candidates[selectedIdx].scores.utilization],
                  ['Routing', candidates[selectedIdx].scores.routing],
                  ['Thermal', candidates[selectedIdx].scores.thermal],
                  ['Wire Len', 100 - Math.min(100, candidates[selectedIdx].scores.wire_length / 2)],
                ].map(([label, score]) => (
                  <div key={label as string} style={{ fontSize: 11 }}>
                    <span style={{ color: '#a6adc8' }}>{label}</span>
                    <div style={{
                      height: 4, background: '#313244', borderRadius: 2, marginTop: 2,
                    }}>
                      <div style={{
                        width: `${score}%`, height: '100%',
                        background: (score as number) > 70 ? '#a6e3a1' : (score as number) > 40 ? '#f9e2af' : '#f38ba8',
                        borderRadius: 2,
                      }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Component count */}
              <div style={{ fontSize: 11, color: '#a6adc8', marginTop: 8 }}>
                {Object.keys(candidates[selectedIdx].positions).length} components placed
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleApply}
              disabled={selectedIdx === null}
              style={{
                flex: 1, padding: 8, background: selectedIdx !== null ? '#3b82f6' : '#313244',
                color: selectedIdx !== null ? '#fff' : '#585b70', border: 'none', borderRadius: 6,
                cursor: selectedIdx !== null ? 'pointer' : 'not-allowed', fontSize: 13,
              }}
            >
              Apply Selected Layout
            </button>
            <button
              onClick={() => { setCandidates([]); setSelectedIdx(null); }}
              style={{
                padding: 8, background: '#313244', color: '#a6adc8',
                border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13,
              }}
            >
              Regenerate
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default LayoutCandidatePanel;
