"""Load + lightly validate plan.json and shots.json.

Plan JSON shape = packages/plan_schema.Plan (we only need to READ it here,
so we parse as plain dicts and keep this module bpy-free + plan_schema-free).

Shots JSON shape (v1):
    {
      "schema_version": "1.0",
      "project_type": "house" | "interior",
      "style_preset": {
        "materials": "<comma string>",   # e.g. "oak, black aluminium, natural white"
        "light": "<colour temp>",         # e.g. "3000K"
        "setting": "<background>",        # e.g. "a beautiful forest"
      },
      "source_plan_image_path": "...png",  # optional; used by the opening-shot desk
      "shots": [
        {
          "id": "s1",
          "ord": 0,
          "kind": "opening" | "room" | "exterior",
          "label": "01 Sitting Room",
          "room_id": "R1",                 # required if kind == "room"
          "camera": {
            "move": "dolly" | "pan" | "crane" | "orbit",
            "duration_s": 5,
            "lens_mm": 18,
            "fps": 24
          }
        }
      ]
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SHOTS_KINDS = {"opening", "room", "exterior", "stair_climb"}
CAMERA_MOVES = {"dolly", "pan", "crane", "orbit", "stair"}


def load_plan(path: Path) -> dict[str, Any]:
    """Load plan.json. Accepts both v2 (floors[]) and v1 (flat walls/openings/
    rooms); v1 is auto-wrapped into a single ground floor so downstream code
    only ever sees the floors[] shape."""
    data = json.loads(Path(path).read_text())
    if "defaults" not in data:
        raise ValueError("plan.json missing 'defaults'")
    if "floors" in data:
        if not isinstance(data["floors"], list) or not data["floors"]:
            raise ValueError("plan.json 'floors' must be a non-empty list")
        for f in data["floors"]:
            for req in ("id", "ord", "z0", "wall_height", "walls", "rooms"):
                if req not in f:
                    raise ValueError(f"floor {f.get('id','?')} missing '{req}'")
    else:
        # v1 shape — wrap into a single ground floor so build.py always sees
        # the v2 structure.
        if "walls" not in data or "rooms" not in data:
            raise ValueError("plan.json missing 'walls'/'rooms' (and no 'floors')")
        data["floors"] = [{
            "id": "ground",
            "ord": 0,
            "z0": 0.0,
            "wall_height": data["defaults"].get("wall_height", 2.8),
            "label": "Ground Floor",
            "walls": data.pop("walls"),
            "openings": data.pop("openings", []),
            "rooms": data.pop("rooms"),
        }]
    data.setdefault("vertical_connections", [])
    return data


# ---------- helpers so build.py / scene.py / cameras.py stay floor-agnostic ----------

def floors_of(plan: dict) -> list[dict]:
    """Return the floors list (always present after load_plan)."""
    return plan["floors"]


def floor_by_id(plan: dict, floor_id: str) -> dict:
    for f in plan["floors"]:
        if f["id"] == floor_id:
            return f
    raise KeyError(f"floor {floor_id} not in plan")


def floor_of_room(plan: dict, room_id: str) -> dict:
    for f in plan["floors"]:
        for r in f["rooms"]:
            if r["id"] == room_id:
                return f
    raise KeyError(f"room {room_id} not found in any floor")


def all_walls(plan: dict) -> list[dict]:
    return [w for f in plan["floors"] for w in f["walls"]]


def all_openings(plan: dict) -> list[dict]:
    return [op for f in plan["floors"] for op in f.get("openings", [])]


def all_rooms(plan: dict) -> list[dict]:
    return [r for f in plan["floors"] for r in f["rooms"]]


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
        # TRD: 5 s default, 8 s for large spaces — we don't *forbid* others
        # but warn by raising; relax here if a project needs it.
        raise ValueError(f"shot {s['id']}.camera.duration_s must be 5 or 8")
    if s["kind"] == "stair_climb" and "stair_connection_id" not in s:
        raise ValueError(f"shot {s['id']}: stair_climb needs 'stair_connection_id'")


def default_style_preset() -> dict[str, str]:
    """TRD default style preset (used when shots.json omits one)."""
    return {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }
