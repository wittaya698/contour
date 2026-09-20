"""Judge a built scene against its spec (ADR 0002, 0005). Runs inside Blender.

The spec is the definition of correct and this file only reads it. Every check
returns {"id", "ok", "info", "msg"}: `info` is the compact reading shown on a
pass, `msg` the detail shown on a failure. A spec field this file cannot enforce
FAILS as unsupported. It is never skipped, because a silently ignored constraint
is the same failure as a weakened one.
"""
import re

import bmesh
import bpy


TOP = {"model", "revision", "description", "targets", "dimensions", "parts",
       "topology", "uv", "materials", "transform", "render", "notes"}
SECTIONS = {
    "topology": {"tri_budget", "quads_min_pct", "ngons_allowed", "manifold",
                 "loose_geometry", "normals", "doubles_tolerance_mm"},
    "uv": {"required", "overlap_allowed", "udim"},
    "materials": {"max_slots", "names"},
    "transform": {"origin", "scale_applied", "rotation_applied", "up_axis"},
    "render": {"grid_metres", "sheet_resolution"},
}
DIMS = ("height", "width", "depth")
IMPLEMENTED_TARGETS = {"web"}
ORIGIN_TOL_MM = 1.0
UNIT_TOL = 1e-4


def _res(cid, ok, info="", msg=""):
    return {"id": cid, "ok": ok, "info": info, "msg": msg}


def _names(objs, cap=4):
    n = sorted({o.name for o in objs})
    return ", ".join(n[:cap]) + (f" +{len(n) - cap} more" if len(n) > cap else "")


# ---------------------------------------------------------------- measurement

