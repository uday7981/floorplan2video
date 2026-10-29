"""Multi-storey schema tests: Floor + VerticalConnection + v1 backwards compat."""
from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from plan_schema import Plan


def _two_storey_plan() -> dict:
    """Minimal 2-storey plan: 6×5 m ground + 6×5 m first with one stair."""
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
        "defaults": {"wall_height": 2.8, "floor_thickness": 0.2},
        "floors": [
            {
                "id": "ground", "ord": 0, "z0": 0.0, "wall_height": 2.8, "label": "Ground Floor",
                "walls": g_walls,
                "openings": [
                    {"id": "go1", "wall_id": "gw1", "type": "door",
                     "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True},
                ],
                "rooms": [
                    {"id": "gr1", "name": "Living", "type": "living",
                     "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]},
                ],
            },
            {
                "id": "first", "ord": 1, "z0": 3.0, "wall_height": 2.8, "label": "First Floor",
                "walls": f_walls,
                "openings": [],  # no exterior door on first floor
                "rooms": [
                    {"id": "fr1", "name": "Bedroom", "type": "bedroom",
                     "polygon": [[0.25, 0.25], [5.75, 0.25], [5.75, 4.75], [0.25, 4.75]]},
                ],
            },
        ],
        "vertical_connections": [
            {"id": "s1", "kind": "stair",
             "from_floor_id": "ground", "to_floor_id": "first",
             "polygon": [[4.5, 0.5], [5.5, 0.5], [5.5, 2.5], [4.5, 2.5]]},
        ],
    }


# ---------- v1 backwards compat ----------

def test_v1_input_auto_upgrades_to_single_floor(valid_plan_dict):
    """A plan with no `floors` key becomes floors[0] with id='ground'."""
    original = deepcopy(valid_plan_dict)
    plan = Plan.model_validate(valid_plan_dict)
    assert len(plan.floors) == 1
    assert plan.floors[0].id == "ground"
    assert plan.floors[0].ord == 0
    assert plan.floors[0].z0 == 0.0
    assert len(plan.floors[0].walls) == 4
    # Input dict must NOT be mutated — regression guard for test-reuse pattern.
    assert valid_plan_dict == original


def test_v1_input_no_walls_key_leaves_dict_alone():
    """If walls is missing (schema violation), the upgrade doesn't touch anything."""
    bad = {"meta": {}, "defaults": {}}
    with pytest.raises(ValidationError):
        Plan.model_validate(bad)
    # Still no floors inserted
    assert "floors" not in bad


# ---------- v2 happy path ----------

def test_two_storey_plan_valid():
    plan = Plan.model_validate(_two_storey_plan())
    assert len(plan.floors) == 2
    assert [f.id for f in plan.floors] == ["ground", "first"]
    assert len(plan.vertical_connections) == 1
    assert plan.vertical_connections[0].kind.value == "stair"
    # Aggregated accessors
    assert len(plan.all_walls) == 8
    assert len(plan.all_rooms) == 2


def test_floor_by_id_lookup():
    plan = Plan.model_validate(_two_storey_plan())
    assert plan.floor_by_id("first").label == "First Floor"
    with pytest.raises(KeyError):
        plan.floor_by_id("basement")


# ---------- v2 validation rules ----------

def test_duplicate_floor_ids_rejected():
    p = _two_storey_plan()
    p["floors"][1]["id"] = "ground"
    with pytest.raises(ValidationError, match="duplicate ids"):
        Plan.model_validate(p)


def test_non_sequential_ords_rejected():
    p = _two_storey_plan()
    p["floors"][1]["ord"] = 5  # skips 1
    with pytest.raises(ValidationError, match="permutation"):
        Plan.model_validate(p)


def test_stair_references_unknown_floor_rejected():
    p = _two_storey_plan()
    p["vertical_connections"][0]["to_floor_id"] = "basement"
    with pytest.raises(ValidationError, match="to_floor_id"):
        Plan.model_validate(p)


def test_unreachable_floor_rejected():
    p = _two_storey_plan()
    p["vertical_connections"] = []
    with pytest.raises(ValidationError, match="vertical_connection"):
        Plan.model_validate(p)


def test_main_entrance_on_either_floor_counts():
    """main_entrance can live on any floor; the count is across all floors."""
    p = _two_storey_plan()
    # Move main_entrance from ground to first (not realistic, but tests the rule).
    p["floors"][0]["openings"][0]["main_entrance"] = False
    p["floors"][1]["openings"].append({
        "id": "fo1", "wall_id": "fw1", "type": "door",
        "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True,
    })
    plan = Plan.model_validate(p)
    assert plan is not None  # exactly one across floors


def test_two_main_entrances_across_floors_rejected():
    p = _two_storey_plan()
    p["floors"][1]["openings"].append({
        "id": "fo1", "wall_id": "fw1", "type": "door",
        "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True,
    })
    with pytest.raises(ValidationError, match="main_entrance"):
        Plan.model_validate(p)


def test_stair_polygon_self_intersecting_rejected():
    p = _two_storey_plan()
    p["vertical_connections"][0]["polygon"] = [[0, 0], [4, 4], [4, 0], [0, 4]]  # bowtie
    with pytest.raises(ValidationError, match="self-intersecting"):
        Plan.model_validate(p)


def test_vertical_connection_same_floor_rejected():
    p = _two_storey_plan()
    p["vertical_connections"][0]["to_floor_id"] = "ground"
    with pytest.raises(ValidationError, match="from and to floors are the same"):
        Plan.model_validate(p)


def test_three_storey_chain_valid():
    """Ground → first → second via two stairs."""
    p = _two_storey_plan()
    second = deepcopy(p["floors"][1])
    second["id"] = "second"
    second["ord"] = 2
    second["z0"] = 6.0
    second["label"] = "Second Floor"
    # Rename walls/openings/rooms so IDs stay unique within the floor
    for w in second["walls"]: w["id"] = w["id"].replace("fw", "sw")
    for op in second.get("openings", []): op["id"] = op["id"].replace("fo", "so")
    for r in second["rooms"]: r["id"] = r["id"].replace("fr", "sr")
    p["floors"].append(second)
    p["vertical_connections"].append({
        "id": "s2", "kind": "stair",
        "from_floor_id": "first", "to_floor_id": "second",
        "polygon": [[4.5, 0.5], [5.5, 0.5], [5.5, 2.5], [4.5, 2.5]],
    })
    plan = Plan.model_validate(p)
    assert len(plan.floors) == 3
    assert len(plan.vertical_connections) == 2
