from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from .. import repo
from ..deps import current_user, get_db, get_prices, get_queue_video
from ..errors import ApiError
from ..schemas import EstimateRequest, EstimateResponse, Job, VideoSubmit
from fpv_common.auth import AuthedUser
from fpv_common.db import Db
from fpv_common.pricing import seedance_cost

router = APIRouter(tags=["generations"])


@router.post("/projects/{project_id}/estimate", response_model=EstimateResponse)
def estimate_video(project_id: UUID, body: EstimateRequest,
                   user: AuthedUser = Depends(current_user),
                   db: Db = Depends(get_db),
                   prices: dict = Depends(get_prices)):
    if repo.project_get(db, user.user_id, project_id) is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    total = 0.0
    breakdown: list[dict] = []
    for sid in body.shot_ids:
        shot = repo.shot_get(db, sid)
        if shot is None:
            continue
        duration = int(shot["camera"]["duration_s"])
        usd = seedance_cost(prices, body.resolution, duration)
        total += usd
        breakdown.append({"shot_id": str(sid), "duration_s": duration,
                           "resolution": body.resolution, "usd": usd})
    return EstimateResponse(usd=total, breakdown=breakdown)


@router.post("/projects/{project_id}/videos", response_model=list[dict])
def submit_videos(project_id: UUID, body: VideoSubmit,
                  user: AuthedUser = Depends(current_user),
                  db: Db = Depends(get_db),
                  queue = Depends(get_queue_video),
                  prices: dict = Depends(get_prices)):
    project = repo.project_get(db, user.user_id, project_id)
    if project is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)

    # Fresh estimate must match confirmation (prevents price drift).
    total = 0.0
    rows: list[dict] = []
    for sid in body.shot_ids:
        shot = repo.shot_get(db, sid)
        if shot is None:
            continue
        duration = int(shot["camera"]["duration_s"])
        usd = seedance_cost(prices, body.resolution, duration)
        total += usd
        rows.append({"shot_id": sid, "usd": usd, "duration_s": duration})

    if body.confirm_usd + 1e-6 < total:
        raise ApiError(code="price_drift",
                       message=f"estimate changed: current ${total:.2f} > confirmed ${body.confirm_usd:.2f}",
                       status_code=409)

    budget = float(project["budget_usd"])
    spent = float(project["spent_usd"])
    if spent + total > budget + 1e-6:
        raise ApiError(code="budget_exceeded",
                       message=f"project budget ${budget:.2f} would be exceeded "
                               f"(spent ${spent:.2f} + estimate ${total:.2f})",
                       status_code=402)

    results: list[dict] = []
    for r in rows:
        gen = repo.generation_create(
            db, r["shot_id"], kind="video", provider="together",
            model="ByteDance/Seedance-2.5",
            prompt="",   # worker fills in from templates
            est_cost_usd=r["usd"],
            resolution=body.resolution,
        )
        queue.enqueue("video_worker.queue_wrapper.run",
                      kwargs={"generation_id": str(gen["id"])},
                      job_timeout=60 * 25)
        results.append({"generation_id": str(gen["id"]), "shot_id": str(r["shot_id"]),
                         "est_cost_usd": r["usd"]})
    return results


@router.post("/generations/{gen_id}/select", response_model=dict)
def select_take(gen_id: UUID,
                user: AuthedUser = Depends(current_user),
                db: Db = Depends(get_db)):
    if repo.generation_get(db, gen_id) is None:
        raise ApiError(code="not_found", message="generation not found", status_code=404)
    repo.generation_set_selected(db, gen_id)
    return {"selected": True, "generation_id": str(gen_id)}
