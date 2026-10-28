"""Seedance 2.5 cost: per_second rate from supabase/seed.sql."""
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
class VideoCost:
    key: str
    duration_s: int
    per_second_usd: float
    usd: float


def seedance_cost(resolution: str, duration_s: int) -> VideoCost:
    prices = load_prices()
    key = f"together.seedance-2.5.{resolution}"
    if key not in prices:
        raise KeyError(f"no price row for '{key}' in supabase/seed.sql")
    unit, usd = prices[key]
    if unit != "per_second":
        raise ValueError(f"'{key}' has unit {unit!r}, expected per_second")
    return VideoCost(key=key, duration_s=duration_s,
                     per_second_usd=usd, usd=usd * duration_s)
