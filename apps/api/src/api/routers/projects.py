from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from .. import repo
from ..deps import current_user, get_config, get_db
from ..errors import ApiError
from ..schemas import Project, ProjectCreate
from fpv_common.auth import AuthedUser
from fpv_common.db import Db

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate,
                   user: AuthedUser = Depends(current_user),
                   db: Db = Depends(get_db),
                   cfg = Depends(get_config)):
    budget = body.budget_usd if body.budget_usd is not None else cfg.default_project_budget_usd
    row = repo.project_create(db, user.user_id, body.name,
                              body.style_preset, body.project_type, budget)
    return _to_project(row)


@router.get("", response_model=list[Project])
def list_projects(user: AuthedUser = Depends(current_user),
                  db: Db = Depends(get_db)):
    rows = repo.project_list(db, user.user_id)
    return [_to_project(r) for r in rows]


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: UUID,
                user: AuthedUser = Depends(current_user),
                db: Db = Depends(get_db)):
    row = repo.project_get(db, user.user_id, project_id)
    if row is None:
        raise ApiError(code="not_found", message="project not found", status_code=404)
    return _to_project(row)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID,
                   user: AuthedUser = Depends(current_user),
                   db: Db = Depends(get_db)):
    n = repo.project_delete(db, user.user_id, project_id)
    if n == 0:
        raise ApiError(code="not_found", message="project not found", status_code=404)


def _to_project(row: dict) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        project_type=row["project_type"],
        style_preset=row.get("style_preset") or {},
        budget_usd=float(row["budget_usd"]),
        spent_usd=float(row["spent_usd"]),
        status=row["status"],
    )
