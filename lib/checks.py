"""Judgement, as arithmetic over a measurement (ADR 0020).

Nothing here touches geometry. A check reads per-part summary numbers that
`lib/measure.py` gathered and answers the same verdict `verify.py` has always
produced — which is what lets a check be exercised from a record written by
hand, with no Blender and no fixture (`tests/test_checks.py`).

In the Blender-free half by name (`tests/test_lib_split.py`), so a check that
acquires a Blender import is a red selftest rather than a discovery.
"""
import re

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


def result(cid, ok, info="", msg=""):
    """One verdict: `info` is the compact reading shown on a pass, `msg` the
    detail shown on a failure. The shape `verify.report` prints and the mutant
    suite reads, which is why it lives with the checks rather than beside the
    printing."""
    return {"id": cid, "ok": ok, "info": info, "msg": msg}


def _tris(faces):
    """Triangles in a face histogram: a quad is two, an n-gon its degree less
    two. The budget has always counted this way; it now counts it from the
    summary rather than from live faces."""
    return sum((degree - 2) * n for degree, n in faces.items())


def tris(parts):
    """Triangles in a whole measurement. Public because the export round-trip
    asks for it without a budget in hand: it compares one measurement against
    another rather than against the spec."""
    return sum(_tris(p["faces"]) for p in parts)


def _blame(parts, count):
    """The parts `count` finds something in, named with their number.

    Capped the way the old report was: four names is a lead to follow, twenty
    is a wall of text nobody reads (ADR 0005).
    """
    bad = [(p["name"], n) for p in parts if (n := count(p))]
    return ", ".join(f"{name}({n})" for name, n in bad[:4]), bad


def topology(spec, parts):
    """The topology section, judged over the per-part records.

    `parts` is the measurement: one record per part, every field a number the
    gather produced. Aggregates are summed here rather than gathered, so a
    part added to the scene needs no new field.
    """
    t = spec.get("topology")
    if not t:
        return []
    out = []
    if "tri_budget" in t:
        n = tris(parts)
        out.append(result("tris", n <= t["tri_budget"],
                          f"{n:,}/{t['tri_budget']:,}",
                          f"tris {n:,} > budget {t['tri_budget']:,}"))
    if "quads_min_pct" in t:
        faces = sum(sum(p["faces"].values()) for p in parts)
        quads = sum(p["faces"].get(4, 0) for p in parts)
        pct = 100.0 * quads / faces if faces else 0.0
        out.append(result("quads", pct >= t["quads_min_pct"], f"{pct:.0f}%",
                          f"quads {pct:.1f}%, want >={t['quads_min_pct']}%"))
    if t.get("ngons_allowed") is False:
        said, bad = _blame(parts, lambda p: sum(n for degree, n in p["faces"].items()
                                                if degree > 4))
        out.append(result("ngons", not bad, "0", "ngons in " + said))
    if t.get("manifold") == "required":
        said, bad = _blame(parts, lambda p: p["non_manifold_edges"])
        out.append(result("manifold", not bad, "ok",
                          "non-manifold edges in " + said))
    if t.get("loose_geometry") == "forbidden":
        said, bad = _blame(parts, lambda p: p["loose_verts"] + p["loose_edges"])
        out.append(result("loose", not bad, "0",
                          "loose verts/edges in " + said))
    if t.get("normals") == "outward":
        said, bad = _blame(parts, lambda p: p["flipped_faces"])
        out.append(result("normals", not bad, "outward",
                          "inward faces in " + said))
    elif "normals" in t:
        out.append(result("normals", False,
                          msg=f"normals: {t['normals']!r} not implemented"))
    if "doubles_tolerance_mm" in t:
        want = t["doubles_tolerance_mm"]
        # `within` includes the tolerance itself, which is what the old
        # `find_doubles(dist=...)` call meant by it. A part with fewer than two
        # vertices has no closest pair and cannot fail this.
        bad = [(p["name"], p["nearest_pair_mm"]) for p in parts
               if p["nearest_pair_mm"] is not None and p["nearest_pair_mm"] <= want]
        out.append(result("doubles", not bad, "0",
                          f"vertices within {want}mm in "
                          + ", ".join(f"{name}({gap:.3f}mm)" for name, gap in bad[:4])))
    return out


