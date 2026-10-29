"""Generate a sensible default shots.json from a plan.json per TRD defaults.

    python scripts/make_shots.py \\
        --plan fixtures/plans/screenshot-01/extracted.json \\
        --out  fixtures/plans/screenshot-01/shots.json \\
        [--project-type house]  (default: house)

Rules:
  - One opening shot (crane, 5s, 35mm)
  - One shot per room over 4 m² (dolly, 5s if area < 20m² else 8s, 18mm)
  - One stair_climb shot per vertical_connection between adjacent floors
    (stair move, 5s, 24mm)
  - Shot order: opening → floor0 rooms → stair_climb → floor1 rooms →
    stair_climb → … → exterior (house only)
  - Accepts v2 plans (floors[]) and v1 plans (flat walls/openings/rooms —
    auto-wrapped into a single ground floor).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MIN_ROOM_AREA_M2_FOR_SHOT = 4.0
BIG_ROOM_AREA_M2 = 20.0


def _polygon_area(points) -> float:
    pts = list(points)
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    a = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2


def _floors_of(plan: dict) -> list[dict]:
    """Normalise to a list of floors regardless of input schema version."""
    if "floors" in plan:
        return sorted(plan["floors"], key=lambda f: int(f["ord"]))
    # v1 shape → single ground floor wrapper
    return [{
        "id": "ground",
        "ord": 0,
        "z0": 0.0,
        "wall_height": plan.get("defaults", {}).get("wall_height", 2.8),
        "label": "Ground Floor",
        "walls": plan.get("walls", []),
        "openings": plan.get("openings", []),
        "rooms": plan.get("rooms", []),
    }]


def build_shots(plan: dict, project_type: str) -> dict:
    style = {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }
    shots: list[dict] = []
    ord_ = 0

    # 1) Opening shot — always first.
    shots.append({
        "id": "s_opening",
        "ord": ord_,
        "kind": "opening",
        "label": "Welcome",
        "camera": {"move": "crane", "duration_s": 5, "lens_mm": 35, "fps": 24},
    })
    ord_ += 1

    # 2) For each floor in order: all its rooms, then a stair_climb to the
    #    next floor (if any). Running room index for stable labels.
    floors = _floors_of(plan)
    vc_by_lower = _vcs_by_lower_floor(plan, floors)
    room_counter = 0

    for i, floor in enumerate(floors):
        for room in floor["rooms"]:
            area = _polygon_area(room["polygon"])
            if area < MIN_ROOM_AREA_M2_FOR_SHOT:
                continue
            room_counter += 1
            duration = 8 if area >= BIG_ROOM_AREA_M2 else 5
            shots.append({
                "id": f"s_f{floor['id']}_r{room_counter:02d}",
                "ord": ord_,
                "kind": "room",
                "room_id": room["id"],
                "floor_id": floor["id"],
                "label": f"{room_counter:02d} {room['name']}",
                "camera": {"move": "dolly", "duration_s": duration,
                           "lens_mm": 18, "fps": 24},
            })
            ord_ += 1

        # Stair climb to the next floor up, if there is one.
        for vc in vc_by_lower.get(floor["id"], []):
            shots.append({
                "id": f"s_stair_{vc['id']}",
                "ord": ord_,
                "kind": "stair_climb",
                "stair_connection_id": vc["id"],
                "label": f"Up to {_label_of_floor_id(floors, vc['to_floor_id'])}",
                "camera": {"move": "stair", "duration_s": 5, "lens_mm": 24, "fps": 24},
            })
            ord_ += 1

    # 3) Exterior orbit — house only, after all interiors.
    if project_type == "house":
        shots.append({
            "id": "s_exterior",
            "ord": ord_,
            "kind": "exterior",
            "label": "Exterior",
            "camera": {"move": "orbit", "duration_s": 8, "lens_mm": 28, "fps": 24},
        })

    return {
        "schema_version": "2.0" if "floors" in plan else "1.0",
        "project_type": project_type,
        "style_preset": style,
        "shots": shots,
    }


def _vcs_by_lower_floor(plan: dict, floors: list[dict]) -> dict[str, list[dict]]:
    """Map floor_id → list of vertical_connections whose lower endpoint is
    that floor. 'Lower' = the floor with the smaller ord."""
    ord_by_id = {f["id"]: int(f["ord"]) for f in floors}
    out: dict[str, list[dict]] = {}
    for vc in plan.get("vertical_connections", []):
        a, b = vc["from_floor_id"], vc["to_floor_id"]
        if a not in ord_by_id or b not in ord_by_id:
            continue
        lower_id = a if ord_by_id[a] < ord_by_id[b] else b
        out.setdefault(lower_id, []).append(vc)
    # Deterministic ordering (vc id)
    for v in out.values():
        v.sort(key=lambda vc: vc["id"])
    return out


def _label_of_floor_id(floors: list[dict], fid: str) -> str:
    for f in floors:
        if f["id"] == fid:
            return f.get("label", fid)
    return fid


def main() -> int:
    ap = argparse.ArgumentParser(prog="make_shots")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--project-type", choices=["house", "interior"], default="house")
    args = ap.parse_args()

    plan = json.loads(args.plan.read_text())
    doc = build_shots(plan, args.project_type)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out} with {len(doc['shots'])} shots", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
