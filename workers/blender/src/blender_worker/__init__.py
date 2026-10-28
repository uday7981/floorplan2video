"""Blender build + render worker. See build.py for the Blender entry point.

Modules split into two groups:
  - Pure Python (no bpy): plan_io, geometry, hashing — testable in a normal venv.
  - bpy-dependent: materials, scene, cameras, render — run only inside Blender.
    These do their `import bpy` at function scope so this package can still be
    imported by tests without Blender installed.
"""
