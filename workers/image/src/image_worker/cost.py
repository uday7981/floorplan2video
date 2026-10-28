"""OpenAI image-edit cost lookup from supabase/seed.sql.

Pricing table key format: openai.<model>.<size>  (e.g. openai.gpt-image-2-5.1792x1024).
In M5 this swaps to a Supabase pricing-table query; everything else stays.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SEED_ROW = re.compile(
    r"\(\s*'([^']+)'\s*,\s*'(per_second|per_image|per_mtok)'\s*,\s*([0-9]+\.[0-9]+|\d+)\s*\)",
    re.MULTILINE,
)


def _seed_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "supabase" / "seed.sql"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("supabase/seed.sql not found walking up from " + str(here))


def load_prices() -> dict[str, tuple[str, float]]:
    text = _seed_path().read_text()
    return {m.group(1): (m.group(2), float(m.group(3))) for m in _SEED_ROW.finditer(text)}


@dataclass
class ImageCost:
    model: str
    size: str
    count: int
    usd: float


def openai_image_cost(model: str, size: str, count: int = 1) -> ImageCost:
    prices = load_prices()
    key = f"openai.{model}.{size}"
    if key not in prices:
        raise KeyError(f"no price row for '{key}' in supabase/seed.sql")
    unit, usd = prices[key]
    if unit != "per_image":
        raise ValueError(f"'{key}' has unit {unit!r}, expected per_image")
    return ImageCost(model=model, size=size, count=count, usd=usd * count)
