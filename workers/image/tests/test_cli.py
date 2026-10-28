from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from image_worker import cli


def _write(tmp: Path, name: str, obj) -> Path:
    p = tmp / name
    p.write_text(json.dumps(obj))
    return p


def _write_png(tmp: Path, name: str) -> Path:
    p = tmp / name
    Image.new("RGB", (1280, 720), (120, 120, 120)).save(p)
    return p


def test_cli_dry_run_without_approval(tmp_path, minimal_plan, minimal_shots_doc,
                                       fake_openai_factory, caplog):
    plan_p = _write(tmp_path, "plan.json", minimal_plan)
    shots_p = _write(tmp_path, "shots.json", minimal_shots_doc)
    clay_p = _write_png(tmp_path, "clay.png")
    out_p = tmp_path / "end.png"

    rc = cli.main([
        "--plan", str(plan_p), "--shots", str(shots_p),
        "--shot-id", "s_r01",
        "--clay", str(clay_p), "--out", str(out_p),
    ])
    assert rc == 0
    assert not out_p.exists()  # dry run writes nothing


def test_cli_happy_path_writes_png(tmp_path, minimal_plan, minimal_shots_doc,
                                     fake_openai_factory):
    plan_p = _write(tmp_path, "plan.json", minimal_plan)
    shots_p = _write(tmp_path, "shots.json", minimal_shots_doc)
    clay_p = _write_png(tmp_path, "clay.png")
    out_p = tmp_path / "end.png"

    client = fake_openai_factory()
    with patch("image_worker.cli.OpenAIImageEditor") as MockEditor:
        MockEditor.return_value.edit.return_value.png_bytes = clay_p.read_bytes()
        MockEditor.return_value.edit.return_value.model = "gpt-image-2-5"
        MockEditor.return_value.edit.return_value.requested_size = "1792x1024"
        rc = cli.main([
            "--plan", str(plan_p), "--shots", str(shots_p),
            "--shot-id", "s_r01",
            "--clay", str(clay_p), "--out", str(out_p),
            "--yes-i-approve-cost",
        ])
    assert rc == 0
    assert out_p.exists()
    img = Image.open(out_p)
    assert img.size == (1280, 720)  # crop-resized to final target


def test_cli_rejects_unknown_shot_id(tmp_path, minimal_plan, minimal_shots_doc,
                                      fake_openai_factory):
    plan_p = _write(tmp_path, "plan.json", minimal_plan)
    shots_p = _write(tmp_path, "shots.json", minimal_shots_doc)
    clay_p = _write_png(tmp_path, "clay.png")
    out_p = tmp_path / "end.png"
    rc = cli.main([
        "--plan", str(plan_p), "--shots", str(shots_p),
        "--shot-id", "nope",
        "--clay", str(clay_p), "--out", str(out_p),
        "--yes-i-approve-cost",
    ])
    assert rc == 2


def test_cli_missing_clay_returns_2(tmp_path, minimal_plan, minimal_shots_doc,
                                     fake_openai_factory):
    plan_p = _write(tmp_path, "plan.json", minimal_plan)
    shots_p = _write(tmp_path, "shots.json", minimal_shots_doc)
    out_p = tmp_path / "end.png"
    rc = cli.main([
        "--plan", str(plan_p), "--shots", str(shots_p),
        "--shot-id", "s_r01",
        "--clay", str(tmp_path / "no_such.png"),
        "--out", str(out_p),
        "--yes-i-approve-cost",
    ])
    assert rc == 2
