"""Style preset → Blender materials. bpy import is deferred to function scope
so this module can be imported by tests without Blender installed.

TRD style preset is a comma-separated free-text string ("oak, black aluminium,
natural white"). We match common keywords to a palette; unknown terms are
ignored (defaults kick in).
"""
from __future__ import annotations

RGBA = tuple[float, float, float, float]

_PALETTE: dict[str, RGBA] = {
    "oak":             (0.63, 0.46, 0.24, 1.0),
    "walnut":          (0.33, 0.21, 0.12, 1.0),
    "pine":            (0.86, 0.75, 0.55, 1.0),
    "concrete":        (0.56, 0.55, 0.52, 1.0),
    "black aluminium": (0.08, 0.08, 0.08, 1.0),
    "aluminium":       (0.74, 0.74, 0.76, 1.0),
    "steel":           (0.60, 0.60, 0.62, 1.0),
    "natural white":   (0.92, 0.90, 0.86, 1.0),
    "white":           (0.97, 0.97, 0.97, 1.0),
    "charcoal":        (0.14, 0.14, 0.15, 1.0),
}
_FLOOR_KEYS = {"oak", "walnut", "pine", "concrete"}
_WALL_KEYS = {"natural white", "white", "concrete"}
_TRIM_KEYS = {"black aluminium", "aluminium", "steel", "charcoal"}

_DEFAULTS: dict[str, RGBA] = {
    "floor": _PALETTE["oak"],
    "wall":  _PALETTE["natural white"],
    "trim":  _PALETTE["black aluminium"],
}


def _pick_colors(preset: dict) -> dict[str, RGBA]:
    terms = [t.strip().lower() for t in preset.get("materials", "").split(",") if t.strip()]
    out = dict(_DEFAULTS)
    for t in terms:
        if t in _FLOOR_KEYS:
            out["floor"] = _PALETTE[t]
        if t in _WALL_KEYS:
            out["wall"] = _PALETTE[t]
        if t in _TRIM_KEYS:
            out["trim"] = _PALETTE[t]
    return out


def make_materials(preset: dict):
    """Create floor/wall/trim materials from a style preset dict.
    Returns {'floor': Material, 'wall': Material, 'trim': Material}."""
    import bpy
    colors = _pick_colors(preset)
    mats = {}
    for role, color in colors.items():
        mat = bpy.data.materials.new(name=f"fp_{role}")
        mat.use_nodes = False
        mat.diffuse_color = color
        mats[role] = mat
    return mats
