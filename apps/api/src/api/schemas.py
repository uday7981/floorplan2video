"""Request / response models. Lean — the DB is Postgres, so most responses
are passthroughs of row dicts; schemas tighten the shape at the API boundary."""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---- shared ----

class Job(BaseModel):
    job_id: UUID


# ---- projects ----

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    style_preset: dict = Field(default_factory=dict)
    project_type: Literal["house", "interior"] = "house"
    budget_usd: float | None = None


class Project(BaseModel):
    id: UUID
    name: str
    project_type: Literal["house", "interior"]
    style_preset: dict
    budget_usd: float
    spent_usd: float
    status: str


# ---- plans ----

class SignedUploadUrl(BaseModel):
    url: str
    path: str


class ExtractRequest(BaseModel):
    source_path: str
    known_dimension_m: float | None = None


class PlanSave(BaseModel):
    plan_json: dict


# ---- shots ----

class ShotIn(BaseModel):
    id: str | None = None
    ord: int
    kind: Literal["opening", "room", "exterior"]
    room_id: str | None = None
    label: str
    camera: dict


class ShotsReplace(BaseModel):
    shots: list[ShotIn]


# ---- end-frame + video ----

class EstimateRequest(BaseModel):
    resolution: Literal["480p", "720p"]
    shot_ids: list[UUID]


class EstimateResponse(BaseModel):
    usd: float
    breakdown: list[dict[str, Any]]


class VideoSubmit(BaseModel):
    resolution: Literal["480p", "720p"]
    shot_ids: list[UUID]
    confirm_usd: float


# ---- exports ----

class ExportRequest(BaseModel):
    project_name: str
    captions: dict[str, str] = Field(default_factory=dict)
