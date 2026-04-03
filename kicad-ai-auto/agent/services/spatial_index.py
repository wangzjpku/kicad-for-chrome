"""
R-tree Spatial Index Service

Provides fast spatial queries for PCB design:
- Component placement collision detection
- DRC proximity checks
- Copper pour region queries
- Net adjacency lookups

Uses rtree library (libspatialindex wrapper) with fallback
to a simple grid-based index when rtree is unavailable.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Callable,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

@dataclass
class BBox:
    """Axis-aligned bounding box in mm coordinates."""
    x1: float  # min-x
    y1: float  # min-y
    x2: float  # max-x
    y2: float  # max-y

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return self.width * self.height

    def intersects(self, other: "BBox") -> bool:
        return not (
            self.x2 < other.x1
            or self.x1 > other.x2
            or self.y2 < other.y1
            or self.y1 > other.y2
        )

    def contains(self, other: "BBox") -> bool:
        return (
            self.x1 <= other.x1
            and self.y1 <= other.y1
            and self.x2 >= other.x2
            and self.y2 >= other.y2
        )

    def expand(self, margin: float) -> "BBox":
        return BBox(
            self.x1 - margin, self.y1 - margin,
            self.x2 + margin, self.y2 + margin,
        )

    def distance_to(self, other: "BBox") -> float:
        """Minimum Euclidean distance between two bounding boxes."""
        dx = max(0, max(self.x1, other.x1) - min(self.x2, other.x2))
        dy = max(0, max(self.y1, other.y1) - min(self.y2, other.y2))
        return math.hypot(dx, dy)

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            min(self.x1, other.x1), min(self.y1, other.y1),
            max(self.x2, other.x2), max(self.y2, other.y2),
        )


@dataclass
class IndexedItem:
    """An item stored in the spatial index."""
    id: str
    bbox: BBox
    layer: str = "F.Cu"
    item_type: str = "component"  # component, track, via, zone, pad
    data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Grid-based spatial index (fallback / lightweight)
# ---------------------------------------------------------------------------

class GridIndex:
    """
    Simple grid-based spatial index.
    Divides space into cells of fixed size for O(1) point lookups.
    """

    def __init__(self, cell_size: float = 10.0):
        self.cell_size = cell_size
        self._items: Dict[str, IndexedItem] = {}
        self._grid: Dict[Tuple[int, int], Set[str]] = {}

    def _cell_key(self, x: float, y: float) -> Tuple[int, int]:
        return (int(math.floor(x / self.cell_size)),
                int(math.floor(y / self.cell_size)))

    def _cells_for_bbox(self, bbox: BBox) -> List[Tuple[int, int]]:
        min_cx, min_cy = self._cell_key(bbox.x1, bbox.y1)
        max_cx, max_cy = self._cell_key(bbox.x2, bbox.y2)
        cells = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                cells.append((cx, cy))
        return cells

    def insert(self, item: IndexedItem) -> None:
        self._items[item.id] = item
        for cell in self._cells_for_bbox(item.bbox):
            if cell not in self._grid:
                self._grid[cell] = set()
            self._grid[cell].add(item.id)

    def remove(self, item_id: str) -> bool:
        if item_id not in self._items:
            return False
        item = self._items.pop(item_id)
        for cell in self._cells_for_bbox(item.bbox):
            if cell in self._grid:
                self._grid[cell].discard(item_id)
                if not self._grid[cell]:
                    del self._grid[cell]
        return True

    def query_bbox(self, bbox: BBox) -> List[IndexedItem]:
        candidate_ids: Set[str] = set()
        for cell in self._cells_for_bbox(bbox):
            candidate_ids.update(self._grid.get(cell, set()))
        results = []
        for item_id in candidate_ids:
            item = self._items.get(item_id)
            if item and item.bbox.intersects(bbox):
                results.append(item)
        return results

    def query_point(self, x: float, y: float) -> List[IndexedItem]:
        point_bbox = BBox(x, y, x, y)
        return self.query_bbox(point_bbox)

    def query_radius(self, cx: float, cy: float, radius: float) -> List[IndexedItem]:
        search_bbox = BBox(cx - radius, cy - radius, cx + radius, cy + radius)
        candidates = self.query_bbox(search_bbox)
        results = []
        r2 = radius * radius
        for item in candidates:
            ix, iy = item.bbox.center
            # distance from center to closest point on bbox
            dx = max(0, abs(ix - cx) - item.bbox.width / 2)
            dy = max(0, abs(iy - cy) - item.bbox.height / 2)
            if dx * dx + dy * dy <= r2:
                results.append(item)
        return results

    def nearest(self, x: float, y: float, k: int = 1) -> List[Tuple[IndexedItem, float]]:
        """Find k nearest items to a point."""
        all_items = list(self._items.values())
        if not all_items:
            return []
        distances = []
        for item in all_items:
            ix, iy = item.bbox.center
            dist = math.hypot(ix - x, iy - y)
            distances.append((item, dist))
        distances.sort(key=lambda t: t[1])
        return distances[:k]

    def count(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._grid.clear()

    def all_items(self) -> List[IndexedItem]:
        return list(self._items.values())


# ---------------------------------------------------------------------------
# R-tree spatial index (preferred, requires rtree package)
# ---------------------------------------------------------------------------

class RTreeIndex:
    """
    R-tree based spatial index using the rtree library.
    Falls back to GridIndex if rtree is not installed.
    """

    def __init__(self):
        self._items: Dict[int, IndexedItem] = {}
        self._id_counter = 0
        self._str_to_int: Dict[str, int] = {}
        self._int_to_str: Dict[int, str] = {}
        self._rtree = None
        try:
            from rtree.index import Index, Property
            p = Property()
            p.dimension = 2
            self._rtree = Index(properties=p)
            logger.info("R-tree spatial index initialized (libspatialindex)")
        except ImportError:
            logger.info("rtree package not available, using GridIndex fallback")
            self._grid_fallback = GridIndex(cell_size=5.0)

    @property
    def _use_rtree(self) -> bool:
        return self._rtree is not None

    def insert(self, item: IndexedItem) -> None:
        if self._use_rtree:
            int_id = self._id_counter
            self._id_counter += 1
            self._str_to_int[item.id] = int_id
            self._int_to_str[int_id] = item.id
            self._items[int_id] = item
            coords = (item.bbox.x1, item.bbox.y1, item.bbox.x2, item.bbox.y2)
            self._rtree.insert(int_id, coords)
        else:
            self._grid_fallback.insert(item)

    def remove(self, item_id: str) -> bool:
        if self._use_rtree:
            int_id = self._str_to_int.get(item_id)
            if int_id is None:
                return False
            item = self._items.get(int_id)
            if not item:
                return False
            coords = (item.bbox.x1, item.bbox.y1, item.bbox.x2, item.bbox.y2)
            self._rtree.delete(int_id, coords)
            del self._items[int_id]
            del self._str_to_int[item_id]
            del self._int_to_str[int_id]
            return True
        else:
            return self._grid_fallback.remove(item_id)

    def query_bbox(self, bbox: BBox) -> List[IndexedItem]:
        if self._use_rtree:
            coords = (bbox.x1, bbox.y1, bbox.x2, bbox.y2)
            int_ids = list(self._rtree.intersection(coords))
            return [self._items[iid] for iid in int_ids if iid in self._items]
        else:
            return self._grid_fallback.query_bbox(bbox)

    def query_point(self, x: float, y: float) -> List[IndexedItem]:
        return self.query_bbox(BBox(x, y, x, y))

    def query_radius(self, cx: float, cy: float, radius: float) -> List[IndexedItem]:
        search_bbox = BBox(cx - radius, cy - radius, cx + radius, cy + radius)
        candidates = self.query_bbox(search_bbox)
        results = []
        for item in candidates:
            if item.bbox.distance_to(search_bbox) <= radius or item.bbox.intersects(search_bbox):
                results.append(item)
        return results

    def nearest(self, x: float, y: float, k: int = 1) -> List[Tuple[IndexedItem, float]]:
        if self._use_rtree:
            int_ids = list(self._rtree.nearest((x, y), num_results=k))
            results = []
            for iid in int_ids:
                item = self._items.get(iid)
                if item:
                    ix, iy = item.bbox.center
                    dist = math.hypot(ix - x, iy - y)
                    results.append((item, dist))
            return results
        else:
            return self._grid_fallback.nearest(x, y, k)

    def count(self) -> int:
        if self._use_rtree:
            return len(self._items)
        return self._grid_fallback.count()

    def clear(self) -> None:
        if self._use_rtree:
            self._items.clear()
            self._str_to_int.clear()
            self._int_to_str.clear()
            self._id_counter = 0
            try:
                from rtree.index import Index, Property
                p = Property()
                p.dimension = 2
                self._rtree = Index(properties=p)
            except ImportError:
                pass
        else:
            self._grid_fallback.clear()

    def all_items(self) -> List[IndexedItem]:
        if self._use_rtree:
            return list(self._items.values())
        return self._grid_fallback.all_items()


# ---------------------------------------------------------------------------
# PCB Spatial Index — high-level API
# ---------------------------------------------------------------------------

class PCBSpatialIndex:
    """
    High-level spatial index for PCB operations.

    Manages multiple layers of spatial data and provides:
    - Collision detection between components
    - DRC clearance checks
    - Net adjacency queries
    - Copper pour overlap detection
    """

    def __init__(self):
        self._index = RTreeIndex()
        self._layer_index: Dict[str, GridIndex] = {}

    # ---- Insert / Remove ----

    def add_component(
        self,
        ref: str,
        x: float, y: float,
        width: float, height: float,
        layer: str = "F.Cu",
        rotation: float = 0.0,
        **extra_data,
    ) -> None:
        bbox = BBox(x - width / 2, y - height / 2, x + width / 2, y + height / 2)
        item = IndexedItem(
            id=ref, bbox=bbox, layer=layer,
            item_type="component",
            data={"rotation": rotation, **extra_data},
        )
        self._index.insert(item)
        self._get_layer_index(layer).insert(item)

    def add_track(
        self,
        track_id: str,
        points: List[Tuple[float, float]],
        width: float,
        layer: str = "F.Cu",
        net: str = "",
    ) -> None:
        if not points:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        half_w = width / 2
        bbox = BBox(
            min(xs) - half_w, min(ys) - half_w,
            max(xs) + half_w, max(ys) + half_w,
        )
        item = IndexedItem(
            id=track_id, bbox=bbox, layer=layer,
            item_type="track",
            data={"points": points, "width": width, "net": net},
        )
        self._index.insert(item)
        self._get_layer_index(layer).insert(item)

    def add_via(
        self,
        via_id: str,
        x: float, y: float,
        drill: float,
        pad: float,
        net: str = "",
    ) -> None:
        half = pad / 2
        bbox = BBox(x - half, y - half, x + half, y + half)
        item = IndexedItem(
            id=via_id, bbox=bbox, layer="ALL",
            item_type="via",
            data={"drill": drill, "net": net},
        )
        self._index.insert(item)

    def add_zone(
        self,
        zone_id: str,
        bbox: BBox,
        layer: str = "F.Cu",
        net: str = "",
    ) -> None:
        item = IndexedItem(
            id=zone_id, bbox=bbox, layer=layer,
            item_type="zone",
            data={"net": net},
        )
        self._index.insert(item)
        self._get_layer_index(layer).insert(item)

    def add_pad(
        self,
        pad_id: str,
        x: float, y: float,
        width: float, height: float,
        layer: str = "F.Cu",
        net: str = "",
    ) -> None:
        bbox = BBox(x - width / 2, y - height / 2, x + width / 2, y + height / 2)
        item = IndexedItem(
            id=pad_id, bbox=bbox, layer=layer,
            item_type="pad",
            data={"net": net},
        )
        self._index.insert(item)
        self._get_layer_index(layer).insert(item)

    def remove(self, item_id: str) -> bool:
        return self._index.remove(item_id)

    # ---- Query ----

    def find_collisions(self, clearance: float = 0.0) -> List[Tuple[str, str, float]]:
        """
        Find all pairs of items that collide or violate clearance.

        Returns list of (id_a, id_b, overlap_distance).
        """
        all_items = self._index.all_items()
        results = []
        seen = set()
        for item in all_items:
            search_area = item.bbox.expand(clearance)
            nearby = self._index.query_bbox(search_area)
            for other in nearby:
                if other.id == item.id:
                    continue
                pair = tuple(sorted([item.id, other.id]))
                if pair in seen:
                    continue
                seen.add(pair)
                dist = item.bbox.distance_to(other.bbox)
                if dist <= clearance:
                    results.append((item.id, other.id, dist))
        return results

    def find_nearby(
        self,
        x: float, y: float,
        radius: float,
        layer: Optional[str] = None,
        item_type: Optional[str] = None,
    ) -> List[IndexedItem]:
        """Find items within radius of a point, optionally filtered."""
        candidates = self._index.query_radius(x, y, radius)
        if layer:
            candidates = [c for c in candidates if c.layer == layer or c.layer == "ALL"]
        if item_type:
            candidates = [c for c in candidates if c.item_type == item_type]
        return candidates

    def check_clearance(
        self,
        bbox: BBox,
        clearance: float,
        layer: str = "F.Cu",
        exclude_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[IndexedItem, float]]:
        """
        Check if a bounding box violates clearance from other items.

        Returns list of (violating_item, actual_distance).
        """
        search_area = bbox.expand(clearance)
        candidates = self._index.query_bbox(search_area)
        exclude_ids = exclude_ids or set()
        violations = []
        for item in candidates:
            if item.id in exclude_ids:
                continue
            dist = bbox.distance_to(item.bbox)
            if dist < clearance:
                violations.append((item, dist))
        return violations

    def find_in_region(
        self,
        bbox: BBox,
        layer: Optional[str] = None,
    ) -> List[IndexedItem]:
        """Find all items within a rectangular region."""
        candidates = self._index.query_bbox(bbox)
        if layer:
            candidates = [c for c in candidates if c.layer == layer or c.layer == "ALL"]
        return candidates

    def net_adjacency(
        self,
        net_name: str,
        radius: float = 2.0,
    ) -> Dict[str, List[str]]:
        """
        Find nets adjacent to the given net within radius.
        Returns {other_net: [item_ids]}.
        """
        net_items = [
            item for item in self._index.all_items()
            if item.data.get("net") == net_name
        ]
        adjacent: Dict[str, List[str]] = {}
        for item in net_items:
            nearby = self._index.query_radius(
                item.bbox.center[0], item.bbox.center[1], radius
            )
            for other in nearby:
                other_net = other.data.get("net", "")
                if other_net and other_net != net_name:
                    adjacent.setdefault(other_net, []).append(other.id)
        return adjacent

    # ---- Statistics ----

    def stats(self) -> Dict[str, Any]:
        """Get spatial index statistics."""
        all_items = self._index.all_items()
        type_counts = {}
        layer_counts = {}
        for item in all_items:
            type_counts[item.item_type] = type_counts.get(item.item_type, 0) + 1
            layer_counts[item.layer] = layer_counts.get(item.layer, 0) + 1

        return {
            "total_items": len(all_items),
            "by_type": type_counts,
            "by_layer": layer_counts,
            "index_type": "rtree" if self._index._use_rtree else "grid",
        }

    def clear(self) -> None:
        self._index.clear()
        self._layer_index.clear()

    # ---- Warmup / Pre-build ----

    def warmup_from_pcb_data(self, pcb_data: Dict[str, Any]) -> int:
        """
        Pre-build spatial index from PCB data.

        This method loads all items from PCB data upfront to avoid
        lazy-loading delays during DRC or routing operations.

        Args:
            pcb_data: Dictionary containing footprints, tracks, vias, zones, pads

        Returns:
            Number of items indexed
        """
        import time
        start = time.time()
        count = 0

        # Add footprints/components
        for fp in pcb_data.get("footprints", []) or []:
            ref = fp.get("reference", fp.get("name", f"fp_{count}"))
            x = fp.get("position", {}).get("x", 0)
            y = fp.get("position", {}).get("y", 0)
            w = fp.get("width", fp.get("bounds", {}).get("width", 5))
            h = fp.get("height", fp.get("bounds", {}).get("height", 5))
            layer = fp.get("layer", "F.Cu")
            rotation = fp.get("rotation", 0)

            self.add_component(ref, x, y, w, h, layer, rotation)
            count += 1

        # Add tracks
        for track in pcb_data.get("tracks", []) or []:
            tid = track.get("id", f"track_{count}")
            points = track.get("points", track.get("path", []))
            width = track.get("width", 0.2)
            layer = track.get("layer", "F.Cu")
            net = track.get("net", "")

            if points:
                self.add_track(tid, points, width, layer, net)
                count += 1

        # Add vias
        for via in pcb_data.get("vias", []) or []:
            vid = via.get("id", f"via_{count}")
            x = via.get("position", {}).get("x", via.get("x", 0))
            y = via.get("position", {}).get("y", via.get("y", 0))
            drill = via.get("drill", 0.3)
            pad = via.get("size", via.get("pad", 0.6))
            net = via.get("net", "")

            self.add_via(vid, x, y, drill, pad, net)
            count += 1

        # Add zones/copper pours
        for zone in pcb_data.get("zones", []) or []:
            zid = zone.get("id", f"zone_{count}")
            bounds = zone.get("bounds", zone.get("bbox", {}))
            layer = zone.get("layer", "F.Cu")
            net = zone.get("net", "")

            if bounds:
                bbox = BBox(
                    bounds.get("x1", bounds.get("min_x", 0)),
                    bounds.get("y1", bounds.get("min_y", 0)),
                    bounds.get("x2", bounds.get("max_x", 10)),
                    bounds.get("y2", bounds.get("max_y", 10)),
                )
                self.add_zone(zid, bbox, layer, net)
                count += 1

        # Add pads
        for pad in pcb_data.get("pads", []) or []:
            pid = pad.get("id", f"pad_{count}")
            x = pad.get("position", {}).get("x", pad.get("x", 0))
            y = pad.get("position", {}).get("y", pad.get("y", 0))
            w = pad.get("width", pad.get("size", 1))
            h = pad.get("height", pad.get("size", 1))
            layer = pad.get("layer", "F.Cu")
            net = pad.get("net", "")

            self.add_pad(pid, x, y, w, h, layer, net)
            count += 1

        elapsed = (time.time() - start) * 1000
        logger.info(f"Spatial index warmup complete: {count} items indexed in {elapsed:.1f}ms")

        return count

    def is_warmed_up(self) -> bool:
        """Check if index has been warmed up with data."""
        return self._index.count() > 0

    # ---- Internal ----

    def _get_layer_index(self, layer: str) -> GridIndex:
        if layer not in self._layer_index:
            self._layer_index[layer] = GridIndex(cell_size=2.0)
        return self._layer_index[layer]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_spatial_index: Optional[PCBSpatialIndex] = None


def get_spatial_index(warmup_data: Optional[Dict[str, Any]] = None) -> PCBSpatialIndex:
    """
    Get or create the singleton spatial index.

    Args:
        warmup_data: Optional PCB data to pre-load into the index.
                     If provided and index is empty, will warmup automatically.

    Returns:
        PCBSpatialIndex instance
    """
    global _spatial_index
    if _spatial_index is None:
        _spatial_index = PCBSpatialIndex()

    # Auto-warmup if data provided and index is empty
    if warmup_data and not _spatial_index.is_warmed_up():
        _spatial_index.warmup_from_pcb_data(warmup_data)

    return _spatial_index


def reset_spatial_index() -> None:
    global _spatial_index
    if _spatial_index:
        _spatial_index.clear()
    _spatial_index = None


def warmup_spatial_index(pcb_data: Dict[str, Any]) -> int:
    """
    Warmup the spatial index with PCB data.

    This is a convenience function that ensures the singleton
    index is initialized and populated.

    Args:
        pcb_data: PCB data dictionary

    Returns:
        Number of items indexed
    """
    return get_spatial_index(warmup_data=pcb_data).warmup_from_pcb_data(pcb_data)
