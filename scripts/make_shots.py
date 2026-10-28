"""Generate a sensible default shots.json from a plan.json per TRD defaults.

    python scripts/make_shots.py \\
        --plan fixtures/plans/screenshot-01/extracted.json \\
        --out  fixtures/plans/screenshot-01/shots.json \\
        [--project-type house]  (default: house)

Rules:
  - One opening shot (crane, 5s, 35mm)
  - One shot per room over 4 m² (dolly, 5s if area < 20m² else 8s, 18mm)
  - One exterior orbit shot for project_type=house (orbit, 8s, 28mm)
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


def build_shots(plan: dict, project_type: str) -> dict:
    shots: list[dict] = []
    ord_ = 0
    style = {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }

    shots.append({
        "id": "s_opening",
        "ord": ord_,
        "kind": "opening",
        "label": "Welcome",
        "camera": {"move": "crane", "duration_s": 5, "lens_mm": 35, "fps": 24},
    })
    ord_ += 1

    for i, room in enumerate(plan.get("rooms", []), start=1):
        area = _polygon_area(room["polygon"])
        if area < MIN_ROOM_AREA_M2_FOR_SHOT:
            continue
        duration = 8 if area >= BIG_ROOM_AREA_M2 else 5
        shots.append({
            "id": f"s_r{i:02d}",
            "ord": ord_,
            "kind": "room",
            "room_id": room["id"],
            "label": f"{i:02d} {room['name']}",
            "camera": {"move": "dolly", "duration_s": duration,
                       "lens_mm": 18, "fps": 24},
        })
        ord_ += 1

    if project_type == "house":
        shots.append({
            "id": "s_exterior",
            "ord": ord_,
            "kind": "exterior",
            "label": "Exterior",
            "camera": {"move": "orbit", "duration_s": 8, "lens_mm": 28, "fps": 24},
        })

    return {
        "schema_version": "1.0",
        "project_type": project_type,
        "style_preset": style,
        "shots": shots,
    }


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
