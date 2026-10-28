from __future__ import annotations

import pytest

from fpv_common.pricing import (
    claude_cost,
    load_prices,
    openai_image_cost,
    seedance_cost,
)


def test_load_prices_from_seed_contains_core_keys():
    prices = load_prices()
    assert "together.seedance-2.5.480p" in prices
    assert "together.seedance-2.5.720p" in prices
    assert "anthropic.claude-opus-5-5.input" in prices


def test_seedance_480p_8s():
    prices = load_prices()
    assert seedance_cost(prices, "480p", 8) == pytest.approx(0.115 * 8)


def test_openai_image_cost():
    prices = load_prices()
    c = openai_image_cost(prices, "gpt-image-2.5-sunburst", "1792x1024", 1)
    assert c == pytest.approx(0.25)


def test_claude_cost():
    prices = load_prices()
    c = claude_cost(prices, "claude-opus-5-5", 1_000_000, 1_000_000)
    assert c == pytest.approx(90.0)
