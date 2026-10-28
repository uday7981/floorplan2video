"""RQ entry point for the end_frame queue.

Reads the shot row, resolves its clay.png path from storage, calls OpenAI
image edit, uploads the result, writes end_frame_path on the shot + a
generations row with cost."""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fpv_common.config import load_config
from fpv_common.db import db_from_config
from fpv_common.jobs import JobContext, run_job
from fpv_common.pricing import openai_image_cost, load_prices
from fpv_common.storage import storage_from_config

log = logging.getLogger(__name__)


def run(*, shot_id: str) -> None:
    cfg = load_config()
    db = db_from_config(cfg)
    storage = storage_from_config(cfg)

    shot = db.fetchrow(
        "select id, project_id, clay_ref_path, kind, room_id from shots where id=%s",
        (shot_id,),
    )
    assert shot is not None, f"shot {shot_id} not found"

    job = db.fetchrow(
        "insert into jobs (project_id, type, ref_id, status) "
        "values (%s, 'end_frame', %s, 'queued') returning *",
        (shot["project_id"], shot_id),
    )
    ctx = JobContext(job_id=UUID(job["id"]), project_id=UUID(shot["project_id"]),
                     job_type="end_frame", ref_id=UUID(shot_id))

    def work():
        from .prompts import fill_end_frame_prompt
        from .openai_client import OpenAIImageEditor, crop_resize_to

        # Load style preset from the project row.
        row = db.fetchrow("select style_preset from projects where id=%s",
                          (shot["project_id"],))
        preset = row.get("style_preset") if row else {}

        # Load room_type if room shot.
        room_type = None
        if shot["kind"] == "room" and shot["room_id"]:
            plan = db.fetchrow(
                "select plan_json from plans where project_id=%s and approved=true "
                "order by version desc limit 1",
                (shot["project_id"],),
            )
            if plan and plan.get("plan_json"):
                import json
                data = plan["plan_json"] if isinstance(plan["plan_json"], dict) else json.loads(plan["plan_json"])
                for r in data.get("rooms", []):
                    if r["id"] == shot["room_id"]:
                        # Prefer room.name (specific) over the enum type —
                        # keeps the prompt accurate for any vocabulary even if
                        # the RoomType enum hasn't been expanded to match.
                        room_type = r.get("name") or r.get("type")
                        break

        prompt = fill_end_frame_prompt(shot["kind"], preset or {}, room_type)

        clay_path = shot["clay_ref_path"]
        if not clay_path:
            raise RuntimeError("shot has no clay_ref_path yet (render must run first)")
        clay_png = storage.download(cfg.bucket_renders, clay_path)

        editor = OpenAIImageEditor()
        result = editor.edit(reference_png=clay_png, prompt=prompt, size="1792x1024")
        final_png = crop_resize_to(result.png_bytes, (1280, 720))

        end_path = f"{ctx.project_id}/{shot_id}/end_frame.png"
        storage.upload(cfg.bucket_frames, end_path, final_png, "image/png")

        prices = load_prices(db)
        cost = openai_image_cost(prices, result.model, result.requested_size)
        db.execute(
            "update shots set end_frame_path=%s where id=%s",
            (end_path, shot_id),
        )
        db.execute(
            "insert into generations (shot_id, kind, provider, model, prompt, "
            "status, output_path, est_cost_usd, actual_cost_usd) "
            "values (%s, 'end_frame', 'openai', %s, %s, 'succeeded', %s, %s, %s)",
            (shot_id, result.model, prompt, end_path, cost, cost),
        )
        db.execute(
            "update projects set spent_usd = spent_usd + %s where id=%s",
            (cost, str(ctx.project_id)),
        )

    run_job(db, ctx, work)
