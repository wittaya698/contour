"""./contour export <variant>: build -> models/<variant>/exports/<variant>.glb (web target, ADR 0006).

The round-trip that proves the file runs as a second, clean process (cmd_roundtrip).
"""
import bpy

from . import checks, ctx_override, space, scene


def write(path, posed=True, fps=None):
    """Export the loaded build to `path` as a `.glb`. -> None, or why not.

    A rig goes out posed and at its clips' rate (issue 54). The build saves
    its armature at rest, and the exporter samples the pose it sees: at rest,
    every clip would be the rest pose held still. And a saved build is one
    collection with no scene, so without its rate set here every clip would
    be timed at Blender's 24 fps. Each NLA track — one per clip, as `kit`
    keys them — is one animation in the file.

    `posed` and `fps` are for the mutants that prove the round-trip sees
    either go wrong.
    """
    rigs = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    rates = {t.name: s.action["fps"] for o in rigs if o.animation_data
             for t in o.animation_data.nla_tracks for s in t.strips[:1]
             if s.action and "fps" in s.action}
    rate, why = checks.one_rate(rates)
    if why:
        return why
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = fps or rate or sc.render.fps, 1.0
    for o in rigs:
        o.data.pose_position = "POSE" if posed else "REST"
    ctx_override.call("export_scene.gltf", filepath=str(path), export_format="GLB",
                      use_selection=False, use_visible=False, export_yup=True,
                      export_apply=True, export_materials="EXPORT",
                      export_cameras=False, export_lights=False,
                      export_animation_mode="NLA_TRACKS")
    return None


def run(args):
    P = space.parse(args)
    variant = P.name
    if not P.blend.exists():
        return {"ok": False, "lines": [f"FAIL no build at {P.display(P.blend)}"
                                       f": run ./contour check {variant} first"]}
    scene.reset()
    scene.load_collections(P.blend)
    P.glb.parent.mkdir(parents=True, exist_ok=True)
    P.glb.unlink(missing_ok=True)  # a refused export leaves no stale file to round-trip
    why = write(P.glb)
    if why:
        return {"ok": False, "lines": [f"FAIL {why}"]}
    if not P.glb.exists():
        return {"ok": False, "lines": [f"FAIL exporter wrote nothing to {P.glb}"]}
    kb = P.glb.stat().st_size / 1024
    return {"ok": True, "lines": [f"{variant} glb {kb:.0f}KB -> {P.display(P.glb)}"]}
