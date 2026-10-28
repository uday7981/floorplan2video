from __future__ import annotations

import pytest


@pytest.fixture
def minimal_plan() -> dict:
    """6x5 m single room, 4 walls, 1 door, 1 room — mirrors plan_schema's fixture."""
    return {
        "schema_version": "1.0",
        "units": "m",
        "meta": {"scale_source": "dimension_text", "confidence": 0.9, "warnings": []},
        "defaults": {"wall_height": 2.8, "floor_thickness": 0.2},
        "walls": [
            {"id": "w1", "a": [0, 0], "b": [6, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w2", "a": [6, 0], "b": [6, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w3", "a": [6, 5], "b": [0, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w4", "a": [0, 5], "b": [0, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
        ],
        "openings": [
            {"id": "o1", "wall_id": "w1", "type": "door",
             "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True},
        ],
        "rooms": [
            {"id": "r1", "name": "Studio", "type": "living",
             "polygon": [[0.23, 0.23], [5.77, 0.23], [5.77, 4.77], [0.23, 4.77]]},
        ],
    }


@pytest.fixture
def minimal_shots() -> dict:
    return {
        "schema_version": "1.0",
        "project_type": "house",
        "style_preset": {"materials": "oak", "light": "3000K", "setting": "forest"},
        "shots": [
            {"id": "s1", "ord": 0, "kind": "opening", "label": "Open",
             "camera": {"move": "crane", "duration_s": 5, "lens_mm": 35, "fps": 24}},
            {"id": "s2", "ord": 1, "kind": "room", "room_id": "r1", "label": "01 Studio",
             "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
            {"id": "s3", "ord": 2, "kind": "exterior", "label": "Exterior",
             "camera": {"move": "orbit", "duration_s": 8, "lens_mm": 28, "fps": 24}},
        ],
    }
