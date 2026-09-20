# 0006 — `.glb` only for now, proven by round-trip

**Status:** Accepted · 2026-09-20

## Context

The target engine is undecided, and the three candidates disagree on
fundamentals:

| | up axis | handed | 1 unit | usual format |
|---|---|---|---|---|
| Unity | Y | left | 1 m | FBX |
| Unreal | Z | left | 1 cm | FBX / glTF |
| Web (three.js) | Y | right | 1 m | glTF 2.0 |

Blender is Z-up, right-handed, 1 unit = 1 m, so each target needs a different
export transform. Exporters are where correct scenes become broken files —
unapplied transforms, wrong scale, flipped axis — and inspecting the Blender
scene proves nothing about what landed in the exported file.

## Decision

The `.blend` stays neutral in Blender's own convention. Export targets are a
table in the spec. Only `web` (`.glb`, glTF 2.0) is implemented now.

Every export is **round-tripped**: re-imported into a clean headless Blender and
re-measured there, asserting dimensions, up axis, handedness and origin. A
broken export fails the build, not the engine import.

## Consequences

- One export path is proven rather than three assumed.
- Adding `unity` or `ue` later is a table entry plus its transform, not a rewrite.
- glTF's strictness about units and axis makes the round-trip assertions sharp.
- Export adds a few seconds per run, so it is not part of the fast `check` loop.

## Rejected

- **All three targets now** — maintaining FBX quirks for engines that may never
  be used, and FBX round-trip fidelity is meaningfully worse than glTF's.
- **Trust the exporter** — export bugs then surface in the engine, far from the
  agent, and get debugged by hand.
- **No export step yet** — engine conventions (origin, scale, axis) stop being
  enforced during modeling, and retrofitting them to finished geometry is painful.
