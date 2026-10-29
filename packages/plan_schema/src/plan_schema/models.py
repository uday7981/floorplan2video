"""Pydantic v2 models for the plan JSON. These are the authoritative types;
Blender's build.py and the browser's three.js preview both read from this
shape. Keep validation strict so a bad plan can't propagate downstream.

Conventions (from TRD):
  - Units are metres.
  - Origin is the plan's bottom-left corner, x right, y up, z up (height).
  - All coordinates round to 0.01 m.

SCHEMA v2 — multi-storey support (2026-10-29)
  - Floors live in `plan.floors`; walls/openings/rooms are nested per floor.
  - `plan.vertical_connections` carries stairs / voids between floors.
  - v1 input (flat walls/openings/rooms at root) is auto-wrapped into a
    single ground floor, so no existing plan.json breaks.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import List, Literal, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .validators import polygon_area, polygon_is_simple

SCHEMA_VERSION = "2.0"

# Validation bounds (TRD "Validation rules").
WALL_MIN_LENGTH_M = 0.3
WALL_MIN_THICKNESS_M = 0.05
WALL_MAX_THICKNESS_M = 0.6
ROOM_MIN_AREA_M2 = 1.0
BBOX_MIN_SIDE_M = 3.0
BBOX_MAX_SIDE_M = 60.0
MAX_FLOORS = 6  # safety ceiling; most residential plans are 1–4


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
    """Common room types the extractor + image prompt both understand.

    Future-proofing: `other` is the catch-all for anything not listed. The
    image prompt uses `room.name` (free text) as the primary descriptor —
    so a well-named room produces a correct image even when the type here
    is `other`. Expand this enum as architectural vocabularies grow.
    """
    # living / shared
    living = "living"
    dining = "dining"
    kitchen = "kitchen"
    # private rooms
    bedroom = "bedroom"
    bath = "bath"
    # service / circulation
    hall = "hall"
    corridor = "corridor"
    stair = "stair"
    utility = "utility"
    laundry = "laundry"
    pantry = "pantry"
    closet = "closet"
    storage = "storage"
    # home-specific
    office = "office"
    library = "library"
    garage = "garage"
    gym = "gym"
    media = "media"
    # outdoor-adjacent
    terrace = "terrace"
    balcony = "balcony"
    porch = "porch"
    # catch-all; room.name carries the real meaning when this is used
    other = "other"


class VerticalConnectionKind(str, Enum):
    stair = "stair"
    void = "void"           # open double-height / atrium
    elevator = "elevator"


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


class Floor(BaseModel):
    """One storey of the building. Walls / openings / rooms are nested here so
    IDs stay scoped per floor and the Blender builder can iterate storeys
    directly.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Stable id, e.g. 'ground', 'first'.")
    ord: int = Field(ge=0, description="0 = ground. Higher = higher up.")
    z0: float = Field(ge=0, description="Metres from world origin to this floor's slab top.")
    wall_height: float = Field(gt=0, description="Floor-to-ceiling height on this floor.")
    label: str = Field(min_length=1, description="Human label, e.g. 'Ground Floor'.")
    walls: List[Wall] = Field(min_length=1)
    openings: List[Opening] = Field(default_factory=list)
    rooms: List[Room] = Field(min_length=1)

    @model_validator(mode="after")
    def _within_floor_refs(self):
        # Unique IDs within each collection on this floor.
        for name, items in (("walls", self.walls), ("openings", self.openings), ("rooms", self.rooms)):
            ids = [i.id for i in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"floor {self.id} {name} has duplicate ids")

        # Each opening fits inside its wall.
        walls_by_id = {w.id: w for w in self.walls}
        for op in self.openings:
            if op.wall_id not in walls_by_id:
                raise ValueError(
                    f"floor {self.id} opening {op.id} references unknown wall {op.wall_id}"
                )
            w = walls_by_id[op.wall_id]
            if op.offset - op.width / 2 < 0 or op.offset + op.width / 2 > w.length + 1e-6:
                raise ValueError(
                    f"floor {self.id} opening {op.id} doesn't fit in wall {w.id}: "
                    f"[{op.offset - op.width/2:.3f}, {op.offset + op.width/2:.3f}] vs {w.length:.3f}"
                )
            if op.sill + op.height > w.height + 1e-6:
                raise ValueError(
                    f"floor {self.id} opening {op.id} top ({op.sill + op.height:.3f} m) "
                    f"exceeds wall height ({w.height:.3f} m)"
                )
        return self


