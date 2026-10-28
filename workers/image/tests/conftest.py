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
def preset() -> dict[str, str]:
    return {
        "materials": "oak, black aluminium, natural white",
        "light": "3000K",
        "setting": "a beautiful forest",
    }


@pytest.fixture
def minimal_plan() -> dict:
    return {
        "rooms": [{"id": "R1", "name": "Living", "type": "living",
                   "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]}],
    }


@pytest.fixture
def minimal_shots_doc(preset) -> dict:
    return {
        "schema_version": "1.0",
        "project_type": "house",
        "style_preset": preset,
        "shots": [
            {"id": "s_r01", "ord": 0, "kind": "room", "room_id": "R1", "label": "Living",
             "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
            {"id": "s_opening", "ord": 1, "kind": "opening", "label": "Open",
             "camera": {"move": "crane", "duration_s": 5, "lens_mm": 35, "fps": 24}},
            {"id": "s_exterior", "ord": 2, "kind": "exterior", "label": "Ext",
             "camera": {"move": "orbit", "duration_s": 8, "lens_mm": 28, "fps": 24}},
        ],
    }


class FakeOpenAI:
    """Minimal stand-in for the OpenAI client used in tests."""

    def __init__(self, png_bytes: bytes):
        self.images = SimpleNamespace(edit=self._edit)
        self._png = png_bytes
        self.calls: list[dict] = []

    def _edit(self, **kwargs):
        self.calls.append(kwargs)
        import base64
        data = SimpleNamespace(b64_json=base64.b64encode(self._png).decode("ascii"))
        return SimpleNamespace(data=[data])


@pytest.fixture
def fake_openai_factory(monkeypatch, tiny_png_bytes):
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def make() -> FakeOpenAI:
        return FakeOpenAI(tiny_png_bytes)
    return make
