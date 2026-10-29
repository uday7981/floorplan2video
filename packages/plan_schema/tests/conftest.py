"""Shared fixtures: a v1 (legacy) plan + a v2 single-storey plan the tests
mutate to trigger failures. The v1 variant proves the auto-upgrade still
works; the v2 variant tests the native shape."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest


@pytest.fixture
def v1_plan_dict() -> dict[str, Any]:
    """Legacy v1 shape (flat walls/openings/rooms at root). Auto-upgrades
    into levels[0] via the model_validator."""
    return {
        "schema_version": "1.0",
        "units": "m",
        "meta": {"scale_source": "dimension_text", "confidence": 0.9, "warnings": []},
        "defaults": {"wall_height": 2.8, "floor_thickness": 0.2},
        "walls": [
            {"id": "w1", "a": [0, 0],   "b": [6, 0],   "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w2", "a": [6, 0],   "b": [6, 5],   "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w3", "a": [6, 5],   "b": [0, 5],   "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w4", "a": [0, 5],   "b": [0, 0],   "thickness": 0.23, "height": 2.8, "exterior": True},
        ],
        "openings": [
            {"id": "o1", "wall_id": "w1", "type": "door",   "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True},
            {"id": "o2", "wall_id": "w3", "type": "window", "offset": 3.0, "width": 1.2, "height": 1.2, "sill": 0.9, "main_entrance": False},
        ],
        "rooms": [
            {"id": "r1", "name": "Studio", "type": "living",
             "polygon": [[0.23, 0.23], [5.77, 0.23], [5.77, 4.77], [0.23, 4.77]]},
        ],
    }


# Keep the old fixture name alive for existing tests that haven't been
# renamed. All existing tests mutate the dict via v1 keys; they still work
# because the Plan validator shallow-copies before upgrading.
@pytest.fixture
def valid_plan_dict(v1_plan_dict):
    return v1_plan_dict


@pytest.fixture
def mutable_plan(v1_plan_dict):
    return deepcopy(v1_plan_dict)


@pytest.fixture
def v2_plan_dict() -> dict[str, Any]:
    """Native v2.0 single-storey — one level, no stairs."""
    return {
        "schema_version": "2.0",
        "units": "m",
        "meta": {"scale_source": "dimension_text", "confidence": 0.9, "warnings": []},
        "defaults": {"floor_thickness": 0.2},
        "levels": [
            {
                "id": "ground", "name": "Ground Floor", "index": 0,
                "elevation": 0.0, "floor_to_floor_height": 3.0,
                "walls": [
                    {"id": "w1", "a": [0, 0], "b": [6, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
                    {"id": "w2", "a": [6, 0], "b": [6, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
                    {"id": "w3", "a": [6, 5], "b": [0, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
                    {"id": "w4", "a": [0, 5], "b": [0, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
                ],
                "openings": [
                    {"id": "o1", "wall_id": "w1", "type": "door", "offset": 2.0,
                     "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True},
                ],
                "rooms": [
                    {"id": "r1", "name": "Studio", "type": "living",
                     "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]},
                ],
            },
        ],
    }
