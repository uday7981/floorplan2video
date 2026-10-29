"""Scene builder: iterates plan.floors to place walls, slabs, stairs, lights.
bpy imports happen at function scope so this module imports cleanly in tests.

Multi-storey model (schema v2):
  - Each floor has z0 (slab top) + wall_height. Walls on floor F sit at
    midpoint z = F.z0 + wall.height/2. Slab for floor F is centred at
    z = F.z0 - floor_thickness/2 (slab top sits exactly at z0).
  - Roof is a single flat slab above the highest-ord floor.
  - vertical_connections place stair treads between floors and cut a
    stairwell void from the upper floor's slab.

v1 plans (flat walls/openings/rooms) are auto-wrapped into a single ground
floor by plan_io.load_plan, so this builder only ever sees floors[].
"""
from __future__ import annotations

import math

from .geometry import opening_world_position, polygon_centroid


BOOLEAN_OVERLAP_M = 0.1   # cutter extends past wall thickness
STAIR_TREADS_PER_METRE = 5


def reset_scene():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    if scn.world is None:
        scn.world = bpy.data.worlds.new("World")
    scn.world.use_nodes = False
    scn.world.color = (0.72, 0.78, 0.85)
    scn.render.fps = 24
    return scn


# ---------- walls + openings ----------

def _add_wall(wall: dict, floor_z0: float, wall_mat):
    import bpy
    ax, ay = wall["a"]
    bx, by = wall["b"]
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    midx, midy = (ax + bx) / 2, (ay + by) / 2
    h = wall["height"]
    t = wall["thickness"]
    bpy.ops.mesh.primitive_cube_add(location=(midx, midy, floor_z0 + h / 2))
    obj = bpy.context.active_object
    obj.name = f"Wall_{wall['id']}"
    obj.rotation_euler = (0.0, 0.0, angle)
    obj.dimensions = (length, t, h)
    obj.data.materials.append(wall_mat)
    return obj


def _add_opening_cutter(wall: dict, opening: dict, floor_z0: float):
    import bpy
    ax, ay = wall["a"]
    bx, by = wall["b"]
    angle = math.atan2(by - ay, bx - ax)
    opx, opy = opening_world_position(wall, opening)
    cutter_h = opening["height"]
    cutter_z = floor_z0 + opening["sill"] + cutter_h / 2
    bpy.ops.mesh.primitive_cube_add(location=(opx, opy, cutter_z))
    cutter = bpy.context.active_object
    cutter.name = f"Cut_{opening['id']}"
    cutter.rotation_euler = (0.0, 0.0, angle)
    cutter.dimensions = (opening["width"], wall["thickness"] + BOOLEAN_OVERLAP_M, cutter_h)
    return cutter


def _apply_boolean_cut(target_obj, cutter):
    import bpy
    mod = target_obj.modifiers.new(name="cut", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = target_obj
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(cutter, do_unlink=True)


def build_walls_and_openings(plan: dict, wall_mat):
    """Iterate every floor; place walls at that floor's z0, cut openings."""
    all_wall_objs = []
    for floor in plan["levels"]:
        z0 = float(floor["elevation"])
        walls_src_by_id = {w["id"]: w for w in floor["walls"]}
        walls_by_id = {w["id"]: _add_wall(w, z0, wall_mat) for w in floor["walls"]}
        for op in floor.get("openings", []):
            src = walls_src_by_id.get(op["wall_id"])
            if src is None:
                continue
            cutter = _add_opening_cutter(src, op, z0)
            _apply_boolean_cut(walls_by_id[op["wall_id"]], cutter)
        all_wall_objs.extend(walls_by_id.values())
    return all_wall_objs


# ---------- bbox + slabs + roof ----------

def _plan_bbox(plan: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for f in plan["levels"]:
        for w in f["walls"]:
            xs.extend((w["a"][0], w["b"][0]))
            ys.extend((w["a"][1], w["b"][1]))
    return min(xs), min(ys), max(xs), max(ys)


def build_floor_slabs(plan: dict, floor_mat) -> dict:
    """One slab per floor, slab top at floor.z0. Returns {floor_id: obj}."""
    import bpy
    xmin, ymin, xmax, ymax = _plan_bbox(plan)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    w, d = xmax - xmin + 0.5, ymax - ymin + 0.5
    t = plan["defaults"]["floor_thickness"]
    slabs: dict = {}
    for floor in plan["levels"]:
        z = float(floor["elevation"]) - t / 2
        bpy.ops.mesh.primitive_cube_add(location=(cx, cy, z))
        obj = bpy.context.active_object
        obj.name = f"Floor_{floor['id']}"
        obj.dimensions = (w, d, t)
        obj.data.materials.append(floor_mat)
        slabs[floor["id"]] = obj
    return slabs


def build_roof(plan: dict, roof_mat):
    """Flat slab above the top-most floor's ceiling."""
    import bpy
    top = max(plan["levels"], key=lambda f: int(f["index"]))
    xmin, ymin, xmax, ymax = _plan_bbox(plan)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    w, d = xmax - xmin + 0.6, ymax - ymin + 0.6
    z = float(top["elevation"]) + float(top["floor_to_floor_height"]) - float(plan["defaults"]["floor_thickness"]) + 0.1
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, z))
    obj = bpy.context.active_object
    obj.name = "Roof"
    obj.dimensions = (w, d, 0.2)
    obj.data.materials.append(roof_mat)
    return obj


