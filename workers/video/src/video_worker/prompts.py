"""Video prompt templates. Loaded from prompts/templates.yaml with an embedded
fallback for tests. VIDEO_MODE=frames_only is the only runtime mode (per M0)
but the standard variant stays for reference / future providers.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_FALLBACK = {
    "frames_only": (
        "Camera {move_words} through the space, {move_detail}. Style transition "
        "from CAD drawing to photorealistic, progressively. Start with the first "
        "frame and finish with this exact shot: the last frame."
    ),
    "standard_reference_video": (
        "Use the reference video as the driving video for camera movement. "
        "Camera {move_words} through the space. Style transition from CAD "
        "drawing to photorealistic, progressively. Start with the first frame "
        "and finish with this exact shot: the last frame."
    ),
}

_FALLBACK_MOVES = {
    "dolly": {"words": "moves slowly forward", "detail": "~1.5 m forward at eye height"},
    "pan":   {"words": "pans slowly",          "detail": "horizontal pan from left to right"},
    "crane": {"words": "rises slowly",         "detail": "~2 m vertical rise from desk height"},
    "orbit": {"words": "orbits the building once", "detail": "90° arc around the exterior"},
}


def _load_templates() -> tuple[dict, dict]:
    try:
        import yaml  # type: ignore
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "prompts" / "templates.yaml"
            if candidate.exists():
                data = yaml.safe_load(candidate.read_text())
                vid = data.get("video") or {}
                moves = data.get("camera_moves") or {}
                tmpl = {
                    "frames_only": vid.get("frames_only", _FALLBACK["frames_only"]),
                    "standard_reference_video": vid.get(
                        "standard_reference_video", _FALLBACK["standard_reference_video"],
                    ),
                }
                moves_out = {k: v for k, v in moves.items()} or _FALLBACK_MOVES
                return tmpl, moves_out
    except Exception as e:  # pragma: no cover
        log.warning("templates.yaml load failed (%s); using embedded fallback", e)
    return _FALLBACK, _FALLBACK_MOVES


def fill_video_prompt(mode: str, camera_move: str) -> str:
    if mode not in ("frames_only", "standard_reference_video"):
        raise ValueError(f"unknown video mode {mode!r}")
    templates, moves = _load_templates()
    if camera_move not in moves:
        raise ValueError(f"unknown camera move {camera_move!r}; expected one of {sorted(moves)}")
    m = moves[camera_move]
    return templates[mode].format(move_words=m["words"], move_detail=m["detail"])
