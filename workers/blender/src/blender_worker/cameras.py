"""Journey camera — one continuous spline through every segment.

bpy imports happen at function scope so this module imports cleanly in tests.

Journey shape (v2.0, from scripts/make_journey.py):
    {
      "total_duration_s": 55.0,
      "segments": [
        {"id","ord","role","level_id","from_room_id","to_room_id",
         "duration_s", "waypoints":[{"t","position","look_at","lens_mm"},...]},
        ...
      ],
      "boundaries": [{"id","ord","kind"}, ...]  // N+1 for N segments
    }

Build order used by `build.py`:
  1. scene.py builds walls/slabs/stairs/voids/lights
  2. build_journey_camera(journey) — one camera + keyframes across every
     segment waypoint
  3. For each segment, Blender renders a frame-range mp4 + end PNG; one
     boundary PNG per junction.

All previous per-shot builders (opening/room/exterior/stair_climb) are gone.
"""
from __future__ import annotations

import math
from typing import Any

FPS = 24


def _aim_at(from_xyz, target_xyz):
    import mathutils
    v = mathutils.Vector(target_xyz) - mathutils.Vector(from_xyz)
    return v.to_track_quat("-Z", "Y").to_euler()


def build_journey_camera(journey: dict):
    """Create one camera, keyframe its position + rotation + lens at every
    waypoint across every segment. The scene's frame_end is set to the full
    journey duration. Linear interpolation between keyframes (Blender default);
    TODO(decision): switch to Bezier with ease curves at segment boundaries
    in v2.C polish."""
    import bpy

    bpy.ops.object.camera_add(location=(0, 0, 0))
    cam = bpy.context.active_object
    cam.name = "JourneyCam"

    scn = bpy.context.scene
    scn.camera = cam
    scn.render.fps = FPS

    t_cursor = 0.0
    for seg in sorted(journey["segments"], key=lambda s: int(s["ord"])):
        waypoints = sorted(seg["waypoints"], key=lambda w: float(w["t"]))
        duration = float(seg["duration_s"])
        for wp in waypoints:
            abs_t = t_cursor + float(wp["t"])
            frame = max(1, int(round(abs_t * FPS)))
            pos = tuple(wp["position"])
            la = tuple(wp["look_at"])
            cam.location = pos
            cam.rotation_euler = _aim_at(pos, la)
            cam.data.lens = float(wp["lens_mm"])
            cam.keyframe_insert(data_path="location", frame=frame)
            cam.keyframe_insert(data_path="rotation_euler", frame=frame)
            cam.data.keyframe_insert(data_path="lens", frame=frame)
        t_cursor += duration

    total_frames = max(1, int(round(float(journey["total_duration_s"]) * FPS)))
    scn.frame_start = 1
    scn.frame_end = total_frames
    return cam


def segment_frame_range(journey: dict, seg_ord: int) -> tuple[int, int]:
    """Return (frame_first, frame_last) for the segment at seg_ord. Both inclusive."""
    t_cursor = 0.0
    for seg in sorted(journey["segments"], key=lambda s: int(s["ord"])):
        duration = float(seg["duration_s"])
        if int(seg["ord"]) == int(seg_ord):
            first = max(1, int(round(t_cursor * FPS)) + 1)
            last = max(first, int(round((t_cursor + duration) * FPS)))
            return first, last
        t_cursor += duration
    raise KeyError(f"segment ord {seg_ord} not in journey")


def boundary_frame_number(journey: dict, boundary_ord: int) -> int:
    """Return the frame number for boundary at ord. Boundary 0 is frame 1
    (opening); boundary N is the end of segment N-1."""
    t_cursor = 0.0
    segs = sorted(journey["segments"], key=lambda s: int(s["ord"]))
    if int(boundary_ord) == 0:
        return 1
    for i, seg in enumerate(segs):
        t_cursor += float(seg["duration_s"])
        if int(boundary_ord) == i + 1:
            return max(1, int(round(t_cursor * FPS)))
    raise KeyError(f"boundary ord {boundary_ord} out of range")
