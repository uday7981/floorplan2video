"""Combine per-floor extracted plan fragments into one multi-storey v2 plan.

The simplest multi-storey workflow:

  # 1) Crop each floor to its own image
  # 2) Extract each floor separately
  python -m extract --input ground.png --output ground.json --floor-id ground --floor-label "Ground Floor"
  python -m extract --input first.png  --output first.json  --floor-id first  --floor-label "First Floor"

  # 3) Merge, declaring the stair that connects them
  python scripts/merge_floors.py \\
      --floor ground=ground.json \\
      --floor first=first.json \\
      --wall-height 2.8 --floor-thickness 0.2 \\
      --stair id=s1,from=ground,to=first,polygon="4.5,0.5;5.5,0.5;5.5,2.5;4.5,2.5" \\
      --out plan.json

  # 4) Normal pipeline
  python scripts/make_shots.py --plan plan.json --out shots.json
  blender -b -P workers/blender/build.py -- --plan plan.json --shots shots.json --out /tmp/out

Rules:
- Argument order of --floor determines `ord`: first flag → ord 0 (ground), next → 1, etc.
- `z0` is derived: floor_N.z0 = sum(f.wall_height + floor_thickness for f in floors[:N]).
- `--stair` can be given multiple times. One stair_climb shot per connection.
- Each floor fragment keeps its own ids; we don't rename to force uniqueness,
  so make sure wall/opening/room ids don't clash across floors (prefix them in
  the extract prompt if needed, or rely on the extractor's natural ids per
  fragment — floor-scoped validation treats w1 on each floor as its own entity).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _parse_kv_list(spec: str) -> dict[str, str]:
    """Parse `k1=v1,k2=v2,k3=v3` with support for a `polygon=...` value that
    contains commas (so we treat polygon= specially via a regex split)."""
    # Pull out polygon=... first since it contains commas.
    poly = None
    m = re.search(r"(?:^|,)polygon=([^,][^$]*?)(?:,[a-z_]+=|$)", spec)
    rest = spec
    if m:
        poly = m.group(1)
        rest = spec.replace(m.group(0), ",", 1).strip(",")
    out: dict[str, str] = {}
    for part in rest.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"bad --stair fragment {part!r}; expected k=v")
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    if poly is not None:
        out["polygon"] = poly
    return out


def _parse_polygon(s: str) -> list[list[float]]:
    """Parse `x1,y1;x2,y2;x3,y3` into [[x1,y1], ...]."""
    pts: list[list[float]] = []
    for seg in s.split(";"):
        seg = seg.strip()
        if not seg:
            continue
        xy = [float(x) for x in seg.split(",")]
        if len(xy) != 2:
            raise ValueError(f"bad polygon point {seg!r}; expected x,y")
        pts.append(xy)
    if len(pts) < 3:
        raise ValueError(f"polygon needs ≥ 3 points, got {len(pts)}")
    return pts


def build_plan(
    floors: list[tuple[str, Path]],
    wall_height: float,
    floor_thickness: float,
    stairs: list[dict],
) -> dict:
    # Build the floor envelope list from each fragment.
    floor_entries: list[dict] = []
    cumulative_z = 0.0
    for ord_, (fid, fpath) in enumerate(floors):
        frag = json.loads(fpath.read_text())
        hint = frag.pop("_floor", None) or {}
        label = hint.get("label") or f"Floor {ord_}"
        if hint.get("id") and hint["id"] != fid:
            print(f"[merge_floors] warning: --floor id {fid!r} doesn't match "
                  f"the fragment's _floor.id {hint['id']!r}; using {fid!r}",
                  file=sys.stderr)
        floor_entries.append({
            "id": fid,
            "ord": ord_,
            "z0": round(cumulative_z, 2),
            "wall_height": wall_height,
            "label": label,
            "walls": frag.get("walls", []),
            "openings": frag.get("openings", []),
            "rooms": frag.get("rooms", []),
        })
        cumulative_z += wall_height + floor_thickness

    # Build vertical_connections.
    vcs: list[dict] = []
    for s in stairs:
        for req in ("id", "from", "to", "polygon"):
            if req not in s:
                raise ValueError(f"--stair missing {req}: {s!r}")
        vcs.append({
            "id": s["id"],
            "kind": s.get("kind", "stair"),
            "from_floor_id": s["from"],
            "to_floor_id": s["to"],
            "polygon": _parse_polygon(s["polygon"]),
        })

    # Carry over meta/defaults from the first fragment that has them.
    first = json.loads(floors[0][1].read_text())
    meta = first.get("meta") or {
        "scale_source": "user_input", "confidence": 0.8, "warnings": []
    }

    return {
        "schema_version": "2.0",
        "units": "m",
        "meta": meta,
        "defaults": {"wall_height": wall_height, "floor_thickness": floor_thickness},
        "floors": floor_entries,
        "vertical_connections": vcs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="merge_floors",
                                 formatter_class=argparse.RawTextHelpFormatter,
                                 description=__doc__)
    ap.add_argument("--floor", action="append", required=True,
                    metavar="FID=PATH",
                    help="repeat per floor; argument order sets ord (0, 1, …)")
    ap.add_argument("--wall-height", type=float, default=2.8)
    ap.add_argument("--floor-thickness", type=float, default=0.2)
    ap.add_argument("--stair", action="append", default=[],
                    metavar="id=…,from=…,to=…,polygon=x,y;x,y;x,y",
                    help="one vertical_connection; repeat for multiple stairs/voids")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    # Parse --floor fid=path
    floors: list[tuple[str, Path]] = []
    for spec in args.floor:
        if "=" not in spec:
            print(f"[merge_floors] bad --floor {spec!r}; expected FID=PATH", file=sys.stderr)
            return 2
        fid, pstr = spec.split("=", 1)
        floors.append((fid.strip(), Path(pstr.strip())))

    stairs = [_parse_kv_list(s) for s in args.stair]

    plan = build_plan(floors, args.wall_height, args.floor_thickness, stairs)

    # Validate via plan_schema before writing so garbage never leaves this CLI.
    try:
        from plan_schema import Plan
        Plan.model_validate(plan)
    except Exception as e:
        print(f"[merge_floors] validation failed: {e}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out} with {len(floors)} floor(s), "
          f"{len(stairs)} vertical connection(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
