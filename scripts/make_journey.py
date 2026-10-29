"""Build a journey.json (single continuous camera path, split into segments)
from a v2.0 plan.json.

    python scripts/make_journey.py \\
        --plan fixtures/plans/<name>/extracted.json \\
        --out  fixtures/plans/<name>/journey.json \\
        [--project-type house | interior]      (default house)
        [--walkthrough-speed 0.7]              (m/s indoors)

Journey structure (v2.0):
  - schema_version: "2.0"
  - total_duration_s
  - segments[]: ord, role (opening|descent|walkthrough|stair|exterior|ending),
                level_id, from_room_id, to_room_id, duration_s, waypoints[]
                where each waypoint is {t, position:[x,y,z], look_at:[x,y,z], lens_mm}
  - boundaries[]: ord (0..N), kind (cad|photoreal). Boundary ord=0 is the
                  opening frame; the last boundary is after the final segment.

Current ordering heuristic (v2.B, intentionally simple):
  - Visit rooms in plan order per level (level.rooms[*] filtered to area ≥ 4 m²).
  - After the last room of each level, add a `stair` segment to the next level.
  - Opening + descent live before the first room. Ending lives after the last.
Future (v2.C+): replace with proper room-adjacency Hamiltonian routing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


MIN_ROOM_AREA_M2 = 4.0
BIG_ROOM_AREA_M2 = 20.0
EYE_HEIGHT_M = 1.6
WALK_SPEED_MS = 0.7
STAIR_SPEED_MS = 0.5
LENS_INDOOR_MM = 18
LENS_STAIR_MM = 24
LENS_OPENING_MM = 35
LENS_EXTERIOR_MM = 28


def _polygon_area(pts) -> float:
    pts = list(pts)
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    a = 0.0
    for i in range(len(pts) - 1):
        a += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return abs(a) / 2


def _centroid(pts) -> tuple[float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _bbox_center_and_diag(walls) -> tuple[tuple[float, float], float]:
    xs = [c for w in walls for c in (w["a"][0], w["b"][0])]
    ys = [c for w in walls for c in (w["a"][1], w["b"][1])]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    return (cx, cy), diag


def _opening_world(wall, op) -> tuple[float, float]:
    """World (x,y) of an opening's centre along its wall."""
    ax, ay = wall["a"]
    bx, by = wall["b"]
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy) or 1.0
    t = op["offset"] / length
    return ax + dx * t, ay + dy * t


def _main_entrance(plan: dict) -> tuple[dict, dict, dict] | None:
    """Return (level, wall, opening) for the one main_entrance across the plan."""
    for lvl in plan["levels"]:
        for op in lvl.get("openings", []):
            if op.get("main_entrance"):
                wall = next(w for w in lvl["walls"] if w["id"] == op["wall_id"])
                return lvl, wall, op
    return None


def _nearest_opening_on_wall_of_room(level: dict, room: dict) -> dict | None:
    """Pick any opening on a wall adjacent to this room. Used to compute an
    'entry doorway' for the camera's walkthrough of this room."""
    rpoly = room["polygon"]
    best = None
    best_dist = float("inf")
    for op in level.get("openings", []):
        wall = next((w for w in level["walls"] if w["id"] == op["wall_id"]), None)
        if wall is None:
            continue
        ox, oy = _opening_world(wall, op)
        # Distance from opening to nearest polygon edge
        d = min(_point_segment_dist((ox, oy), rpoly[i], rpoly[(i + 1) % len(rpoly)])
                for i in range(len(rpoly)))
        if d < best_dist:
            best_dist = d
            best = op
    return best


