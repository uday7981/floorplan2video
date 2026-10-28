from __future__ import annotations

import pytest

from video_worker.cost import load_prices, seedance_cost


def test_prices_load_from_seed():
    prices = load_prices()
    assert "together.seedance-2.5.480p" in prices
    assert "together.seedance-2.5.720p" in prices


def test_seedance_480p_4s():
    c = seedance_cost("480p", 4)
    assert c.usd == pytest.approx(0.115 * 4)
    assert c.per_second_usd == pytest.approx(0.115)


def test_seedance_720p_8s():
    c = seedance_cost("720p", 8)
    assert c.usd == pytest.approx(0.249 * 8)


def test_unknown_resolution():
    with pytest.raises(KeyError, match="no price row"):
        seedance_cost("1080p", 4)
