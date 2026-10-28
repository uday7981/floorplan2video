from __future__ import annotations

import pytest

from video_worker.prompts import fill_video_prompt


def test_frames_only_dolly():
    out = fill_video_prompt("frames_only", "dolly")
    assert "forward" in out
    assert "CAD" in out
    assert "last frame" in out


def test_frames_only_orbit():
    out = fill_video_prompt("frames_only", "orbit")
    assert "orbits" in out or "arc" in out


def test_standard_reference_video_dolly():
    out = fill_video_prompt("standard_reference_video", "dolly")
    assert "reference video" in out


def test_unknown_mode():
    with pytest.raises(ValueError, match="unknown video mode"):
        fill_video_prompt("made_up", "dolly")


def test_unknown_move():
    with pytest.raises(ValueError, match="unknown camera move"):
        fill_video_prompt("frames_only", "zoom")
