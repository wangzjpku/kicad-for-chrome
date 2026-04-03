/**
 * Hook for running PCB routing in a Web Worker.
 *
 * Provides a clean API to offload routing computation while
 * tracking progress via callbacks.
 */

import { useCallback, useRef, useState } from 'react';

export interface RoutingPin {
  x: number;
  y: number;
}

export interface RoutingObstacle {
  id: string;
  bbox: { x1: number; y1: number; x2: number; y2: number };
  layer: string;
  net?: string;
}

export interface RoutingNet {
  id: string;
  name: string;
  pins: RoutingPin[];
  layer: string;
  width: number;
  clearance: number;
  type: 'signal' | 'power' | 'diff_pair' | 'high_speed';
}

export interface RoutingResult {
  netId: string;
  netName: string;
  paths: { x: number; y: number }[][];
  length: number;
  vias: number;
  status: 'completed' | 'failed' | 'partial';
  error?: string;
}

export interface RoutingSummary {
  total: number;
  completed: number;
  failed: number;
  partial: number;
  totalLength: number;
  totalVias: number;
}

interface RoutingProgress {
  phase: string;
  progress: number;
  completedNets?: number;
  totalNets?: number;
  lastNet?: string;
  lastStatus?: string;
}

export function useRoutingWorker() {
  const workerRef = useRef<Worker | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<RoutingProgress | null>(null);
  const [results, setResults] = useState<RoutingResult[] | null>(null);
  const [summary, setSummary] = useState<RoutingSummary | null>(null);
  const jobIdRef = useRef(0);

  const startRouting = useCallback(
    (
      gridWidth: number,
      gridHeight: number,
      resolution: number,
      obstacles: RoutingObstacle[],
      nets: RoutingNet[],
      maxIterations: number = 50000,
      algorithm: 'astar' | 'lee' | 'dijkstra' = 'astar',
    ) => {
      // Cancel any running job
      if (workerRef.current) {
        workerRef.current.terminate();
      }

      const jobId = `route-${++jobIdRef.current}`;
      setIsRunning(true);
      setProgress(null);
      setResults(null);
      setSummary(null);

      const worker = new Worker(
        new URL('../workers/routerWorker.ts', import.meta.url),
        { type: 'module' },
      );

      worker.onmessage = (event) => {
        const msg = event.data;

        if (msg.jobId !== jobId) return; // stale message

        switch (msg.type) {
          case 'progress':
            setProgress({
              phase: msg.phase,
              progress: msg.progress,
              completedNets: msg.completedNets,
              totalNets: msg.totalNets,
              lastNet: msg.lastNet,
              lastStatus: msg.lastStatus,
            });
            break;

          case 'complete':
            setResults(msg.results);
            setSummary(msg.summary);
            setIsRunning(false);
            setProgress((p) => p ? { ...p, progress: 100 } : null);
            worker.terminate();
            workerRef.current = null;
            break;

          case 'cancelled':
            setIsRunning(false);
            worker.terminate();
            workerRef.current = null;
            break;
        }
      };

      worker.onerror = (err) => {
        console.error('Routing worker error:', err);
        setIsRunning(false);
        worker.terminate();
        workerRef.current = null;
      };

      workerRef.current = worker;

      worker.postMessage({
        type: 'route',
        jobId,
        data: {
          grid: {
            width: gridWidth,
            height: gridHeight,
            resolution,
            obstacles,
          },
          nets,
          maxIterations,
          algorithm,
        },
      });
    },
    [],
  );

  const cancelRouting = useCallback(() => {
    if (workerRef.current && isRunning) {
      const jobId = `route-${jobIdRef.current}`;
      workerRef.current.postMessage({ type: 'cancel', jobId });
    }
  }, [isRunning]);

  return {
    startRouting,
    cancelRouting,
    isRunning,
    progress,
    results,
    summary,
  };
}
