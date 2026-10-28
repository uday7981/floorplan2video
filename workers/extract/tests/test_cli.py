from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from extract import cli


def _write_png(tmp: Path, name="plan.png") -> Path:
    p = tmp / name
    Image.new("RGB", (200, 150), (240, 240, 240)).save(p)
    return p


def test_cli_happy_path_writes_plan_json(tmp_path, valid_plan, fake_anthropic_factory, capsys):
    in_path = _write_png(tmp_path)
    out_path = tmp_path / "plan.json"
    client = fake_anthropic_factory([valid_plan])

    with patch("extract.cli.ClaudeExtractor") as MockExtractor:
        instance = MockExtractor.return_value
        from extract.claude_client import ExtractResult
        instance.extract.return_value = ExtractResult(
            plan_json=valid_plan, input_tokens=1000, output_tokens=500, repaired=False
        )
        rc = cli.main(["--input", str(in_path), "--output", str(out_path)])

    assert rc == 0
    assert out_path.exists()
    saved = json.loads(out_path.read_text())
    assert saved == valid_plan

    err = capsys.readouterr().err
    assert "[cost]" in err
    assert "USD=" in err


def test_cli_missing_input_returns_2(tmp_path):
    out_path = tmp_path / "plan.json"
    rc = cli.main(["--input", str(tmp_path / "nope.png"), "--output", str(out_path)])
    assert rc == 2


def test_cli_extractor_failure_returns_1(tmp_path, valid_plan):
    in_path = _write_png(tmp_path)
    out_path = tmp_path / "plan.json"

    with patch("extract.cli.ClaudeExtractor") as MockExtractor:
        MockExtractor.return_value.extract.side_effect = RuntimeError("boom")
        rc = cli.main(["--input", str(in_path), "--output", str(out_path)])
    assert rc == 1
    assert not out_path.exists()
