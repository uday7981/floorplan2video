"""Multi-storey schema tests: Level + Stair + Void + legacy auto-upgrade."""
from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from plan_schema import Plan


def _two_storey_plan() -> dict:
    """Minimal 2-storey v2.0 plan: 6×5 m ground + 6×5 m first + one stair."""
    g_walls = [
        {"id": "gw1", "a": [0, 0], "b": [6, 0], "thickness": 0.25, "height": 2.8, "exterior": True},
        {"id": "gw2", "a": [6, 0], "b": [6, 5], "thickness": 0.25, "height": 2.8, "exterior": True},
        {"id": "gw3", "a": [6, 5], "b": [0, 5], "thickness": 0.25, "height": 2.8, "exterior": True},
        {"id": "gw4", "a": [0, 5], "b": [0, 0], "thickness": 0.25, "height": 2.8, "exterior": True},
    ]
    f_walls = [
        {"id": "fw1", "a": [0, 0], "b": [6, 0], "thickness": 0.25, "height": 2.8, "exterior": True},
        {"id": "fw2", "a": [6, 0], "b": [6, 5], "thickness": 0.25, "height": 2.8, "exterior": True},
        {"id": "fw3", "a": [6, 5], "b": [0, 5], "thickness": 0.25, "height": 2.8, "exterior": True},
        {"id": "fw4", "a": [0, 5], "b": [0, 0], "thickness": 0.25, "height": 2.8, "exterior": True},
    ]
    return {
        "schema_version": "2.0",
        "units": "m",
        "meta": {"scale_source": "dimension_text", "confidence": 0.9, "warnings": []},
        "defaults": {"floor_thickness": 0.2},
        "levels": [
            {
                "id": "ground", "name": "Ground Floor", "index": 0,
                "elevation": 0.0, "floor_to_floor_height": 3.0,
                "walls": g_walls,
                "openings": [{"id": "go1", "wall_id": "gw1", "type": "door",
                              "offset": 2.0, "width": 1.0, "height": 2.1,
                              "sill": 0.0, "main_entrance": True}],
                "rooms": [{"id": "gr1", "name": "Living", "type": "living",
                           "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]}],
                "voids": [{"id": "gv1",
                           "polygon": [[4.5, 0.5], [5.5, 0.5], [5.5, 2.5], [4.5, 2.5]]}],
            },
            {
                "id": "first", "name": "First Floor", "index": 1,
                "elevation": 3.0, "floor_to_floor_height": 3.0,
                "walls": f_walls,
                "openings": [],
                "rooms": [{"id": "fr1", "name": "Bedroom", "type": "bedroom",
                           "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]}],
            },
        ],
        "stairs": [
            {"id": "s1",
             "from_level": "ground", "to_level": "first",
             "footprint":  [[4.5, 0.5], [5.5, 0.5], [5.5, 2.5], [4.5, 2.5]],
             "start_point": [4.75, 0.6],
             "end_point":   [5.25, 2.4],
             "direction": "up"},
        ],
    }


# ---------- v1 → v2 upgrade ----------

def test_v1_input_auto_upgrades_to_single_level(v1_plan_dict):
    original = deepcopy(v1_plan_dict)
    plan = Plan.model_validate(v1_plan_dict)
    assert len(plan.levels) == 1
    assert plan.levels[0].id == "ground"
    assert plan.levels[0].index == 0
    assert plan.levels[0].elevation == 0.0
    assert len(plan.levels[0].walls) == 4
    # f2f = wall_height + floor_thickness = 2.8 + 0.2 = 3.0
    assert plan.levels[0].floor_to_floor_height == pytest.approx(3.0)
    # Caller's dict must not have been mutated.
    assert v1_plan_dict == original


# ---------- v2-M8 → v2.0 upgrade (floors → levels, vertical_connections → stairs) ----------

def test_v2m8_input_renames_floors_and_stairs():
    legacy = {
        "schema_version": "2.0",
        "units": "m",
        "meta": {"scale_source": "dimension_text", "confidence": 0.9, "warnings": []},
        "defaults": {"floor_thickness": 0.2},
        "floors": [
            {"id": "ground", "ord": 0, "z0": 0.0, "wall_height": 2.8, "label": "Ground Floor",
             "walls": [{"id": "w1", "a": [0, 0], "b": [6, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
                       {"id": "w2", "a": [6, 0], "b": [6, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
                       {"id": "w3", "a": [6, 5], "b": [0, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
                       {"id": "w4", "a": [0, 5], "b": [0, 0], "thickness": 0.23, "height": 2.8, "exterior": True}],
             "openings": [{"id": "o1", "wall_id": "w1", "type": "door", "offset": 2.0,
                           "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True}],
             "rooms": [{"id": "r1", "name": "Studio", "type": "living",
                        "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]}]},
            {"id": "first", "ord": 1, "z0": 3.0, "wall_height": 2.8, "label": "First Floor",
             "walls": [{"id": "fw1", "a": [0, 0], "b": [6, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
                       {"id": "fw2", "a": [6, 0], "b": [6, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
                       {"id": "fw3", "a": [6, 5], "b": [0, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
                       {"id": "fw4", "a": [0, 5], "b": [0, 0], "thickness": 0.23, "height": 2.8, "exterior": True}],
             "openings": [],
             "rooms": [{"id": "fr1", "name": "Bedroom", "type": "bedroom",
                        "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]}]},
        ],
        "vertical_connections": [
            {"id": "vc1", "kind": "stair",
             "from_floor_id": "ground", "to_floor_id": "first",
             "polygon": [[4.5, 0.5], [5.5, 0.5], [5.5, 2.5], [4.5, 2.5]]},
        ],
    }
    plan = Plan.model_validate(legacy)
    assert [l.id for l in plan.levels] == ["ground", "first"]
    assert plan.levels[0].name == "Ground Floor"
    assert plan.levels[1].name == "First Floor"
    assert len(plan.stairs) == 1
    s = plan.stairs[0]
    assert s.from_level == "ground"
    assert s.to_level == "first"
    # Fabricated endpoints should sit on the short-side centres of the footprint.
    assert s.start_point != s.end_point


# ---------- v2.0 happy path ----------

def test_two_storey_plan_valid():
    plan = Plan.model_validate(_two_storey_plan())
    assert len(plan.levels) == 2
    assert [l.id for l in plan.levels] == ["ground", "first"]
    assert len(plan.stairs) == 1
    assert plan.stairs[0].direction.value == "up"
    assert len(plan.all_walls) == 8
    assert len(plan.all_rooms) == 2
    assert len(plan.levels[0].voids) == 1


def test_level_by_id_lookup():
    plan = Plan.model_validate(_two_storey_plan())
    assert plan.level_by_id("first").name == "First Floor"
    with pytest.raises(KeyError):
        plan.level_by_id("basement")


# ---------- v2.0 validation rules ----------

def test_duplicate_level_ids_rejected():
    p = _two_storey_plan()
    p["levels"][1]["id"] = "ground"
    with pytest.raises(ValidationError, match="duplicate ids"):
        Plan.model_validate(p)


def test_non_sequential_indexes_rejected():
    p = _two_storey_plan()
    p["levels"][1]["index"] = 5
    with pytest.raises(ValidationError, match="permutation"):
        Plan.model_validate(p)


def test_stair_references_unknown_level_rejected():
    p = _two_storey_plan()
    p["stairs"][0]["to_level"] = "basement"
    with pytest.raises(ValidationError, match="to_level"):
        Plan.model_validate(p)


def test_unreachable_level_rejected():
    p = _two_storey_plan()
    p["stairs"] = []
    with pytest.raises(ValidationError, match="at least one stair"):
        Plan.model_validate(p)


def test_two_main_entrances_across_levels_rejected():
    p = _two_storey_plan()
    p["levels"][1]["openings"].append({
        "id": "fo1", "wall_id": "fw1", "type": "door",
        "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True,
    })
    with pytest.raises(ValidationError, match="main_entrance"):
        Plan.model_validate(p)


def test_stair_footprint_self_intersecting_rejected():
    p = _two_storey_plan()
    p["stairs"][0]["footprint"] = [[0, 0], [4, 4], [4, 0], [0, 4]]  # bowtie
    with pytest.raises(ValidationError, match="self-intersecting"):
        Plan.model_validate(p)


def test_void_self_intersecting_rejected():
    p = _two_storey_plan()
    p["levels"][0]["voids"][0]["polygon"] = [[0, 0], [4, 4], [4, 0], [0, 4]]
    with pytest.raises(ValidationError, match="self-intersecting"):
        Plan.model_validate(p)


def test_three_storey_chain_valid():
    """Ground → first → second via two stairs."""
    p = _two_storey_plan()
    second = deepcopy(p["levels"][1])
    second["id"] = "second"
    second["index"] = 2
    second["elevation"] = 6.0
    second["name"] = "Second Floor"
    for w in second["walls"]:
        w["id"] = w["id"].replace("fw", "sw")
    for r in second["rooms"]:
        r["id"] = r["id"].replace("fr", "sr")
    p["levels"].append(second)
    p["stairs"].append({
        "id": "s2", "from_level": "first", "to_level": "second",
        "footprint": [[4.5, 0.5], [5.5, 0.5], [5.5, 2.5], [4.5, 2.5]],
        "start_point": [4.75, 0.6], "end_point": [5.25, 2.4],
        "direction": "up",
    })
    plan = Plan.model_validate(p)
    assert len(plan.levels) == 3
    assert len(plan.stairs) == 2
