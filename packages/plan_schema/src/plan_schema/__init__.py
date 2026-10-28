"""Floor-plan JSON schema. Single source of truth for geometry."""

from .models import (
    Defaults,
    Meta,
    Opening,
    Plan,
    Room,
    Wall,
    OpeningType,
    RoomType,
    ScaleSource,
    SCHEMA_VERSION,
)
from .canonical import canonical_json, plan_hash

__all__ = [
    "Defaults",
    "Meta",
    "Opening",
    "Plan",
    "Room",
    "Wall",
    "OpeningType",
    "RoomType",
    "ScaleSource",
    "SCHEMA_VERSION",
    "canonical_json",
    "plan_hash",
]
