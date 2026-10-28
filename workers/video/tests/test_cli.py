from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from video_worker import cli


def _write_json(tmp: Path, name: str, obj) -> Path:
    p = tmp / name
    p.write_text(json.dumps(obj))
    return p


def _write_png(tmp: Path, name: str) -> Path:
    p = tmp / name
    Image.new("RGB", (32, 32), (120, 120, 120)).save(p)
    return p


def test_cli_dry_run_without_approval(tmp_path, minimal_plan, minimal_shots_doc,
                                      fake_together_success):
    plan_p = _write_json(tmp_path, "plan.json", minimal_plan)
    shots_p = _write_json(tmp_path, "shots.json", minimal_shots_doc)
    start_p = _write_png(tmp_path, "start.png")
    end_p = _write_png(tmp_path, "end.png")
    out_p = tmp_path / "take.mp4"
    rc = cli.main([
        "--plan", str(plan_p), "--shots", str(shots_p),
        "--shot-id", "s_r01",
        "--start", str(start_p), "--end", str(end_p),
        "--out", str(out_p),
    ])
    assert rc == 0
    assert not out_p.exists()


def test_cli_happy_path_downloads_video(tmp_path, minimal_plan, minimal_shots_doc,
                                        fake_together_success):
    plan_p = _write_json(tmp_path, "plan.json", minimal_plan)
    shots_p = _write_json(tmp_path, "shots.json", minimal_shots_doc)
    start_p = _write_png(tmp_path, "start.png")
    end_p = _write_png(tmp_path, "end.png")
    out_p = tmp_path / "take.mp4"

    with patch("video_worker.cli.TogetherVideoProvider") as MockProvider, \
         patch("video_worker.cli._download") as mock_download:
        from video_worker.providers.base import PollResult, SubmitResult
        inst = MockProvider.return_value
        inst.submit.return_value = SubmitResult(provider_job_id="j1", est_cost_usd=0.0)
        inst.poll.return_value = PollResult(status="succeeded",
                                              output_url="https://x/out.mp4")
        rc = cli.main([
            "--plan", str(plan_p), "--shots", str(shots_p),
            "--shot-id", "s_r01",
            "--start", str(start_p), "--end", str(end_p),
            "--out", str(out_p),
            "--poll-interval", "0",
            "--yes-i-approve-cost",
        ])
    assert rc == 0
    mock_download.assert_called_once()
    # First arg: URL
    assert mock_download.call_args.args[0] == "https://x/out.mp4"
    # Second arg: output path
    assert mock_download.call_args.args[1] == out_p


def test_cli_fails_when_provider_fails(tmp_path, minimal_plan, minimal_shots_doc,
                                        fake_together_success):
    plan_p = _write_json(tmp_path, "plan.json", minimal_plan)
    shots_p = _write_json(tmp_path, "shots.json", minimal_shots_doc)
    start_p = _write_png(tmp_path, "start.png")
    end_p = _write_png(tmp_path, "end.png")
    out_p = tmp_path / "take.mp4"

    with patch("video_worker.cli.TogetherVideoProvider") as MockProvider:
        from video_worker.providers.base import PollResult, SubmitResult
        inst = MockProvider.return_value
        inst.submit.return_value = SubmitResult(provider_job_id="j1", est_cost_usd=0.0)
        inst.poll.return_value = PollResult(status="failed", error="boom")
        rc = cli.main([
            "--plan", str(plan_p), "--shots", str(shots_p),
            "--shot-id", "s_r01",
            "--start", str(start_p), "--end", str(end_p),
            "--out", str(out_p),
            "--poll-interval", "0",
            "--yes-i-approve-cost",
        ])
    assert rc == 1


def test_cli_rejects_unknown_shot(tmp_path, minimal_plan, minimal_shots_doc,
                                   fake_together_success):
    plan_p = _write_json(tmp_path, "plan.json", minimal_plan)
    shots_p = _write_json(tmp_path, "shots.json", minimal_shots_doc)
    start_p = _write_png(tmp_path, "start.png")
    end_p = _write_png(tmp_path, "end.png")
    out_p = tmp_path / "take.mp4"
    rc = cli.main([
        "--plan", str(plan_p), "--shots", str(shots_p),
        "--shot-id", "ghost",
        "--start", str(start_p), "--end", str(end_p),
        "--out", str(out_p),
        "--yes-i-approve-cost",
    ])
    assert rc == 2
