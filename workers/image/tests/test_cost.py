from __future__ import annotations

import pytest

from image_worker.cost import openai_image_cost, load_prices


def test_prices_load_from_seed():
    prices = load_prices()
    assert "openai.gpt-image-2.5-sunburst.1792x1024" in prices


def test_openai_image_cost_single():
    c = openai_image_cost("gpt-image-2.5-sunburst", "1792x1024", count=1)
    assert c.usd == pytest.approx(0.25)
    assert c.count == 1


def test_openai_image_cost_scales_with_count():
    c = openai_image_cost("gpt-image-2.5-sunburst", "1024x1024", count=3)
    assert c.usd == pytest.approx(0.167 * 3)


def test_unknown_size_raises():
    with pytest.raises(KeyError, match="no price row"):
        openai_image_cost("gpt-image-2.5-sunburst", "999x999")
