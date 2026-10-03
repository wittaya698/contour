"""The only bpy.ops calls this repo may make (ADR 0004).

Geometry is bmesh + the data API. An operator earns a line here only when it has
no data-API equivalent, and the line must say why. Call them through
lib.ctx_override.call, never directly.
"""

ALLOWED = {
    "export_scene.gltf": "glTF export has no data-API equivalent (ADR 0006).",
    "import_scene.gltf": "glTF import has no data-API equivalent; the round-trip needs it.",
    "render.render": "Rendering a still has no data-API equivalent (ADR 0005).",
    "object.mode_set": "Creating a bone has no data-API equivalent: Armature.bones has no new(), and edit_bones exist only in edit mode (ADR 0023, issue 47).",
}
