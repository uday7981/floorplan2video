"""Pure helpers for per-shot overlay text.

TRD rules:
- Opening shot: project title.
- Room shot: shot.label (make_shots.py already produces "NN RoomName").
- Exterior shot: shot.label.
- End card: 2s at the end, project name centred over the final frame.

Captions aren't in the shots.json schema yet (TODO: M7). For now, label is
whatever make_shots emitted plus any override the CLI supplies via a JSON
caption map.
"""
from __future__ import annotations


def label_for_shot(shot: dict, project_name: str, captions: dict[str, str] | None = None) -> str:
    """Return the text drawtext should overlay on this shot."""
    captions = captions or {}
    if shot["id"] in captions:
        return captions[shot["id"]]
    if shot["kind"] == "opening":
        return project_name
    return shot.get("label", "")


def end_card_text(project_name: str) -> str:
    return project_name
