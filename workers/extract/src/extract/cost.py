"""Cost tracker for the extract CLI.

Prices are parsed from `supabase/seed.sql` so there is a single source of truth
at this stage. When the API comes online in M5, swap this for a Supabase
`pricing` table lookup; everything else here stays the same.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Rows: ('provider.model.flavor', 'per_second|per_image|per_mtok', <float>)
_SEED_ROW = re.compile(
    r"\(\s*'([^']+)'\s*,\s*'(per_second|per_image|per_mtok)'\s*,\s*([0-9]+\.[0-9]+|\d+)\s*\)",
    re.MULTILINE,
)


def _seed_path() -> Path:
    # Walk up to the repo root.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "supabase" / "seed.sql"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("supabase/seed.sql not found walking up from " + str(here))


def load_prices() -> dict[str, tuple[str, float]]:
    path = _seed_path()
    text = path.read_text()
    return {m.group(1): (m.group(2), float(m.group(3))) for m in _SEED_ROW.finditer(text)}


@dataclass
class ClaudeCost:
    model: str
    input_tokens: int
    output_tokens: int
    input_usd: float
    output_usd: float

    @property
    def total_usd(self) -> float:
        return self.input_usd + self.output_usd


def claude_cost(model: str, input_tokens: int, output_tokens: int) -> ClaudeCost:
    prices = load_prices()
    in_key, out_key = f"anthropic.{model}.input", f"anthropic.{model}.output"
    if in_key not in prices or out_key not in prices:
        raise KeyError(
            f"no price rows for model '{model}' in supabase/seed.sql "
            f"(looked for {in_key} and {out_key})"
        )
    in_per_mtok = prices[in_key][1]
    out_per_mtok = prices[out_key][1]
    return ClaudeCost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_usd=input_tokens / 1_000_000 * in_per_mtok,
        output_usd=output_tokens / 1_000_000 * out_per_mtok,
    )
