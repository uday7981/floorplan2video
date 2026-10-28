"""RQ entry point for the render queue.

Runs on the RunPod GPU pod. Downloads plan.json + shots.json from storage,
invokes build.py via subprocess (Blender's bundled Python can't use the venv),
then uploads driving.mp4/start.png/clay.png per shot and writes paths back
to the shots table.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

from fpv_common.config import load_config
from fpv_common.db import db_from_config
from fpv_common.jobs import JobContext, run_job
from fpv_common.storage import storage_from_config

log = logging.getLogger(__name__)
BLENDER_BIN = os.environ.get("BLENDER_BIN", "blender")
BUILD_PY = Path(__file__).resolve().parents[3] / "build.py"


def run(*, job_id: str, project_id: str) -> None:
    cfg = load_config()
    db = db_from_config(cfg)
    storage = storage_from_config(cfg)

    ctx = JobContext(job_id=UUID(job_id), project_id=UUID(project_id),
                     job_type="render", ref_id=None)

    def work():
        with tempfile.TemporaryDirectory(prefix="render_") as tmp:
            root = Path(tmp)
            plan_row = db.fetchrow(
                "select plan_json from plans where project_id=%s and approved=true "
                "order by version desc limit 1",
                (project_id,),
            )
            if not plan_row or not plan_row.get("plan_json"):
                raise RuntimeError("no approved plan with plan_json")
            plan_json = plan_row["plan_json"] if isinstance(plan_row["plan_json"], dict) else json.loads(plan_row["plan_json"])
            (root / "plan.json").write_text(json.dumps(plan_json))

            shots = db.fetchall(
                "select id, ord, kind, room_id, label, camera from shots where project_id=%s",
                (project_id,),
            )
            proj = db.fetchrow("select project_type, style_preset from projects where id=%s",
                               (project_id,))
            shots_doc = {
                "schema_version": "1.0",
                "project_type": proj["project_type"] if proj else "house",
                "style_preset": proj.get("style_preset") or {},
                "shots": [
                    {"id": str(s["id"]), "ord": s["ord"], "kind": s["kind"],
                     "room_id": s.get("room_id"), "label": s["label"],
                     "camera": s["camera"] if isinstance(s["camera"], dict) else json.loads(s["camera"])}
                    for s in shots
                ],
            }
            (root / "shots.json").write_text(json.dumps(shots_doc))

            out_root = root / "out"
            out_root.mkdir(exist_ok=True)
            subprocess.run([
                BLENDER_BIN, "-b", "--factory-startup", "-P", str(BUILD_PY), "--",
                "--plan", str(root / "plan.json"),
                "--shots", str(root / "shots.json"),
                "--out", str(out_root),
            ], check=True)

            # Each shot's outputs land under out_root/<render_hash>/ — but we need
            # them keyed by shot id for the DB. Map by matching shot ids against
            # output dirs via a shot_hash file written by build.py. For M5 we fall
            # back to the simplest convention: upload each file under
            # renders/{project}/{shot_id}/{basename}.
            for s in shots:
                sid = str(s["id"])
                # Find the directory whose contents match this shot. For M5 we take
                # the first available dir with all three files; mapping tightening
                # moves to M7.
                for shot_dir in out_root.iterdir():
                    files = {"driving.mp4", "start.png", "clay.png"}
                    present = {p.name for p in shot_dir.iterdir()}
                    if files <= present:
                        prefix = f"{project_id}/{sid}"
                        for name in files:
                            data = (shot_dir / name).read_bytes()
                            storage.upload(cfg.bucket_renders, f"{prefix}/{name}",
                                           data,
                                           "video/mp4" if name.endswith(".mp4") else "image/png")
                        db.execute(
                            "update shots set driving_clip_path=%s, start_frame_path=%s, "
                            "clay_ref_path=%s where id=%s",
                            (f"{prefix}/driving.mp4", f"{prefix}/start.png",
                             f"{prefix}/clay.png", sid),
                        )
                        break

    run_job(db, ctx, work)
