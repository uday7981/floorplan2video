from __future__ import annotations

import math

import pytest

from blender_worker.geometry import (
    bbox_center_and_diagonal,
    building_bbox,
    nearest_opening_to_polygon,
    opening_world_position,
    orbit_position,
    point_to_segment_distance,
    polygon_centroid,
)


def test_centroid_of_square():
    assert polygon_centroid([(0, 0), (4, 0), (4, 4), (0, 4)]) == pytest.approx((2.0, 2.0))


def test_centroid_of_closed_square_same_as_open():
    open_ = polygon_centroid([(0, 0), (4, 0), (4, 4), (0, 4)])
    closed = polygon_centroid([(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)])
    assert open_ == pytest.approx(closed)


def test_centroid_of_triangle():
    # Right triangle with vertices (0,0),(3,0),(0,3). Centroid = (1,1).
    assert polygon_centroid([(0, 0), (3, 0), (0, 3)]) == pytest.approx((1.0, 1.0))


def test_building_bbox(minimal_plan):
    bbox = building_bbox(minimal_plan["walls"])
    assert bbox == ((0.0, 0.0), (6.0, 5.0))


def test_bbox_center_and_diagonal(minimal_plan):
    bbox = building_bbox(minimal_plan["walls"])
    center, diag = bbox_center_and_diagonal(bbox)
    assert center == pytest.approx((3.0, 2.5))
    assert diag == pytest.approx(math.hypot(6.0, 5.0))


def test_opening_world_position_mid_of_wall(minimal_plan):
    w = minimal_plan["walls"][0]       # (0,0)-(6,0), length 6
    op = minimal_plan["openings"][0]   # offset 2.0
    assert opening_world_position(w, op) == pytest.approx((2.0, 0.0))


def test_point_to_segment_distance_perpendicular():
    assert point_to_segment_distance((2, 3), (0, 0), (6, 0)) == pytest.approx(3.0)


def test_point_to_segment_distance_past_endpoint():
    # Point beyond segment end — nearest is the endpoint.
    assert point_to_segment_distance((8, 1), (0, 0), (6, 0)) == pytest.approx(math.hypot(2, 1))


def test_nearest_opening_to_polygon(minimal_plan):
    room = minimal_plan["rooms"][0]
    nearest = nearest_opening_to_polygon(
        room["polygon"], minimal_plan["walls"], minimal_plan["openings"]
    )
    assert nearest is not None
    assert nearest["id"] == "o1"


def test_nearest_opening_returns_none_if_no_openings(minimal_plan):
    assert nearest_opening_to_polygon(
        minimal_plan["rooms"][0]["polygon"], minimal_plan["walls"], []
    ) is None


def test_orbit_position_is_on_circle():
    pos = orbit_position((5, 5), 10, 6, math.radians(90))
    # 90° → (cos=0, sin=1) → (5, 15, 6)
    assert pos == pytest.approx((5.0, 15.0, 6.0))
