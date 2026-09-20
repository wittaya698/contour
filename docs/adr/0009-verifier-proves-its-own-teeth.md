# 0009 — The verifier proves it can fail, and refuses what it cannot check

**Status:** Accepted · 2026-09-20

## Context

ADR 0002 makes the spec the definition of correct and `verify.py` its enforcer. Two
silent failures remain inside the toolkit itself. A check can be broken so that it
always passes, and a spec field can be one the verifier does not implement, so it is
ignored. Both report green. Per ADR 0003 the toolkit is never run on `master`, so
either would first surface inside variant work, disguised as a modelling success.

## Decision

1. **`./contour selftest` includes mutants.** `lib/mutants.py` rebuilds the fixture
   and breaks it one known way at a time (raised part, missing part, extra object,
   flipped normals, loose vertex, open mesh, doubled vertex, unapplied scale and
   rotation, n-gon, extra material, shifted origin, blown budget). Each must make
   the named check fail. The round-trip does the same to real `.glb` files: mirrored,
   Z-up, millimetre units, shifted origin, renamed part, and a Z-up re-import.
   A mutant that passes fails the selftest.
2. **Unsupported spec fields fail, never skip.** Unknown keys, named
   `dimensions` sub-measurements, `origin: world_origin`, UV overlap checking, a
   `udim` request and non-`web` targets each produce a FAIL naming the field. A green
   run therefore means every constraint in the spec was enforced.
3. **The verifier has fixed tolerances it does not read from the spec:** origin
   1 mm, unit scale/rotation 1e-4. They are constants in `verify.py`, changed only
   on `master`.

## Consequences

- A weakened or broken check shows up as a red selftest on `master`, before any
  variant is judged by it.
- A spec can be rejected for using a field the toolkit has not grown yet. That is
  the intended trade: the gap is visible, not hidden.
- Adding a check means adding its mutant. The selftest grows with the verifier.
- Mutants exercise the checks, not the geometry. They do not prove the fixture
  resembles a real model.

## Rejected

- **Selftest on the happy path only** — proves the pipeline runs, not that it judges.
- **Warn on unsupported fields** — warnings are not read; a constraint becomes advice.
- **Golden-file hashes** — already rejected in ADR 0005 for float brittleness.
