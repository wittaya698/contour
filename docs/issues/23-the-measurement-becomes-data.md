# 23 — The measurement becomes data

**Type:** AFK · **Source:** [ADR 0020](../adr/0020-checks-are-pure-over-a-measurement.md) · ADR 0009, ADR 0005

## What to build

The rest of ADR 0020, once slice 22 has accepted it.

`verify.measure()` gathers once from the evaluated scene and then hands back live
`bpy` objects and open `bmesh` handles, so every check iterates geometry in place.
`verify.py` consequently has no test file at all, its pure `report()` and `stats()`
included; `measure`/`release` is a lifetime obligation that `lib/cmd_render.py`
does not honour, leaking every `bmesh` on a raise; and `cmd_render` pays a full
`bmesh` build of every mesh to read two corners of a bounding box, while
`cmd_roundtrip` passes the `verify` module itself as an argument for want of a
handle.

**`lib/measure.py`** gathers per-part summary records and frees every `bmesh`
before returning. `release()` ceases to exist, and the leak goes with it — removed,
not fixed.

**`lib/checks.py`**, in the Blender-free half, holds the six checks plus
`check_spec`, which was already pure. Slice 03's roster proves a check that
acquires a Blender import is a red selftest.

**`verify.py` keeps `run`, `report` and `stats`.** ADR 0002 and ADR 0009 name the
path; it stays what Blender-side code calls, and `report()` gets its first test —
which is where ADR 0005's token budget becomes checkable rather than intended.

**`bounds()` is a separate cheap call** for the render, which asks for what it
needs and pays a depsgraph walk instead of a bmesh per mesh.

**Every mutant stays.** Pure tests join them; they do not replace them. A mutant
proves the gather, the checks and the report are wired together, which no pure
test can show. Each of ADR 0009's thirteen gains a counterpart: the same defect as
a measurement, asserted straight against the check.

**`cmd_roundtrip` stops taking `verify` as a parameter,** because a measurement is
now a thing it can hold.

## Acceptance criteria

- [ ] No `bpy` object or `bmesh` handle survives a gather; `release()` does not exist
- [ ] Every check is a pure function over a measurement, in the Blender-free half
- [ ] `lib/cmd_render.py` calls `bounds()` and builds no bmesh
- [ ] `_tris_now(verify)` is gone
- [ ] `tests/test_checks.py` covers every check from hand-written measurements, with no Blender
- [ ] `report()` and `stats()` have tests, including the green line's token budget
- [ ] All thirteen ADR 0009 mutants still fail their named checks
- [ ] `tests/test_lib_split.py`'s roster names `checks` free and `measure` Blender-side
- [ ] `contour check` output is byte-identical for the fixture and for a green space
- [ ] `contour selftest` green

## Blocked by

- [22 — Accept ADR 0020](22-accept-adr-0020.md)
