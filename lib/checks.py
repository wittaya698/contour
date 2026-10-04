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
       "topology", "uv", "materials", "transform", "render", "notes", "clips"}
SECTIONS = {
    "topology": {"tri_budget", "quads_min_pct", "ngons_allowed", "manifold",
                 "loose_geometry", "normals", "doubles_tolerance_mm"},
    "uv": {"required", "overlap_allowed", "udim"},
    "materials": {"max_slots", "names"},
    "transform": {"origin", "scale_applied", "rotation_applied", "up_axis",
                  "pivot_tolerance_mm"},
    "render": {"grid_metres", "sheet_resolution"},
}
CLIP = {"feel", "frames", "fps", "loop", "keys", "tol_deg", "seam_growth_mm",
        "roundtrip_mm"}
CLIP_NEEDS = ("frames", "fps", "keys", "tol_deg", "seam_growth_mm", "roundtrip_mm")
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


def rig(spec):
    """The rig tree, over the spec alone (ADR 0023).

    A part names the part it hangs from with `parent:`. A spec with no
    `parent:` anywhere has no rig and is judged on nothing, so every spec
    written before the rig existed stays as it was. With one, the tree must be
    a tree: one root, every parent a part, no cycle — and one bone per part,
    so a rigged name counted more than once fails rather than guessing which
    instance the bone is.
    """
    want = spec.get("parts") or []
    if not any("parent" in p for p in want):
        return []
    named = {p["name"]: p for p in want}
    problems = []
    roots = sorted(name for name, p in named.items() if "parent" not in p)
    if len(roots) != 1:
        problems.append(f"{len(roots)} roots: {_named(roots)}" if roots else "no root")
    for name, p in named.items():
        if "parent" in p and p["parent"] not in named:
            problems.append(f"{name}'s parent {p['parent']!r} is not a part")
        if p.get("count", 1) != 1:
            problems.append(f"{name} x{p['count']}: one bone per part, count must be 1")
    looped = set()
    for name in named:
        seen, at = [], name
        while at in named and "parent" in named[at] and at not in seen:
            seen.append(at)
            at = named[at]["parent"]
        if at in seen:
            looped.update(seen[seen.index(at):])
    if looped:
        problems.append(f"cycle: {_named(looped)}")
    root = roots[0] if len(roots) == 1 else "?"
    return [result("rig", not problems, f"{len(named)} parts from {root}",
                   "rig " + "; ".join(problems))]


def _joints(spec):
    """Every `(part, parent)` pair the rig names, in spec order."""
    return [(p["name"], p["parent"]) for p in spec.get("parts") or [] if "parent" in p]


def _gap_mm(a, b):
    """How far apart two world boxes are, in mm; 0 when they touch or overlap.

    A floor under the gap between the surfaces themselves, which is all the
    message needs: a part this far off its parent is not near a seam.
    """
    return _mm(sum(max(0.0, b[0][i] - a[1][i], a[0][i] - b[1][i]) ** 2
                   for i in range(3)) ** 0.5)


def _no_seam(name, parent, boxes):
    """Why a joint has no seam, as far as the boxes can say."""
    said = f"{name} has no seam with {parent}"
    if boxes.get(name) and boxes.get(parent):
        gap = _gap_mm(boxes[name], boxes[parent])
        said += f": floats {gap:.1f}mm off" if gap > 0 else ": touches at most, does not cross"
    return said


def seams(spec, m):
    """A seam at every joint (ADR 0023): where a part turns is measured, so
    it has to be there to measure.

    A seam is the gather's crossing between the two parts, which a part that
    floats off or only touches its parent at a point does not have.
    """
    joints = _joints(spec)
    if not joints:
        return []
    crossed = {frozenset(c["parts"]) for c in m["contacts"]}
    boxes = {p["name"]: p["bounds"] for p in m["parts"]}
    bad = [_no_seam(name, parent, boxes) for name, parent in joints
           if frozenset((name, parent)) not in crossed]
    n = len(joints)
    return [result("seams", not bad, f"{n} joint" + ("s" if n != 1 else ""),
                   "; ".join(bad))]


