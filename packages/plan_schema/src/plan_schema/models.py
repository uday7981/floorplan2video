"""Pydantic v2 models for the plan JSON. These are the authoritative types;
Blender's build.py and the browser's three.js preview both read from this
shape. Keep validation strict so a bad plan can't propagate downstream.

Conventions (from TRD):
  - Units are metres.
  - Origin is the plan's bottom-left corner, x right, y up, z up (height).
  - All coordinates round to 0.01 m.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import List, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .validators import polygon_area, polygon_is_simple

SCHEMA_VERSION = "1.0"

# Validation bounds (TRD "Validation rules").
WALL_MIN_LENGTH_M = 0.3
WALL_MIN_THICKNESS_M = 0.05
WALL_MAX_THICKNESS_M = 0.6
ROOM_MIN_AREA_M2 = 1.0
BBOX_MIN_SIDE_M = 3.0
BBOX_MAX_SIDE_M = 60.0


# ---------- Enums ----------

class ScaleSource(str, Enum):
    dimension_text = "dimension_text"
    scale_bar = "scale_bar"
    user_input = "user_input"


class OpeningType(str, Enum):
    door = "door"
    window = "window"
    opening = "opening"


class RoomType(str, Enum):
    living = "living"
    kitchen = "kitchen"
    dining = "dining"
    bedroom = "bedroom"
    bath = "bath"
    terrace = "terrace"
    other = "other"


# ---------- Submodels ----------

Point2 = Tuple[float, float]


def _round01(v: float) -> float:
    """Round to 0.01 m per TRD convention."""
    return round(float(v), 2)


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scale_source: ScaleSource
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wall_height: float = Field(gt=0, description="Default wall height in metres.")
    floor_thickness: float = Field(gt=0, description="Floor slab thickness in metres.")


class Wall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    a: Point2 = Field(description="Centreline start point (x, y) in metres.")
    b: Point2 = Field(description="Centreline end point (x, y) in metres.")
    thickness: float = Field(ge=WALL_MIN_THICKNESS_M, le=WALL_MAX_THICKNESS_M)
    height: float = Field(gt=0)
    exterior: bool = False

    @field_validator("a", "b", mode="before")
    @classmethod
    def _round_points(cls, v):
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (_round01(v[0]), _round01(v[1]))
        return v

    @model_validator(mode="after")
    def _length(self):
        if self.length < WALL_MIN_LENGTH_M:
            raise ValueError(
                f"wall {self.id} length {self.length:.3f} m < min {WALL_MIN_LENGTH_M} m"
            )
        return self

    @property
    def length(self) -> float:
        dx = self.b[0] - self.a[0]
        dy = self.b[1] - self.a[1]
        return math.hypot(dx, dy)


class Opening(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    wall_id: str = Field(min_length=1)
    type: OpeningType
    offset: float = Field(ge=0, description="Metres from wall start (a) to opening centre.")
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    sill: float = Field(ge=0, description="Height from floor to bottom of opening.")
    main_entrance: bool = False

    @field_validator("offset", "width", "height", "sill", mode="before")
    @classmethod
    def _round(cls, v):
        return _round01(v) if v is not None else v


class Room(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str
    type: RoomType
    polygon: List[Point2] = Field(min_length=3)

    @field_validator("polygon", mode="before")
    @classmethod
    def _round_poly(cls, v):
        if isinstance(v, list):
            return [(_round01(p[0]), _round01(p[1])) for p in v]
        return v

    @model_validator(mode="after")
    def _polygon_valid(self):
        if not polygon_is_simple(self.polygon):
            raise ValueError(f"room {self.id} polygon is self-intersecting")
        area = polygon_area(self.polygon)
        if area < ROOM_MIN_AREA_M2:
            raise ValueError(
                f"room {self.id} area {area:.3f} m² < min {ROOM_MIN_AREA_M2} m²"
            )
        return self


# ---------- Root ----------

class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION)
    units: str = Field(default="m", pattern="^m$")
    meta: Meta
    defaults: Defaults
    walls: List[Wall] = Field(min_length=1)
    openings: List[Opening] = Field(default_factory=list)
    rooms: List[Room] = Field(min_length=1)

    @model_validator(mode="after")
    def _cross_refs(self):
        # Unique IDs across each collection.
        for name, items in (("walls", self.walls), ("openings", self.openings), ("rooms", self.rooms)):
            ids = [i.id for i in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{name} contains duplicate ids")

        # Openings: wall_id must exist; opening fits inside its wall.
        walls_by_id = {w.id: w for w in self.walls}
        for op in self.openings:
            if op.wall_id not in walls_by_id:
                raise ValueError(f"opening {op.id} references unknown wall {op.wall_id}")
            w = walls_by_id[op.wall_id]
            if op.offset - op.width / 2 < 0 or op.offset + op.width / 2 > w.length + 1e-6:
                raise ValueError(
                    f"opening {op.id} doesn't fit in wall {w.id}: "
                    f"[{op.offset - op.width/2:.3f}, {op.offset + op.width/2:.3f}] vs wall length {w.length:.3f}"
                )
            if op.sill + op.height > w.height + 1e-6:
                raise ValueError(
                    f"opening {op.id} top ({op.sill + op.height:.3f} m) exceeds wall height ({w.height:.3f} m)"
                )

        # Exactly one main_entrance.
        main_count = sum(1 for op in self.openings if op.main_entrance)
        if main_count != 1:
            raise ValueError(
                f"exactly one opening must have main_entrance=true (found {main_count})"
            )

        # Overall bounding box within [3, 60] m per side.
        xs = [p for w in self.walls for p in (w.a[0], w.b[0])]
        ys = [p for w in self.walls for p in (w.a[1], w.b[1])]
        width = max(xs) - min(xs)
        depth = max(ys) - min(ys)
        for name, side in (("width", width), ("depth", depth)):
            if side < BBOX_MIN_SIDE_M or side > BBOX_MAX_SIDE_M:
                raise ValueError(
                    f"building {name} {side:.2f} m outside allowed [{BBOX_MIN_SIDE_M}, {BBOX_MAX_SIDE_M}] m — scale is likely wrong"
                )

        return self
