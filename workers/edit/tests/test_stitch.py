from __future__ import annotations

import pytest

from edit_worker.stitch import (
    FPS,
    HEIGHT,
    TakeSpec,
    WIDTH,
    XFADE_DUR,
    build_endcard_filtergraph,
    build_stitch_filtergraph,
    pick_font,
)


def _spec(duration=5.0, label=""):
    return TakeSpec(source_path="x.mp4", duration_s=duration, label_text=label)


def test_single_take_no_xfade():
    fg, final, total = build_stitch_filtergraph([_spec(5.0, "01 Living")], font_path=None)
    assert final == "v0"
    assert total == pytest.approx(5.0)
    assert "[v0]" in fg
    assert "xfade" not in fg


def test_two_takes_single_xfade():
    takes = [_spec(5.0, "01 Living"), _spec(5.0, "02 Kitchen")]
    fg, final, total = build_stitch_filtergraph(takes, font_path=None)
    assert final == "xf1"
    # 5 + 5 - 0.3 = 9.7
    assert total == pytest.approx(10 - XFADE_DUR)
    # xfade offset should be 5 - 0.3 = 4.7
    assert "offset=4.700" in fg


def test_three_takes_cumulative_offsets():
    takes = [_spec(5.0, "a"), _spec(5.0, "b"), _spec(8.0, "c")]
    fg, final, total = build_stitch_filtergraph(takes, font_path=None)
    assert final == "xf2"
    # 5 + 5 + 8 - 0.3*2 = 17.4
    assert total == pytest.approx(5 + 5 + 8 - XFADE_DUR * 2)
    # Second xfade offset = 9.7 - 0.3 = 9.4
    assert "offset=4.700" in fg
    assert "offset=9.400" in fg


def test_normalisation_targets_fixed_resolution_and_fps():
    fg, _, _ = build_stitch_filtergraph([_spec(5.0, "")], font_path=None)
    assert f"scale={WIDTH}:{HEIGHT}" in fg
    assert f"fps={FPS}" in fg
    assert "yuv420p" in fg


def test_label_present_when_text_given():
    fg, _, _ = build_stitch_filtergraph([_spec(5.0, "01 Living")], font_path=None)
    assert "drawtext=" in fg
    assert "01 Living" in fg


def test_label_absent_when_text_empty():
    fg, _, _ = build_stitch_filtergraph([_spec(5.0, "")], font_path=None)
    assert "drawtext=" not in fg


def test_colon_in_label_escaped():
    fg, _, _ = build_stitch_filtergraph([_spec(5.0, "Hello: world")], font_path=None)
    # Raw ':' between drawtext options would be parsed as separator — must be escaped.
    assert r"Hello\: world" in fg


def test_font_included_when_supplied():
    fg, _, _ = build_stitch_filtergraph([_spec(5.0, "x")], font_path="/tmp/x.ttf")
    assert "fontfile='/tmp/x.ttf'" in fg


def test_endcard_filtergraph_centers_text():
    fg = build_endcard_filtergraph("last.png", "Oakhill", font_path=None, duration_s=2.0)
    assert "Oakhill" in fg
    assert "x=(w-text_w)/2" in fg
    assert "y=(h-text_h)/2" in fg


def test_empty_takes_rejected():
    with pytest.raises(ValueError, match="no takes"):
        build_stitch_filtergraph([], font_path=None)


def test_pick_font_explicit(tmp_path):
    f = tmp_path / "x.ttf"
    f.write_bytes(b"dummy")
    assert pick_font(str(f)) == str(f)
