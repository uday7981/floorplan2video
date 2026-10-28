from __future__ import annotations

import pytest

from image_worker.prompts import fill_end_frame_prompt, load_end_frame_templates


def test_templates_have_all_three_kinds():
    tmpls = load_end_frame_templates()
    assert {"room", "opening", "exterior"} <= set(tmpls.keys())


def test_room_prompt_interpolates(preset):
    out = fill_end_frame_prompt("room", preset, room_type="living")
    assert "oak" in out
    assert "3000K" in out
    assert "forest" in out
    assert "living" in out


def test_exterior_prompt_no_room_type(preset):
    out = fill_end_frame_prompt("exterior", preset)
    assert "oak" in out
    assert "exterior" in out.lower()


def test_opening_prompt_only_needs_light(preset):
    out = fill_end_frame_prompt("opening", preset)
    assert "3000K" in out


def test_room_prompt_requires_room_type(preset):
    with pytest.raises(ValueError, match="room_type"):
        fill_end_frame_prompt("room", preset)


def test_unknown_shot_kind_rejected(preset):
    with pytest.raises(ValueError, match="no end-frame template"):
        fill_end_frame_prompt("flyover", preset)
