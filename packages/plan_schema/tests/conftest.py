"""Shared fixtures: a minimal valid plan the tests mutate to trigger failures."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest


@pytest.fixture
def valid_plan_dict() -> dict[str, Any]:
    """6x5 m single-room house with one entrance door and one window.
    Hits all required collections and passes every validator by design.
    """
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


@pytest.fixture
def mutable_plan(valid_plan_dict):
    """A deep copy so individual tests can mutate freely."""
    return deepcopy(valid_plan_dict)
