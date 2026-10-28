"""Camera builders per shot kind, with keyframed animation across the shot
duration. Numbers come from the TRD §"Blender worker" section.
"""
from __future__ import annotations

import math

from .geometry import (
    bbox_center_and_diagonal,
    building_bbox,
    nearest_opening_to_polygon,
    opening_world_position,
    orbit_position,
    polygon_centroid,
)

CAM_HEIGHT_ROOM = 1.6
DOLLY_DISTANCE_M = 1.5
ROOM_INSET_M = 0.6
EXTERIOR_HEIGHT_M = 6.0
EXTERIOR_RADIUS_FACTOR = 0.8      # radius = factor * bbox diagonal
EXTERIOR_RADIUS_MIN_M = 5.0
EXTERIOR_ORBIT_DEG = 90.0
OPENING_CRANE_RISE_M = 2.0
OPENING_CRANE_HEIGHT_ABOVE_HOUSE_M = 5.0


def _aim_at(from_xyz, target_xyz):
    """Euler rotation so the camera's -Z looks at `target_xyz`."""
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


def build_room_camera(plan: dict, shot: dict):
    room = next(r for r in plan["rooms"] if r["id"] == shot["room_id"])
    cx, cy = polygon_centroid(room["polygon"])
    centroid = (cx, cy, CAM_HEIGHT_ROOM)

    nearest = nearest_opening_to_polygon(
        room["polygon"], plan["walls"], plan.get("openings", []),
    )
    if nearest is not None:
        wall = next(w for w in plan["walls"] if w["id"] == nearest["wall_id"])
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

    start_loc = (start_x, start_y, CAM_HEIGHT_ROOM)
    end_loc = (start_x + dx * DOLLY_DISTANCE_M,
               start_y + dy * DOLLY_DISTANCE_M,
               CAM_HEIGHT_ROOM)
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


def build_exterior_camera(plan: dict, shot: dict):
    """Orbit around the building centre. Camera parented to an empty pivot;
    pivot rotates about Z over the shot duration."""
    import bpy
    bbox = building_bbox(plan["walls"])
    center, diag = bbox_center_and_diagonal(bbox)
    radius = max(diag * EXTERIOR_RADIUS_FACTOR, EXTERIOR_RADIUS_MIN_M)
    wall_h = plan["defaults"]["wall_height"]

    bpy.ops.object.empty_add(location=(center[0], center[1], 0.0))
    pivot = bpy.context.active_object
    pivot.name = f"Pivot_{shot['id']}"

    start_angle = math.radians(-EXTERIOR_ORBIT_DEG / 2)
    start_pos = orbit_position(center, radius, EXTERIOR_HEIGHT_M, start_angle)
    rot = _aim_at(start_pos, (center[0], center[1], wall_h / 2))

    cam = _add_camera(start_pos, rot, shot["camera"]["lens_mm"])
    cam.name = f"Cam_{shot['id']}"
    cam.parent = pivot
    cam.matrix_parent_inverse = pivot.matrix_world.inverted()

    first, last = _frame_range(shot["camera"])
    pivot.rotation_euler = (0.0, 0.0, 0.0)
    _keyframe(pivot, "rotation_euler", first)
    pivot.rotation_euler = (0.0, 0.0, math.radians(EXTERIOR_ORBIT_DEG))
    _keyframe(pivot, "rotation_euler", last)
    _set_scene_camera_and_range(cam, first, last)
    return cam


def build_opening_camera(plan: dict, shot: dict):
    """Top-down crane over the building. (TRD describes the source-image desk
    + rising-model effect; that's simplified for M2 — the AI model handles
    the stylised transition between start/end frames.)"""
    import bpy
    bbox = building_bbox(plan["walls"])
    center, _diag = bbox_center_and_diagonal(bbox)
    wall_h = plan["defaults"]["wall_height"]

    start_z = wall_h + OPENING_CRANE_HEIGHT_ABOVE_HOUSE_M
    end_z = start_z + OPENING_CRANE_RISE_M
    start_loc = (center[0], center[1], start_z)
    end_loc = (center[0], center[1], end_z)
    rot_down = (0.0, 0.0, 0.0)  # default cam orientation is -Z (straight down)

    cam = _add_camera(start_loc, rot_down, shot["camera"]["lens_mm"])
    cam.name = f"Cam_{shot['id']}"
    first, last = _frame_range(shot["camera"])
    cam.location = start_loc
    _keyframe(cam, "location", first)
    cam.location = end_loc
    _keyframe(cam, "location", last)
    _set_scene_camera_and_range(cam, first, last)
    return cam


def build_camera_for_shot(plan: dict, shot: dict):
    kind = shot["kind"]
    if kind == "room":
        return build_room_camera(plan, shot)
    if kind == "opening":
        return build_opening_camera(plan, shot)
    if kind == "exterior":
        return build_exterior_camera(plan, shot)
    raise ValueError(f"unknown shot kind: {kind!r}")