def pivots(spec, m):
    """Each part's origin on its pivot, the centre of its seam (ADR 0023).

    `build.py` places every origin by hand; this is what makes that placement
    checked rather than trusted. A joint with no seam has no pivot to be on,
    and `seams` has already said so.
    """
    joints = _joints(spec)
    if not joints:
        return []
    tol = (spec.get("transform") or {}).get("pivot_tolerance_mm")
    if tol is None:
        return [result("pivots", False,
                       msg="rig needs transform.pivot_tolerance_mm: the user's, not a default")]
    centres = {frozenset(c["parts"]): c["centre"] for c in m["contacts"]}
    origins = {p["name"]: p["origin"] for p in m["parts"]}
    bad, worst = [], 0.0
    for name, parent in joints:
        centre = centres.get(frozenset((name, parent)))
        if centre is None or name not in origins:
            continue
        off = _mm(sum((a - b) ** 2 for a, b in zip(origins[name], centre)) ** 0.5)
        worst = max(worst, off)
        if off > tol:
            at = ", ".join(f"{_mm(c):.1f}" for c in centre)
            bad.append(f"{name} origin {off:.1f}mm off its pivot at ({at})mm")
    return [result("pivots", not bad, f"{worst:.1f}/{tol}mm",
                   "; ".join(bad) + f" (tolerance {tol}mm)")]


def bones(spec, m):
    """The armature against the tree (ADR 0023): one rig, one bone per part,
    each hanging from the bone the tree says, each part wholly on its own.

    The gather says what the scene holds; the tree says what it should.
    """
    rigs, names = m["rigs"], _named(r["name"] for r in m["rigs"])
    if not _joints(spec):
        return [result("bones", False, msg=f"bones: armature {names}, and the spec has no rig")
                ] if rigs else []
    if len(rigs) != 1:
        said = (f"{len(rigs)} armatures: {names}; one rig per model" if rigs
                else "no armature; build.py needs kit.rig()")
        return [result("bones", False, msg="bones: " + said)]
    want = {p["name"]: p.get("parent") for p in spec["parts"]}
    have = {b["name"]: b["parent"] for b in rigs[0]["bones"]}
    bad = [f"no bone for {name}" for name in want if name not in have]
    bad += [f"bone {name} is no part" for name in have if name not in want]
    bad += [f"{name}'s bone hangs from {have[name] or 'none'}, the tree says {parent or 'none'}"
            for name, parent in want.items() if name in have and have[name] != parent]
    for p in m["parts"]:
        if p["name"] in want and p["bound_to"] != p["name"]:
            bad.append(f"{p['name']} is on {p['bound_to']}'s bone, not its own"
                       if p["bound_to"] else f"{p['name']} is not wholly on a bone")
    return [result("bones", not bad, f"{len(have)}/{len(want)}", "bones " + "; ".join(bad))]


def _clip_problems(name, clip, parts):
    """What is wrong with how the spec writes one clip, before any keying.

    `feel` is the user's word for how it should look and is judged at the
    checkpoint, by eye (ADR 0023); it is known here and checked nowhere.
    """
    if not isinstance(clip, dict):
        return [f"clips.{name} is not a mapping"]
    bad = [f"unknown field clips.{name}.{k}" for k in clip if k not in CLIP]
    missing = [k for k in CLIP_NEEDS if k not in clip]
    if missing:
        return bad + [f"clips.{name} needs {', '.join(missing)}"]
    last = clip["frames"] - 1 if clip.get("loop") else clip["frames"]
    for frame, pose in clip["keys"].items():
        if not (isinstance(frame, int) and 0 <= frame <= last):
            bad.append(f"clips.{name} key {frame} is outside 0..{last}")
        for bone, angles in (pose or {}).items():
            if bone not in parts:
                bad.append(f"clips.{name} key {frame} names {bone}, which is no part")
            elif not (isinstance(angles, list) and len(angles) == 3):
                bad.append(f"clips.{name} key {frame} {bone}: want [x, y, z] degrees")
    return bad


def _angles(xyz):
    return ", ".join(f"{a:.1f}" for a in xyz)


def _off(reads, want):
    """The largest difference between two sets of angles, in degrees, each
    taken the short way round: 335 and -25 are the same angle."""
    return max(abs((r - w + 180) % 360 - 180) for r, w in zip(reads, want))


