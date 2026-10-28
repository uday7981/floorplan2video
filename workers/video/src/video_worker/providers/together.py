"""Together AI Seedance 2.5 implementation of VideoProvider.

Reference: https://docs.together.ai/docs/seedance2.5-quickstart
Pricing (from supabase/seed.sql): 480p $0.115/s, 720p $0.249/s.

Mode: frames_only — first + last frame via `media.frame_images`. Together's docs
explicitly forbid combining frame_images with reference_videos in one request.
"""
from __future__ import annotations

import base64
import os
from typing import Any

from .base import PollResult, SubmitRequest, SubmitResult


class TogetherVideoProvider:
    name = "together"

    def __init__(self, *, model: str | None = None, api_key: str | None = None,
                 _client: Any = None) -> None:
        self.model = model or os.environ.get("TOGETHER_VIDEO_MODEL") or "ByteDance/Seedance-2.5"
        if _client is not None:
            self.client = _client
        else:
            from together import Together
            self.client = Together(api_key=api_key or os.environ.get("TOGETHER_API_KEY"))

    def submit(self, req: SubmitRequest) -> SubmitResult:
        if req.start_frame_url is None or req.end_frame_url is None:
            raise ValueError("TogetherVideoProvider requires start_frame_url + end_frame_url")
        if req.reference_video_url is not None:
            raise ValueError(
                "Seedance 2.5 forbids combining frame_images with reference_videos "
                "in one request. Use frames_only mode or switch to reference_guided."
            )
        media = {
            "frame_images": [
                {"input_image": req.start_frame_url, "frame": "first"},
                {"input_image": req.end_frame_url, "frame": "last"},
            ]
        }
        job = self.client.videos.create(
            model=self.model,
            prompt=req.prompt,
            resolution=req.resolution,
            seconds=str(req.duration_s),
            media=media,
        )
        job_id = _attr_or_item(job, "id")
        return SubmitResult(provider_job_id=job_id, est_cost_usd=0.0)

    def poll(self, provider_job_id: str) -> PollResult:
        obj = self.client.videos.retrieve(provider_job_id)
        status = _attr_or_item(obj, "status")
        if status in ("completed", "succeeded"):
            # Response shape per Together docs: outputs.video_url. Fall back to
            # a few other paths observed in SDK responses.
            output_url = _dig(obj, ["outputs", "video_url"]) or _dig(obj, ["output_url"]) or _dig(obj, ["result", "video_url"])
            return PollResult(status="succeeded", output_url=output_url)
        if status == "failed":
            err = _dig(obj, ["error"]) or _dig(obj, ["error", "message"]) or "unknown"
            return PollResult(status="failed", error=str(err))
        if status in ("queued", "pending"):
            return PollResult(status="queued")
        # running / processing / other in-flight
        return PollResult(status="running")


# ------------------------- helpers -------------------------

def _attr_or_item(obj: Any, key: str) -> Any:
    v = getattr(obj, key, None)
    if v is not None:
        return v
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def _dig(obj: Any, path: list[str]) -> Any:
    cur = obj
    for k in path:
        if cur is None:
            return None
        cur = _attr_or_item(cur, k)
    return cur


def encode_png_data_url(png_bytes: bytes) -> str:
    """Together accepts data URLs for image frames. Convenience helper."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"
