from __future__ import annotations

import io
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image


@pytest.fixture
def tiny_png_bytes() -> bytes:
    """A 32x32 solid PNG; good enough for Claude-mocked paths."""
    img = Image.new("RGB", (32, 32), (240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def valid_plan() -> dict[str, Any]:
    """Minimum plan that satisfies Plan.model_validate (mirrors plan_schema's conftest).
    We don't import that conftest because test packages are independent."""
    return {
        "schema_version": "1.0",
        "units": "m",
        "meta": {"scale_source": "dimension_text", "confidence": 0.9, "warnings": []},
        "defaults": {"wall_height": 2.8, "floor_thickness": 0.2},
        "walls": [
            {"id": "w1", "a": [0, 0], "b": [6, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w2", "a": [6, 0], "b": [6, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w3", "a": [6, 5], "b": [0, 5], "thickness": 0.23, "height": 2.8, "exterior": True},
            {"id": "w4", "a": [0, 5], "b": [0, 0], "thickness": 0.23, "height": 2.8, "exterior": True},
        ],
        "openings": [
            {"id": "o1", "wall_id": "w1", "type": "door",
             "offset": 2.0, "width": 1.0, "height": 2.1, "sill": 0.0, "main_entrance": True},
        ],
        "rooms": [
            {"id": "r1", "name": "Studio", "type": "living",
             "polygon": [[0.23, 0.23], [5.77, 0.23], [5.77, 4.77], [0.23, 4.77]]},
        ],
    }


class FakeClaudeResponse:
    """Mimics an anthropic.types.Message enough for ClaudeExtractor._extract_tool_input."""
    def __init__(self, tool_input: dict, in_tokens: int = 100, out_tokens: int = 200, tool_use_id: str = "tu_1"):
        self.content = [SimpleNamespace(
            type="tool_use", id=tool_use_id, name="save_plan", input=tool_input,
        )]
        self.usage = SimpleNamespace(input_tokens=in_tokens, output_tokens=out_tokens)


class FakeAnthropic:
    """Mimics anthropic.Anthropic() for test-time dependency injection.
    Supply a list of tool-input dicts; each call returns the next one.
    """
    def __init__(self, tool_inputs: list[dict]):
        self._queued = list(tool_inputs)
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._queued:
            raise AssertionError("FakeAnthropic ran out of queued tool_inputs")
        return FakeClaudeResponse(self._queued.pop(0))


@pytest.fixture
def fake_anthropic_factory(monkeypatch):
    """Build a FakeAnthropic + inject the model env var."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _make(tool_inputs: list[dict]) -> FakeAnthropic:
        return FakeAnthropic(tool_inputs)
    return _make
