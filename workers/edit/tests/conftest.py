from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _ffmpeg_has_filter(name: str) -> bool:
    if not HAS_FFMPEG:
        return False
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                       capture_output=True, text=True)
    return any(line.strip().endswith(name) or f" {name} " in line for line in r.stdout.splitlines())


HAS_DRAWTEXT = _ffmpeg_has_filter("drawtext")
requires_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not on PATH")
requires_drawtext = pytest.mark.skipif(
    not HAS_DRAWTEXT,
    reason="ffmpeg built without libfreetype (no drawtext filter) — common on brew ffmpeg",
)


def _make_test_clip(path: Path, duration_s: float, color: str = "red", label: str = "A") -> None:
    """Generate a tiny synthetic clip for integration tests. No drawtext —
    we leave on-clip label testing to the real CLI run, which does its own
    drawtext filter (and gets skipped if the local ffmpeg lacks it)."""
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"color=c={color}:s=320x180:d={duration_s}:r=24",
        "-c:v", "libx264", "-crf", "30", "-pix_fmt", "yuv420p",
        "-an",
        str(path),
    ], check=True)


@pytest.fixture
def make_test_clip():
    return _make_test_clip


@pytest.fixture
def plan_dict() -> dict:
    return {"rooms": [{"id": "R1", "name": "Living", "type": "living",
                       "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]}]}


@pytest.fixture
def shots_doc() -> dict:
    return {
        "schema_version": "1.0",
        "project_type": "house",
        "style_preset": {"materials": "oak", "light": "3000K", "setting": "forest"},
        "shots": [
            {"id": "s_opening", "ord": 0, "kind": "opening", "label": "Welcome",
             "camera": {"move": "crane", "duration_s": 5, "lens_mm": 35, "fps": 24}},
            {"id": "s_r01", "ord": 1, "kind": "room", "room_id": "R1",
             "label": "01 Sitting Room",
             "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
            {"id": "s_exterior", "ord": 2, "kind": "exterior", "label": "Exterior",
             "camera": {"move": "orbit", "duration_s": 8, "lens_mm": 28, "fps": 24}},
        ],
    }
