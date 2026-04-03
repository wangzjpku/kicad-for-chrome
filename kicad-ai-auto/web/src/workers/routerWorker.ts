/**
 * Web Worker for PCB routing computation
 *
 * Offloads A* / Lee's maze routing from the main UI thread.
 * Communicates via postMessage with structured messages.
 */

// ---- Types (must be self-contained, no external imports) ----

interface Point {
  x: number;
  y: number;
}

interface RoutingObstacle {
  id: string;
  bbox: { x1: number; y1: number; x2: number; y2: number };
  layer: string;
  net?: string;
}

interface RoutingNet {
  id: string;
  name: string;
  pins: Point[];
  layer: string;
  width: number;
  clearance: number;
  type: 'signal' | 'power' | 'diff_pair' | 'high_speed';
}

interface RoutingGrid {
  width: number;
  height: number;
  resolution: number; // mm per grid cell
  obstacles: RoutingObstacle[];
}

interface RouteResult {
  netId: string;
  netName: string;
  paths: Point[][];
  length: number;
  vias: number;
  status: 'completed' | 'failed' | 'partial';
  error?: string;
}

interface WorkerMessage {
  type: 'route' | 'cancel' | 'status';
  jobId: string;
  data: unknown;
}

interface RouteRequest {
  grid: RoutingGrid;
  nets: RoutingNet[];
  maxIterations: number;
  algorithm: 'astar' | 'lee' | 'dijkstra';
}

// ---- Grid-based pathfinding ----

class RoutingSolver {
  private gridWidth: number;
  private gridHeight: number;
  private resolution: number;
  private blockedCells: Set<string>;
  private netBlockedCells: Map<string, Set<string>>;

  constructor(grid: RoutingGrid) {
    this.gridWidth = grid.width;
    this.gridHeight = grid.height;
    this.resolution = grid.resolution;
    this.blockedCells = new Set();
    this.netBlockedCells = new Map();

    // Mark obstacle cells as blocked
    for (const obs of grid.obstacles) {
      const x1 = Math.floor(obs.bbox.x1 / this.resolution);
      const y1 = Math.floor(obs.bbox.y1 / this.resolution);
      const x2 = Math.ceil(obs.bbox.x2 / this.resolution);
      const y2 = Math.ceil(obs.bbox.y2 / this.resolution);

      for (let gx = x1; gx <= x2; gx++) {
        for (let gy = y1; gy <= y2; gy++) {
          const key = `${gx},${gy}`;
          if (obs.net) {
            // Track cells blocked by other nets
            if (!this.netBlockedCells.has(obs.net)) {
              this.netBlockedCells.set(obs.net, new Set());
            }
            this.netBlockedCells.get(obs.net)!.add(key);
          } else {
            this.blockedCells.add(key);
          }
        }
      }
    }
  }

  private isBlocked(gx: number, gy: number, currentNetName: string): boolean {
    const key = `${gx},${gy}`;
    if (this.blockedCells.has(key)) return true;
    // Allow routing through own net's obstacles
    for (const [net, cells] of this.netBlockedCells) {
      if (net !== currentNetName && cells.has(key)) return true;
    }
    return false;
  }

  private toGrid(p: Point): [number, number] {
    return [
      Math.round(p.x / this.resolution),
      Math.round(p.y / this.resolution),
    ];
  }

  private toWorld(gx: number, gy: number): Point {
    return {
      x: gx * this.resolution,
      y: gy * this.resolution,
    };
  }

  private heuristic(ax: number, ay: number, bx: number, by: number): number {
    // Octile distance (allows diagonal movement)
    const dx = Math.abs(ax - bx);
    const dy = Math.abs(ay - by);
    return Math.max(dx, dy) + (Math.SQRT2 - 1) * Math.min(dx, dy);
  }

