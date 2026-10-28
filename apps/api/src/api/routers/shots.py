from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from .. import repo
from ..deps import current_user, get_db, get_queue_end_frame, get_queue_render, get_runpod, get_config
from ..errors import ApiError
from ..schemas import Job, ShotsReplace
from fpv_common.auth import AuthedUser
from fpv_common.db import Db
from fpv_common.runpod import RunPodClient

router = APIRouter(tags=["shots"])


@router.put("/projects/{project_id}/shots", response_model=list[dict])
def replace_shots(project_id: UUID, body: ShotsReplace,
                  user: AuthedUser = Depends(current_user),
                  db: Db = Depends(get_db)):
    project = repo.project_get(db, user.user_id, project_id)
    if project is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    # Use the latest approved plan (fallback: the latest plan).
    plan_row = db.fetchrow(
        "select * from plans where project_id=%s "
        "order by approved desc, version desc limit 1",
        (str(project_id),),
    )
    if plan_row is None:
        raise ApiError(code="no_plan", message="no plan yet", status_code=409)
    shots = [s.model_dump() for s in body.shots]
    return repo.shots_replace(db, project_id, plan_row["id"], shots)


@router.post("/projects/{project_id}/render", response_model=Job)
def start_render(project_id: UUID,
                 user: AuthedUser = Depends(current_user),
                 db: Db = Depends(get_db),
                 queue = Depends(get_queue_render),
                 runpod: RunPodClient = Depends(get_runpod),
                 cfg = Depends(get_config)):
    if repo.project_get(db, user.user_id, project_id) is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    # Pod wake-up: ensure the GPU pod is RUNNING before enqueueing.
    if cfg.runpod_gpu_pod_id:
        try:
            runpod.ensure_running(cfg.runpod_gpu_pod_id)
        except Exception as e:
            raise ApiError(code="pod_start_failed",
                           message=f"could not start the GPU pod: {e}",
                           status_code=503)
    job = repo.job_create(db, project_id, "render", None)
    queue.enqueue("blender_worker.queue_wrapper.run",
                  kwargs={"job_id": str(job["id"]), "project_id": str(project_id)},
                  job_timeout=60 * 30)
    return Job(job_id=job["id"])


@router.post("/shots/{shot_id}/end-frame", response_model=dict)
def gen_end_frame(shot_id: UUID,
                  user: AuthedUser = Depends(current_user),
                  db: Db = Depends(get_db),
                  queue = Depends(get_queue_end_frame)):
    shot = repo.shot_get(db, shot_id)
    if shot is None:
        raise ApiError(code="not_found", message="shot not found", status_code=404)
    queue.enqueue("image_worker.queue_wrapper.run",
                  kwargs={"shot_id": str(shot_id)},
                  job_timeout=180)
    return {"queued": True, "shot_id": str(shot_id)}


@router.post("/shots/{shot_id}/end-frame/approve", response_model=dict)
def approve_end_frame(shot_id: UUID,
                      user: AuthedUser = Depends(current_user),
                      db: Db = Depends(get_db)):
    if repo.shot_get(db, shot_id) is None:
        raise ApiError(code="not_found", message="shot not found", status_code=404)
    repo.shot_approve_end_frame(db, shot_id)
    return {"approved": True, "shot_id": str(shot_id)}
