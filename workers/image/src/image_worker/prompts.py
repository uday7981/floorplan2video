"""Load boundary-frame prompt templates from prompts/templates.yaml.

Three variants per TRD v2.0: room / exterior / stair-landing. Each takes
{materials}, {light}, {setting} from the project's style preset, plus
{room_type} for the room variant (free-text; prefer room.name over
room.type for specificity).
"""
from __future__ import annotations

from pathlib import Path

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


def load_boundary_frame_templates() -> dict[str, str]:
    data = yaml.safe_load(_templates_path().read_text())
    # Keep the old `end_frames` section name for template reuse — same three
    # variants, now serving boundary frames.
    return data["end_frames"]


# Back-compat alias so legacy imports keep working during the v2 migration.
load_end_frame_templates = load_boundary_frame_templates


def fill_boundary_frame_prompt(role: str, preset: dict[str, str],
                               room_type: str | None = None) -> str:
    """role is the segment role from journey.json.
      walkthrough / stair → room template
      exterior            → exterior template
      opening / descent   → opening template (handled by the one CAD→photoreal
                            transition in the video worker; here we still
                            generate a boundary frame to feed Seedance)
    """
    templates = load_boundary_frame_templates()
    # Accept both new segment roles and legacy shot kinds (room/exterior/opening).
    if role in ("walkthrough", "stair", "ending", "room"):
        tmpl_key = "room"
    elif role == "exterior":
        tmpl_key = "exterior"
    elif role in ("opening", "descent"):
        tmpl_key = "opening"
    else:
        raise ValueError(f"no end-frame template for shot kind {role!r}")
    tmpl = templates[tmpl_key]
    fields = {
        "materials": preset.get("materials", ""),
        "light": preset.get("light", ""),
        "setting": preset.get("setting", ""),
    }
    if tmpl_key == "room":
        if not room_type:
            raise ValueError("room shots need room_type (living, kitchen, ...)")
        fields["room_type"] = room_type
    return tmpl.format(**fields)


# Back-compat alias
fill_end_frame_prompt = fill_boundary_frame_prompt
