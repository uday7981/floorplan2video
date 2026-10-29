"""Load + lightly validate journey.json. Separate from plan_io so the schema
versions can evolve independently.

Journey shape (v2.0):
    {
      "schema_version": "2.0",
      "project_type": "house" | "interior",
      "style_preset": {...},
      "total_duration_s": 55.0,
      "segments": [{"id","ord","role","level_id","from_room_id","to_room_id",
                    "duration_s", "waypoints": [{"t","position","look_at","lens_mm"}]}],
      "boundaries": [{"id","ord","kind":"cad"|"photoreal"}, ...]  // N+1 entries
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEGMENT_ROLES = {"opening", "descent", "walkthrough", "stair", "exterior", "ending"}
BOUNDARY_KINDS = {"cad", "photoreal"}


def load_journey(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    for req in ("segments", "boundaries", "total_duration_s"):
        if req not in data:
            raise ValueError(f"journey.json missing '{req}'")
    if not isinstance(data["segments"], list) or not data["segments"]:
        raise ValueError("journey.segments must be a non-empty list")
    for s in data["segments"]:
        _validate_segment(s)
    for b in data["boundaries"]:
        _validate_boundary(b)
    n = len(data["segments"])
    if len(data["boundaries"]) != n + 1:
        raise ValueError(f"journey needs {n+1} boundaries for {n} segments, "
                         f"got {len(data['boundaries'])}")
    return data


def _validate_segment(s: dict) -> None:
    for req in ("id", "ord", "role", "duration_s", "waypoints"):
        if req not in s:
            raise ValueError(f"segment missing '{req}': {s!r}")
    if s["role"] not in SEGMENT_ROLES:
        raise ValueError(f"segment {s['id']}: unknown role {s['role']!r}")
    if s["duration_s"] not in (5, 8):
        raise ValueError(f"segment {s['id']}: duration_s must be 5 or 8")
    if not isinstance(s["waypoints"], list) or len(s["waypoints"]) < 2:
        raise ValueError(f"segment {s['id']}: needs ≥ 2 waypoints")
    for wp in s["waypoints"]:
        for req in ("t", "position", "look_at", "lens_mm"):
            if req not in wp:
                raise ValueError(f"segment {s['id']} waypoint missing '{req}'")


def _validate_boundary(b: dict) -> None:
    for req in ("id", "ord", "kind"):
        if req not in b:
            raise ValueError(f"boundary missing '{req}': {b!r}")
    if b["kind"] not in BOUNDARY_KINDS:
        raise ValueError(f"boundary {b['id']}: unknown kind {b['kind']!r}")
