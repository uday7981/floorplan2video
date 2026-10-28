from __future__ import annotations

import json
from pathlib import Path

import pytest

from edit_worker import cli
from edit_worker.ffmpeg_run import ffprobe

from .conftest import requires_drawtext, requires_ffmpeg


@requires_drawtext
def test_cli_stitches_three_tiny_clips(tmp_path, plan_dict, shots_doc, make_test_clip):
    plan_p = tmp_path / "plan.json"
    plan_p.write_text(json.dumps(plan_dict))
    shots_p = tmp_path / "shots.json"
    shots_p.write_text(json.dumps(shots_doc))
    takes = tmp_path / "takes"
    takes.mkdir()
    make_test_clip(takes / "s_opening.mp4", duration_s=5.0, color="red", label="opening")
    make_test_clip(takes / "s_r01.mp4",     duration_s=5.0, color="green", label="r01")
    make_test_clip(takes / "s_exterior.mp4", duration_s=8.0, color="blue", label="ext")

    out = tmp_path / "final.mp4"
    rc = cli.main([
        "--plan", str(plan_p),
        "--shots", str(shots_p),
        "--takes-dir", str(takes),
        "--project-name", "Oakhill Residence",
        "--out", str(out),
    ])
    assert rc == 0
    assert out.exists() and out.stat().st_size > 0

    info = ffprobe(out)
    assert info.width == 1280
    assert info.height == 720
    assert abs(info.fps - 24.0) < 0.1
    # 5 + 5 + 8 - 0.3*2 = 17.4; + 2s end card = 19.4; concat demuxer gives
    # the sum of parts, allow a small ffmpeg rounding window.
    expected = 17.4 + 2.0
    assert abs(info.duration_s - expected) < 0.5, info.duration_s


@requires_drawtext
def test_cli_handles_missing_takes_gracefully(tmp_path, plan_dict, shots_doc, make_test_clip):
    plan_p = tmp_path / "plan.json"
    plan_p.write_text(json.dumps(plan_dict))
    shots_p = tmp_path / "shots.json"
    shots_p.write_text(json.dumps(shots_doc))
    takes = tmp_path / "takes"
    takes.mkdir()
    # Only one take present; the others are skipped with a warning.
    make_test_clip(takes / "s_r01.mp4", duration_s=5.0, color="green", label="r01")

    out = tmp_path / "final.mp4"
    rc = cli.main([
        "--plan", str(plan_p),
        "--shots", str(shots_p),
        "--takes-dir", str(takes),
        "--project-name", "Oakhill",
        "--out", str(out),
    ])
    assert rc == 0
    info = ffprobe(out)
    # 5 s shot + 2 s end card = 7 s
    assert abs(info.duration_s - 7.0) < 0.5


def test_cli_exits_2_if_no_takes(tmp_path, plan_dict, shots_doc):
    plan_p = tmp_path / "plan.json"
    plan_p.write_text(json.dumps(plan_dict))
    shots_p = tmp_path / "shots.json"
    shots_p.write_text(json.dumps(shots_doc))
    empty = tmp_path / "takes"
    empty.mkdir()
    out = tmp_path / "final.mp4"
    rc = cli.main([
        "--plan", str(plan_p),
        "--shots", str(shots_p),
        "--takes-dir", str(empty),
        "--project-name", "Oakhill",
        "--out", str(out),
    ])
    assert rc == 2
