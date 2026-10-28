from __future__ import annotations

import json
from pathlib import Path

import pytest

from blender_worker.plan_io import (
    CAMERA_MOVES,
    SHOTS_KINDS,
    default_style_preset,
    load_plan,
    load_shots,
)


def _write(tmp: Path, name: str, obj: dict) -> Path:
    p = tmp / name
    p.write_text(json.dumps(obj))
    return p


def test_load_plan_happy(tmp_path, minimal_plan):
    p = _write(tmp_path, "plan.json", minimal_plan)
    data = load_plan(p)
    assert len(data["walls"]) == 4


def test_load_plan_missing_section(tmp_path, minimal_plan):
    minimal_plan.pop("walls")
    p = _write(tmp_path, "plan.json", minimal_plan)
    with pytest.raises(ValueError, match="walls"):
        load_plan(p)


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
    assert SHOTS_KINDS == {"opening", "room", "exterior"}
    assert CAMERA_MOVES == {"dolly", "pan", "crane", "orbit"}
