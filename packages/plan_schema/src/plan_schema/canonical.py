"""Canonical plan JSON + stable hash. Used as `plans.plan_hash` and inside
`shots.render_hash` so Blender can skip re-rendering unchanged scenes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(plan: BaseModel | dict[str, Any]) -> str:
    """Deterministic JSON encoding: sorted keys, no extra whitespace."""
    data = plan.model_dump(mode="json") if isinstance(plan, BaseModel) else plan
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def plan_hash(plan: BaseModel | dict[str, Any]) -> str:
    """sha256(canonical_json(plan)) — stable across machines and runs."""
    return hashlib.sha256(canonical_json(plan).encode("utf-8")).hexdigest()
