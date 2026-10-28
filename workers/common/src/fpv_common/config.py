"""Environment-driven configuration.

Rules:
- Secret keys stay server-side (SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_*, etc).
- Only NEXT_PUBLIC_* reach the browser (handled in apps/web, not here).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _req(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"required env var {name} is not set")
    return v


def _opt(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str  # for JWT verification (TODO M7)
    upstash_redis_url: str
    anthropic_api_key: str
    anthropic_model: str
    openai_api_key: str
    openai_image_model: str
    together_api_key: str
    together_video_model: str
    runpod_api_key: str
    runpod_gpu_pod_id: str
    default_project_budget_usd: float
    pod_idle_shutdown_minutes: int
    video_mode: str

    bucket_uploads: str
    bucket_renders: str
    bucket_frames: str
    bucket_takes: str
    bucket_exports: str


def load_config() -> Config:
    return Config(
        supabase_url=_req("SUPABASE_URL"),
        supabase_service_role_key=_req("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_jwt_secret=_opt("SUPABASE_JWT_SECRET"),  # verification deferred to M7
        upstash_redis_url=_req("UPSTASH_REDIS_URL"),
        anthropic_api_key=_opt("ANTHROPIC_API_KEY"),
        anthropic_model=_opt("ANTHROPIC_MODEL"),
        openai_api_key=_opt("OPENAI_API_KEY"),
        openai_image_model=_opt("OPENAI_IMAGE_MODEL"),
        together_api_key=_opt("TOGETHER_API_KEY"),
        together_video_model=_opt("TOGETHER_VIDEO_MODEL", "ByteDance/Seedance-2.5"),
        runpod_api_key=_opt("RUNPOD_API_KEY"),
        runpod_gpu_pod_id=_opt("RUNPOD_GPU_POD_ID"),
        default_project_budget_usd=float(_opt("DEFAULT_PROJECT_BUDGET_USD", "40")),
        pod_idle_shutdown_minutes=int(_opt("POD_IDLE_SHUTDOWN_MINUTES", "15")),
        video_mode=_opt("VIDEO_MODE", "frames_only"),
        bucket_uploads=_opt("SUPABASE_BUCKET_UPLOADS", "uploads"),
        bucket_renders=_opt("SUPABASE_BUCKET_RENDERS", "renders"),
        bucket_frames=_opt("SUPABASE_BUCKET_FRAMES", "frames"),
        bucket_takes=_opt("SUPABASE_BUCKET_TAKES", "takes"),
        bucket_exports=_opt("SUPABASE_BUCKET_EXPORTS", "exports"),
    )