def bounds(parts):
    """The world box every part sits inside, as `(lo, hi)` — `(None, None)`
    when nothing in the measurement has a corner to contribute."""
    boxes = [p["bounds"] for p in parts if p["bounds"]]
    if not boxes:
        return None, None
    return ([min(b[0][i] for b in boxes) for i in range(3)],
            [max(b[1][i] for b in boxes) for i in range(3)])


def _mm(v):
    return v * 1000.0


def dimensions(spec, parts):
    """The stated dimensions against the box the parts occupy."""
    out = []
    dims = spec.get("dimensions") or {}
    axis = {"width": 0, "depth": 1, "height": 2}  # Blender: X, Y, Z-up
    lo, hi = bounds(parts)
    for k in DIMS:
        if k not in dims:
            continue
        if lo is None:
            out.append(result(k, False, msg=f"{k}: no mesh to measure"))
            continue
        a = axis[k]
        got = _mm(hi[a] - lo[a])
        want, tol = dims[k]["value"], dims[k]["tol"]
        out.append(result(k, abs(got - want) <= tol, f"{got:.1f}",
                          f"{k} {got:.1f}mm, want {want}±{tol}"))
    return out


def _named(names, cap=4):
    """Some of the names, alphabetically, and how many more there were."""
    n = sorted(set(names))
    return ", ".join(n[:cap]) + (f" +{len(n) - cap} more" if len(n) > cap else "")


def parts(spec, objects):
    """The parts the spec names against the objects the scene holds.

    `objects` is every object name, mesh or not: a stray empty is a part list
    that does not match, and a check that only looked at meshes would not see
    it.
    """
    want = spec.get("parts")
    if want is None:
        return []
    problems, matched = [], set()
    for p in want:
        rx = re.compile(rf"{re.escape(p['name'])}(\.\d{{3}})?")
        hit = [name for name in objects if rx.fullmatch(name)]
        matched.update(hit)
        n = p.get("count", 1)
        if len(hit) != n:
            problems.append(f"{p['name']} x{len(hit)}, want {n}")
    extra = [name for name in objects if name not in matched]
    if extra:
        problems.append(f"unexpected: {_named(extra)}")
    total = sum(p.get("count", 1) for p in want)
    return [result("parts", not problems, f"{len(objects)}/{total}",
                   "parts " + "; ".join(problems))]


def uv(spec, parts):
    """UV coverage, and the two UV rules this verifier cannot yet enforce.

    Unsupported rules FAIL rather than skip, which is `verify.py`'s oldest rule
    and the one the move must not lose: a silently ignored constraint is the
    same failure as a weakened one.
    """
    u = spec.get("uv")
    if not u or not u.get("required"):
        return []
    msgs = []
    if u.get("udim"):
        msgs.append("udim not implemented")
    if u.get("overlap_allowed") is False:
        msgs.append("uv overlap check not implemented (OPEN-QUESTIONS #4)")
    missing = [p["name"] for p in parts if not p["uv_layers"]]
    if missing:
        msgs.append(f"no UV layer: {_named(missing)}")
    return [result("uv", not msgs, "ok", "uv " + "; ".join(msgs))]


def materials(spec, parts):
    """Material slots and names, counted over the scene rather than per part."""
    mat = spec.get("materials")
    if not mat:
        return []
    used = {name for p in parts for name in p["materials"]}
    out = []
    if "max_slots" in mat:
        out.append(result("mat_slots", len(used) <= mat["max_slots"],
                          f"{len(used)}/{mat['max_slots']}",
                          f"{len(used)} materials > max {mat['max_slots']}"))
    if mat.get("names"):
        want = set(mat["names"])
        problems = []
        if used - want:
            problems.append(f"unexpected {sorted(used - want)}")
        if want - used:
            problems.append(f"unused {sorted(want - used)}")
        out.append(result("mat_names", not problems, "ok",
                          "materials " + "; ".join(problems)))
    return out


