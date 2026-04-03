/**
 * SuggestionOverlay - AI suggestion visualization overlay (Phase 10C-1)
 *
 * Renders AI-generated design suggestions on the PCB canvas:
 * - Ghost footprints for placement suggestions
 * - Suggested routing paths
 * - DRC fix hints
 * - Accept/dismiss controls via HTML overlay cards
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Group, Rect, Line, Circle, Text as KonvaText } from 'react-konva';
import { MM_TO_PX } from '../data/samplePCB';

// --- Types ---

export type SuggestionType = 'placement' | 'routing' | 'drc_fix' | 'copper_pour';

export interface Suggestion {
  id: string;
  type: SuggestionType;
  title: string;
  description: string;
  /** PCB coordinates for the suggestion marker (mm) */
  position?: { x: number; y: number };
  /** Optional polygon outline for zone suggestions */
  outline?: Array<{ x: number; y: number }>;
  /** Optional routing path points */
  path?: Array<{ x: number; y: number }>;
  /** Confidence score 0-1 */
  confidence: number;
  /** Action payload for applying the suggestion */
  action?: Record<string, unknown>;
}

export interface SuggestionOverlayProps {
  suggestions: Suggestion[];
  onAccept: (suggestion: Suggestion) => void;
  onDismiss: (suggestionId: string) => void;
  onDismissAll: () => void;
  visible: boolean;
}

// --- Color mapping by suggestion type ---

const TYPE_COLORS: Record<SuggestionType, { stroke: string; fill: string; badge: string }> = {
  placement: { stroke: '#4a9eff', fill: 'rgba(74,158,255,0.15)', badge: '#4a9eff' },
  routing: { stroke: '#00e676', fill: 'rgba(0,230,118,0.15)', badge: '#00e676' },
  drc_fix: { stroke: '#ff5252', fill: 'rgba(255,82,82,0.15)', badge: '#ff5252' },
  copper_pour: { stroke: '#ffab40', fill: 'rgba(255,171,64,0.15)', badge: '#ffab40' },
};

const TYPE_ICONS: Record<SuggestionType, string> = {
  placement: '📍',
  routing: '🔌',
  drc_fix: '⚠️',
  copper_pour: '🟠',
};

// --- Konva canvas markers ---

interface SuggestionMarkersProps {
  suggestions: Suggestion[];
}

