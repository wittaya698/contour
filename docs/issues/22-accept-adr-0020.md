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

- [ ] `check_topology` exists as a pure function over a measurement, with a gather that feeds it
- [ ] Every ADR 0009 mutant that targets a topology check still fails that check
- [ ] A hand-written measurement in a test exercises the same check with no Blender
- [ ] The per-part record's fields are named, and any field no check reads is listed
- [ ] ADR 0020 is Accepted, amended, or withdrawn, with the result recorded in it
- [ ] If accepted, `docs/adr/README.md` lists it

## Blocked by

None.
