from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from .. import repo
from ..deps import current_user, get_config, get_db, get_queue_export, get_runpod
from ..errors import ApiError
from ..schemas import ExportRequest, Job
from fpv_common.auth import AuthedUser
from fpv_common.db import Db
from fpv_common.runpod import RunPodClient

router = APIRouter(tags=["exports"])


@router.post("/projects/{project_id}/export", response_model=Job)
def start_export(project_id: UUID, body: ExportRequest,
                 user: AuthedUser = Depends(current_user),
                 db: Db = Depends(get_db),
                 queue = Depends(get_queue_export),
                 runpod: RunPodClient = Depends(get_runpod),
                 cfg = Depends(get_config)):
    if repo.project_get(db, user.user_id, project_id) is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    if cfg.runpod_gpu_pod_id:
        try:
            runpod.ensure_running(cfg.runpod_gpu_pod_id)
        except Exception as e:
            raise ApiError(code="pod_start_failed",
                           message=f"could not start the GPU pod: {e}",
                           status_code=503)
    # Collect selected generation ids for this project.
    rows = db.fetchall(
        "select g.id from generations g join shots s on g.shot_id = s.id "
        "where s.project_id = %s and g.selected = true order by s.ord",
        (str(project_id),),
    )
    if not rows:
        raise ApiError(code="no_takes_selected",
                       message="no take is marked selected for this project",
                       status_code=409)
    gen_ids = [str(r["id"]) for r in rows]
    export = db.fetchrow(
        "insert into exports (project_id, generation_ids, status) "
        "values (%s, %s, 'queued') returning *",
        (str(project_id), gen_ids),
    )
    job = repo.job_create(db, project_id, "export", export["id"] if export else None)
    queue.enqueue("edit_worker.queue_wrapper.run",
                  kwargs={"job_id": str(job["id"]),
                          "export_id": str(export["id"]) if export else None,
                          "project_name": body.project_name,
                          "captions": body.captions},
                  job_timeout=60 * 30)
    return Job(job_id=job["id"])
