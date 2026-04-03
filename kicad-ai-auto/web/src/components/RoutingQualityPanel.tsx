/**
 * RoutingQualityPanel.tsx - 布线质量评分面板
 *
 * Phase 8D-4: Displays routing quality score with radar chart,
 * dimension breakdown, and improvement suggestions.
 */

import React, { useState, useCallback } from 'react';
import { phase6Api } from '../services/api';

interface QualityDimension {
  name: string;
  score: number;
  weight: number;
  weighted_score: number;
  details: string;
}

interface RoutingQualityPanelProps {
  projectId?: string;
  onReRoute?: () => void;
}

const DIMENSION_COLORS: Record<string, string> = {
  'Completion': '#4caf50',
  'DRC Compliance': '#f44336',
  'Efficiency': '#ff9800',
  'Via Usage': '#2196f3',
  'Diff Pairs': '#e040fb',
};

const GRADE_COLORS: Record<string, string> = {
  'A': '#4caf50',
  'B': '#8bc34a',
  'C': '#ff9800',
  'D': '#ff5722',
  'F': '#f44336',
};

export const RoutingQualityPanel: React.FC<RoutingQualityPanelProps> = ({
  projectId,
  onReRoute,
}) => {
  const [quality, setQuality] = useState<{
    total_score: number;
    grade: string;
    is_passing: boolean;
    is_production_ready: boolean;
    dimensions: QualityDimension[];
    improvements: string[];
    message: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [routeInput, setRouteInput] = useState({
    totalNets: 10,
    routedNets: 9,
    drcViolations: 0,
    totalTrackLength: 150,
    idealTrackLength: 120,
    totalVias: 8,
  });

  const scoreQuality = useCallback(async () => {
    setLoading(true);
    try {
      const result = await (phase6Api as any).scoreRoutingQuality({
        total_nets: routeInput.totalNets,
        routed_nets: routeInput.routedNets,
        drc_violations: routeInput.drcViolations,
        total_track_length: routeInput.totalTrackLength,
        ideal_track_length: routeInput.idealTrackLength,
        total_vias: routeInput.totalVias,
      });
      setQuality(result);
    } catch (err) {
      console.error('Quality scoring failed:', err);
    } finally {
      setLoading(false);
    }
  }, [routeInput]);

  // Radar chart SVG
  const renderRadarChart = () => {
    if (!quality?.dimensions) return null;

    const dims = quality.dimensions;
    const n = dims.length;
    const cx = 80, cy = 80, r = 60;

    // Axis angles
    const angles = dims.map((_, i) => (2 * Math.PI * i) / n - Math.PI / 2);

    // Grid lines
    const gridLevels = [0.25, 0.5, 0.75, 1.0];

    return (
      <svg width={160} height={160} style={{ margin: '0 auto', display: 'block' }}>
        {/* Grid */}
        {gridLevels.map(level => (
          <polygon
            key={level}
            points={angles.map(a => `${cx + r * level * Math.cos(a)},${cy + r * level * Math.sin(a)}`).join(' ')}
            fill="none"
            stroke="#444"
            strokeWidth={0.5}
          />
        ))}
        {/* Axes */}
        {angles.map((a, i) => (
          <line key={i} x1={cx} y1={cy}
            x2={cx + r * Math.cos(a)} y2={cy + r * Math.sin(a)}
            stroke="#555" strokeWidth={0.5} />
        ))}
        {/* Data polygon */}
        <polygon
          points={dims.map((d, i) => {
            const val = d.score / 100;
            const x = cx + r * val * Math.cos(angles[i]);
            const y = cy + r * val * Math.sin(angles[i]);
            return `${x},${y}`;
          }).join(' ')}
          fill="rgba(74,158,255,0.2)"
          stroke="#4a9eff"
          strokeWidth={2}
        />
        {/* Labels */}
        {dims.map((d, i) => {
          const lx = cx + (r + 14) * Math.cos(angles[i]);
          const ly = cy + (r + 14) * Math.sin(angles[i]);
          return (
            <text key={i} x={lx} y={ly}
              textAnchor="middle" dominantBaseline="middle"
              fill="#a0a0a0" fontSize={8} fontFamily="monospace">
              {d.name.split(' ')[0]}
            </text>
          );
        })}
      </svg>
    );
  };

  return (
    <div style={{ padding: 12, color: '#e0e0e0', fontSize: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14, color: '#fff' }}>
        Routing Quality
      </div>

      {/* Input controls */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 12 }}>
        {[
          { label: 'Total Nets', key: 'totalNets', val: routeInput.totalNets },
          { label: 'Routed Nets', key: 'routedNets', val: routeInput.routedNets },
          { label: 'DRC Violations', key: 'drcViolations', val: routeInput.drcViolations },
          { label: 'Track Length (mm)', key: 'totalTrackLength', val: routeInput.totalTrackLength },
          { label: 'Ideal Length (mm)', key: 'idealTrackLength', val: routeInput.idealTrackLength },
          { label: 'Via Count', key: 'totalVias', val: routeInput.totalVias },
        ].map(({ label, key, val }) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: '#888', fontSize: 10, minWidth: 70 }}>{label}</span>
            <input
              type="number"
              value={val}
              onChange={e => setRouteInput(prev => ({ ...prev, [key]: parseInt(e.target.value) || 0 }))}
              style={{
                width: 50, padding: '2px 4px', backgroundColor: '#333', border: '1px solid #555',
                borderRadius: 3, color: '#e0e0e0', fontSize: 11,
              }}
            />
          </div>
        ))}
      </div>

      <button
        onClick={scoreQuality}
        disabled={loading}
        style={{
          width: '100%', padding: '8px 16px', marginBottom: 16,
          backgroundColor: loading ? '#3d3d3d' : '#4a9eff', color: '#fff',
          border: 'none', borderRadius: 6, cursor: loading ? 'wait' : 'pointer',
          fontSize: 12, fontWeight: 500,
        }}
      >
        {loading ? 'Scoring...' : 'Score Routing Quality'}
      </button>

      {/* Results */}
      {quality && (
        <>
          {/* Grade badge */}
          <div style={{
            textAlign: 'center', marginBottom: 12,
          }}>
            <div style={{
              display: 'inline-block', width: 64, height: 64, borderRadius: '50%',
              backgroundColor: `${GRADE_COLORS[quality.grade] || '#888'}22`,
              border: `3px solid ${GRADE_COLORS[quality.grade] || '#888'}`,
              lineHeight: '56px', fontSize: 28, fontWeight: 700,
              color: GRADE_COLORS[quality.grade] || '#888',
            }}>
              {quality.grade}
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {quality.total_score}/100
            </div>
            <div style={{ fontSize: 10, color: quality.is_production_ready ? '#4caf50' : quality.is_passing ? '#ff9800' : '#f44336' }}>
              {quality.is_production_ready ? 'Production Ready' : quality.is_passing ? 'Passing' : 'Not Passing'}
            </div>
          </div>

          {/* Radar chart */}
          {renderRadarChart()}

          {/* Dimension bars */}
          <div style={{ marginTop: 12 }}>
            {quality.dimensions.map(dim => (
              <div key={dim.name} style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                  <span style={{ color: DIMENSION_COLORS[dim.name] || '#78909c', fontSize: 11, fontWeight: 500 }}>
                    {dim.name}
                  </span>
                  <span style={{ color: '#e0e0e0', fontSize: 11 }}>
                    {dim.score.toFixed(0)} <span style={{ color: '#666' }}>(x{dim.weight})</span>
                  </span>
                </div>
                <div style={{ height: 6, backgroundColor: '#333', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    width: `${dim.score}%`, height: '100%',
                    backgroundColor: DIMENSION_COLORS[dim.name] || '#78909c',
                    borderRadius: 3,
                    transition: 'width 0.5s',
                  }} />
                </div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 1 }}>{dim.details}</div>
              </div>
            ))}
          </div>

          {/* Improvement suggestions */}
          {quality.improvements.length > 0 && (
            <div style={{
              marginTop: 12, padding: 10, backgroundColor: '#252525',
              borderRadius: 6, border: '1px solid #3a3a3a',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#ff9800', marginBottom: 6 }}>
                Suggestions
              </div>
              {quality.improvements.map((imp, i) => (
                <div key={i} style={{ fontSize: 10, color: '#bbb', marginBottom: 4, paddingLeft: 8, borderLeft: '2px solid #555' }}>
                  {imp}
                </div>
              ))}
            </div>
          )}

          {onReRoute && (
            <button
              onClick={onReRoute}
              style={{
                width: '100%', padding: '8px 16px', marginTop: 12,
                backgroundColor: '#ff9800', color: '#fff',
                border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12,
              }}
            >
              Re-Route with Suggestions
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default RoutingQualityPanel;
