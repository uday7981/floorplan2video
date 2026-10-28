"""RQ entry point for the extract queue.

Enqueued by apps/api/routers/plans.py as:
    "extract.queue_wrapper.run"  kwargs={job_id, plan_id, source_path, known_dimension_m}

Downloads the source file from Supabase Storage, runs the existing CLI's
ClaudeExtractor against it, writes the plan_json + plan_hash back to the plans
row, and updates the jobs row at every step.
"""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fpv_common.config import load_config
from fpv_common.db import db_from_config, dumps_jsonb
from fpv_common.jobs import JobContext, run_job
from fpv_common.storage import storage_from_config

log = logging.getLogger(__name__)


def run(*, job_id: str, plan_id: str, source_path: str,
        known_dimension_m: float | None = None) -> None:
    cfg = load_config()
    db = db_from_config(cfg)
    storage = storage_from_config(cfg)

    row = db.fetchrow("select project_id from jobs where id=%s", (job_id,))
    assert row is not None
    ctx = JobContext(job_id=UUID(job_id), project_id=UUID(row["project_id"]),
                     job_type="extract", ref_id=UUID(plan_id))

    def work():
        from .normalise import normalise
        from .claude_client import ClaudeExtractor
        from .cost import claude_cost

        # bucket for uploads is cfg.bucket_uploads; path format: {project_id}/{file}
        source_bytes = storage.download(cfg.bucket_uploads, source_path)
        tmp = Path("/tmp") / f"extract_{job_id}.bin"
        tmp.write_bytes(source_bytes)

        png, _mime, _info = normalise(tmp)
        tmp2 = tmp.with_suffix(".png")
        tmp2.write_bytes(png)

        extractor = ClaudeExtractor()
        result = extractor.extract(png, known_dim_m=known_dimension_m)

        from plan_schema import plan_hash
        plan_h = plan_hash(result.plan_json)
        db.execute(
            "update plans set plan_json=%s::jsonb, plan_hash=%s where id=%s",
            (dumps_jsonb(result.plan_json), plan_h, plan_id),
        )

        cost = claude_cost(cfg.anthropic_model, result.input_tokens, result.output_tokens)
        db.execute(
            "update projects set spent_usd = spent_usd + %s where id=%s",
            (cost.total_usd, str(ctx.project_id)),
        )

    run_job(db, ctx, work)
