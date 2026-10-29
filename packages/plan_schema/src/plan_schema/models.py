"""Pydantic v2 models for the plan JSON. These are the authoritative types;
Blender's build.py and the browser's three.js preview both read from this
shape. Keep validation strict so a bad plan can't propagate downstream.

Conventions (from TRD):
  - Units are metres.
  - Origin is the plan's bottom-left corner, x right, y up, z up (height).
  - All coordinates round to 0.01 m.

SCHEMA v2.0 (continuous-journey rewrite, 2026-10-29)
  - levels[]  — one per floor (always ≥ 1). A single-storey plan has one
    level at index 0, elevation 0. Multi-storey has N levels in ascending
    index order. Each level owns walls / openings / rooms / voids.
  - stairs[]  — vertical connections between adjacent levels. Carries
    footprint + start_point + end_point + direction so the journey builder
    can place a continuous camera along the stair path.
  - Legacy inputs auto-upgrade:
      v1    (flat walls/openings/rooms at root)         → wrapped into levels[0]
      v2-M8 (floors[] + vertical_connections[])         → renamed on the fly
    so no existing plan.json breaks.
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
MAX_LEVELS = 6
DEFAULT_FLOOR_TO_FLOOR_M = 3.0


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


class StairDirection(str, Enum):
    """Travel direction when going from_level → to_level. Normally 'up'."""
    up = "up"
    down = "down"


# ---------- Submodels ----------

Point2 = Tuple[float, float]


def _round01(v: float) -> float:
    return round(float(v), 2)


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scale_source: ScaleSource
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    offset: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    sill: float = Field(ge=0)
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
            raise ValueError(f"room {self.id} area {area:.3f} m² < min {ROOM_MIN_AREA_M2} m²")
        return self


class Void(BaseModel):
    """A polygon on this level's slab that is cut away — stair wells + any
    double-height spaces. Blender boolean-DIFFs the polygon from the slab
    ABOVE this level so the camera can see through."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    polygon: List[Point2] = Field(min_length=3)

    @field_validator("polygon", mode="before")
    @classmethod
    def _round_poly(cls, v):
        if isinstance(v, list):
            return [(_round01(p[0]), _round01(p[1])) for p in v]
        return v

    @model_validator(mode="after")
    def _simple(self):
        if not polygon_is_simple(self.polygon):
            raise ValueError(f"void {self.id} polygon is self-intersecting")
        return self


class Level(BaseModel):
    """One storey of the building. Walls/openings/rooms/voids are nested so
    IDs stay scoped per level and the Blender builder iterates storeys
    directly."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Stable id, e.g. 'ground', 'first'.")
    name: str = Field(min_length=1, description="Human label, e.g. 'Ground Floor'.")
    index: int = Field(ge=0, description="0 = ground. Higher = higher up.")
    elevation: float = Field(ge=0, description="Metres from world origin to this level's slab top.")
    floor_to_floor_height: float = Field(
        gt=0, default=DEFAULT_FLOOR_TO_FLOOR_M,
        description="Height from this level's slab top to the next level's slab top (metres).",
    )
    walls: List[Wall] = Field(min_length=1)
    openings: List[Opening] = Field(default_factory=list)
    rooms: List[Room] = Field(min_length=1)
    voids: List[Void] = Field(default_factory=list)

    @model_validator(mode="after")
    def _within_level_refs(self):
        for name, items in (("walls", self.walls), ("openings", self.openings),
                            ("rooms", self.rooms), ("voids", self.voids)):
            ids = [i.id for i in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"level {self.id} {name} has duplicate ids")

        walls_by_id = {w.id: w for w in self.walls}
        for op in self.openings:
            if op.wall_id not in walls_by_id:
                raise ValueError(
                    f"level {self.id} opening {op.id} references unknown wall {op.wall_id}"
                )
            w = walls_by_id[op.wall_id]
            if op.offset - op.width / 2 < 0 or op.offset + op.width / 2 > w.length + 1e-6:
                raise ValueError(
                    f"level {self.id} opening {op.id} doesn't fit in wall {w.id}"
                )
            if op.sill + op.height > w.height + 1e-6:
                raise ValueError(
                    f"level {self.id} opening {op.id} top exceeds wall height"
                )
        return self


class Stair(BaseModel):
    """A vertical connection between two levels.

    footprint   — polygon on plan view (xy) that the stair occupies.
    start_point — xy where the user begins the climb at from_level elevation.
    end_point   — xy where the user emerges at to_level elevation.
    direction   — 'up' or 'down' when traveling from_level → to_level.
                  Normally 'up'; 'down' is allowed for descending stairs
                  (e.g. a basement).
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    from_level: str = Field(min_length=1)
    to_level: str = Field(min_length=1)
    footprint: List[Point2] = Field(min_length=3)
    start_point: Point2
    end_point: Point2
    direction: StairDirection = StairDirection.up

    @field_validator("footprint", mode="before")
    @classmethod
    def _round_footprint(cls, v):
        if isinstance(v, list):
            return [(_round01(p[0]), _round01(p[1])) for p in v]
        return v

    @field_validator("start_point", "end_point", mode="before")
    @classmethod
    def _round_pt(cls, v):
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (_round01(v[0]), _round01(v[1]))
        return v

    @model_validator(mode="after")
    def _polygon_valid(self):
        if not polygon_is_simple(self.footprint):
            raise ValueError(f"stair {self.id} footprint polygon is self-intersecting")
        if self.from_level == self.to_level:
            raise ValueError(f"stair {self.id}: from_level == to_level")
        return self


# ---------- Root ----------

