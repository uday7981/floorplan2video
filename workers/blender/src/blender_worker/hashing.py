"""render_hash + file-cache check.

TRD: `shots.render_hash = hash(plan_hash + camera)` — if the three output
files already exist for a given hash, that shot is skipped.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RENDER_OUTPUTS = ("driving.mp4", "start.png", "clay.png")


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_hash(plan: dict) -> str:
    return sha256_hex(canonical_json(plan))


def render_hash(plan: dict, shot: dict) -> str:
    """hash( plan_json + shot_id + camera ). Short-circuits re-renders.

    We include shot_id as well as camera so renaming a shot (which keeps the
    camera the same) still invalidates the cache — labels end up on the clip.
    """
    camera_blob = {
        "id": shot["id"],
        "kind": shot["kind"],
        "room_id": shot.get("room_id"),
        "camera": shot["camera"],
    }
    return sha256_hex(plan_hash(plan) + "|" + canonical_json(camera_blob))


def cached_dir_for_shot(out_root: Path, shot_hash: str) -> Path:
    return out_root / shot_hash


def is_fully_cached(out_root: Path, shot_hash: str) -> bool:
    d = cached_dir_for_shot(out_root, shot_hash)
    return all((d / name).exists() and (d / name).stat().st_size > 0
               for name in RENDER_OUTPUTS)


def ensure_shot_dir(out_root: Path, shot_hash: str) -> Path:
    d = cached_dir_for_shot(out_root, shot_hash)
    d.mkdir(parents=True, exist_ok=True)
    return d
