"""./contour check <variant>: build from an empty scene, save, verify."""
import runpy
import sys
import os

import bpy

from . import miniyaml, paths, scene


def build(P, variant):
    """Empty scene -> build.py -> one collection. Returns the collection."""
    scene.reset()
    runpy.run_path(str(P["build"]), run_name="__main__")
    return scene.organize(variant)


def run(args):
    import verify

    variant, fixture = paths.parse(args)
    P = paths.resolve(variant, fixture)
    for key in ("spec", "build"):
        if not P[key].exists():
            return {"ok": False, "lines": [f"FAIL {variant}: missing {P[key].relative_to(paths.ROOT)}"]}
    spec = miniyaml.load(P["spec"])
    coll = build(P, variant)
    scene.save_collection(coll, P["blend"])
    branch = None if fixture else os.environ.get("CONTOUR_BRANCH", "")
    results = verify.run(spec, variant, branch)
    rep = {"ok": all(r["ok"] for r in results), "lines": verify.report(variant, results),
           "results": results}
    if fixture:
        from . import mutants
        rep = mutants.attach(rep, spec, P, variant)
    return rep
