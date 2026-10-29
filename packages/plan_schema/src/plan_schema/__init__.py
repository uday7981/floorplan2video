"""Floor-plan JSON schema (v2.0). Single source of truth for geometry."""

from .models import (
    Defaults,
    Level,
    Meta,
    Opening,
    OpeningType,
    Plan,
    Room,
    RoomType,
    SCHEMA_VERSION,
    ScaleSource,
    Stair,
    StairDirection,
    Void,
    Wall,
)
from .canonical import canonical_json, plan_hash

__all__ = [
    "Defaults",
    "Level",
    "Meta",
    "Opening",
    "OpeningType",
    "Plan",
    "Room",
    "RoomType",
    "SCHEMA_VERSION",
    "ScaleSource",
    "Stair",
    "StairDirection",
    "Void",
    "Wall",
    "canonical_json",
    "plan_hash",
]
