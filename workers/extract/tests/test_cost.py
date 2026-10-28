from __future__ import annotations

import pytest

from extract.cost import claude_cost, load_prices


def test_prices_load_from_seed():
    prices = load_prices()
    # Seed must contain the models we care about.
    assert "anthropic.claude-opus-5-5.input" in prices
    assert "anthropic.claude-opus-5-5.output" in prices
    assert "together.seedance-2.5.480p" in prices


def test_claude_cost_arithmetic():
    # 1M input tokens at $15 → $15; 1M output tokens at $75 → $75.
    c = claude_cost("claude-opus-5-5", 1_000_000, 1_000_000)
    assert c.input_usd == pytest.approx(15.0)
    assert c.output_usd == pytest.approx(75.0)
    assert c.total_usd == pytest.approx(90.0)


def test_unknown_model_raises():
    with pytest.raises(KeyError, match="no price rows"):
        claude_cost("claude-ghost-9", 100, 100)
