/**
 * useRoutingProgress - Real-time routing progress via WebSocket/SSE
 *
 * Phase 10B-1: Subscribes to routing progress events and pushes
 * new tracks to the PCB store in real-time.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { usePCBStore } from '../stores/pcbStore';

interface RoutingProgressEvent {
  type: 'routing_progress' | 'routing_complete' | 'routing_error';
  task_id?: string;
  progress?: number;       // 0-100
  current_net?: string;
  routed_nets?: number;
  total_nets?: number;
  new_tracks?: Array<{
    id: string;
    net: string;
    layer: string;
    width: number;
    start: { x: number; y: number };
    end: { x: number; y: number };
    points?: Array<{ x: number; y: number }>;
  }>;
  message?: string;
  error?: string;
}

export interface RoutingProgressState {
  isRouting: boolean;
  progress: number;         // 0-100
  currentNet: string;
  routedNets: number;
  totalNets: number;
  taskId: string | null;
  error: string | null;
}

const DEFAULT_STATE: RoutingProgressState = {
  isRouting: false,
  progress: 0,
  currentNet: '',
  routedNets: 0,
  totalNets: 0,
  taskId: null,
  error: null,
};

/**
 * Hook that provides real-time routing progress updates.
 *
 * Connects to the backend SSE endpoint for routing events,
 * and automatically pushes new tracks into the PCB store.
 */
export function useRoutingProgress() {
  const [state, setState] = useState<RoutingProgressState>(DEFAULT_STATE);
  const eventSourceRef = useRef<EventSource | null>(null);
  const addTrack = usePCBStore((s) => s.addTrack);

  const startListening = useCallback((taskId: string) => {
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const url = `${baseUrl}/api/v1/agent/progress/${taskId}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    setState({
      ...DEFAULT_STATE,
      isRouting: true,
      taskId,
    });

    es.onmessage = (event) => {
      try {
        const data: RoutingProgressEvent = JSON.parse(event.data);

        switch (data.type) {
          case 'routing_progress':
            // Push new tracks to PCB store immediately
            if (data.new_tracks && data.new_tracks.length > 0) {
              const pcbData = usePCBStore.getState().pcbData;
              if (pcbData) {
                for (const track of data.new_tracks) {
                  // Convert routing track format to store track format
                  const storeTrack = {
                    id: track.id || `route-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                    type: 'track' as const,
                    layer: track.layer || 'F.Cu',
                    width: track.width || 0.25,
                    points: track.points || [
                      track.start,
                      track.end,
                    ],
                    net: track.net,
                    selected: false,
                  };
                  // Avoid duplicate tracks
                  const exists = pcbData.tracks.some(t => t.net === track.net && t.id === storeTrack.id);
                  if (!exists) {
                    addTrack(storeTrack);
                  }
                }
              }
            }

            setState((prev) => ({
              ...prev,
              progress: data.progress ?? prev.progress,
              currentNet: data.current_net ?? prev.currentNet,
              routedNets: data.routed_nets ?? prev.routedNets,
              totalNets: data.total_nets ?? prev.totalNets,
            }));
            break;

          case 'routing_complete':
            setState((prev) => ({
              ...prev,
              isRouting: false,
              progress: 100,
            }));
            es.close();
            eventSourceRef.current = null;
            break;

          case 'routing_error':
            setState((prev) => ({
              ...prev,
              isRouting: false,
              error: data.error ?? data.message ?? 'Routing failed',
            }));
            es.close();
            eventSourceRef.current = null;
            break;
        }
      } catch (e) {
        console.error('[useRoutingProgress] Failed to parse event:', e);
      }
    };

    es.onerror = () => {
      setState((prev) => ({
        ...prev,
        isRouting: false,
        error: 'Connection lost',
      }));
      es.close();
      eventSourceRef.current = null;
    };
  }, [addTrack]);

  const stopListening = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setState(DEFAULT_STATE);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    ...state,
    startListening,
    stopListening,
  };
}

export default useRoutingProgress;