def _clip(name, clip, got):
    """One clip as read back against the spec's: length, fps, the loop
    closing, and every bone at every key."""
    tol, poses = clip["tol_deg"], got["poses"]
    bad = []
    if got["frames"] != clip["frames"]:
        bad.append(f"{name}: {got['frames']} frames, want {clip['frames']}")
    if got["fps"] != clip["fps"]:
        bad.append(f"{name}: {got['fps']} fps, want {clip['fps']}")
    end, first = got["frames"], poses[0]
    if clip.get("loop") and end in poses:
        for bone, reads in poses[end].items():
            if _off(reads, first[bone]) > tol:
                bad.append(f"{name} f{end} {bone}: reads ({_angles(reads)}), "
                           f"f0 ({_angles(first[bone])}); the loop does not close")
    for frame, pose in clip["keys"].items():
        # a key past the clip's end is the length's failure, already said
        for bone, reads in poses.get(frame, {}).items():
            angles = (pose or {}).get(bone, [0, 0, 0])
            if _off(reads, angles) > tol:
                bad.append(f"{name} f{frame} {bone}: reads ({_angles(reads)}), "
                           f"want ({', '.join(str(a) for a in angles)}) ±{tol}°")
    return bad


def _motion(name, clip, got, joints, rest):
    """Every frame's crossings (ADR 0023). A part may cross only its parent,
    at their seam, and that seam may grow no more than the clip allows past
    the size it has at rest: a part swinging through its parent grows it.

    A part entering another is named once, at the first frame it does; a
    seam that grows, once, at its worst frame. A joint with no seam at rest
    has nothing to grow from, and `seams` has said why.
    """
    child = {frozenset(j): j for j in joints}
    tol = clip["seam_growth_mm"]
    bad, said, worst = [], set(), {}
    for frame, crossed in sorted(got["contacts"].items()):
        for c in crossed:
            pair = frozenset(c["parts"])
            if pair not in child:
                if pair not in said:
                    said.add(pair)
                    bad.append(f"{name} f{frame}: {c['parts'][0]} enters {c['parts'][1]}")
            elif pair in rest:
                grew = _mm(c["reach"] - rest[pair])
                if grew > worst.get(pair, (0.0,))[0]:
                    worst[pair] = (grew, frame)
    for pair, (grew, frame) in worst.items():
        if grew > tol:
            part, parent = child[pair]
            bad.append(f"{name} f{frame}: {part}'s seam with {parent} grows "
                       f"{grew:.1f}mm, past {tol}mm")
    return bad


def clips(spec, m):
    """Each clip as keyed against the spec's keys (ADR 0023)."""
    want = spec.get("clips")
    if not want or not isinstance(want, dict):
        return []
    if not _joints(spec):
        return [result("clips", False, msg="clips need a rig: give the parts a parent:")]
    if len(m["rigs"]) != 1:
        return []  # `bones` has said why there is no one rig to read
    have = {c["name"]: c for c in m["rigs"][0]["clips"]}
    rest = {frozenset(c["parts"]): c["reach"] for c in m["contacts"]}
    bad = [f"{name} is keyed and not in the spec" for name in have if name not in want]
    parts_ = {p["name"] for p in spec.get("parts") or []}
    for name, clip in want.items():
        if _clip_problems(name, clip, parts_):
            bad.append(f"{name} cannot be judged: the spec check says why")
            continue
        if name not in have:
            bad.append(f"{name} is not keyed")
            continue
        bad += _clip(name, clip, have[name])
        bad += _motion(name, clip, have[name], _joints(spec), rest)
    info = ", ".join(f"{name} {have[name]['frames']}f" for name in want if name in have)
    return [result("clips", not bad, info, "clips " + "; ".join(bad))]


def _corners_off(a, b):
    """How far apart the furthest pair of matching corners of two world boxes
    stand, in metres: on each axis the worse of the two faces, then across."""
    return sum(max(abs(a[0][i] - b[0][i]), abs(a[1][i] - b[1][i])) ** 2
               for i in range(3)) ** 0.5


