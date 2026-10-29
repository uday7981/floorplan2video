"""Load + lightly validate plan.json and shots.json.

Plan JSON shape = packages/plan_schema.Plan v2.0 (levels + stairs + voids).
This loader accepts THREE input shapes and normalises them all to v2.0 so
downstream code only ever iterates `plan["levels"]`:

  1. v2.0 proper (levels[] + stairs[])            — passthrough
  2. v2-M8 (floors[] + vertical_connections[])    — renamed on the fly
  3. v1 (flat walls/openings/rooms at root)       — wrapped into levels[0]

Shots JSON shape (v1 — the per-shot API; replaced by `journey.json` in v2 but
retained here while the journey builder lands):
    {
      "schema_version": "1.0",
      "project_type": "house" | "interior",
      "style_preset": {...},
      "shots": [{"id","ord","kind","label","room_id?","camera":{...}}]
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SHOTS_KINDS = {"opening", "room", "exterior", "stair_climb"}
CAMERA_MOVES = {"dolly", "pan", "crane", "orbit", "stair"}


def load_plan(path: Path) -> dict[str, Any]:
    """Load + normalise to v2.0. Downstream only ever sees `levels` + `stairs`."""
    data = json.loads(Path(path).read_text())
    if "defaults" not in data:
        raise ValueError("plan.json missing 'defaults'")
    data = _normalise_to_v2(data)
    data.setdefault("stairs", [])
    for l in data["levels"]:
        for req in ("id", "name", "index", "elevation", "walls", "rooms"):
            if req not in l:
                raise ValueError(f"level {l.get('id','?')} missing '{req}'")
        l.setdefault("floor_to_floor_height", 3.0)
        l.setdefault("voids", [])
        l.setdefault("openings", [])
    return data


def _normalise_to_v2(data: dict) -> dict:
    """Promote v1 / v2-M8 inputs into the v2.0 shape in-place-friendly fashion."""
    if "levels" in data:
        return data

    # Shape 2: floors[] + vertical_connections[]
    if "floors" in data:
        data = dict(data)
        legacy_floors = data.pop("floors")
        thickness = data.get("defaults", {}).get("floor_thickness", 0.2)
        data["levels"] = [{
            "id": f.get("id"),
            "name": f.get("label") or f.get("name") or f.get("id", "Level"),
            "index": f.get("ord", 0),
            "elevation": f.get("z0", 0.0),
            "floor_to_floor_height":
                f.get("floor_to_floor_height")
                or (f.get("wall_height", 2.8) + thickness),
            "walls": f.get("walls", []),
            "openings": f.get("openings", []),
            "rooms": f.get("rooms", []),
            "voids": f.get("voids", []),
        } for f in legacy_floors]
        if "vertical_connections" in data and "stairs" not in data:
            old = data.pop("vertical_connections")
            data["stairs"] = [{
                "id": vc.get("id"),
                "from_level": vc.get("from_floor_id"),
                "to_level": vc.get("to_floor_id"),
                "footprint": vc.get("polygon", []),
                "start_point": [0, 0],  # downstream code should ignore unless needed
                "end_point": [0, 0],
                "direction": "up",
            } for vc in old]
        return data

    # Shape 3: v1 flat walls/openings/rooms
    if "walls" in data:
        data = dict(data)
        defaults = dict(data.get("defaults", {}) or {})
        thickness = defaults.get("floor_thickness", 0.2)
        wall_height = defaults.pop("wall_height", 2.8)
        data["defaults"] = defaults if defaults else {"floor_thickness": thickness}
        data["defaults"].setdefault("floor_thickness", thickness)
        data["levels"] = [{
            "id": "ground", "name": "Ground Floor",
            "index": 0, "elevation": 0.0,
            "floor_to_floor_height": wall_height + thickness,
            "walls": data.pop("walls"),
            "openings": data.pop("openings", []),
            "rooms": data.pop("rooms"),
            "voids": data.pop("voids", []),
        }]
        return data

    raise ValueError("plan.json has none of 'levels', 'floors', or 'walls' at root")


def load_shots(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    if "shots" not in data or not isinstance(data["shots"], list):
        raise ValueError("shots.json must have a top-level 'shots' array")
    pt = data.get("project_type", "house")
    if pt not in ("house", "interior"):
        raise ValueError(f"project_type must be 'house' or 'interior', got {pt!r}")
    for s in data["shots"]:
        _validate_shot(s)
    return data


def _validate_shot(s: dict[str, Any]) -> None:
    for req in ("id", "ord", "kind", "label", "camera"):
        if req not in s:
            raise ValueError(f"shot missing required field '{req}': {s!r}")
    if s["kind"] not in SHOTS_KINDS:
        raise ValueError(f"shot {s['id']}: unknown kind {s['kind']!r}")
    if s["kind"] == "room" and "room_id" not in s:
        raise ValueError(f"shot {s['id']}: room shot needs 'room_id'")
    cam = s["camera"]
    for req in ("move", "duration_s", "lens_mm", "fps"):
        if req not in cam:
            raise ValueError(f"shot {s['id']}.camera missing '{req}'")
    if cam["move"] not in CAMERA_MOVES:
        raise ValueError(f"shot {s['id']}.camera.move invalid: {cam['move']!r}")
    if cam["duration_s"] not in (5, 8):
        raise ValueError(f"shot {s['id']}.camera.duration_s must be 5 or 8")
    if s["kind"] == "stair_climb" and "stair_connection_id" not in s:
        raise ValueError(f"shot {s['id']}: stair_climb needs 'stair_connection_id'")


def default_style_preset() -> dict[str, str]:
    return {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }


# ---------- v2.0 convenience helpers ----------

def levels_of(plan: dict) -> list[dict]:
    return plan["levels"]


def level_by_id(plan: dict, level_id: str) -> dict:
    for l in plan["levels"]:
        if l["id"] == level_id:
            return l
    raise KeyError(f"level {level_id} not in plan")


def level_of_room(plan: dict, room_id: str) -> dict:
    for l in plan["levels"]:
        for r in l["rooms"]:
            if r["id"] == room_id:
                return l
    raise KeyError(f"room {room_id} not found in any level")


def all_walls(plan: dict) -> list[dict]:
    return [w for l in plan["levels"] for w in l["walls"]]


def all_openings(plan: dict) -> list[dict]:
    return [op for l in plan["levels"] for op in l.get("openings", [])]


def all_rooms(plan: dict) -> list[dict]:
    return [r for l in plan["levels"] for r in l["rooms"]]


# ---------- legacy aliases (keep imports working during the migration) ----------

floors_of = levels_of
floor_by_id = level_by_id
floor_of_room = level_of_room
