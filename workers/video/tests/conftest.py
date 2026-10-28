from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image


@pytest.fixture
def tiny_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (240, 240, 240)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def minimal_plan() -> dict:
    return {"rooms": [{"id": "R1", "name": "Living", "type": "living",
                       "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]}]}


@pytest.fixture
def minimal_shots_doc() -> dict:
    return {
        "schema_version": "1.0",
        "project_type": "house",
        "style_preset": {"materials": "oak", "light": "3000K", "setting": "forest"},
        "shots": [
            {"id": "s_r01", "ord": 0, "kind": "room", "room_id": "R1", "label": "Living",
             "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
            {"id": "s_exterior", "ord": 1, "kind": "exterior", "label": "Ext",
             "camera": {"move": "orbit", "duration_s": 8, "lens_mm": 28, "fps": 24}},
        ],
    }


class FakeTogetherSuccess:
    """Returns a 'succeeded' response immediately with a fake output URL."""

    def __init__(self):
        self.videos = SimpleNamespace(create=self._create, retrieve=self._retrieve)
        self.calls_create: list[dict] = []
        self.calls_retrieve: list[str] = []

    def _create(self, **kwargs):
        self.calls_create.append(kwargs)
        return SimpleNamespace(id="job_test")

    def _retrieve(self, job_id):
        self.calls_retrieve.append(job_id)
        return SimpleNamespace(
            status="succeeded",
            outputs=SimpleNamespace(video_url="https://example.invalid/out.mp4"),
        )


class FakeTogetherFailure:
    def __init__(self):
        self.videos = SimpleNamespace(create=self._create, retrieve=self._retrieve)

    def _create(self, **kwargs):
        return SimpleNamespace(id="job_fail")

    def _retrieve(self, job_id):
        return SimpleNamespace(status="failed", error="validation error")


@pytest.fixture
def fake_together_success(monkeypatch) -> FakeTogetherSuccess:
    monkeypatch.setenv("TOGETHER_API_KEY", "test-key")
    monkeypatch.setenv("TOGETHER_VIDEO_MODEL", "ByteDance/Seedance-2.5")
    monkeypatch.setenv("VIDEO_MODE", "frames_only")
    return FakeTogetherSuccess()


@pytest.fixture
def fake_together_failure(monkeypatch) -> FakeTogetherFailure:
    monkeypatch.setenv("TOGETHER_API_KEY", "test-key")
    monkeypatch.setenv("TOGETHER_VIDEO_MODEL", "ByteDance/Seedance-2.5")
    monkeypatch.setenv("VIDEO_MODE", "frames_only")
    return FakeTogetherFailure()
