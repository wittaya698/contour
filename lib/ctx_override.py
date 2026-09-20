"""Run a whitelisted operator under an explicit context (ADR 0004).

Under --background the ambient context is frequently wrong or absent, which is
how operators fail silently or act on the wrong object. Naming the scene and view
layer removes the guesswork.
"""
import bpy

from .ops_whitelist import ALLOWED


def call(name, **kwargs):
    """call('export_scene.gltf', filepath=...) -> the operator's result set."""
    if name not in ALLOWED:
        raise PermissionError(f"bpy.ops.{name} is not in lib/ops_whitelist.py (ADR 0004)")
    mod, fn = name.split(".")
    op = getattr(getattr(bpy.ops, mod), fn)
    with bpy.context.temp_override(scene=bpy.context.scene,
                                   view_layer=bpy.context.view_layer):
        result = op(**kwargs)
    if "FINISHED" not in result:
        raise RuntimeError(f"bpy.ops.{name} returned {set(result)}")
    return result
