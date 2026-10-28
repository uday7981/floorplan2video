"""RQ entry point for the export queue."""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fpv_common.config import load_config
from fpv_common.db import db_from_config
from fpv_common.jobs import JobContext, run_job
from fpv_common.storage import storage_from_config

from .cli import main as cli_main

log = logging.getLogger(__name__)


def run(*, job_id: str, export_id: str, project_name: str,
        captions: dict | None = None) -> None:
    cfg = load_config()
    db = db_from_config(cfg)
    storage = storage_from_config(cfg)

    row = db.fetchrow("select project_id, generation_ids from exports where id=%s",
                      (export_id,))
    assert row is not None
    project_id = row["project_id"]

    ctx = JobContext(job_id=UUID(job_id), project_id=UUID(project_id),
                     job_type="export", ref_id=UUID(export_id))

    def work():
        with tempfile.TemporaryDirectory(prefix="export_") as tmp:
            root = Path(tmp)
            takes_dir = root / "takes"
            takes_dir.mkdir()

            # Download each selected generation's take.
            for gid in row["generation_ids"]:
                g = db.fetchrow("select output_path, shot_id from generations where id=%s",
                                (str(gid),))
                if not g or not g["output_path"]:
                    continue
                data = storage.download(cfg.bucket_takes, g["output_path"])
                (takes_dir / f"{g['shot_id']}.mp4").write_bytes(data)

            # Need plan.json + shots.json for the cli; synthesise shots.json
            # from the shots table.
            plan = db.fetchrow(
                "select plan_json from plans where project_id=%s and approved=true "
                "order by version desc limit 1", (project_id,),
            )
            plan_json = plan["plan_json"] if plan and isinstance(plan.get("plan_json"), dict) else json.loads(plan["plan_json"]) if plan else {}
            (root / "plan.json").write_text(json.dumps(plan_json))

            shots = db.fetchall(
                "select id, ord, kind, room_id, label, camera from shots where project_id=%s",
                (project_id,),
            )
            shots_doc = {
                "schema_version": "1.0",
                "project_type": "house",
                "shots": [
                    {"id": str(s["id"]), "ord": s["ord"], "kind": s["kind"],
                     "room_id": s.get("room_id"), "label": s["label"],
                     "camera": s["camera"] if isinstance(s["camera"], dict) else json.loads(s["camera"])}
                    for s in shots
                ],
            }
            (root / "shots.json").write_text(json.dumps(shots_doc))

            caps_path = None
            if captions:
                caps_path = root / "captions.json"
                caps_path.write_text(json.dumps(captions))

            out_mp4 = root / "final.mp4"
            args = [
                "--plan", str(root / "plan.json"),
                "--shots", str(root / "shots.json"),
                "--takes-dir", str(takes_dir),
                "--project-name", project_name,
                "--out", str(out_mp4),
            ]
            if caps_path:
                args += ["--captions-json", str(caps_path)]
            cli_main(args)

            out_path = f"{project_id}/{export_id}.mp4"
            storage.upload(cfg.bucket_exports, out_path, out_mp4.read_bytes(), "video/mp4")
            db.execute(
                "update exports set output_path=%s, status='succeeded' where id=%s",
                (out_path, export_id),
            )

    run_job(db, ctx, work)