def _point_segment_dist(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


# ---------- segment builders ----------

def _opening_segment(plan: dict, idx: int) -> dict:
    """Top-down → extruded 3D → cutaway reveal, cranes down to building center."""
    center, diag = _bbox_center_and_diag([w for l in plan["levels"] for w in l["walls"]])
    is_multi = len(plan["levels"]) > 1
    duration_s = 8 if is_multi else 5
    top_z = max(l["elevation"] + l["floor_to_floor_height"] for l in plan["levels"])
    start_z = top_z + diag * 1.2         # high above the building
    end_z = top_z + diag * 0.4           # closer, ready to descend
    return {
        "id": f"seg_{idx:03d}",
        "ord": idx,
        "role": "opening",
        "level_id": None,
        "from_room_id": None,
        "to_room_id": None,
        "duration_s": duration_s,
        "waypoints": [
            {"t": 0.0, "position": [center[0], center[1], start_z],
             "look_at": [center[0], center[1], 0.0], "lens_mm": LENS_OPENING_MM},
            {"t": float(duration_s), "position": [center[0], center[1], end_z],
             "look_at": [center[0], center[1], 0.0], "lens_mm": LENS_OPENING_MM},
        ],
    }


def _descent_segment(plan: dict, idx: int) -> dict:
    """Glide down at an angle to the main entrance, settle at eye height."""
    entrance = _main_entrance(plan)
    if entrance is None:
        raise ValueError("plan has no main_entrance; can't build descent segment")
    lvl, wall, op = entrance
    ox, oy = _opening_world(wall, op)
    # Approach from the outside — perpendicular to the wall, 3m out
    dx, dy = wall["b"][0] - wall["a"][0], wall["b"][1] - wall["a"][1]
    length = math.hypot(dx, dy) or 1.0
    # Outward normal: rotate wall direction -90° (to the right of the wall when walking a→b)
    # Pick whichever side faces away from the room centroid; simplest heuristic: use the
    # exterior-wall normal that points away from the plan centre.
    center, _ = _bbox_center_and_diag([w for l in plan["levels"] for w in l["walls"]])
    nx, ny = -dy / length, dx / length
    # Flip the normal if it points toward the centre
    if (ox + nx * 1.0 - center[0]) ** 2 + (oy + ny * 1.0 - center[1]) ** 2 < \
       (ox - nx * 1.0 - center[0]) ** 2 + (oy - ny * 1.0 - center[1]) ** 2:
        nx, ny = -nx, -ny
    approach_x, approach_y = ox + nx * 3.0, oy + ny * 3.0
    z_floor = float(lvl["elevation"]) + EYE_HEIGHT_M
    z_approach = z_floor + 2.5          # start above eye-level, come down
    return {
        "id": f"seg_{idx:03d}",
        "ord": idx,
        "role": "descent",
        "level_id": lvl["id"],
        "from_room_id": None,
        "to_room_id": None,
        "duration_s": 5,
        "waypoints": [
            {"t": 0.0, "position": [approach_x, approach_y, z_approach],
             "look_at": [ox, oy, z_floor], "lens_mm": LENS_INDOOR_MM},
            {"t": 5.0, "position": [approach_x, approach_y, z_floor],
             "look_at": [ox, oy, z_floor], "lens_mm": LENS_INDOOR_MM},
        ],
    }


def _room_segment(plan: dict, level: dict, room: dict, idx: int,
                  prev_room_id: str | None, next_room_id: str | None) -> dict:
    cx, cy = _centroid(room["polygon"])
    z = float(level["elevation"]) + EYE_HEIGHT_M
    # Entry doorway: pick an opening nearest the room polygon
    entry_op = _nearest_opening_on_wall_of_room(level, room)
    if entry_op is not None:
        wall = next(w for w in level["walls"] if w["id"] == entry_op["wall_id"])
        ex, ey = _opening_world(wall, entry_op)
        # Pull the camera 0.6m into the room from the doorway
        rx, ry = cx - ex, cy - ey
        rlen = math.hypot(rx, ry) or 1.0
        ex2, ey2 = ex + rx / rlen * 0.6, ey + ry / rlen * 0.6
    else:
        ex2, ey2 = cx - 1.0, cy
    area = _polygon_area(room["polygon"])
    duration_s = 8 if area >= BIG_ROOM_AREA_M2 else 5
    return {
        "id": f"seg_{idx:03d}",
        "ord": idx,
        "role": "walkthrough",
        "level_id": level["id"],
        "from_room_id": prev_room_id,
        "to_room_id": room["id"],
        "duration_s": duration_s,
        "waypoints": [
            {"t": 0.0, "position": [ex2, ey2, z],
             "look_at": [cx, cy, z], "lens_mm": LENS_INDOOR_MM},
            {"t": float(duration_s / 2), "position": [cx, cy, z],
             "look_at": [cx + 1.0, cy, z], "lens_mm": LENS_INDOOR_MM},
            {"t": float(duration_s), "position": [cx, cy, z],
             "look_at": [cx, cy + 1.0, z], "lens_mm": LENS_INDOOR_MM},
        ],
    }


def _stair_segment(plan: dict, stair: dict, idx: int) -> dict:
    """Walk from stair.start_point at from_level elevation to end_point at to_level."""
    from_lvl = next(l for l in plan["levels"] if l["id"] == stair["from_level"])
    to_lvl = next(l for l in plan["levels"] if l["id"] == stair["to_level"])
    z_lo = float(from_lvl["elevation"]) + EYE_HEIGHT_M
    z_hi = float(to_lvl["elevation"]) + EYE_HEIGHT_M
    sx, sy = stair["start_point"]
    ex, ey = stair["end_point"]
    return {
        "id": f"seg_{idx:03d}",
        "ord": idx,
        "role": "stair",
        "level_id": from_lvl["id"],
        "from_room_id": None,
        "to_room_id": None,
        "duration_s": 5,
        "waypoints": [
            {"t": 0.0, "position": [sx, sy, z_lo],
             "look_at": [ex, ey, z_hi], "lens_mm": LENS_STAIR_MM},
            {"t": 5.0, "position": [ex, ey, z_hi],
             "look_at": [ex, ey, z_hi], "lens_mm": LENS_STAIR_MM},
        ],
    }


def _exterior_segment(plan: dict, idx: int) -> dict:
    """House ending: 8s orbit around the whole building at mid-wall height."""
    center, diag = _bbox_center_and_diag([w for l in plan["levels"] for w in l["walls"]])
    top_z = max(l["elevation"] + l["floor_to_floor_height"] for l in plan["levels"])
    radius = max(diag * 0.9, 6.0)
    cam_z = top_z * 0.6 + 2.0
    aim_z = top_z / 2
    return {
        "id": f"seg_{idx:03d}",
        "ord": idx,
        "role": "exterior",
        "level_id": None,
        "from_room_id": None,
        "to_room_id": None,
        "duration_s": 8,
        "waypoints": [
            {"t": 0.0, "position": [center[0] + radius, center[1], cam_z],
             "look_at": [center[0], center[1], aim_z], "lens_mm": LENS_EXTERIOR_MM},
            {"t": 4.0, "position": [center[0], center[1] + radius, cam_z],
             "look_at": [center[0], center[1], aim_z], "lens_mm": LENS_EXTERIOR_MM},
            {"t": 8.0, "position": [center[0] - radius, center[1], cam_z],
             "look_at": [center[0], center[1], aim_z], "lens_mm": LENS_EXTERIOR_MM},
        ],
    }


def _ending_pullback(plan: dict, last_room: dict, level: dict, idx: int) -> dict:
    """Interior ending: slow pull-back in the last visited room."""
    cx, cy = _centroid(last_room["polygon"])
    z = float(level["elevation"]) + EYE_HEIGHT_M
    return {
        "id": f"seg_{idx:03d}",
        "ord": idx,
        "role": "ending",
        "level_id": level["id"],
        "from_room_id": last_room["id"],
        "to_room_id": None,
        "duration_s": 5,
        "waypoints": [
            {"t": 0.0, "position": [cx, cy, z],
             "look_at": [cx + 1.0, cy, z], "lens_mm": LENS_INDOOR_MM},
            {"t": 5.0, "position": [cx - 2.0, cy, z],
             "look_at": [cx + 1.0, cy, z], "lens_mm": LENS_INDOOR_MM},
        ],
    }


# ---------- main builder ----------

def build_journey(plan: dict, project_type: str) -> dict:
    style = {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }

    levels_sorted = sorted(plan["levels"], key=lambda l: int(l["index"]))
    stairs_from = {}  # level_id → list of stairs leaving that level
    for st in plan.get("stairs", []):
        from_lvl = next(l for l in plan["levels"] if l["id"] == st["from_level"])
        to_lvl = next(l for l in plan["levels"] if l["id"] == st["to_level"])
        lower = from_lvl if int(from_lvl["index"]) < int(to_lvl["index"]) else to_lvl
        stairs_from.setdefault(lower["id"], []).append(st)

    segments: list[dict] = []
    idx = 0

    # 1. Opening
    segments.append(_opening_segment(plan, idx))
    idx += 1

    # 2. Descent
    segments.append(_descent_segment(plan, idx))
    idx += 1

    # 3. Walkthrough — per level in order, rooms in plan order (≥ 4 m²).
    last_room = None
    last_level = None
    for lvl in levels_sorted:
        prev_room_id = None
        rooms = [r for r in lvl["rooms"] if _polygon_area(r["polygon"]) >= MIN_ROOM_AREA_M2]
        for i, room in enumerate(rooms):
            next_room_id = rooms[i + 1]["id"] if i + 1 < len(rooms) else None
            segments.append(_room_segment(plan, lvl, room, idx, prev_room_id, next_room_id))
            idx += 1
            prev_room_id = room["id"]
            last_room = room
            last_level = lvl
        # Stair up to the next level
        for st in stairs_from.get(lvl["id"], []):
            segments.append(_stair_segment(plan, st, idx))
            idx += 1

    # 4. Ending
    if project_type == "house":
        segments.append(_exterior_segment(plan, idx))
        idx += 1
    elif last_room is not None and last_level is not None:
        segments.append(_ending_pullback(plan, last_room, last_level, idx))
        idx += 1

    # 5. Boundaries: one at the start, one after every segment. Boundary 0 is
    #    the CAD opening frame; all others are photoreal.
    boundaries = [{"id": f"bnd_{i:03d}", "ord": i,
                   "kind": "cad" if i == 0 else "photoreal"}
                  for i in range(len(segments) + 1)]

    return {
        "schema_version": "2.0",
        "project_type": project_type,
        "style_preset": style,
        "total_duration_s": sum(s["duration_s"] for s in segments),
        "segments": segments,
        "boundaries": boundaries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="make_journey")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--project-type", choices=["house", "interior"], default="house")
    args = ap.parse_args()

    plan_raw = json.loads(args.plan.read_text())
    # Normalise via Pydantic so legacy (v1 / v2-M8) inputs auto-upgrade to v2.0.
    try:
        from plan_schema import Plan
        plan = Plan.model_validate(plan_raw).model_dump(mode="json")
    except Exception as e:
        print(f"[make_journey] plan validation failed: {e}", file=sys.stderr)
        return 1

    doc = build_journey(plan, args.project_type)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}  {len(doc['segments'])} segments  "
          f"total={doc['total_duration_s']}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