  private neighbors(
    gx: number,
    gy: number
  ): Array<[number, number, number]> {
    const dirs: Array<[number, number, number]> = [
      [0, -1, 1], [1, 0, 1], [0, 1, 1], [-1, 0, 1],
      [1, -1, Math.SQRT2], [1, 1, Math.SQRT2],
      [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2],
    ];
    return dirs.filter(([dx, dy]) => {
      const nx = gx + dx;
      const ny = gy + dy;
      return nx >= 0 && nx < this.gridWidth && ny >= 0 && ny < this.gridHeight;
    });
  }

  /**
   * A* pathfinding between two points
   */
  astar(
    start: Point,
    end: Point,
    netName: string,
    maxIterations: number
  ): Point[] | null {
    const [sgx, sgy] = this.toGrid(start);
    const [egx, egy] = this.toGrid(end);

    if (sgx === egx && sgy === egy) return [start];

    // Open set: Map<gKey, {gx, gy, g, f}>
    const openSet = new Map<string, { gx: number; gy: number; g: number; f: number }>();
    const cameFrom = new Map<string, string>();
    const gScore = new Map<string, number>();
    const closedSet = new Set<string>();

    const startKey = `${sgx},${sgy}`;
    const endKey = `${egx},${egy}`;
    const startH = this.heuristic(sgx, sgy, egx, egy);

    openSet.set(startKey, { gx: sgx, gy: sgy, g: 0, f: startH });
    gScore.set(startKey, 0);

    let iterations = 0;

    while (openSet.size > 0 && iterations < maxIterations) {
      iterations++;

      // Find node with lowest f score
      let bestKey = '';
      let bestF = Infinity;
      for (const [key, node] of openSet) {
        if (node.f < bestF) {
          bestF = node.f;
          bestKey = key;
        }
      }

      const current = openSet.get(bestKey)!;
      openSet.delete(bestKey);

      if (bestKey === endKey) {
        // Reconstruct path
        const gridPath: [number, number][] = [];
        let k: string | undefined = bestKey;
        while (k) {
          const [px, py] = k.split(',').map(Number);
          gridPath.unshift([px, py]);
          k = cameFrom.get(k);
        }
        return gridPath.map(([gx, gy]) => this.toWorld(gx, gy));
      }

      closedSet.add(bestKey);

      for (const [dx, dy, cost] of this.neighbors(current.gx, current.gy)) {
        const nx = current.gx + dx;
        const ny = current.gy + dy;
        const nKey = `${nx},${ny}`;

        if (closedSet.has(nKey)) continue;
        if (this.isBlocked(nx, ny, netName)) continue;

        const tentativeG = current.g + cost;
        const existingG = gScore.get(nKey);

        if (existingG === undefined || tentativeG < existingG) {
          gScore.set(nKey, tentativeG);
          const h = this.heuristic(nx, ny, egx, egy);
          const f = tentativeG + h;
          cameFrom.set(nKey, bestKey);
          openSet.set(nKey, { gx: nx, gy: ny, g: tentativeG, f });
        }
      }
    }

    return null; // No path found
  }

  /**
   * Route a single net (multi-pin using MST + point-to-point)
   */
  routeNet(net: RoutingNet, maxIterations: number): RouteResult {
    if (net.pins.length < 2) {
      return {
        netId: net.id,
        netName: net.name,
        paths: [],
        length: 0,
        vias: 0,
        status: 'completed',
      };
    }

    // Build MST (Minimum Spanning Tree) for pin connections
    const mstEdges = this.buildMST(net.pins);
    const paths: Point[][] = [];
    let totalLength = 0;
    let failedSegments = 0;

    for (const [i, j] of mstEdges) {
      const path = this.astar(net.pins[i], net.pins[j], net.name, maxIterations);
      if (path) {
        paths.push(path);
        for (let k = 1; k < path.length; k++) {
          const dx = path[k].x - path[k - 1].x;
          const dy = path[k].y - path[k - 1].y;
          totalLength += Math.hypot(dx, dy);
        }
      } else {
        failedSegments++;
      }
    }

    return {
      netId: net.id,
      netName: net.name,
      paths,
      length: totalLength,
      vias: 0,
      status: failedSegments === 0 ? 'completed' : failedSegments < mstEdges.length ? 'partial' : 'failed',
    };
  }

