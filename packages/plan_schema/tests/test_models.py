"""Validation tests for the Plan model. Every TRD rule gets at least one
positive and one negative case."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from plan_schema import Plan, canonical_json, plan_hash


# ---------- Happy path ----------

def test_minimal_valid_plan_parses(valid_plan_dict):
    plan = Plan.model_validate(valid_plan_dict)
    assert plan.schema_version == "1.0"
    assert plan.units == "m"
    assert len(plan.walls) == 4
    assert sum(1 for o in plan.openings if o.main_entrance) == 1


def test_json_round_trip(valid_plan_dict):
    plan = Plan.model_validate(valid_plan_dict)
    dumped = json.loads(canonical_json(plan))
    Plan.model_validate(dumped)  # must re-parse


# ---------- Wall rules ----------

def test_wall_too_short_rejected(mutable_plan):
    mutable_plan["walls"][0]["b"] = [0.2, 0]  # 0.2 m < 0.3 m
    with pytest.raises(ValidationError, match="length"):
        Plan.model_validate(mutable_plan)


def test_wall_thickness_out_of_range_rejected(mutable_plan):
    mutable_plan["walls"][0]["thickness"] = 0.01  # < 0.05
    with pytest.raises(ValidationError):
        Plan.model_validate(mutable_plan)

    mutable_plan["walls"][0]["thickness"] = 0.7   # > 0.6
    with pytest.raises(ValidationError):
        Plan.model_validate(mutable_plan)


# ---------- Opening rules ----------

def test_opening_offset_outside_wall_rejected(mutable_plan):
    # w1 has length 6 m; offset 5.6 + width/2 = 6.1 → outside.
    mutable_plan["openings"][0]["offset"] = 5.6
    mutable_plan["openings"][0]["width"] = 1.0
    with pytest.raises(ValidationError, match="doesn't fit in wall"):
        Plan.model_validate(mutable_plan)


def test_opening_above_wall_height_rejected(mutable_plan):
    # wall height 2.8, sill 2.0 + height 1.0 = 3.0 → too tall
    mutable_plan["openings"][0]["sill"] = 2.0
    mutable_plan["openings"][0]["height"] = 1.0
    with pytest.raises(ValidationError, match="exceeds wall height"):
        Plan.model_validate(mutable_plan)


def test_opening_unknown_wall_rejected(mutable_plan):
    mutable_plan["openings"][0]["wall_id"] = "nope"
    with pytest.raises(ValidationError, match="unknown wall"):
        Plan.model_validate(mutable_plan)


# ---------- main_entrance uniqueness ----------

def test_zero_main_entrance_rejected(mutable_plan):
    for op in mutable_plan["openings"]:
        op["main_entrance"] = False
    with pytest.raises(ValidationError, match="main_entrance"):
        Plan.model_validate(mutable_plan)


def test_two_main_entrances_rejected(mutable_plan):
    mutable_plan["openings"][1]["main_entrance"] = True
    with pytest.raises(ValidationError, match="main_entrance"):
        Plan.model_validate(mutable_plan)


# ---------- Room polygon rules ----------

def test_tiny_room_rejected(mutable_plan):
    mutable_plan["rooms"][0]["polygon"] = [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5]]  # area 0.25
    with pytest.raises(ValidationError, match="area"):
        Plan.model_validate(mutable_plan)


def test_self_intersecting_room_rejected(mutable_plan):
    # Classic bowtie.
    mutable_plan["rooms"][0]["polygon"] = [[0, 0], [4, 4], [4, 0], [0, 4]]
    with pytest.raises(ValidationError, match="self-intersecting"):
        Plan.model_validate(mutable_plan)


# ---------- Bounding box ----------

def test_bbox_too_small_rejected(mutable_plan):
    # Shrink building to 2 x 2 m — below the 3 m floor.
    for w in mutable_plan["walls"]:
        w["a"] = [w["a"][0] / 3, w["a"][1] / 3]
        w["b"] = [w["b"][0] / 3, w["b"][1] / 3]
    mutable_plan["rooms"][0]["polygon"] = [[0.1, 0.1], [1.9, 0.1], [1.9, 1.5], [0.1, 1.5]]
    # Shrink opening so it still fits in the smaller wall.
    mutable_plan["openings"][0]["offset"] = 1.0
    mutable_plan["openings"][0]["width"] = 0.5
    mutable_plan["openings"][1]["offset"] = 1.0
    mutable_plan["openings"][1]["width"] = 0.5
    # The failure we're asserting is bbox.
    with pytest.raises(ValidationError, match="outside allowed"):
        Plan.model_validate(mutable_plan)


def test_bbox_too_large_rejected(mutable_plan):
    for w in mutable_plan["walls"]:
        w["a"] = [w["a"][0] * 20, w["a"][1] * 20]  # 120 m across — too big
        w["b"] = [w["b"][0] * 20, w["b"][1] * 20]
    mutable_plan["rooms"][0]["polygon"] = [[0.5, 0.5], [100, 0.5], [100, 50], [0.5, 50]]
    mutable_plan["openings"][0]["offset"] = 50.0
    with pytest.raises(ValidationError, match="outside allowed"):
        Plan.model_validate(mutable_plan)


# ---------- ID uniqueness ----------

def test_duplicate_wall_ids_rejected(mutable_plan):
    mutable_plan["walls"][1]["id"] = "w1"
    with pytest.raises(ValidationError, match="duplicate"):
        Plan.model_validate(mutable_plan)


# ---------- Extra fields ----------

def test_unknown_field_rejected(mutable_plan):
    mutable_plan["mystery"] = True
    with pytest.raises(ValidationError):
        Plan.model_validate(mutable_plan)


# ---------- Hashing ----------

def test_plan_hash_stable(valid_plan_dict):
    p1 = Plan.model_validate(valid_plan_dict)
    p2 = Plan.model_validate(valid_plan_dict)
    assert plan_hash(p1) == plan_hash(p2)


def test_plan_hash_changes_on_edit(valid_plan_dict, mutable_plan):
    mutable_plan["walls"][0]["thickness"] = 0.3
    assert plan_hash(Plan.model_validate(valid_plan_dict)) != plan_hash(
        Plan.model_validate(mutable_plan)
    )
