# 22 — Accept ADR 0020

**Type:** HITL · **Source:** [ADR 0020](../adr/0020-checks-are-pure-over-a-measurement.md)

## What to build

Nothing, until the tracer bullet has run.

ADR 0020 is Proposed, and its untested claim is narrow and checkable: **every
check in `verify.py` can be expressed as arithmetic over per-part summary numbers,
with no live geometry.** If one check needs real `bmesh`, the ADR is wrong and the
honest alternative is the one it rejects — a handle behind the seam, with the cost
stated rather than hidden.

**The bullet:** rewrite `check_topology` alone — the richest of the six, reading
face degree, quad percentage, n-gons and the triangle budget — as a pure function
over a hand-written measurement, alongside a gather that produces it. Then run its
ADR 0009 mutants and confirm each still fails the named check.

**Accept, amend, or withdraw** on that result. The precedent is ADR 0017, drafted
Proposed and accepted the same day on its tracer bullet's result — which
disagreed with what was expected and was more valuable for it.

**Do not start slice 23 first.** The whole point of a Proposed ADR is that the
measurement's shape is not yet known to be sufficient, and six checks rewritten
against a shape that turns out wrong is six rewrites.

## Acceptance criteria

- [x] `check_topology` exists as a pure function over a measurement, with a gather that feeds it
- [x] Every ADR 0009 mutant that targets a topology check still fails that check
- [x] A hand-written measurement in a test exercises the same check with no Blender
- [x] The per-part record's fields are named, and any field no check reads is listed
- [x] ADR 0020 is Accepted, amended, or withdrawn, with the result recorded in it
- [x] If accepted, `docs/adr/README.md` lists it

## What it came to

**Accepted, with ADR 0020's decision 1 amended.** `check_topology` is a pure function in
`lib/checks.py` — the Blender-free half by roster — over per-part records that
`lib/measure.py` gathers. All six sub-checks came out as arithmetic. `tris`,
`quads` and `ngons` are three readings of one face-degree histogram; `manifold`,
`loose` and `normals` are counts. Nothing reached for the handle behind the seam
that the rejected alternative would have given it, which is the result the ADR
was waiting on.

**The one field that could not be gathered as drafted.** A *duplicate-vertex
count* is a count at a tolerance, and the tolerance is
`topology.doubles_tolerance_mm` — in the spec, which a gather does not read. The
gather answers `nearest_pair_mm` instead: how close the closest two vertices
came. A pair within `d` exists if and only if the nearest pair is within `d`, so
the verdict is unchanged, and the failure line improves from *how many* to *how
close*. The ADR now carries the general rule — where a field would need the spec
to gather, gather the reading the spec is compared against — because that is the
part which will come up again in slice 23.

**Two checks still need real geometry, and the gather does it.** Whether a face
points outward is decided against a recomputed copy; the nearest pair is a
spatial query (`mathutils.kdtree`, signature read from `./contour api`, not
recalled). Both are reduced to a number before the gather returns. The ADR's
claim was always about the *check*, and it survives exactly as stated.

**The boundary was chosen rather than inherited.** `within 0.01mm` includes
0.01mm, which is what the `find_doubles(dist=...)` call it replaces meant. A
float will never land on it; it is pinned by a test anyway, because the next
person to read `<=` should find the reason beside it rather than a coin toss.

**What was proven.** Twelve pure tests in `tests/test_checks.py`, no Blender and
no fixture, and twelve mutants against `lib/checks.py`, all twelve caught —
including the two that would otherwise have been taken on faith, the tolerance
boundary and the part with no closest pair. `contour selftest` PASS (127.6s)
with `mutants 13/13` and `roundtrip 6/6`; all six ADR 0009 topology mutants
still fail their *named* check, which is what `attach()` asserts by id. The unit
suite went 372 -> 384.

`quads` is the one topology check with no ADR 0009 mutant, so it was covered a
different way rather than called covered: `tris` is derived from the same
histogram and `roundtrip` cross-checks it against the `.glb`'s own triangle
count, which nothing in this code produces. A wrong histogram fails there first.

**What this slice did not do**, and slice 23 will: `verify.measure()` still
builds its own `bmesh` per mesh for the bounds walk, so the fixture is gathered
twice. It cost nothing measurable — 127.6s against the 127.6s and 127.7s either
side of it — and removing it is ADR 0020's decision 5, not this bullet. `release()` still
exists for the same reason, and `report()` and `stats()` are still untested.

**measurement** is now in `docs/CONTEXT.md`'s vocabulary. The ADR makes it a
published shape, and a shape every check reads needs a name that means the same
thing in all of them.

## Blocked by

None.
