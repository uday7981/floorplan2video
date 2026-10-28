"""FastAPI dependency injection. Everything the routers need is created here
and overridden in tests via app.dependency_overrides."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from fastapi import Depends, Header, HTTPException

from fpv_common.auth import AuthedUser, AuthError, decode_jwt
from fpv_common.config import Config, load_config
from fpv_common.db import Db, db_from_config
from fpv_common.pricing import load_prices as _load_prices
from fpv_common.queue import QueueName, rq_queue, redis_from_url
from fpv_common.runpod import RunPodClient, runpod_from_config
from fpv_common.storage import Storage, storage_from_config


@lru_cache
def get_config() -> Config:
    return load_config()


@lru_cache
def get_redis_conn():
    return redis_from_url(get_config().upstash_redis_url)


def get_db() -> Db:
    return db_from_config(get_config())


def get_storage() -> Storage:
    return storage_from_config(get_config())


def get_runpod() -> RunPodClient:
    return runpod_from_config(get_config())


def _queue_factory(name: QueueName):
    def _dep() -> Any:
        return rq_queue(name, connection=get_redis_conn())
    return _dep


# One stable callable per queue — makes FastAPI's Depends() + dependency_overrides work.
get_queue_extract   = _queue_factory("extract")
get_queue_render    = _queue_factory("render")
get_queue_end_frame = _queue_factory("end_frame")
get_queue_video     = _queue_factory("video")
get_queue_export    = _queue_factory("export")


def get_prices(db: Db = Depends(get_db)) -> dict:
    return _load_prices(db)


# ---- auth ----

async def current_user(authorization: str | None = Header(default=None)) -> AuthedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    # Signature verification is toggled by SUPABASE_JWT_VERIFY=1 so unit tests
    # (and local dev with hand-rolled tokens) keep working. In prod the pod
    # sets it; SUPABASE_JWT_SECRET must be present.
    verify = os.environ.get("SUPABASE_JWT_VERIFY", "0") == "1"
    secret = get_config().supabase_jwt_secret if verify else ""
    try:
        return decode_jwt(token, jwt_secret=secret, verify=verify)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
