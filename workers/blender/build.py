"""Main entry — invoked by Blender:

    blender -b --factory-startup -P workers/blender/build.py -- \\
        --plan path/to/plan.json \\
        --shots path/to/shots.json \\
        --out /tmp/out \\
        [--only s_r01 --only s_exterior]

Outputs per shot (under <out>/<render_hash>/):
    driving.mp4   Workbench solid, 1280x720 24fps, animated
    start.png     EEVEE Next + Freestyle, flat white materials, frame 1
    clay.png      Workbench clay shading, last frame

Fully-cached shots (all three files present + non-empty) are skipped.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Make the blender_worker package importable when run as `blender -P` (no venv).
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from blender_worker import cameras, materials, render, scene      # noqa: E402
from blender_worker.hashing import ensure_shot_dir, is_fully_cached, render_hash  # noqa: E402
from blender_worker.plan_io import default_style_preset, load_plan, load_shots    # noqa: E402

log = logging.getLogger("build")


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--shots", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--only", action="append", default=None,
                    help="Render only these shot ids (repeatable); default = all")
    return ap.parse_args(argv)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[build] %(message)s")
    args = parse_args()

    plan = load_plan(args.plan)
    shots_doc = load_shots(args.shots)
    preset = shots_doc.get("style_preset") or default_style_preset()
    project_type = shots_doc.get("project_type", "house")

    out_root = args.out
    out_root.mkdir(parents=True, exist_ok=True)

    shots = shots_doc["shots"]
    if args.only:
        shots = [s for s in shots if s["id"] in args.only]
    log.info(f"will render {len(shots)} shot(s) to {out_root} (project_type={project_type})")

    t_total = time.time()
    for shot in sorted(shots, key=lambda s: s["ord"]):
        h = render_hash(plan, shot)
        if is_fully_cached(out_root, h):
            log.info(f"[skip] {shot['id']} already cached at {h[:8]}")
            continue

        shot_dir = ensure_shot_dir(out_root, h)
        log.info(f"[shot] {shot['id']} kind={shot['kind']} hash={h[:8]} -> {shot_dir}")

        t_shot = time.time()
        scene.reset_scene()
        mats = materials.make_materials(preset)
        scene.build_walls_and_openings(plan, mats["wall"])
        slabs = scene.build_floor_slabs(plan, mats["floor"])
        scene.build_stairs_and_voids(plan, slabs, mats["trim"])
        if project_type == "house":
            scene.build_roof(plan, mats["trim"])
        scene.build_lights(plan)
        cameras.build_camera_for_shot(plan, shot)

        render.render_driving(shot_dir / "driving.mp4")
        render.render_start_frame(shot_dir / "start.png")
        render.render_clay_frame(shot_dir / "clay.png")

        log.info(f"[done] {shot['id']} in {time.time() - t_shot:.1f}s")

    log.info(f"[total] {time.time() - t_total:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