/** Konva layer content that draws visual markers for each suggestion */
export const SuggestionMarkers: React.FC<SuggestionMarkersProps> = ({ suggestions }) => {
  return (
    <>
      {suggestions.map((s) => {
        const colors = TYPE_COLORS[s.type];
        const px = s.position ? s.position.x * MM_TO_PX : 0;
        const py = s.position ? s.position.y * MM_TO_PX : 0;

        // Zone outline (e.g. copper pour suggestion)
        if (s.outline && s.outline.length > 0) {
          const flatPoints = s.outline.flatMap((p) => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
          return (
            <Group key={s.id}>
              <Line
                points={flatPoints}
                closed
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth={2}
                dash={[8, 4]}
              />
            </Group>
          );
        }

        // Routing path suggestion
        if (s.path && s.path.length > 1) {
          const flatPoints = s.path.flatMap((p) => [p.x * MM_TO_PX, p.y * MM_TO_PX]);
          return (
            <Group key={s.id}>
              <Line
                points={flatPoints}
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth={2}
                dash={[6, 3]}
                opacity={0.7}
              />
              {/* Start/end markers */}
              <Circle
                x={s.path[0].x * MM_TO_PX}
                y={s.path[0].y * MM_TO_PX}
                radius={4}
                fill={colors.stroke}
                opacity={0.8}
              />
              <Circle
                x={s.path[s.path.length - 1].x * MM_TO_PX}
                y={s.path[s.path.length - 1].y * MM_TO_PX}
                radius={4}
                fill={colors.stroke}
                opacity={0.8}
              />
            </Group>
          );
        }

        // Point marker (placement / DRC fix)
        if (s.position) {
          return (
            <Group key={s.id} x={px} y={py}>
              {/* Pulsing ring */}
              <Circle
                radius={16}
                stroke={colors.stroke}
                strokeWidth={2}
                dash={[4, 4]}
                opacity={0.5}
              />
              {/* Inner marker */}
              <Circle radius={6} fill={colors.fill} stroke={colors.stroke} strokeWidth={1.5} />
              {/* Confidence indicator arc — drawn as a simple label */}
              <KonvaText
                x={-12}
                y={-26}
                text={`${Math.round(s.confidence * 100)}%`}
                fontSize={9}
                fill={colors.stroke}
                fontFamily="monospace"
              />
            </Group>
          );
        }

        return null;
      })}
    </>
  );
};

// --- HTML overlay cards ---

interface SuggestionCardsProps {
  suggestions: Suggestion[];
  onAccept: (suggestion: Suggestion) => void;
  onDismiss: (suggestionId: string) => void;
  onDismissAll: () => void;
}

const SuggestionCards: React.FC<SuggestionCardsProps> = ({
  suggestions,
  onAccept,
  onDismiss,
  onDismissAll,
}) => {
  if (suggestions.length === 0) return null;

  return (
    <div style={{
      position: 'absolute',
      top: 40,
      left: 10,
      zIndex: 50,
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      maxWidth: 280,
      maxHeight: '60%',
      overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '4px 8px',
        background: 'rgba(0,0,0,0.8)',
        borderRadius: 6,
        color: '#ccc',
        fontSize: 11,
      }}>
        <span>{suggestions.length} suggestion{suggestions.length > 1 ? 's' : ''}</span>
        <button
          onClick={onDismissAll}
          style={{
            background: 'none',
            border: 'none',
            color: '#888',
            cursor: 'pointer',
            fontSize: 10,
            padding: '2px 6px',
          }}
        >
          Dismiss all
        </button>
      </div>

      {/* Cards */}
      {suggestions.map((s) => {
        const colors = TYPE_COLORS[s.type];
        const icon = TYPE_ICONS[s.type];
        return (
          <div
            key={s.id}
            style={{
              background: 'rgba(30,30,40,0.92)',
              border: `1px solid ${colors.stroke}`,
              borderRadius: 6,
              padding: '8px 10px',
              color: '#e0e0e0',
              fontSize: 11,
              lineHeight: 1.4,
              backdropFilter: 'blur(4px)',
            }}
          >
            {/* Title row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span>{icon}</span>
              <span style={{ fontWeight: 600, color: colors.stroke }}>{s.title}</span>
              <span style={{
                marginLeft: 'auto',
                fontSize: 9,
                background: colors.badge,
                color: '#000',
                padding: '1px 5px',
                borderRadius: 3,
                fontWeight: 600,
              }}>
                {Math.round(s.confidence * 100)}%
              </span>
            </div>
            {/* Description */}
            <div style={{ color: '#aaa', fontSize: 10, marginBottom: 6 }}>{s.description}</div>
            {/* Actions */}
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => onAccept(s)}
                style={{
                  flex: 1,
                  padding: '3px 0',
                  background: colors.stroke,
                  color: '#fff',
                  border: 'none',
                  borderRadius: 3,
                  cursor: 'pointer',
                  fontSize: 10,
                  fontWeight: 600,
                }}
              >
                Apply
              </button>
              <button
                onClick={() => onDismiss(s.id)}
                style={{
                  padding: '3px 10px',
                  background: 'transparent',
                  color: '#888',
                  border: '1px solid #555',
                  borderRadius: 3,
                  cursor: 'pointer',
                  fontSize: 10,
                }}
              >
                Dismiss
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// --- Main composite component ---

const SuggestionOverlay: React.FC<SuggestionOverlayProps> = ({
  suggestions,
  onAccept,
  onDismiss,
  onDismissAll,
  visible,
}) => {
  const [filteredSuggestions, setFilteredSuggestions] = useState<Suggestion[]>(suggestions);

  // Sync suggestions, removing dismissed ones
  useEffect(() => {
    setFilteredSuggestions(suggestions);
  }, [suggestions]);

  const handleDismiss = useCallback((id: string) => {
    setFilteredSuggestions((prev) => prev.filter((s) => s.id !== id));
    onDismiss(id);
  }, [onDismiss]);

  if (!visible || filteredSuggestions.length === 0) return null;

  return (
    <SuggestionCards
      suggestions={filteredSuggestions}
      onAccept={onAccept}
      onDismiss={handleDismiss}
      onDismissAll={() => {
        setFilteredSuggestions([]);
        onDismissAll();
      }}
    />
  );
};

export default SuggestionOverlay;
