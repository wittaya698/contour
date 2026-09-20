"""./contour export <variant>: build -> exports/<variant>.glb (web target, ADR 0006).

The round-trip that proves the file runs as a second, clean process (cmd_roundtrip).
"""
from . import ctx_override, paths, scene


def run(args):
    variant, fixture = paths.parse(args)
    P = paths.resolve(variant, fixture)
    if not P["blend"].exists():
        return {"ok": False, "lines": [f"FAIL no build at {P['blend'].relative_to(paths.ROOT)}"
                                       f": run ./contour check {variant} first"]}
    scene.reset()
    scene.load_collections(P["blend"])
    P["glb"].parent.mkdir(parents=True, exist_ok=True)
    P["glb"].unlink(missing_ok=True)
    ctx_override.call("export_scene.gltf", filepath=str(P["glb"]), export_format="GLB",
                      use_selection=False, use_visible=False, export_yup=True,
                      export_apply=True, export_materials="EXPORT",
                      export_cameras=False, export_lights=False)
    if not P["glb"].exists():
        return {"ok": False, "lines": [f"FAIL exporter wrote nothing to {P['glb']}"]}
    kb = P["glb"].stat().st_size / 1024
    return {"ok": True, "lines": [f"{variant} glb {kb:.0f}KB -> {P['glb'].relative_to(paths.ROOT)}"]}
