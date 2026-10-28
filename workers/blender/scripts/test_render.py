"""M0.3 — Prove headless Blender can render a Workbench frame and a Freestyle
white-line frame on this host.

Run: blender -b --factory-startup -P /workspace/scripts/test_render.py -- --out /workspace/out
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    # Blender passes script args after `--`
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, help="output directory for PNGs")
    return p.parse_args(argv)


def build_scene() -> None:
    # Fresh scene: delete the default cube/light/camera and rebuild deterministically.
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # A plain cube.
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
    cube = bpy.context.active_object
    cube.name = "TestCube"

    # White material so Freestyle lines show on white (CAD look).
    mat = bpy.data.materials.new(name="FlatWhite")
    mat.diffuse_color = (1.0, 1.0, 1.0, 1.0)
    cube.data.materials.append(mat)

    # A ground plane.
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0, 0, 0))

    # A camera.
    bpy.ops.object.camera_add(location=(4.0, -4.0, 3.0),
                              rotation=(1.1, 0.0, 0.785))
    bpy.context.scene.camera = bpy.context.active_object

    # A sun.
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))

    # Render settings
    scn = bpy.context.scene
    scn.render.resolution_x = 1280
    scn.render.resolution_y = 720
    scn.render.resolution_percentage = 100
    scn.render.image_settings.file_format = "PNG"


def render_workbench(out_path: Path) -> None:
    scn = bpy.context.scene
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.light = "STUDIO"
    scn.display.shading.color_type = "MATERIAL"
    scn.render.use_freestyle = False
    scn.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)


def render_freestyle(out_path: Path) -> None:
    scn = bpy.context.scene
    # Freestyle runs with the EEVEE/Workbench engine; use Workbench + flat white
    # materials so the only visible content is Freestyle lines on a white world.
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.light = "FLAT"
    scn.display.shading.color_type = "SINGLE"
    scn.display.shading.single_color = (1.0, 1.0, 1.0)
    scn.world.color = (1.0, 1.0, 1.0)
    scn.render.use_freestyle = True

    rl = scn.view_layers[0]
    rl.use_freestyle = True
    # Reset linesets to a known state.
    for ls in list(rl.freestyle_settings.linesets):
        rl.freestyle_settings.linesets.remove(ls)
    lineset = rl.freestyle_settings.linesets.new("CAD")
    lineset.select_silhouette = True
    lineset.select_border = True
    lineset.select_crease = True
    lineset.select_edge_mark = False
    lineset.linestyle.color = (0.0, 0.0, 0.0)   # black on white; swap if the look needs inverting
    lineset.linestyle.thickness = 1.5

    scn.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    build_scene()

    workbench_path = out / "workbench.png"
    freestyle_path = out / "freestyle.png"

    render_workbench(workbench_path)
    render_freestyle(freestyle_path)

    for p in (workbench_path, freestyle_path):
        size = p.stat().st_size if p.exists() else 0
        print(f"[test_render] wrote {p}  ({size} bytes)")
        if size == 0:
            print(f"[test_render] FAIL: {p} is empty", file=sys.stderr)
            return 2
    print("[test_render] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