def _counts(built, file):
    """Bones, clips and each clip's frames, as the file itself has them. A
    file carries seconds and no rate, so a clip's length is read at the fps
    its build keyed it at: one exported at another rate is the wrong number
    of frames long (issue 52)."""
    bones = len(built[0]["bones"]) if built else 0
    clips_ = built[0]["clips"] if built else []
    bad = [] if file["joints"] == bones else [f"{file['joints']} bones in the file, built {bones}"]
    for clip in clips_:
        secs = file["clips"].get(clip["name"])
        if secs is None:
            bad.append(f"{clip['name']} is not in the file")
        elif abs(secs * clip["fps"] - clip["frames"]) > UNIT_TOL:
            bad.append(f"{clip['name']} runs {secs * clip['fps']:.1f}f at {clip['fps']}fps "
                       f"in the file, built {clip['frames']}f")
    bad += [f"{name} is in the file and not the build"
            for name in file["clips"] if name not in {c["name"] for c in clips_}]
    info = ", ".join([f"{bones} bones"] + [f"{c['name']} {c['frames']}f" for c in clips_])
    return result("gl_rig", not bad, info, "; ".join(bad))


def one_rate(rates):
    """`{clip: fps}` -> `(fps, "")`, or `(None, why)` when the clips do not
    share one. A `.glb` holds seconds, and the exporter turns frames into them
    at the scene's one rate, so clips at two rates cannot go in one file."""
    if len(set(rates.values())) > 1:
        each = ", ".join(f"{n} {f}fps" for n, f in sorted(rates.items()))
        return None, f"clips at more than one rate ({each}): a .glb plays at one"
    return next(iter(rates.values()), None), ""


def carried(spec, built, got, file):
    """The rig as the export carried it, against the build (ADR 0023).

    `built` and `got` are the `rigs` of two measurements, the `.blend`'s and
    the re-imported `.glb`'s, and `file` what `glb.measure` read off the file
    itself; `_counts` says what is counted. Every part's world box at every frame of every
    clip is compared, and a part off by more than the clip's `roundtrip_mm`
    is named once, at its worst frame. Not angles: the importer may re-orient
    a bone, and where the part ends up does not care which way it points.
    """
    want = spec.get("clips") or {}
    have = {c["name"]: c for r in got for c in r["clips"]}
    bad = []
    for clip in built[0]["clips"] if built else []:
        name = clip["name"]
        tol = (want.get(name) or {}).get("roundtrip_mm")
        if not isinstance(tol, (int, float)):
            bad.append(f"{name} cannot be judged: the spec check says why")
            continue
        if name not in have:
            bad.append(f"{name} is not in the re-import")
            continue
        worst, lost = {}, set()
        for frame, boxes in sorted(clip["boxes"].items()):
            back = have[name]["boxes"].get(frame, {})
            for part, box in boxes.items():
                if part not in back:
                    if part not in lost:
                        lost.add(part)
                        bad.append(f"{name} f{frame}: {part} is not in the re-import")
                    continue
                off = _mm(_corners_off(box, back[part]))
                if off > worst.get(part, (0.0,))[0]:
                    worst[part] = (off, frame)
        bad += [f"{name} f{frame}: {part} {off:.1f}mm from the build, past {tol}mm"
                for part, (off, frame) in sorted(worst.items()) if off > tol]
    return [_counts(built, file), result("re_motion", not bad, msg="; ".join(bad))]


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
        extra = set(p) - {"name", "count", "notes", "parent"}
        if "name" not in p or extra:
            bad.append(f"part entry {p!r}: needs name; unknown {sorted(extra)}")
        elif "parent" in p and not isinstance(p["parent"], str):
            bad.append(f"{p['name']}: parent must be a part name, got {p['parent']!r}")
    names = {p.get("name") for p in doc.get("parts") or []}
    clips_ = doc.get("clips") or {}
    if not isinstance(clips_, dict):
        bad.append("clips is not a mapping of clip names")
        clips_ = {}
    for name, clip in clips_.items():
        bad += _clip_problems(name, clip, names)
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
    out = spec(doc, variant) + rig(doc)
    for check, reads in SEQUENCE:
        out += check(doc, m[reads])
    out += seams(doc, m) + pivots(doc, m) + bones(doc, m) + clips(doc, m)
    if only is not None:
        out = [r for r in out if r["id"] in only]
    return out