def transform(spec, parts):
    """Up axis, origin placement, and whether scale and rotation were applied.

    The origin is read off the box rather than off any object's own origin,
    because what the spec means by `base_center` is where the model stands,
    not where Blender put a pivot.
    """
    t = spec.get("transform")
    if not t:
        return []
    out = []
    if t.get("up_axis", "Z") != "Z":
        out.append(result("up_axis", False,
                          msg=f"up_axis {t['up_axis']!r}: build is Z-up (ADR 0006)"))
    origin = t.get("origin")
    lo, hi = bounds(parts)
    if origin and lo is not None:
        cx, cy = _mm((lo[0] + hi[0]) / 2), _mm((lo[1] + hi[1]) / 2)
        cz, floor = _mm((lo[2] + hi[2]) / 2), _mm(lo[2])
        if origin == "base_center":
            got = (cx, cy, floor)
        elif origin == "bbox_center":
            got = (cx, cy, cz)
        else:
            out.append(result("origin", False,
                              msg=f"origin {origin!r} not implemented"))
            got = None
        if got is not None:
            ok = all(abs(g) <= ORIGIN_TOL_MM for g in got)
            out.append(result("origin", ok, origin,
                              f"{origin} at ({got[0]:.1f}, {got[1]:.1f}, {got[2]:.1f})mm, "
                              f"want 0±{ORIGIN_TOL_MM}"))
    if t.get("scale_applied"):
        bad = [p["name"] for p in parts
               if any(abs(s - 1) > UNIT_TOL for s in p["scale"])]
        out.append(result("scale", not bad, "1",
                          f"scale not applied: {_named(bad)}"))
    if t.get("rotation_applied"):
        bad = [p["name"] for p in parts if p["rotation_rad"] > UNIT_TOL]
        out.append(result("rotation", not bad, "0",
                          f"rotation not applied: {_named(bad)}"))
    return out


def spec(doc, variant):
    """The spec against what this verifier can enforce, before any geometry.

    Judged over the document rather than over a measurement, which is why it
    was already pure and why it moves here unchanged: a check is a check.
    """
    bad = []
    if not isinstance(doc, dict):
        return [result("spec", False, msg="spec is not a mapping")]
    bad += [f"unknown field {k!r}" for k in doc if k not in TOP]
    for sec, known in SECTIONS.items():
        if isinstance(doc.get(sec), dict):
            bad += [f"unknown field {sec}.{k}" for k in doc[sec] if k not in known]
    dims = doc.get("dimensions") or {}
    bad += [f"dimensions.{k}: named sub-measurements are not implemented"
            for k in dims if k not in DIMS]
    for k in DIMS:
        if k in dims and not (isinstance(dims[k], dict) and {"value", "tol"} <= set(dims[k])):
            bad.append(f"dimensions.{k} needs value and tol")
    for p in doc.get("parts") or []:
        extra = set(p) - {"name", "count", "notes"}
        if "name" not in p or extra:
            bad.append(f"part entry {p!r}: needs name; unknown {sorted(extra)}")
    if doc.get("model") != variant:
        bad.append(f"model {doc.get('model')!r} != variant {variant!r}")
    unsupported = set(doc.get("targets") or []) - IMPLEMENTED_TARGETS
    bad += [f"target {t!r} not implemented (ADR 0006)" for t in sorted(unsupported)]
    return [result("spec", not bad, "spec ok", "; ".join(bad))]


# The order the report reads in, and the one `verify.run` has always produced:
# the spec first, because a spec nobody can enforce makes every reading after
# it beside the point. Each entry names the part of the measurement it reads,
# so a check states what it needs rather than being handed everything.
SEQUENCE = ((dimensions, "parts"), (parts, "objects"), (topology, "parts"),
            (uv, "parts"), (materials, "parts"), (transform, "parts"))


def run(doc, variant, m, only=None):
    """Every verdict, over a measurement and nothing else (ADR 0020).

    `only` narrows to a set of check ids — the export round-trip re-measures a
    subset, because an importer legitimately re-welds and re-triangulates and
    topology is not judged there.
    """
    out = spec(doc, variant)
    for check, reads in SEQUENCE:
        out += check(doc, m[reads])
    if only is not None:
        out = [r for r in out if r["id"] in only]
    return out
