from __future__ import annotations

from edit_worker.labels import end_card_text, label_for_shot


def _shot(kind: str, label: str = "", shot_id: str = "sx", room_id: str = "r") -> dict:
    s = {"id": shot_id, "kind": kind, "label": label}
    if kind == "room":
        s["room_id"] = room_id
    return s


def test_opening_uses_project_title():
    assert label_for_shot(_shot("opening", "Welcome"), "Oakhill Residence") == "Oakhill Residence"


def test_room_uses_label():
    assert label_for_shot(_shot("room", "01 Living"), "Oakhill") == "01 Living"


def test_exterior_uses_label():
    assert label_for_shot(_shot("exterior", "Exterior Orbit"), "Oakhill") == "Exterior Orbit"


def test_captions_override_for_any_kind():
    captions = {"sx": "Hand-written caption"}
    assert label_for_shot(_shot("room", "01 Living"), "Oakhill", captions) == "Hand-written caption"


def test_endcard_text():
    assert end_card_text("Oakhill Residence") == "Oakhill Residence"