  private buildMST(pins: Point[]): Array<[number, number]> {
    const n = pins.length;
    const edges: Array<[number, number, number]> = [];

    // All pairwise distances
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const d = Math.hypot(pins[i].x - pins[j].x, pins[i].y - pins[j].y);
        edges.push([i, j, d]);
      }
    }
    edges.sort((a, b) => a[2] - b[2]);

    // Kruskal's algorithm
    const parent = Array.from({ length: n }, (_, i) => i);
    const rank = new Array(n).fill(0);

    const find = (x: number): number => {
      if (parent[x] !== x) parent[x] = find(parent[x]);
      return parent[x];
    };

    const union = (a: number, b: number): boolean => {
      const ra = find(a);
      const rb = find(b);
      if (ra === rb) return false;
      if (rank[ra] < rank[rb]) parent[ra] = rb;
      else if (rank[ra] > rank[rb]) parent[rb] = ra;
      else { parent[rb] = ra; rank[ra]++; }
      return true;
    };

    const mst: Array<[number, number]> = [];
    for (const [i, j] of edges) {
      if (union(i, j)) {
        mst.push([i, j]);
        if (mst.length === n - 1) break;
      }
    }
    return mst;
  }
}

// ---- Worker Message Handler ----

let currentJobId: string | null = null;
let cancelled = false;

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  const msg = event.data;

  switch (msg.type) {
    case 'route':
      handleRoute(msg);
      break;
    case 'cancel':
      if (msg.jobId === currentJobId) {
        cancelled = true;
        self.postMessage({
          type: 'cancelled',
          jobId: msg.jobId,
        });
      }
      break;
    case 'status':
      self.postMessage({
        type: 'status',
        jobId: msg.jobId,
        busy: currentJobId !== null,
        currentJob: currentJobId,
      });
      break;
  }
};

function handleRoute(msg: WorkerMessage) {
  const req = msg.data as RouteRequest;
  currentJobId = msg.jobId;
  cancelled = false;

  self.postMessage({
    type: 'progress',
    jobId: msg.jobId,
    phase: 'building_grid',
    progress: 0,
  });

  const solver = new RoutingSolver(req.grid);

  self.postMessage({
    type: 'progress',
    jobId: msg.jobId,
    phase: 'solving',
    progress: 10,
    totalNets: req.nets.length,
  });

  const results: RouteResult[] = [];
  const totalNets = req.nets.length;

  for (let i = 0; i < totalNets; i++) {
    if (cancelled) break;

    const net = req.nets[i];
    const result = solver.routeNet(net, req.maxIterations);
    results.push(result);

    // Report progress
    const progress = Math.round(10 + (i + 1) / totalNets * 85);
    self.postMessage({
      type: 'progress',
      jobId: msg.jobId,
      phase: 'solving',
      progress,
      completedNets: i + 1,
      totalNets,
      lastNet: net.name,
      lastStatus: result.status,
    });
  }

  self.postMessage({
    type: 'progress',
    jobId: msg.jobId,
    phase: 'finalizing',
    progress: 95,
  });

  const completed = results.filter((r) => r.status === 'completed').length;
  const failed = results.filter((r) => r.status === 'failed').length;
  const partial = results.filter((r) => r.status === 'partial').length;

  self.postMessage({
    type: 'complete',
    jobId: msg.jobId,
    results,
    summary: {
      total: results.length,
      completed,
      failed,
      partial,
      totalLength: results.reduce((sum, r) => sum + r.length, 0),
      totalVias: results.reduce((sum, r) => sum + r.vias, 0),
    },
  });

  currentJobId = null;
}

export {};
