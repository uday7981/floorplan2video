"""Camera builders per shot kind, with keyframed animation across the shot
duration. Numbers come from the TRD §"Blender worker" section.

Multi-storey (schema v2): room cameras pull their floor's z0 so cameras sit
at the correct storey height. New kind `stair_climb` moves the camera up a
stair polygon from one floor to the next.
"""
from __future__ import annotations

import math

from .geometry import (
    bbox_center_and_diagonal,
    nearest_opening_to_polygon,
    opening_world_position,
    orbit_position,
    polygon_centroid,
)
from .plan_io import all_openings, all_walls, floor_of_room, floor_by_id


CAM_HEIGHT_ROOM = 1.6
DOLLY_DISTANCE_M = 1.5
ROOM_INSET_M = 0.6
EXTERIOR_HEIGHT_ABOVE_TOP_M = 3.0  # 3 m above the top wall head
EXTERIOR_RADIUS_FACTOR = 0.8      # radius = factor * bbox diagonal
EXTERIOR_RADIUS_MIN_M = 5.0
EXTERIOR_ORBIT_DEG = 90.0
OPENING_CRANE_RISE_M = 2.0
# 3/4 isometric: pure top-down renders a flat roof; offset diagonally.
OPENING_OFFSET_FACTOR = 0.9
OPENING_HEIGHT_ABOVE_TOP_M = 4.0
STAIR_CAM_SHOULDER_M = 1.6         # camera eye-height above each tread


def _aim_at(from_xyz, target_xyz):
    import mathutils
    v = mathutils.Vector(target_xyz) - mathutils.Vector(from_xyz)
    return v.to_track_quat("-Z", "Y").to_euler()


def _add_camera(location, rotation_euler, lens_mm):
    import bpy
    bpy.ops.object.camera_add(location=location, rotation=rotation_euler)
    cam = bpy.context.active_object
    cam.data.lens = lens_mm
    return cam


def _frame_range(camera_cfg: dict) -> tuple[int, int]:
    fps = camera_cfg["fps"]
    duration = camera_cfg["duration_s"]
    return 1, int(fps * duration)


def _keyframe(obj, data_path: str, frame: int):
    obj.keyframe_insert(data_path=data_path, frame=frame)


def _set_scene_camera_and_range(cam, first: int, last: int):
    import bpy
    scn = bpy.context.scene
    scn.camera = cam
    scn.frame_start = first
    scn.frame_end = last


