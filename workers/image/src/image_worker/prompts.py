"""Load end-frame prompt templates from prompts/templates.yaml and fill them
with the shot's style preset + room type.

The templates themselves live in prompts/templates.yaml so prompt tweaks
don't require a code change (hard rule).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    raise RuntimeError("PyYAML is required: pip install PyYAML") from e


def _templates_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "prompts" / "templates.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("prompts/templates.yaml not found walking up from " + str(here))


def load_end_frame_templates() -> dict[str, str]:
    data = yaml.safe_load(_templates_path().read_text())
    return data["end_frames"]


def fill_end_frame_prompt(shot_kind: str, preset: dict[str, str],
                          room_type: str | None = None) -> str:
    """shot_kind in {opening, room, exterior}. For 'room', room_type is required."""
    templates = load_end_frame_templates()
    if shot_kind not in templates:
        raise ValueError(f"no end-frame template for shot kind {shot_kind!r}")
    tmpl = templates[shot_kind]
    fields = {
        "materials": preset.get("materials", ""),
        "light": preset.get("light", ""),
        "setting": preset.get("setting", ""),
    }
    if shot_kind == "room":
        if not room_type:
            raise ValueError("room shots need room_type (living, kitchen, ...)")
        fields["room_type"] = room_type
    return tmpl.format(**fields)