# ---------- vertical connections (stairs + voids) ----------

def _polygon_bbox(polygon: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _cut_stairwell_in_slab(upper_slab, vc_polygon, floor_thickness):
    """Boolean DIFFERENCE a prism matching the stair footprint out of the upper
    slab so the stair_climb camera can see through."""
    import bpy
    xmin, ymin, xmax, ymax = _polygon_bbox(vc_polygon)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    cutter_w = xmax - xmin + 0.05
    cutter_d = ymax - ymin + 0.05
    cutter_h = floor_thickness + 0.3  # taller than slab to guarantee clean cut
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, upper_slab.location.z))
    cutter = bpy.context.active_object
    cutter.name = "StairVoid"
    cutter.dimensions = (cutter_w, cutter_d, cutter_h)
    _apply_boolean_cut(upper_slab, cutter)


def _add_stair_treads(polygon, z_lo, z_hi, mat):
    """Row of tread boxes between z_lo and z_hi along the polygon's long side."""
    import bpy
    xmin, ymin, xmax, ymax = _polygon_bbox(polygon)
    w = xmax - xmin
    d = ymax - ymin
    along_x = w >= d
    length = max(w, d)
    width = max(0.6, min(w, d))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    climb = z_hi - z_lo
    n_steps = max(6, min(24, round(climb * STAIR_TREADS_PER_METRE)))
    rise = climb / n_steps
    run = length / n_steps

    for i in range(n_steps):
        step_center_z = z_lo + (i + 0.5) * rise
        # Offset along long axis from one end of the polygon to the other
        along = (xmin if along_x else ymin) + (i + 0.5) * run
        if along_x:
            loc = (along, cy, step_center_z)
            dims = (run, width, rise)
        else:
            loc = (cx, along, step_center_z)
            dims = (width, run, rise)
        bpy.ops.mesh.primitive_cube_add(location=loc)
        obj = bpy.context.active_object
        obj.name = f"Tread_{i:02d}"
        obj.dimensions = dims
        if mat is not None:
            obj.data.materials.append(mat)


def build_stairs_and_voids(plan: dict, slabs: dict, stair_mat):
    """For each stair: cut void in upper slab + add stair treads.
    For each level's `voids`: boolean-cut the polygon out of the slab ABOVE it
    (so a double-height living room's ceiling is open to the floor above).
    """
    levels_by_id = {l["id"]: l for l in plan["levels"]}
    levels_sorted = sorted(plan["levels"], key=lambda l: int(l["index"]))
    floor_thickness = plan["defaults"]["floor_thickness"]

    # Stairs
    for s_rec in plan.get("stairs", []):
        lo = levels_by_id[s_rec["from_level"]]
        hi = levels_by_id[s_rec["to_level"]]
        if int(lo["index"]) > int(hi["index"]):
            lo, hi = hi, lo
        z_lo = float(lo["elevation"])
        z_hi = float(hi["elevation"])
        upper_slab = slabs.get(hi["id"])
        if upper_slab is not None:
            _cut_stairwell_in_slab(upper_slab, s_rec["footprint"], floor_thickness)
        _add_stair_treads(s_rec["footprint"], z_lo, z_hi, stair_mat)

    # Per-level voids: cut from the slab of the LEVEL ABOVE this one.
    for i, lvl in enumerate(levels_sorted[:-1]):
        upper = levels_sorted[i + 1]
        upper_slab = slabs.get(upper["id"])
        if upper_slab is None:
            continue
        for v in lvl.get("voids", []):
            _cut_stairwell_in_slab(upper_slab, v["polygon"], floor_thickness)


# ---------- lights ----------

def build_lights(plan: dict):
    """Sun for exterior + one area light per room at that floor's ceiling."""
    import bpy
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 20))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), 0.0, math.radians(135))

    for floor in plan["levels"]:
        ceiling_z = float(floor["elevation"]) + float(floor["floor_to_floor_height"] - plan["defaults"]["floor_thickness"]) - 0.1
        for room in floor["rooms"]:
            cx, cy = polygon_centroid(room["polygon"])
            bpy.ops.object.light_add(type="AREA", location=(cx, cy, ceiling_z))
            area = bpy.context.active_object
            area.name = f"Light_{floor['id']}_{room['id']}"
            area.data.size = 2.0
            area.data.energy = 80.0
            area.rotation_euler = (math.pi, 0.0, 0.0)


# ---------- backwards-compat shim ----------

def build_floor(plan: dict, floor_mat):
    """Legacy single-slab API — now returns the ground floor's slab. Prefer
    build_floor_slabs() in new code so you can hand slabs to the stair cutter."""
    slabs = build_floor_slabs(plan, floor_mat)
    ground = min(plan["levels"], key=lambda f: int(f["index"]))
    return slabs[ground["id"]]
