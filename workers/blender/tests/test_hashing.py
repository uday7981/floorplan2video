from __future__ import annotations

from pathlib import Path

from blender_worker.hashing import (
    RENDER_OUTPUTS,
    cached_dir_for_shot,
    ensure_shot_dir,
    is_fully_cached,
    plan_hash,
    render_hash,
)


def test_plan_hash_deterministic(minimal_plan):
    assert plan_hash(minimal_plan) == plan_hash({**minimal_plan})


def test_plan_hash_changes_on_edit(minimal_plan):
    h1 = plan_hash(minimal_plan)
    minimal_plan["walls"][0]["thickness"] = 0.3
    assert plan_hash(minimal_plan) != h1


def test_render_hash_differs_per_shot(minimal_plan, minimal_shots):
    h0 = render_hash(minimal_plan, minimal_shots["shots"][0])
    h1 = render_hash(minimal_plan, minimal_shots["shots"][1])
    assert h0 != h1


def test_render_hash_changes_with_camera(minimal_plan, minimal_shots):
    s = minimal_shots["shots"][0]
    h0 = render_hash(minimal_plan, s)
    s2 = {**s, "camera": {**s["camera"], "duration_s": 8}}
    assert render_hash(minimal_plan, s2) != h0


def test_render_hash_changes_with_id_only(minimal_plan, minimal_shots):
    """Renaming a shot's id (e.g. for a different label) still invalidates."""
    s = minimal_shots["shots"][0]
    s2 = {**s, "id": "s1_renamed"}
    assert render_hash(minimal_plan, s2) != render_hash(minimal_plan, s)


def test_is_fully_cached_requires_all_outputs(tmp_path):
    out_root = tmp_path / "out"
    shot_hash = "abc123"
    d = ensure_shot_dir(out_root, shot_hash)
    assert not is_fully_cached(out_root, shot_hash)
    for name in RENDER_OUTPUTS:
        (d / name).write_bytes(b"x")
    assert is_fully_cached(out_root, shot_hash)
    # Zero-byte file counts as missing.
    (d / "driving.mp4").write_bytes(b"")
    assert not is_fully_cached(out_root, shot_hash)


def test_cached_dir_for_shot_uses_hash_path(tmp_path):
    d = cached_dir_for_shot(tmp_path, "deadbeef")
    assert d == tmp_path / "deadbeef"
