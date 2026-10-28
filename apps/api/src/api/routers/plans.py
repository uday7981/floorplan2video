from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from .. import repo
from ..deps import current_user, get_config, get_db, get_queue_extract, get_storage
from ..errors import ApiError
from ..schemas import ExtractRequest, Job, PlanSave, SignedUploadUrl
from fpv_common.auth import AuthedUser
from fpv_common.db import Db
from fpv_common.storage import Storage

router = APIRouter(tags=["plans"])


@router.post("/projects/{project_id}/plans/upload-url", response_model=SignedUploadUrl)
def upload_url(project_id: UUID,
               user: AuthedUser = Depends(current_user),
               db: Db = Depends(get_db),
               storage: Storage = Depends(get_storage),
               cfg = Depends(get_config)):
    if repo.project_get(db, user.user_id, project_id) is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    path = f"{project_id}/{uuid4()}.bin"
    signed = storage.create_signed_upload_url(cfg.bucket_uploads, path)
    return SignedUploadUrl(url=signed.url, path=signed.path)


@router.post("/projects/{project_id}/plans/extract", response_model=Job)
def start_extract(project_id: UUID,
                  body: ExtractRequest,
                  user: AuthedUser = Depends(current_user),
                  db: Db = Depends(get_db),
                  queue = Depends(get_queue_extract)):
    if repo.project_get(db, user.user_id, project_id) is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    # Create a plan row at version N with the source_path; worker fills in plan_json.
    version = repo.plan_next_version(db, project_id)
    plan = repo.plan_create(db, project_id, body.source_path,
                            plan_json=None, plan_hash=None, version=version)
    job = repo.job_create(db, project_id, "extract", plan["id"])
    queue.enqueue(
        "extract.queue_wrapper.run",
        kwargs={"job_id": str(job["id"]), "plan_id": str(plan["id"]),
                "source_path": body.source_path,
                "known_dimension_m": body.known_dimension_m},
        job_timeout=600,
    )
    return Job(job_id=job["id"])


@router.put("/plans/{plan_id}", response_model=dict)
def save_plan(plan_id: UUID,
              body: PlanSave,
              user: AuthedUser = Depends(current_user),
              db: Db = Depends(get_db)):
    existing = repo.plan_get(db, plan_id)
    if existing is None:
        raise ApiError(code="not_found", message="plan not found", status_code=404)
    # TODO(decision): verify ownership via project. Stubbed in M5 — trust the jwt.
    version = repo.plan_next_version(db, existing["project_id"])
    new = repo.plan_create(db, existing["project_id"], existing["source_path"],
                           plan_json=body.plan_json, plan_hash=None, version=version)
    return {"id": str(new["id"]), "version": version}


@router.post("/plans/{plan_id}/approve", response_model=dict)
def approve_plan(plan_id: UUID,
                 user: AuthedUser = Depends(current_user),
                 db: Db = Depends(get_db)):
    plan = repo.plan_get(db, plan_id)
    if plan is None:
        raise ApiError(code="not_found", message="plan not found", status_code=404)
    repo.plan_approve(db, plan_id)
    # TODO(decision): auto-generate shots from plan.rooms. For M5, return empty
    # list; the frontend posts shots via PUT /shots. Full auto-gen comes in M7.
    return {"approved": True, "shots": []}
