"""Prove an export is right by re-measuring the FILE, then re-importing it (ADR 0006).

Two independent readings of the same .glb:
  1. lib/glb.py parses the container directly, in glTF space (Y-up, metres):
     dimensions, origin, handedness (no negative-determinant node, every mesh
     wound outward), part names.
  2. A clean Blender scene imports it back: dimensions and origin in Blender
     space, part names, materials, and an unchanged triangle count.
Topology checks (manifold, doubles, quad %) are NOT re-run: glTF is triangles-only
and splits vertices at hard edges, so an importer legitimately changes both.
"""
from . import ctx_override, glb, miniyaml, space, scene

ORIGIN_TOL_MM = 1.0
GL_AXIS = {"width": 0, "height": 1, "depth": 2}  # glTF: X right, Y up, Z toward viewer
RE_CHECKS = {"height", "width", "depth", "origin", "parts", "mat_names", "mat_slots"}


def _res(cid, ok, info="", msg=""):
    return {"id": cid, "ok": ok, "info": info, "msg": msg}


def file_checks(spec, g):
    out = []
    lo, hi = g["lo"], g["hi"]
    for k, a in GL_AXIS.items():
        d = (spec.get("dimensions") or {}).get(k)
        if d:
            got = (hi[a] - lo[a]) * 1000
            out.append(_res(f"gl_{k}", abs(got - d["value"]) <= d["tol"], f"{got:.1f}",
                            f"file {k} {got:.1f}mm (glTF axis {'XYZ'[a]}), want {d['value']}±{d['tol']}"))
    origin = (spec.get("transform") or {}).get("origin")
    if origin:
        c = [(l + h) / 2 * 1000 for l, h in zip(lo, hi)]
        got = (c[0], lo[1] * 1000, c[2]) if origin == "base_center" else tuple(c)
        ok = origin in ("base_center", "bbox_center") and all(abs(v) <= ORIGIN_TOL_MM for v in got)
        out.append(_res("gl_origin", ok, origin,
                        f"file {origin} at ({got[0]:.1f}, {got[1]:.1f}, {got[2]:.1f})mm, want 0"))
    flipped = [n for n, v in g["meshes"].items() if v <= 0]
    out.append(_res("gl_handed", g["det_min"] > 0 and not flipped, "right",
                    f"mirrored or inside-out: det_min={g['det_min']:.3g} "
                    f"volume<=0 in {flipped[:4]}"))
    want = spec.get("parts")
    if want is not None:
        have = [glb.base_name(n) for n in g["meshes"]]
        bad = [f"{p['name']} x{have.count(p['name'])}, want {p.get('count', 1)}"
               for p in want if have.count(p["name"]) != p.get("count", 1)]
        extra = sorted(set(have) - {p["name"] for p in want})
        out.append(_res("gl_parts", not bad and not extra, f"{len(have)}",
                        "; ".join(bad + ([f"unexpected {extra}"] if extra else []))))
    return out


def run(args):
    import verify

    P = space.parse(args)
    variant = P.name
    if not P.glb.exists():
        return {"ok": False, "lines": [f"FAIL no {P.display(P.glb)}: "
                                       f"run ./contour export {variant} first"]}
    spec = miniyaml.load(P.spec)
    g = glb.measure(P.glb)
    results = file_checks(spec, g)

    scene.reset()
    scene.load_collections(P.blend)
    built_tris = _tris_now(verify)
    scene.reset()
    ctx_override.call("import_scene.gltf", filepath=str(P.glb))
    results += [dict(r, id=f"re_{r['id']}") for r in verify.run(spec, variant, only=RE_CHECKS)]
    got_tris = _tris_now(verify)
    results.append(_res("tris_kept", got_tris == built_tris == g["tris"], f"{got_tris:,}",
                        f"triangles: built {built_tris:,}, file {g['tris']:,}, "
                        f"re-imported {got_tris:,}"))

    n, ok = len(results), sum(r["ok"] for r in results)
    d = [(g["hi"][a] - g["lo"][a]) * 1000 for a in (1, 0, 2)]
    if ok == n:
        lines = [f"{variant} roundtrip PASS {ok}/{n} | file h{d[0]:.1f} w{d[1]:.1f} d{d[2]:.1f}mm"
                 f" Y-up right-handed | tris {got_tris:,} kept"]
    else:
        lines = [f"{variant} roundtrip FAIL {ok}/{n}"] + [
            f"  FAIL {r['id']:<10} {r['msg']}" for r in results if not r["ok"]]
    rep = {"ok": ok == n, "lines": lines, "results": results}
    if P.fixture:
        from . import mutants
        rep = mutants.attach_roundtrip(rep, spec, P, variant)
    return rep


def _tris_now(verify):
    m = verify.measure()
    try:
        return sum(len(f.verts) - 2 for _, bm in m["meshes"] for f in bm.faces)
    finally:
        verify.release(m)
