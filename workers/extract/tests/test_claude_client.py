from __future__ import annotations

import pytest

from extract.claude_client import ClaudeExtractor


def test_happy_path_no_repair(tiny_png_bytes, valid_plan, fake_anthropic_factory):
    client = fake_anthropic_factory([valid_plan])
    extractor = ClaudeExtractor(_client=client)

    result = extractor.extract(tiny_png_bytes)

    assert result.plan_json == valid_plan
    assert result.repaired is False
    assert result.input_tokens == 100
    assert result.output_tokens == 200
    assert len(client.calls) == 1
    assert client.calls[0]["tool_choice"] == {"type": "auto"}


def test_repair_round_on_invalid_first_response(tiny_png_bytes, valid_plan, fake_anthropic_factory):
    """First response is missing main_entrance → repair round should fix it."""
    broken = {**valid_plan,
              "openings": [{**valid_plan["openings"][0], "main_entrance": False}]}
    client = fake_anthropic_factory([broken, valid_plan])
    extractor = ClaudeExtractor(_client=client)

    result = extractor.extract(tiny_png_bytes)

    assert result.repaired is True
    assert result.plan_json == valid_plan
    assert len(client.calls) == 2
    # Second call must include a tool_result marked as an error.
    second_msgs = client.calls[1]["messages"]
    err_blocks = [b for m in second_msgs for b in (m.get("content") or [])
                  if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error")]
    assert err_blocks, "repair round should include an is_error=True tool_result"


def test_hard_fail_still_invalid_after_repair_raises(tiny_png_bytes, valid_plan, fake_anthropic_factory):
    """Both attempts fail validation → extract() raises."""
    broken1 = {**valid_plan, "openings": []}  # zero main_entrance
    broken2 = {**valid_plan, "walls": []}     # min_length violation
    client = fake_anthropic_factory([broken1, broken2])
    extractor = ClaudeExtractor(_client=client)

    with pytest.raises(Exception):
        extractor.extract(tiny_png_bytes)
    assert len(client.calls) == 2


def test_known_dimension_appears_in_user_text(tiny_png_bytes, valid_plan, fake_anthropic_factory):
    client = fake_anthropic_factory([valid_plan])
    extractor = ClaudeExtractor(_client=client)
    extractor.extract(tiny_png_bytes, known_dim_m=12.5)

    first_user_content = client.calls[0]["messages"][0]["content"]
    text_block = next(b for b in first_user_content if b["type"] == "text")
    assert "12.5" in text_block["text"]


def test_model_name_from_env(tiny_png_bytes, valid_plan, fake_anthropic_factory, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    client = fake_anthropic_factory([valid_plan])
    extractor = ClaudeExtractor(_client=client)
    extractor.extract(tiny_png_bytes)
    assert client.calls[0]["model"] == "claude-sonnet-4-6"


def test_missing_model_env_var_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_MODEL"):
        ClaudeExtractor(_client=object())