class VerticalConnection(BaseModel):
    """A stair / void / elevator shaft that connects two floors.

    `polygon` is the connection footprint on the shared slab, in world (x, y)
    metres. Blender uses it to cut a stairwell void in the upper floor's slab
    and position the stair geometry; the stair_climb camera traverses from
    the centroid-at-z0_lower to the centroid-at-z0_upper over the shot duration.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: VerticalConnectionKind
    from_floor_id: str = Field(min_length=1)
    to_floor_id: str = Field(min_length=1)
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
            raise ValueError(f"vertical connection {self.id} polygon is self-intersecting")
        if self.from_floor_id == self.to_floor_id:
            raise ValueError(f"vertical connection {self.id}: from and to floors are the same")
        return self


# ---------- Root ----------

class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION)
    units: str = Field(default="m", pattern="^m$")
    meta: Meta
    defaults: Defaults
    floors: List[Floor] = Field(min_length=1, max_length=MAX_FLOORS)
    vertical_connections: List[VerticalConnection] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_v1(cls, v):
        """Backwards-compat: v1 shape has walls/openings/rooms at the root with
        no `floors` key. Wrap them into a single ground floor so legacy
        extracted.json files keep working unchanged."""
        if not isinstance(v, dict):
            return v
        if "floors" in v:
            return v
        if "walls" not in v:
            return v
        v = dict(v)  # shallow copy — don't mutate caller's dict
        defaults = v.get("defaults", {}) or {}
        wall_height = defaults.get("wall_height", 2.8)
        floor = {
            "id": "ground",
            "ord": 0,
            "z0": 0.0,
            "wall_height": wall_height,
            "label": "Ground Floor",
            "walls": v.pop("walls"),
            "openings": v.pop("openings", []),
            "rooms": v.pop("rooms"),
        }
        v["floors"] = [floor]
        # Keep schema_version if present; otherwise mark as v2 since we're in v2.
        v.setdefault("schema_version", SCHEMA_VERSION)
        return v

    @model_validator(mode="after")
    def _cross_floor_refs(self):
        # Floor IDs unique.
        floor_ids = [f.id for f in self.floors]
        if len(floor_ids) != len(set(floor_ids)):
            raise ValueError("floors contain duplicate ids")

        # ord must be unique and start at 0.
        ords = sorted(f.ord for f in self.floors)
        if ords != list(range(len(ords))):
            raise ValueError(f"floor `ord` must be a 0..N-1 permutation; got {ords}")

        # Vertical connections reference existing floors.
        valid_ids = set(floor_ids)
        for vc in self.vertical_connections:
            if vc.from_floor_id not in valid_ids:
                raise ValueError(
                    f"vertical connection {vc.id}: from_floor_id {vc.from_floor_id!r} not in floors"
                )
            if vc.to_floor_id not in valid_ids:
                raise ValueError(
                    f"vertical connection {vc.id}: to_floor_id {vc.to_floor_id!r} not in floors"
                )

        # Multi-storey sanity: every floor above ground must be reachable via
        # at least one vertical connection path from the lowest-ord floor.
        if len(self.floors) > 1:
            if not self.vertical_connections:
                raise ValueError(
                    "multi-storey plans need at least one vertical_connection — "
                    "no stair/void links the floors"
                )
            reachable = {min(self.floors, key=lambda f: f.ord).id}
            # BFS up through the connections.
            for _ in range(len(self.floors)):
                for vc in self.vertical_connections:
                    if vc.from_floor_id in reachable:
                        reachable.add(vc.to_floor_id)
                    if vc.to_floor_id in reachable:
                        reachable.add(vc.from_floor_id)
            unreachable = set(floor_ids) - reachable
            if unreachable:
                raise ValueError(
                    f"floors {sorted(unreachable)} have no stair/void path to the ground floor"
                )

        # Exactly one main_entrance across the whole building (any floor; usually ground).
        main_count = sum(
            1 for f in self.floors for op in f.openings if op.main_entrance
        )
        if main_count != 1:
            raise ValueError(
                f"exactly one opening must have main_entrance=true across all floors (found {main_count})"
            )

        # Overall bounding box across all floors.
        xs: list[float] = []
        ys: list[float] = []
        for f in self.floors:
            for w in f.walls:
                xs.extend((w.a[0], w.b[0]))
                ys.extend((w.a[1], w.b[1]))
        width = max(xs) - min(xs)
        depth = max(ys) - min(ys)
        for name, side in (("width", width), ("depth", depth)):
            if side < BBOX_MIN_SIDE_M or side > BBOX_MAX_SIDE_M:
                raise ValueError(
                    f"building {name} {side:.2f} m outside allowed "
                    f"[{BBOX_MIN_SIDE_M}, {BBOX_MAX_SIDE_M}] m — scale likely wrong"
                )

        return self

    # ----- convenience accessors for downstream code -----

    def floor_by_id(self, floor_id: str) -> Floor:
        for f in self.floors:
            if f.id == floor_id:
                return f
        raise KeyError(floor_id)

    @property
    def all_walls(self) -> list[Wall]:
        return [w for f in self.floors for w in f.walls]

    @property
    def all_openings(self) -> list[Opening]:
        return [op for f in self.floors for op in f.openings]

    @property
    def all_rooms(self) -> list[Room]:
        return [r for f in self.floors for r in f.rooms]
