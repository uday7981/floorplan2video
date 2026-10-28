from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import current_user, get_config, get_storage
from ..errors import ApiError
from fpv_common.auth import AuthedUser
from fpv_common.storage import Storage

router = APIRouter(tags=["files"])


@router.get("/files/sign")
def sign_url(
    path: str = Query(..., description="object path like <project_id>/<file>"),
    bucket: str = Query("uploads"),
    user: AuthedUser = Depends(current_user),
    storage: Storage = Depends(get_storage),
    cfg = Depends(get_config),
):
    allowed = {cfg.bucket_uploads, cfg.bucket_renders, cfg.bucket_frames,
               cfg.bucket_takes, cfg.bucket_exports}
    if bucket not in allowed:
        raise ApiError(code="bad_bucket", message=f"bucket {bucket!r} not allowed",
                       status_code=400)
    signed = storage.create_signed_read_url(bucket, path)
    return {"url": signed.url, "expires_in_s": signed.expires_in_s}
