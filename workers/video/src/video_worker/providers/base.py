"""VideoProvider interface. Every paid video call goes through this adapter so
cost logging and the frames_only / reference_guided switch stay centralised.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Protocol


Resolution = Literal["480p", "720p"]
Status = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class SubmitRequest:
    prompt: str
    resolution: Resolution
    duration_s: int
    # frames_only mode: first + last frames set, reference_video_url is None.
    # reference_guided mode: reference_video_url set, start/end are None.
    # Together Seedance 2.5 forbids combining both (per M0).
    start_frame_url: Optional[str] = None
    end_frame_url: Optional[str] = None
    reference_video_url: Optional[str] = None


@dataclass
class SubmitResult:
    provider_job_id: str
    est_cost_usd: float


@dataclass
class PollResult:
    status: Status
    output_url: Optional[str] = None
    actual_cost_usd: Optional[float] = None
    error: Optional[str] = None


class VideoProvider(Protocol):
    name: str

    def submit(self, req: SubmitRequest) -> SubmitResult: ...
    def poll(self, provider_job_id: str) -> PollResult: ...