def _add_track_to_constraint(cam, target_xyz, name_suffix: str):
    import bpy
    bpy.ops.object.empty_add(location=target_xyz)
    target = bpy.context.active_object
    target.name = f"Target_{name_suffix}"
    c = cam.constraints.new(type="TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return target


def _plan_bbox_metric(plan: dict):
    """Return (center xy, diagonal) across every floor's walls."""
    xs: list[float] = []
    ys: list[float] = []
    for f in plan["floors"]:
        for w in f["walls"]:
            xs.extend((w["a"][0], w["b"][0]))
            ys.extend((w["a"][1], w["b"][1]))
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    diag = math.hypot(xmax - xmin, ymax - ymin)
    return (cx, cy), diag


def _building_top_z(plan: dict) -> float:
    """Highest wall head across all floors (top of top-floor's walls)."""
    return max(float(f["z0"]) + float(f["wall_height"]) for f in plan["floors"])


# ---------- room ----------

def build_room_camera(plan: dict, shot: dict):
    """Camera 1.6 m above the room's floor, 0.6 m inside the entry opening,
    dollies 1.5 m toward the room centroid."""
    floor = floor_of_room(plan, shot["room_id"])
    z0 = float(floor["z0"])
    room = next(r for r in floor["rooms"] if r["id"] == shot["room_id"])
    cx, cy = polygon_centroid(room["polygon"])
    centroid = (cx, cy, z0 + CAM_HEIGHT_ROOM)

    nearest = nearest_opening_to_polygon(
        room["polygon"], floor["walls"], floor.get("openings", []),
    )
    if nearest is not None:
        wall = next(w for w in floor["walls"] if w["id"] == nearest["wall_id"])
        opx, opy = opening_world_position(wall, nearest)
        dx, dy = cx - opx, cy - opy
        length = math.hypot(dx, dy)
        if length < 1e-6:
            dx, dy = 1.0, 0.0
        else:
            dx, dy = dx / length, dy / length
        start_x = opx + dx * ROOM_INSET_M
        start_y = opy + dy * ROOM_INSET_M
    else:
        start_x, start_y = cx - 2.0, cy
        dx, dy = 1.0, 0.0

    start_loc = (start_x, start_y, z0 + CAM_HEIGHT_ROOM)
    end_loc = (start_x + dx * DOLLY_DISTANCE_M,
               start_y + dy * DOLLY_DISTANCE_M,
               z0 + CAM_HEIGHT_ROOM)
    rot = _aim_at(start_loc, centroid)

    cam = _add_camera(start_loc, rot, shot["camera"]["lens_mm"])
    cam.name = f"Cam_{shot['id']}"
    first, last = _frame_range(shot["camera"])
    cam.location = start_loc
    _keyframe(cam, "location", first)
    cam.location = end_loc
    _keyframe(cam, "location", last)
    _set_scene_camera_and_range(cam, first, last)
    return cam


# ---------- exterior ----------

def build_exterior_camera(plan: dict, shot: dict):
    """Orbit around the whole-building bbox centre; camera parented to a Z-pivot."""
    import bpy
    center, diag = _plan_bbox_metric(plan)
    radius = max(diag * EXTERIOR_RADIUS_FACTOR, EXTERIOR_RADIUS_MIN_M)
    top_z = _building_top_z(plan)
    cam_z = top_z - top_z / 2 + EXTERIOR_HEIGHT_ABOVE_TOP_M  # mid-building eye line

    bpy.ops.object.empty_add(location=(center[0], center[1], 0.0))
    pivot = bpy.context.active_object
    pivot.name = f"Pivot_{shot['id']}"

    start_angle = math.radians(-EXTERIOR_ORBIT_DEG / 2)
    start_pos = orbit_position(center, radius, cam_z, start_angle)

    cam = _add_camera(start_pos, (0.0, 0.0, 0.0), shot["camera"]["lens_mm"])
    cam.name = f"Cam_{shot['id']}"
    cam.parent = pivot
    cam.matrix_parent_inverse = pivot.matrix_world.inverted()
    _add_track_to_constraint(cam, (center[0], center[1], top_z / 2), shot["id"])

    first, last = _frame_range(shot["camera"])
    pivot.rotation_euler = (0.0, 0.0, 0.0)
    _keyframe(pivot, "rotation_euler", first)
    pivot.rotation_euler = (0.0, 0.0, math.radians(EXTERIOR_ORBIT_DEG))
    _keyframe(pivot, "rotation_euler", last)
    _set_scene_camera_and_range(cam, first, last)
    return cam


# ---------- opening ----------

def build_opening_camera(plan: dict, shot: dict):
    """3/4 isometric establishing shot; cranes up over its duration."""
    center, diag = _plan_bbox_metric(plan)
    top_z = _building_top_z(plan)

    offset = diag * OPENING_OFFSET_FACTOR
    start_x = center[0] - offset * 0.707
    start_y = center[1] - offset * 0.707
    start_z = top_z + OPENING_HEIGHT_ABOVE_TOP_M
    end_z = start_z + OPENING_CRANE_RISE_M

    cam = _add_camera((start_x, start_y, start_z), (0.0, 0.0, 0.0),
                      shot["camera"]["lens_mm"])
    cam.name = f"Cam_{shot['id']}"
    _add_track_to_constraint(cam, (center[0], center[1], top_z / 2), shot["id"])

    first, last = _frame_range(shot["camera"])
    cam.location = (start_x, start_y, start_z)
    _keyframe(cam, "location", first)
    cam.location = (start_x, start_y, end_z)
    _keyframe(cam, "location", last)
    _set_scene_camera_and_range(cam, first, last)
    return cam


# ---------- stair_climb (M8.3) ----------

def build_stair_climb_camera(plan: dict, shot: dict):
    """Travel along a stair polygon from floor N's z0 up to floor N+1's z0.
    Camera stays STAIR_CAM_SHOULDER_M above the current step height and is
    aimed via TRACK_TO at the climb's end point (top of stair, next-floor
    eye-level) so the viewer always sees where they're going.
    """
    vc_id = shot["stair_connection_id"]
    vc = next(v for v in plan.get("vertical_connections", []) if v["id"] == vc_id)
    lo = floor_by_id(plan, vc["from_floor_id"])
    hi = floor_by_id(plan, vc["to_floor_id"])
    if int(lo["ord"]) > int(hi["ord"]):
        lo, hi = hi, lo

    # polygon bbox + longest axis
    xs = [p[0] for p in vc["polygon"]]
    ys = [p[1] for p in vc["polygon"]]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    w, d = xmax - xmin, ymax - ymin
    along_x = w >= d
    length = max(w, d)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    # start at the lower end of the stair at eye level above floor_lo
    if along_x:
        start_xy = (xmin + 0.3, cy)
        end_xy = (xmax - 0.3, cy)
    else:
        start_xy = (cx, ymin + 0.3)
        end_xy = (cx, ymax - 0.3)

    z_lo = float(lo["z0"]) + STAIR_CAM_SHOULDER_M
    z_hi = float(hi["z0"]) + STAIR_CAM_SHOULDER_M

    start_loc = (start_xy[0], start_xy[1], z_lo)
    end_loc = (end_xy[0], end_xy[1], z_hi)

    cam = _add_camera(start_loc, (0.0, 0.0, 0.0), shot["camera"]["lens_mm"])
    cam.name = f"Cam_{shot['id']}"
    # Aim at the top-landing eye point; stays fixed so the climb feels forward.
    _add_track_to_constraint(cam, (end_xy[0], end_xy[1], z_hi), shot["id"])

    first, last = _frame_range(shot["camera"])
    cam.location = start_loc
    _keyframe(cam, "location", first)
    cam.location = end_loc
    _keyframe(cam, "location", last)
    _set_scene_camera_and_range(cam, first, last)
    return cam


# ---------- dispatch ----------

def build_camera_for_shot(plan: dict, shot: dict):
    kind = shot["kind"]
    if kind == "room":
        return build_room_camera(plan, shot)
    if kind == "opening":
        return build_opening_camera(plan, shot)
    if kind == "exterior":
        return build_exterior_camera(plan, shot)
    if kind == "stair_climb":
        return build_stair_climb_camera(plan, shot)
    raise ValueError(f"unknown shot kind: {kind!r}")
