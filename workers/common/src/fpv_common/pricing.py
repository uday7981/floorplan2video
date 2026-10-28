"""Unified pricing lookup. In M5 this reads from the Supabase `pricing` table
(single source of truth per the hard rule); if the table is unreachable we fall
back to parsing supabase/seed.sql so dev + tests still work.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SEED_ROW = re.compile(
    r"\(\s*'([^']+)'\s*,\s*'(per_second|per_image|per_mtok)'\s*,\s*([0-9]+\.[0-9]+|\d+)\s*\)",
    re.MULTILINE,
)


def _seed_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        c = parent / "supabase" / "seed.sql"
        if c.exists():
            return c
    raise FileNotFoundError("supabase/seed.sql not found")


def load_from_seed() -> dict[str, tuple[str, float]]:
    text = _seed_path().read_text()
    return {m.group(1): (m.group(2), float(m.group(3))) for m in _SEED_ROW.finditer(text)}


def load_from_db(db) -> dict[str, tuple[str, float]]:
    rows = db.fetchall("select key, unit, usd from pricing")
    return {r["key"]: (r["unit"], float(r["usd"])) for r in rows}


def load_prices(db=None) -> dict[str, tuple[str, float]]:
    if db is not None:
        try:
            prices = load_from_db(db)
            if prices:
                return prices
        except Exception:
            pass
    return load_from_seed()


# ---- estimators ----

def seedance_cost(prices: dict, resolution: str, duration_s: int) -> float:
    key = f"together.seedance-2.5.{resolution}"
    unit, usd = prices[key]
    assert unit == "per_second"
    return usd * duration_s


def openai_image_cost(prices: dict, model: str, size: str, count: int = 1) -> float:
    key = f"openai.{model}.{size}"
    unit, usd = prices[key]
    assert unit == "per_image"
    return usd * count


def claude_cost(prices: dict, model: str, in_tokens: int, out_tokens: int) -> float:
    i_u, i_v = prices[f"anthropic.{model}.input"]
    o_u, o_v = prices[f"anthropic.{model}.output"]
    assert i_u == "per_mtok" and o_u == "per_mtok"
    return (in_tokens * i_v + out_tokens * o_v) / 1_000_000
