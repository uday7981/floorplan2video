"""Job runner: wrap each worker so it:
  - marks the jobs row as running at start
  - executes the inner callable (the worker's unit of work)
  - marks the row as succeeded on success or failed+error on exception
  - never retries silently — RQ-level retries are configured on enqueue
"""
from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

log = logging.getLogger(__name__)

# RQ retry policy (TRD): 3 attempts total with backoff.
RETRY_INTERVALS_S = [10, 60, 300]


@dataclass
class JobContext:
    job_id: UUID
    project_id: UUID
    job_type: str
    ref_id: UUID | None


def mark_running(db, job_id: UUID) -> None:
    db.execute(
        "update jobs set status='running', attempts=attempts+1, "
        "started_at = coalesce(started_at, now()), updated_at=now() where id=%s",
        (str(job_id),),
    )


def mark_succeeded(db, job_id: UUID) -> None:
    db.execute(
        "update jobs set status='succeeded', finished_at=now(), updated_at=now() "
        "where id=%s",
        (str(job_id),),
    )


def mark_failed(db, job_id: UUID, error: str) -> None:
    db.execute(
        "update jobs set status='failed', error=%s, finished_at=now(), updated_at=now() "
        "where id=%s",
        (error[:4000], str(job_id)),
    )


def run_job(db, ctx: JobContext, func: Callable[[], None]) -> None:
    """Execute func() with full state tracking. Re-raise so RQ sees the failure
    and schedules a retry if applicable."""
    log.info("job %s type=%s starting", ctx.job_id, ctx.job_type)
    try:
        mark_running(db, ctx.job_id)
        func()
    except Exception as e:
        tb = traceback.format_exc()
        log.exception("job %s failed: %s", ctx.job_id, e)
        mark_failed(db, ctx.job_id, f"{e}\n{tb}")
        raise
    else:
        mark_succeeded(db, ctx.job_id)
        log.info("job %s succeeded", ctx.job_id)
