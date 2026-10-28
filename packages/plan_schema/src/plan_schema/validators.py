"""Polygon geometry helpers. Thin wrapper around shapely so the models don't
import shapely directly and tests can swap in a pure-Python stub if ever needed.
"""
from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from shapely.geometry import Polygon

Point2 = Tuple[float, float]


def _ensure_closed(points: Sequence[Point2]) -> list[Point2]:
    pts = list(points)
    if len(pts) >= 2 and pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def polygon_area(points: Sequence[Point2]) -> float:
    """Return absolute area in m² for a 2D polygon. Accepts open or closed rings."""
    poly = Polygon(_ensure_closed(points))
    return abs(poly.area)


def polygon_is_simple(points: Sequence[Point2]) -> bool:
    """True if the polygon's boundary is non-self-intersecting (simple)."""
    poly = Polygon(_ensure_closed(points))
    # shapely's `is_valid` catches self-intersections and ring-order problems.
    return bool(poly.is_valid)