def measure():
    """Everything the checks need, gathered once from the evaluated scene."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    m = {"objects": list(bpy.context.scene.objects), "meshes": [], "lo": None, "hi": None}
    lo, hi = [1e30] * 3, [-1e30] * 3
    for obj in m["objects"]:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        ev.to_mesh_clear()
        bm.normal_update()
        mw = obj.matrix_world
        for v in bm.verts:
            w = mw @ v.co
            for i in range(3):
                lo[i], hi[i] = min(lo[i], w[i]), max(hi[i], w[i])
        m["meshes"].append((obj, bm))
    if m["meshes"]:
        m["lo"], m["hi"] = lo, hi
    return m


def release(m):
    for _, bm in m["meshes"]:
        bm.free()
    m["meshes"] = []


def _mm(v):
    return v * 1000.0


# --------------------------------------------------------------------- checks

def check_spec(spec, variant):
    bad = []
    if not isinstance(spec, dict):
        return [_res("spec", False, msg="spec is not a mapping")]
    bad += [f"unknown field {k!r}" for k in spec if k not in TOP]
    for sec, known in SECTIONS.items():
        if isinstance(spec.get(sec), dict):
            bad += [f"unknown field {sec}.{k}" for k in spec[sec] if k not in known]
    dims = spec.get("dimensions") or {}
    bad += [f"dimensions.{k}: named sub-measurements are not implemented"
            for k in dims if k not in DIMS]
    for k in DIMS:
        if k in dims and not (isinstance(dims[k], dict) and {"value", "tol"} <= set(dims[k])):
            bad.append(f"dimensions.{k} needs value and tol")
    for p in spec.get("parts") or []:
        extra = set(p) - {"name", "count", "notes"}
        if "name" not in p or extra:
            bad.append(f"part entry {p!r}: needs name; unknown {sorted(extra)}")
    if spec.get("model") != variant:
        bad.append(f"model {spec.get('model')!r} != variant {variant!r}")
    unsupported = set(spec.get("targets") or []) - IMPLEMENTED_TARGETS
    bad += [f"target {t!r} not implemented (ADR 0006)" for t in sorted(unsupported)]
    return [_res("spec", not bad, "spec ok", "; ".join(bad))]


def check_dimensions(spec, m):
    out = []
    dims = spec.get("dimensions") or {}
    axis = {"width": 0, "depth": 1, "height": 2}  # Blender: X, Y, Z-up
    for k in DIMS:
        if k not in dims:
            continue
        if m["lo"] is None:
            out.append(_res(k, False, msg=f"{k}: no mesh to measure"))
            continue
        a = axis[k]
        got = _mm(m["hi"][a] - m["lo"][a])
        want, tol = dims[k]["value"], dims[k]["tol"]
        out.append(_res(k, abs(got - want) <= tol, f"{got:.1f}",
                        f"{k} {got:.1f}mm, want {want}±{tol}"))
    return out


def check_parts(spec, m):
    want = spec.get("parts")
    if want is None:
        return []
    objs = m["objects"]
    problems, matched = [], set()
    for p in want:
        rx = re.compile(rf"{re.escape(p['name'])}(\.\d{{3}})?")
        hit = [o for o in objs if rx.fullmatch(o.name)]
        matched.update(o.name for o in hit)
        n = p.get("count", 1)
        if len(hit) != n:
            problems.append(f"{p['name']} x{len(hit)}, want {n}")
    extra = [o for o in objs if o.name not in matched]
    if extra:
        problems.append(f"unexpected: {_names(extra)}")
    total = sum(p.get("count", 1) for p in want)
    return [_res("parts", not problems, f"{len(objs)}/{total}", "parts " + "; ".join(problems))]


def _per_mesh(m, pred):
    """Names of meshes for which pred(bm) is truthy, and the summed detail."""
    return [(o, r) for o, bm in m["meshes"] if (r := pred(bm))]


def check_topology(spec, m):
    t = spec.get("topology")
    if not t:
        return []
    out = []
    faces = sum(len(bm.faces) for _, bm in m["meshes"])
    tris = sum(len(f.verts) - 2 for _, bm in m["meshes"] for f in bm.faces)
    if "tri_budget" in t:
        out.append(_res("tris", tris <= t["tri_budget"], f"{tris:,}/{t['tri_budget']:,}",
                        f"tris {tris:,} > budget {t['tri_budget']:,}"))
    if "quads_min_pct" in t:
        quads = sum(1 for _, bm in m["meshes"] for f in bm.faces if len(f.verts) == 4)
        pct = 100.0 * quads / faces if faces else 0.0
        out.append(_res("quads", pct >= t["quads_min_pct"], f"{pct:.0f}%",
                        f"quads {pct:.1f}%, want >={t['quads_min_pct']}%"))
    if t.get("ngons_allowed") is False:
        bad = _per_mesh(m, lambda bm: sum(1 for f in bm.faces if len(f.verts) > 4))
        out.append(_res("ngons", not bad, "0",
                        "ngons in " + ", ".join(f"{o.name}({n})" for o, n in bad[:4])))
    if t.get("manifold") == "required":
        bad = _per_mesh(m, lambda bm: sum(1 for e in bm.edges if not e.is_manifold))
        out.append(_res("manifold", not bad, "ok",
                        "non-manifold edges in "
                        + ", ".join(f"{o.name}({n})" for o, n in bad[:4])))
    if t.get("loose_geometry") == "forbidden":
        def loose(bm):
            return (sum(1 for v in bm.verts if not v.link_edges)
                    + sum(1 for e in bm.edges if not e.link_faces))
        bad = _per_mesh(m, loose)
        out.append(_res("loose", not bad, "0",
                        "loose verts/edges in "
                        + ", ".join(f"{o.name}({n})" for o, n in bad[:4])))
    if t.get("normals") == "outward":
        out.append(_check_normals(m))
    elif "normals" in t:
        out.append(_res("normals", False, msg=f"normals: {t['normals']!r} not implemented"))
    if "doubles_tolerance_mm" in t:
        d = t["doubles_tolerance_mm"] / 1000.0

        def doubles(bm):
            return len(bmesh.ops.find_doubles(bm, verts=bm.verts, dist=d)["targetmap"])
        bad = _per_mesh(m, doubles)
        out.append(_res("doubles", not bad, "0",
                        f"verts within {t['doubles_tolerance_mm']}mm in "
                        + ", ".join(f"{o.name}({n})" for o, n in bad[:4])))
    return out


def _check_normals(m):
    """Recompute outward normals on a copy and count faces that disagree."""
    bad = []
    for obj, bm in m["meshes"]:
        ref = bm.copy()
        bmesh.ops.recalc_face_normals(ref, faces=ref.faces)
        ref.normal_update()
        bm.faces.ensure_lookup_table()
        ref.faces.ensure_lookup_table()
        n = sum(1 for a, b in zip(bm.faces, ref.faces) if a.normal.dot(b.normal) < 0)
        ref.free()
        if n:
            bad.append((obj, n))
    return _res("normals", not bad, "outward",
                "inward faces in " + ", ".join(f"{o.name}({n})" for o, n in bad[:4]))


def check_uv(spec, m):
    uv = spec.get("uv")
    if not uv or not uv.get("required"):
        return []
    msgs = []
    if uv.get("udim"):
        msgs.append("udim not implemented")
    if uv.get("overlap_allowed") is False:
        msgs.append("uv overlap check not implemented (OPEN-QUESTIONS #4)")
    missing = [o for o, _ in m["meshes"] if not o.data.uv_layers]
    if missing:
        msgs.append(f"no UV layer: {_names(missing)}")
    return [_res("uv", not msgs, "ok", "uv " + "; ".join(msgs))]


def check_materials(spec, m):
    mat = spec.get("materials")
    if not mat:
        return []
    used = {s.material.name for o, _ in m["meshes"] for s in o.material_slots if s.material}
    out = []
    if "max_slots" in mat:
        out.append(_res("mat_slots", len(used) <= mat["max_slots"],
                        f"{len(used)}/{mat['max_slots']}",
                        f"{len(used)} materials > max {mat['max_slots']}"))
    if mat.get("names"):
        want = set(mat["names"])
        problems = []
        if used - want:
            problems.append(f"unexpected {sorted(used - want)}")
        if want - used:
            problems.append(f"unused {sorted(want - used)}")
        out.append(_res("mat_names", not problems, "ok", "materials " + "; ".join(problems)))
    return out


def check_transform(spec, m):
    t = spec.get("transform")
    if not t:
        return []
    out = []
    if t.get("up_axis", "Z") != "Z":
        out.append(_res("up_axis", False, msg=f"up_axis {t['up_axis']!r}: build is Z-up (ADR 0006)"))
    origin = t.get("origin")
    if origin and m["lo"] is not None:
        lo, hi = m["lo"], m["hi"]
        cx, cy = _mm((lo[0] + hi[0]) / 2), _mm((lo[1] + hi[1]) / 2)
        cz, floor = _mm((lo[2] + hi[2]) / 2), _mm(lo[2])
        if origin == "base_center":
            got = (cx, cy, floor)
        elif origin == "bbox_center":
            got = (cx, cy, cz)
        else:
            out.append(_res("origin", False, msg=f"origin {origin!r} not implemented"))
            got = None
        if got is not None:
            ok = all(abs(g) <= ORIGIN_TOL_MM for g in got)
            out.append(_res("origin", ok, origin,
                            f"{origin} at ({got[0]:.1f}, {got[1]:.1f}, {got[2]:.1f})mm, "
                            f"want 0±{ORIGIN_TOL_MM}"))
    if t.get("scale_applied"):
        bad = [o for o, _ in m["meshes"] if any(abs(s - 1) > UNIT_TOL for s in o.scale)]
        out.append(_res("scale", not bad, "1", f"scale not applied: {_names(bad)}"))
    if t.get("rotation_applied"):
        bad = [o for o, _ in m["meshes"]
               if any(abs(a) > UNIT_TOL for a in o.rotation_euler)
               or abs(o.rotation_quaternion.angle) > UNIT_TOL and o.rotation_mode == "QUATERNION"]
        out.append(_res("rotation", not bad, "0", f"rotation not applied: {_names(bad)}"))
    return out


CHECKS = (check_dimensions, check_parts, check_topology, check_uv, check_materials,
          check_transform)


def run(spec, variant, only=None):
    """All checks against the current scene -> list of results.

    `only` narrows to a set of check ids (the export round-trip re-measures a subset;
    an importer legitimately re-welds and re-triangulates, so topology is not judged there).
    """
    m = measure()
    try:
        results = check_spec(spec, variant)
        for fn in CHECKS:
            results += fn(spec, m)
    finally:
        release(m)
    if only is not None:
        results = [r for r in results if r["id"] in only]
    return results


def stats(spec, results):
    """Compact readings for the report and the commit-message stamp."""
    return {r["id"]: r["info"] for r in results}


def report(variant, results):
    """Results -> terse report lines (ADR 0005: ~50 tokens on green)."""
    n, ok = len(results), sum(r["ok"] for r in results)
    fails = [r for r in results if not r["ok"]]
    info = {r["id"]: r["info"] for r in results}
    if fails:
        lines = [f"{variant} FAIL {ok}/{n}"]
        lines += [f"  FAIL {r['id']:<9} {r['msg']}" for r in fails]
        return lines
    stamp = f"verify {ok}/{n}"
    if "tris" in info:
        stamp += f" | tris {info['tris'].split('/')[0]}"
    if "height" in info:
        stamp += f" | height {info['height'].split('.')[0]}mm"
    rest = [f"{k} {info[k]}" for k in ("width", "depth", "quads", "parts", "mat_slots", "origin")
            if k in info]
    return [f"{variant} PASS  {stamp}", "  " + " | ".join(rest)] if rest else [f"{variant} PASS  {stamp}"]
