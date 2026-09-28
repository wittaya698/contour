"""Judgement, as arithmetic over a measurement (ADR 0020).

Nothing here touches geometry. A check reads per-part summary numbers that
`lib/measure.py` gathered and answers the same verdict `verify.py` has always
produced — which is what lets a check be exercised from a record written by
hand, with no Blender and no fixture (`tests/test_checks.py`).

In the Blender-free half by name (`tests/test_lib_split.py`), so a check that
acquires a Blender import is a red selftest rather than a discovery.
"""


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
        tris = sum(_tris(p["faces"]) for p in parts)
        out.append(result("tris", tris <= t["tri_budget"],
                          f"{tris:,}/{t['tri_budget']:,}",
                          f"tris {tris:,} > budget {t['tri_budget']:,}"))
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
