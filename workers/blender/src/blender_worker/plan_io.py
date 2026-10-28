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


SHOTS_KINDS = {"opening", "room", "exterior"}
CAMERA_MOVES = {"dolly", "pan", "crane", "orbit"}


def load_plan(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    for required in ("walls", "rooms", "defaults"):
        if required not in data:
            raise ValueError(f"plan.json missing '{required}'")
    return data


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


def default_style_preset() -> dict[str, str]:
    """TRD default style preset (used when shots.json omits one)."""
    return {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }
