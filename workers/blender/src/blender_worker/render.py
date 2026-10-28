"""Render orchestration. Three outputs per shot — see TRD §"Blender worker"."""
from __future__ import annotations

from pathlib import Path


DRIVING_RES = (1280, 720)
CLAY_SINGLE_COLOR = (0.75, 0.72, 0.65)   # warm beige clay


def _apply_common(scn, res: tuple[int, int] = DRIVING_RES):
    scn.render.resolution_x = res[0]
    scn.render.resolution_y = res[1]
    scn.render.resolution_percentage = 100


def render_driving(out_path: Path) -> Path:
    """driving.mp4 — Workbench solid shading, 1280x720, animated at scene fps."""
    import bpy
    scn = bpy.context.scene
    _apply_common(scn)
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.light = "STUDIO"
    scn.display.shading.color_type = "MATERIAL"
    scn.render.use_freestyle = False

    scn.render.image_settings.file_format = "FFMPEG"
    scn.render.ffmpeg.format = "MPEG4"
    scn.render.ffmpeg.codec = "H264"
    scn.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scn.render.ffmpeg.ffmpeg_preset = "GOOD"
    scn.render.ffmpeg.audio_codec = "NONE"

    # FFMPEG format: Blender appends .mp4 to the filepath automatically.
    scn.render.filepath = str(out_path.with_suffix(""))
    bpy.ops.render.render(animation=True)
    produced = out_path.with_suffix(".mp4")
    if produced.exists() and produced != out_path:
        produced.rename(out_path)
    return out_path


def render_start_frame(out_path: Path) -> Path:
    """start.png — EEVEE Next + Freestyle; all meshes overridden to flat white
    for a clean CAD line-drawing look. Only frame_start is rendered."""
    import bpy
    scn = bpy.context.scene
    _apply_common(scn)
    scn.render.engine = "BLENDER_EEVEE_NEXT"
    scn.render.use_freestyle = True

    rl = scn.view_layers[0]
    rl.use_freestyle = True
    for ls in list(rl.freestyle_settings.linesets):
        rl.freestyle_settings.linesets.remove(ls)
    lineset = rl.freestyle_settings.linesets.new("CAD")
    lineset.select_silhouette = True
    lineset.select_border = True
    lineset.select_crease = True
    lineset.linestyle.color = (0.0, 0.0, 0.0)
    lineset.linestyle.thickness = 1.5

    if scn.world is None:
        scn.world = bpy.data.worlds.new("World")
    scn.world.use_nodes = False
    scn.world.color = (1.0, 1.0, 1.0)

    # Temporarily swap every mesh material for a flat white, then restore.
    white = bpy.data.materials.new("fp_cad_white")
    white.use_nodes = False
    white.diffuse_color = (1.0, 1.0, 1.0, 1.0)
    saved: dict[str, list] = {}
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            saved[obj.name] = list(obj.data.materials)
            obj.data.materials.clear()
            obj.data.materials.append(white)

    try:
        scn.render.image_settings.file_format = "PNG"
        scn.render.filepath = str(out_path)
        scn.frame_set(scn.frame_start)
        bpy.ops.render.render(write_still=True)
    finally:
        for name, mats in saved.items():
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            obj.data.materials.clear()
            for m in mats:
                obj.data.materials.append(m)
        bpy.data.materials.remove(white, do_unlink=True)

    return out_path


def render_clay_frame(out_path: Path) -> Path:
    """clay.png — Workbench clay shading, scene's final frame. End-frame
    reference image passed to OpenAI image edit in M3."""
    import bpy
    scn = bpy.context.scene
    _apply_common(scn)
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.render.use_freestyle = False
    scn.display.shading.light = "MATCAP"
    scn.display.shading.color_type = "SINGLE"
    scn.display.shading.single_color = CLAY_SINGLE_COLOR

    scn.render.image_settings.file_format = "PNG"
    scn.render.filepath = str(out_path)
    scn.frame_set(scn.frame_end)
    bpy.ops.render.render(write_still=True)
    return out_path
