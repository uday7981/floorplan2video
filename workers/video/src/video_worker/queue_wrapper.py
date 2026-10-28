"""RQ entry point for the video queue.

The API's /videos endpoint pre-creates a generations row (status=queued) and
enqueues this with generation_id. The wrapper submits to Together, polls,
downloads, uploads, and writes output_path + actual_cost.
"""
from __future__ import annotations

import logging
import time
from uuid import UUID

import requests

from fpv_common.config import load_config
from fpv_common.db import db_from_config
from fpv_common.jobs import JobContext, run_job
from fpv_common.pricing import load_prices, seedance_cost
from fpv_common.storage import storage_from_config

log = logging.getLogger(__name__)


def run(*, generation_id: str, poll_interval: int = 15, timeout: int = 20 * 60) -> None:
    cfg = load_config()
    db = db_from_config(cfg)
    storage = storage_from_config(cfg)

    gen = db.fetchrow("select * from generations where id=%s", (generation_id,))
    assert gen is not None
    shot = db.fetchrow(
        "select id, project_id, start_frame_path, end_frame_path, camera from shots where id=%s",
        (gen["shot_id"],),
    )
    assert shot is not None

    job = db.fetchrow(
        "insert into jobs (project_id, type, ref_id, status) "
        "values (%s, 'video', %s, 'queued') returning *",
        (shot["project_id"], generation_id),
    )
    ctx = JobContext(job_id=UUID(job["id"]), project_id=UUID(shot["project_id"]),
                     job_type="video", ref_id=UUID(generation_id))

    def work():
        from .prompts import fill_video_prompt
        from .providers.together import TogetherVideoProvider, encode_png_data_url
        from .providers.base import SubmitRequest

        camera = shot["camera"]
        import json
        if isinstance(camera, str):
            camera = json.loads(camera)
        duration_s = int(camera["duration_s"])
        prompt = fill_video_prompt("frames_only", camera["move"])

        start_png = storage.download(cfg.bucket_renders, shot["start_frame_path"])
        end_png = storage.download(cfg.bucket_frames, shot["end_frame_path"])

        provider = TogetherVideoProvider()

        # Idempotency: if we already submitted this generation on a previous
        # attempt, skip submit and resume polling. provider_job_id is set on
        # first submit; a worker killed mid-job then retried by RQ sees it and
        # avoids a duplicate paid request (TRD acceptance test).
        existing = gen.get("provider_job_id")
        if existing:
            log.info("resuming poll on existing provider_job_id=%s", existing)
            provider_job_id = existing
        else:
            req = SubmitRequest(
                prompt=prompt,
                resolution=gen["resolution"],
                duration_s=duration_s,
                start_frame_url=encode_png_data_url(start_png),
                end_frame_url=encode_png_data_url(end_png),
                idempotency_key=f"fpv-gen-{generation_id}",
            )
            sr = provider.submit(req)
            provider_job_id = sr.provider_job_id
            db.execute(
                "update generations set status='running', provider_job_id=%s, prompt=%s where id=%s",
                (provider_job_id, prompt, generation_id),
            )

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(poll_interval)
            pr = provider.poll(provider_job_id)
            if pr.status == "succeeded":
                r = requests.get(pr.output_url, timeout=300)
                r.raise_for_status()
                take_path = f"{ctx.project_id}/{shot['id']}/{generation_id}.mp4"
                storage.upload(cfg.bucket_takes, take_path, r.content, "video/mp4")

                prices = load_prices(db)
                cost = seedance_cost(prices, gen["resolution"], duration_s)
                # Idempotent completion: only bump project spend if actual_cost
                # was NULL (first time landing here). A retry that re-polled to
                # succeeded can't double-charge the project.
                rc = db.execute(
                    "update generations set status='succeeded', output_path=%s, "
                    "actual_cost_usd=%s where id=%s and actual_cost_usd is null",
                    (take_path, cost, generation_id),
                )
                if rc == 1:
                    db.execute(
                        "update projects set spent_usd = spent_usd + %s where id=%s",
                        (cost, str(ctx.project_id)),
                    )
                else:
                    log.info("completion already recorded for %s; skipping spend bump", generation_id)
                return
            if pr.status == "failed":
                db.execute(
                    "update generations set status='failed', error=%s where id=%s",
                    (pr.error or "unknown", generation_id),
                )
                raise RuntimeError(f"together failed: {pr.error}")

        db.execute(
            "update generations set status='failed', error='timeout' where id=%s",
            (generation_id,),
        )
        raise TimeoutError(f"video poll timed out after {timeout}s")

    run_job(db, ctx, work)
