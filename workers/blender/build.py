"""Main entry — invoked by Blender:

    blender -b --factory-startup -P workers/blender/build.py -- \\
        --plan path/to/plan.json \\
        --journey path/to/journey.json \\
        --out /tmp/out \\
        [--only-seg 0 --only-seg 3]        (default: all segments)

Outputs:
    <out>/seg_{ord}/driving.mp4   Workbench solid, 1280x720 24fps, segment's frame range
    <out>/seg_{ord}/clay_end.png  Workbench clay shading, last frame of the segment
    <out>/boundary_{ord}.png      Camera frame at the boundary (ord 0 = CAD style, rest Workbench)
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from blender_worker import cameras, materials, render, scene          # noqa: E402
from blender_worker.journey_io import load_journey                     # noqa: E402
from blender_worker.plan_io import default_style_preset, load_plan     # noqa: E402

log = logging.getLogger("build")


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--journey", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--only-seg", type=int, action="append", default=None,
                    help="Render only these segment ords; default = all")
    return ap.parse_args(argv)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[build] %(message)s")
    args = parse_args()

    plan = load_plan(args.plan)
    journey = load_journey(args.journey)
    preset = journey.get("style_preset") or default_style_preset()
    project_type = journey.get("project_type", "house")

    out_root = args.out
    out_root.mkdir(parents=True, exist_ok=True)
    log.info(f"journey: {len(journey['segments'])} segments · "
             f"{journey['total_duration_s']}s · {project_type}")

    t_build = time.time()
    scene.reset_scene()
    mats = materials.make_materials(preset)
    scene.build_walls_and_openings(plan, mats["wall"])
    slabs = scene.build_floor_slabs(plan, mats["floor"])
    scene.build_stairs_and_voids(plan, slabs, mats["trim"])
    if project_type == "house":
        scene.build_roof(plan, mats["trim"])
    scene.build_lights(plan)
    cameras.build_journey_camera(journey)
    log.info(f"[scene+camera] {time.time() - t_build:.1f}s")

    segs = journey["segments"]
    if args.only_seg is not None:
        wanted = set(args.only_seg)
        segs = [s for s in segs if int(s["ord"]) in wanted]

    t_total = time.time()
    for seg in sorted(segs, key=lambda s: int(s["ord"])):
        seg_dir = out_root / f"seg_{int(seg['ord']):03d}"
        seg_dir.mkdir(parents=True, exist_ok=True)
        first, last = cameras.segment_frame_range(journey, int(seg["ord"]))
        log.info(f"[seg {seg['ord']:>3} · {seg['role']:>11}] frames {first}-{last}  "
                 f"→ {seg_dir}")

        t_shot = time.time()
        render.render_driving_range(seg_dir / "driving.mp4", first, last)
        render.render_clay_frame_at(seg_dir / "clay_end.png", last)
        log.info(f"  done in {time.time() - t_shot:.1f}s")

    for bnd in sorted(journey["boundaries"], key=lambda b: int(b["ord"])):
        if args.only_seg is not None:
            touched = set(args.only_seg)
            if int(bnd["ord"]) not in touched and int(bnd["ord"]) - 1 not in touched:
                continue
        frame = cameras.boundary_frame_number(journey, int(bnd["ord"]))
        out_file = out_root / f"boundary_{int(bnd['ord']):03d}.png"
        if bnd["kind"] == "cad":
            render.render_cad_frame_at(out_file, frame)
        else:
            render.render_clay_frame_at(out_file, frame)
        log.info(f"[boundary {bnd['ord']:>3}] kind={bnd['kind']:>9}  frame={frame}  → {out_file.name}")

    log.info(f"[total] {time.time() - t_total:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
