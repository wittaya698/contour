"""./contour check <variant>: build from an empty scene, save, verify."""
import runpy

import bpy

from . import miniyaml, space, scene


def build(P, variant):
    """Empty scene -> build.py -> one collection. Returns the collection."""
    scene.reset()
    runpy.run_path(str(P.build), run_name="__main__")
    return scene.organize(variant)


def run(args):
    import verify

    P = space.parse(args)
    variant = P.name
    for needed in (P.spec, P.build):
        if not needed.exists():
            return {"ok": False,
                    "lines": [f"FAIL {variant}: missing {P.display(needed)}"]}
    spec = miniyaml.load(P.spec)
    coll = build(P, variant)
    scene.save_collection(coll, P.blend)
    results = verify.run(spec, variant)
    rep = {"ok": all(r["ok"] for r in results), "lines": verify.report(variant, results),
           "results": results}
    if P.fixture:
        from . import mutants
        rep = mutants.attach(rep, spec, P, variant)
    return rep
