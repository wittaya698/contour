# 0020 — Checks are pure over a measurement

**Status:** Accepted · 2026-09-28 · **extends [ADR 0009](0009-verifier-proves-its-own-teeth.md)**

> **Accepted on its tracer bullet, with decision 1 amended** (issue 22).
> `check_topology` — the richest of the six, and the one that would have broken
> this if anything did — was rewritten as a pure function over per-part summary
> numbers. All six of its sub-checks came out as arithmetic; none needed the
> handle behind the seam that the rejected alternative would have given them.
> Twelve pure tests exercise it from records written by hand, with no Blender,
> and all six of ADR 0009's topology mutants still fail their named check.
>
> One field could not be gathered as drafted, and decision 1 says so below: a
> *duplicate-vertex count* is a count at a tolerance, and the tolerance is in
> the spec, which a gather does not read. The gather answers the nearest-pair
> distance instead — the same verdict for any tolerance, and a better failure
> line. That the correction made the measurement *more* spec-free is why the
> claim was accepted rather than merely survived.
>
> **Implemented in full** (issue 23). All six checks and `check_spec` are pure
> in `lib/checks.py`; `release()` is gone and `verify.py` is fifty lines that
> import no Blender, which is what gave `report()` and `stats()` their first
> tests. One thing decision 1 did not draft: the measurement carries the name
> of every object in the scene beside the per-part records, because the parts
> check is about the scene rather than about any part — a stray empty is a part
> list that does not match, and records of meshes alone cannot see it. An
> addition to the shape and not a correction to it; each check names which of
> the two it reads.

## Context

ADR 0009 makes the verifier prove its own teeth: `lib/mutants.py` breaks the
fixture one known way at a time under `contour selftest`, and a mutant that
passes fails the selftest. That covers the thing it was aimed at — a check
silently rewired to always pass.

It does not cover the shape of the verifier's own interface, and that shape has
three costs that have been paid quietly since.

`verify.measure()` exists to gather everything the checks need, once, from the
evaluated scene. It then hands back a dict containing live `bpy` objects and open
`bmesh` handles, so every check iterates `bm.faces` and `bm.verts` in place.

1. **No check can run outside Blender.** `verify.py` has no test file. Its only
   exercise is the mutant suite, which rebuilds the fixture in Blender once per
   mutant — so adding a check means adding a mutant *and* a Blender round trip.
   `report()` and `stats()` are pure string formatting against the token budget
   ADR 0005 sets, and they are untested for the same reason: they live in a file
   nothing can import without Blender.
2. **The interface leaks lifetimes.** `measure()` then `release(m)` is an
   ordering obligation on every caller. `verify.run` honours it with
   `try/finally`; `lib/cmd_render.py` does not, so a raise between its two lines
   leaks every `bmesh` in the scene.
3. **The narrowest caller pays the widest price.** `cmd_render` wants nothing but
   `lo`/`hi` to frame the sheet and pays a full `bmesh` build of every mesh to
   get it. `cmd_roundtrip` passes the `verify` module itself as a function
   argument, for want of any other handle on a measurement.

The common cause is that `measure()` stops halfway. It is named for gathering and
it does gather, but it hands over the instrument instead of the reading.

## Decision

1. **A measurement is data.** One record per part: face-degree histogram, vertex
   and edge counts, non-manifold and loose counts, **nearest-pair distance**,
   flipped-normal count, bounds, world transform, material names. No `bpy`
   object and no `bmesh` handle survives the gather. The record is small enough
   to write by hand in a test, which is the property the whole ADR is for.

   *Nearest-pair distance and not a duplicate-vertex count* (amended, issue 22).
   How many vertices are duplicates is a question about a tolerance, and the
   tolerance is `topology.doubles_tolerance_mm` — in the spec, which the gather
   does not read and must not, or the gather is coupled to the thing it is
   being kept clean of. How close the closest two vertices came is the same
   question with the tolerance taken out of it: a pair within `d` exists if and
   only if the nearest pair is within `d`, so the check is unchanged as a
   verdict and improved as a report, since it can say how close rather than how
   many. The rule this is an instance of: **where a field would need the spec
   to gather, gather the reading the spec is compared against.**
2. **The gather owns its own lifetimes.** `lib/measure.py` frees every `bmesh`
   before it returns. `release()` ceases to exist, and the leak in `cmd_render`
   goes with it — not fixed, removed.
3. **The checks are pure, and live in the Blender-free half.** `lib/checks.py`,
   named in `tests/test_lib_split.py`'s `FREE` roster, so a check that acquires a
   Blender import is a red selftest rather than a discovery.
4. **`verify.py` keeps `run`, `report` and `stats`.** ADR 0002 and ADR 0009 both
   name the path; it stays what Blender-side code calls.
5. **`bounds()` is a separate cheap call.** The render asks for bounds and pays a
   depsgraph walk, not a `bmesh` per mesh.
6. **ADR 0009 is unchanged.** Every mutant stays. Pure tests join them; they do
   not replace them. A mutant proves the gather, the checks and the report are
   wired together, which no pure test can show.

**Per-part summaries rather than exactly the aggregates the checks read today.**
That is a deliberate trade against coupling: ADR 0009 says the selftest grows
with the verifier, so a gather that must be edited for every new check is a
gather that will be edited constantly. Some fields will be gathered that no check
reads yet. That is the cheaper mistake.

## Consequences

- Every check gets an in-process test from a hand-written measurement, with no
  Blender, no fixture and no rebuild. `report()` and `stats()` get their first
  tests, which is where ADR 0005's token budget becomes checkable rather than
  merely intended.
- Each of ADR 0009's thirteen mutants gains a cheap counterpart: the same defect
  as a measurement, asserted directly against the check. The mutant keeps proving
  the wiring; the pure test proves the judgement.
- Adding a check may still mean adding a field to the gather. The coupling is
  reduced, not removed, and it now fails loudly — a check reading a field the
  gather does not produce is a `KeyError` in a pure test.
- `contour selftest` does not get cheaper. That is accepted: its cost buys the
  end-to-end proof, and the new tests are not a substitute for it.
- The measurement becomes a published shape. A field renamed is a change every
  check sees, which is the locality this is for and also the new cost.

## Rejected

- **Keeping geometry reachable behind the seam** — a measurement of reduced
  numbers *plus* a handle for anything that needs real geometry. Any check using
  the handle is back to needing Blender, and which checks those are stops being
  obvious, which is exactly the property being bought.
- **Only the aggregates the checks read today** — smallest data, nothing
  speculative, and it inverts the coupling: every new check edits the gather.
- **Moving `report()` out of `verify.py`** — ADR 0002 and ADR 0009 name the file
  by path. The split is worth two correction notes; the rename is not.
- **Moving most mutants to pure tests** — would make `contour selftest` much
  cheaper, at the price that a gather which stopped reporting a defect would no
  longer be caught by twelve of the thirteen.
- **`cmd_render` taking the full measurement** — one interface, no second entry
  point, and it keeps the wasted work in the one place that provably does not
  need it.
