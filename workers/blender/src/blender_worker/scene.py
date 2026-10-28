"""Scene builder: walls (as extruded boxes with boolean-cut openings), floor
slab, optional flat roof, sun + per-room area lights.

bpy imports happen at function scope so this module imports cleanly in tests.
"""
from __future__ import annotations

import math

from .geometry import building_bbox, opening_world_position, polygon_centroid


BOOLEAN_OVERLAP_M = 0.1  # cutter extends past wall thickness so boolean is clean


def reset_scene():
    """Factory settings with the scene emptied; create a World for Freestyle."""
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    if scn.world is None:
        scn.world = bpy.data.worlds.new("World")
    scn.world.use_nodes = False
    scn.world.color = (0.72, 0.78, 0.85)  # pale sky
    scn.render.fps = 24
    return scn


def _add_wall(wall: dict, wall_mat):
    import bpy
    ax, ay = wall["a"]
    bx, by = wall["b"]
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    midx, midy = (ax + bx) / 2, (ay + by) / 2
    h = wall["height"]
    t = wall["thickness"]
    bpy.ops.mesh.primitive_cube_add(location=(midx, midy, h / 2))
    obj = bpy.context.active_object
    obj.name = f"Wall_{wall['id']}"
    obj.rotation_euler = (0.0, 0.0, angle)
    obj.dimensions = (length, t, h)
    obj.data.materials.append(wall_mat)
    return obj


def _add_opening_cutter(wall: dict, opening: dict):
    import bpy
    ax, ay = wall["a"]
    bx, by = wall["b"]
    angle = math.atan2(by - ay, bx - ax)
    opx, opy = opening_world_position(wall, opening)
    cutter_h = opening["height"]
    cutter_z = opening["sill"] + cutter_h / 2
    bpy.ops.mesh.primitive_cube_add(location=(opx, opy, cutter_z))
    cutter = bpy.context.active_object
    cutter.name = f"Cut_{opening['id']}"
    cutter.rotation_euler = (0.0, 0.0, angle)
    cutter.dimensions = (opening["width"], wall["thickness"] + BOOLEAN_OVERLAP_M, cutter_h)
    return cutter


def _apply_boolean_cut(wall_obj, cutter):
    import bpy
    mod = wall_obj.modifiers.new(name="cut", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = wall_obj
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(cutter, do_unlink=True)


def build_walls_and_openings(plan: dict, wall_mat):
    walls_by_id = {w["id"]: _add_wall(w, wall_mat) for w in plan["walls"]}
    walls_src_by_id = {w["id"]: w for w in plan["walls"]}
    for op in plan.get("openings", []):
        src = walls_src_by_id.get(op["wall_id"])
        if src is None:
            continue
        cutter = _add_opening_cutter(src, op)
        _apply_boolean_cut(walls_by_id[op["wall_id"]], cutter)
    return list(walls_by_id.values())


def build_floor(plan: dict, floor_mat):
    import bpy
    (xmin, ymin), (xmax, ymax) = building_bbox(plan["walls"])
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    w, d = xmax - xmin, ymax - ymin
    t = plan["defaults"]["floor_thickness"]
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, -t / 2))
    obj = bpy.context.active_object
    obj.name = "Floor"
    obj.dimensions = (w + 0.5, d + 0.5, t)
    obj.data.materials.append(floor_mat)
    return obj


def build_roof(plan: dict, roof_mat):
    """Flat slab at wall_height + small gap. House projects only (caller decides)."""
    import bpy
    (xmin, ymin), (xmax, ymax) = building_bbox(plan["walls"])
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    w, d = xmax - xmin, ymax - ymin
    wall_h = plan["defaults"]["wall_height"]
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, wall_h + 0.1))
    obj = bpy.context.active_object
    obj.name = "Roof"
    obj.dimensions = (w + 0.6, d + 0.6, 0.2)
    obj.data.materials.append(roof_mat)
    return obj


def build_lights(plan: dict):
    """One sun + one area light per room, aimed down."""
    import bpy
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 20))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), 0.0, math.radians(135))

    wall_h = plan["defaults"]["wall_height"]
    for room in plan["rooms"]:
        cx, cy = polygon_centroid(room["polygon"])
        bpy.ops.object.light_add(type="AREA", location=(cx, cy, wall_h - 0.1))
        area = bpy.context.active_object
        area.name = f"Light_{room['id']}"
        area.data.size = 2.0
        area.data.energy = 80.0
        area.rotation_euler = (math.pi, 0.0, 0.0)
