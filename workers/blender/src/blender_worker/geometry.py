"""Pure geometry helpers. No bpy. All units in metres."""
from __future__ import annotations

import math
from typing import Iterable, Sequence

Point2 = tuple[float, float]


def polygon_centroid(points: Sequence[Point2]) -> Point2:
    """Area-weighted centroid of a non-self-intersecting polygon."""
    pts = list(points)
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    a = 0.0
    cx = cy = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-9:
        # degenerate (zero-area) — fall back to simple average
        xs = [p[0] for p in pts[:-1]]
        ys = [p[1] for p in pts[:-1]]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    cx /= 6 * a
    cy /= 6 * a
    return (cx, cy)


def building_bbox(walls: Iterable[dict]) -> tuple[Point2, Point2]:
    """(min, max) corners of the axis-aligned bbox of all wall endpoints."""
    xs: list[float] = []
    ys: list[float] = []
    for w in walls:
        xs.extend((w["a"][0], w["b"][0]))
        ys.extend((w["a"][1], w["b"][1]))
    return (min(xs), min(ys)), (max(xs), max(ys))


def bbox_center_and_diagonal(bbox: tuple[Point2, Point2]) -> tuple[Point2, float]:
    (xmin, ymin), (xmax, ymax) = bbox
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    diag = math.hypot(xmax - xmin, ymax - ymin)
    return (cx, cy), diag


def wall_segment(wall: dict) -> tuple[Point2, Point2]:
    return tuple(wall["a"]), tuple(wall["b"])  # type: ignore[return-value]


def opening_world_position(wall: dict, opening: dict) -> Point2:
    """World (x,y) of an opening's centre, interpolated along its wall."""
    (ax, ay), (bx, by) = wall_segment(wall)
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length == 0:
        return (ax, ay)
    t = opening["offset"] / length
    return (ax + dx * t, ay + dy * t)


def point_to_segment_distance(p: Point2, seg_a: Point2, seg_b: Point2) -> float:
    (x, y) = p
    (ax, ay) = seg_a
    (bx, by) = seg_b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(x - ax, y - ay)
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
    px, py = ax + t * dx, ay + t * dy
    return math.hypot(x - px, y - py)


def nearest_opening_to_polygon(polygon: Sequence[Point2],
                               walls: list[dict],
                               openings: list[dict]) -> dict | None:
    """Find the opening whose world position is closest to any edge of the
    given polygon. Returns the opening dict, or None if there are no openings.

    Used by room-shot camera: 'the opening that leads into this room'.
    """
    if not openings:
        return None
    walls_by_id = {w["id"]: w for w in walls}
    poly = list(polygon)
    if poly[0] != poly[-1]:
        poly = poly + [poly[0]]
    edges = list(zip(poly[:-1], poly[1:]))

    def dist_to_polygon(p: Point2) -> float:
        return min(point_to_segment_distance(p, a, b) for a, b in edges)

    best = None
    best_dist = float("inf")
    for op in openings:
        w = walls_by_id.get(op["wall_id"])
        if w is None:
            continue
        p = opening_world_position(w, op)
        d = dist_to_polygon(p)
        if d < best_dist:
            best_dist = d
            best = op
    return best


def orbit_position(center: Point2, radius: float, height: float,
                   angle_rad: float) -> tuple[float, float, float]:
    """3D position on a horizontal circle around `center`, at height `height`."""
    cx, cy = center
    return (cx + radius * math.cos(angle_rad),
            cy + radius * math.sin(angle_rad),
            height)
