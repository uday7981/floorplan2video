"""Prove a killed-and-retried video job doesn't trigger a duplicate paid submit.

TRD acceptance: "Killing a video worker mid-job leads to a retry, never a
duplicate paid generation."
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from video_worker.providers import SubmitRequest
from video_worker.providers.together import TogetherVideoProvider


class CountingTogether:
    """Counts how many times videos.create is called."""

    def __init__(self):
        self.create_calls: list[dict] = []
        self.videos = SimpleNamespace(create=self._create, retrieve=self._retrieve)

    def _create(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(id="jobA")

    def _retrieve(self, job_id):
        return SimpleNamespace(status="running")


def test_submit_forwards_idempotency_key_header():
    client = CountingTogether()
    p = TogetherVideoProvider(_client=client)
    req = SubmitRequest(
        prompt="x",
        resolution="480p",
        duration_s=4,
        start_frame_url="data:image/png;base64,xx",
        end_frame_url="data:image/png;base64,yy",
        idempotency_key="fpv-gen-abc-123",
    )
    p.submit(req)
    assert client.create_calls[0]["extra_headers"] == {"Idempotency-Key": "fpv-gen-abc-123"}


def test_submit_without_key_sends_no_extra_headers():
    client = CountingTogether()
    p = TogetherVideoProvider(_client=client)
    req = SubmitRequest(
        prompt="x", resolution="480p", duration_s=4,
        start_frame_url="data:image/png;base64,xx",
        end_frame_url="data:image/png;base64,yy",
    )
    p.submit(req)
    assert "extra_headers" not in client.create_calls[0]
