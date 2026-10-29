from __future__ import annotations

import json
from pathlib import Path

import pytest

from blender_worker.plan_io import (
    CAMERA_MOVES,
    SHOTS_KINDS,
    all_openings,
    all_rooms,
    all_walls,
    default_style_preset,
    floor_by_id,
    floor_of_room,
    load_plan,
    load_shots,
)


def _write(tmp: Path, name: str, obj: dict) -> Path:
    p = tmp / name
    p.write_text(json.dumps(obj))
    return p


def test_load_plan_happy_v1_autoupgrades(tmp_path, minimal_plan):
    """v1 input (flat walls/openings/rooms) auto-wraps into floors[0] so
    everything downstream only sees the v2 shape."""
    p = _write(tmp_path, "plan.json", minimal_plan)
    data = load_plan(p)
    assert "floors" in data
    assert len(data["floors"]) == 1
    assert data["floors"][0]["id"] == "ground"
    assert data["floors"][0]["z0"] == 0.0
    assert len(data["floors"][0]["walls"]) == 4
    # Aggregators pull from every floor
    assert len(all_walls(data)) == 4
    assert len(all_rooms(data)) == 1
    assert len(all_openings(data)) == 1
    # vertical_connections defaulted to []
    assert data["vertical_connections"] == []


def test_load_plan_missing_section(tmp_path, minimal_plan):
    minimal_plan.pop("walls")
    p = _write(tmp_path, "plan.json", minimal_plan)
    with pytest.raises(ValueError, match="walls"):
        load_plan(p)


def test_load_plan_v2_passthrough(tmp_path):
    plan_v2 = {
        "schema_version": "2.0",
        "units": "m",
        "defaults": {"wall_height": 2.8, "floor_thickness": 0.2},
        "floors": [{
            "id": "ground", "ord": 0, "z0": 0.0, "wall_height": 2.8, "label": "Ground",
            "walls": [{"id": "w1", "a": [0, 0], "b": [6, 0], "thickness": 0.23, "height": 2.8}],
            "openings": [],
            "rooms": [{"id": "r1", "name": "Hall", "type": "hall",
                       "polygon": [[0, 0], [6, 0], [6, 5], [0, 5]]}],
        }],
        "vertical_connections": [],
    }
    p = _write(tmp_path, "plan.json", plan_v2)
    data = load_plan(p)
    assert len(data["floors"]) == 1
    assert floor_by_id(data, "ground")["label"] == "Ground"
    assert floor_of_room(data, "r1")["id"] == "ground"


def test_load_shots_happy(tmp_path, minimal_shots):
    p = _write(tmp_path, "shots.json", minimal_shots)
    data = load_shots(p)
    assert len(data["shots"]) == 3


def test_load_shots_invalid_kind(tmp_path, minimal_shots):
    minimal_shots["shots"][0]["kind"] = "nope"
    p = _write(tmp_path, "shots.json", minimal_shots)
    with pytest.raises(ValueError, match="unknown kind"):
        load_shots(p)


def test_load_shots_room_without_room_id(tmp_path, minimal_shots):
    del minimal_shots["shots"][1]["room_id"]
    p = _write(tmp_path, "shots.json", minimal_shots)
    with pytest.raises(ValueError, match="room_id"):
        load_shots(p)


def test_load_shots_invalid_duration(tmp_path, minimal_shots):
    minimal_shots["shots"][0]["camera"]["duration_s"] = 3
    p = _write(tmp_path, "shots.json", minimal_shots)
    with pytest.raises(ValueError, match="duration_s"):
        load_shots(p)


def test_load_shots_invalid_move(tmp_path, minimal_shots):
    minimal_shots["shots"][0]["camera"]["move"] = "zoom"
    p = _write(tmp_path, "shots.json", minimal_shots)
    with pytest.raises(ValueError, match="move"):
        load_shots(p)


def test_default_style_preset_has_required_keys():
    p = default_style_preset()
    assert set(p.keys()) == {"materials", "light", "setting"}


def test_shots_kinds_and_moves_sets():
    assert SHOTS_KINDS == {"opening", "room", "exterior", "stair_climb"}
    assert CAMERA_MOVES == {"dolly", "pan", "crane", "orbit", "stair"}


def test_stair_climb_shot_requires_connection_id(tmp_path, minimal_shots):
    minimal_shots["shots"].append({
        "id": "sc1", "ord": 3, "kind": "stair_climb", "label": "Up to first",
        "camera": {"move": "stair", "duration_s": 5, "lens_mm": 24, "fps": 24},
    })
    p = _write(tmp_path, "shots.json", minimal_shots)
    with pytest.raises(ValueError, match="stair_connection_id"):
        load_shots(p)