class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION)
    units: str = Field(default="m", pattern="^m$")
    meta: Meta
    defaults: Defaults
    levels: List[Level] = Field(min_length=1, max_length=MAX_LEVELS)
    stairs: List[Stair] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy(cls, v):
        """Accept three input shapes:
        1. v2.0 proper (levels[] + stairs[]) — passthrough.
        2. v2-M8 (floors[] + vertical_connections[]) — renamed on the fly.
        3. v1 (flat walls/openings/rooms at root) — wrapped into levels[0].
        """
        if not isinstance(v, dict):
            return v

        # Shape 2 → rename floors + vertical_connections.
        if "floors" in v and "levels" not in v:
            v = dict(v)
            legacy_floors = v.pop("floors")
            levels: list[dict] = []
            default_thickness = v.get("defaults", {}).get("floor_thickness", 0.2)
            for f in legacy_floors:
                levels.append({
                    "id": f.get("id"),
                    "name": f.get("label") or f.get("name") or f.get("id", "Level"),
                    "index": f.get("ord", 0),
                    "elevation": f.get("z0", 0.0),
                    "floor_to_floor_height":
                        f.get("floor_to_floor_height")
                        or (f.get("wall_height", 2.8) + default_thickness),
                    "walls": f.get("walls", []),
                    "openings": f.get("openings", []),
                    "rooms": f.get("rooms", []),
                    "voids": f.get("voids", []),
                })
            v["levels"] = levels
            if "vertical_connections" in v and "stairs" not in v:
                old = v.pop("vertical_connections")
                stairs = []
                for vc in old:
                    poly = vc.get("polygon", [])
                    sp, ep = _fabricate_endpoints(poly)
                    stairs.append({
                        "id": vc.get("id"),
                        "from_level": vc.get("from_floor_id"),
                        "to_level": vc.get("to_floor_id"),
                        "footprint": poly,
                        "start_point": sp,
                        "end_point": ep,
                        "direction": "up",
                    })
                v["stairs"] = stairs
            v.setdefault("schema_version", SCHEMA_VERSION)
            return v

        # Shape 3 → wrap v1 into a single ground level.
        if "levels" not in v and "walls" in v:
            v = dict(v)
            defaults = dict(v.get("defaults", {}) or {})
            floor_thickness = defaults.get("floor_thickness", 0.2)
            wall_height = defaults.pop("wall_height", 2.8)  # strip legacy key
            v["defaults"] = defaults or {"floor_thickness": floor_thickness}
            v["defaults"].setdefault("floor_thickness", floor_thickness)
            level = {
                "id": "ground",
                "name": "Ground Floor",
                "index": 0,
                "elevation": 0.0,
                "floor_to_floor_height": wall_height + floor_thickness,
                "walls": v.pop("walls"),
                "openings": v.pop("openings", []),
                "rooms": v.pop("rooms"),
                "voids": v.pop("voids", []),
            }
            v["levels"] = [level]
            v.setdefault("schema_version", SCHEMA_VERSION)
        return v

    @model_validator(mode="after")
    def _cross_level_refs(self):
        level_ids = [l.id for l in self.levels]
        if len(level_ids) != len(set(level_ids)):
            raise ValueError("levels contain duplicate ids")

        indexes = sorted(l.index for l in self.levels)
        if indexes != list(range(len(indexes))):
            raise ValueError(f"level `index` must be a 0..N-1 permutation; got {indexes}")

        valid = set(level_ids)
        for s in self.stairs:
            if s.from_level not in valid:
                raise ValueError(f"stair {s.id}: unknown from_level {s.from_level!r}")
            if s.to_level not in valid:
                raise ValueError(f"stair {s.id}: unknown to_level {s.to_level!r}")

        if len(self.levels) > 1:
            if not self.stairs:
                raise ValueError(
                    "multi-storey plans need at least one stair — no vertical link between levels"
                )
            reachable = {min(self.levels, key=lambda l: l.index).id}
            for _ in range(len(self.levels)):
                for s in self.stairs:
                    if s.from_level in reachable:
                        reachable.add(s.to_level)
                    if s.to_level in reachable:
                        reachable.add(s.from_level)
            unreachable = set(level_ids) - reachable
            if unreachable:
                raise ValueError(
                    f"levels {sorted(unreachable)} have no stair path to the ground level"
                )

        main_count = sum(
            1 for l in self.levels for op in l.openings if op.main_entrance
        )
        if main_count != 1:
            raise ValueError(
                f"exactly one opening must have main_entrance=true across all levels (found {main_count})"
            )

        xs: list[float] = []
        ys: list[float] = []
        for l in self.levels:
            for w in l.walls:
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

    # ----- convenience accessors -----

    def level_by_id(self, level_id: str) -> Level:
        for l in self.levels:
            if l.id == level_id:
                return l
        raise KeyError(level_id)

    @property
    def all_walls(self) -> list[Wall]:
        return [w for l in self.levels for w in l.walls]

    @property
    def all_openings(self) -> list[Opening]:
        return [op for l in self.levels for op in l.openings]

    @property
    def all_rooms(self) -> list[Room]:
        return [r for l in self.levels for r in l.rooms]


# ---------- helpers ----------

def _fabricate_endpoints(polygon: list) -> tuple[list, list]:
    """Pick reasonable start/end points from a footprint polygon: centres of
    the two short sides of its AABB. Used only when upgrading legacy plans
    that lack explicit stair endpoints."""
    if not polygon or len(polygon) < 3:
        return [0.0, 0.0], [0.0, 0.0]
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    w = max(xs) - min(xs)
    d = max(ys) - min(ys)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    if w >= d:
        return [min(xs) + 0.3, cy], [max(xs) - 0.3, cy]
    return [cx, min(ys) + 0.3], [cx, max(ys) - 0.3]
