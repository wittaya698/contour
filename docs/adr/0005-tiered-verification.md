# 0005 — Tiered verification: asserts always, renders at checkpoints

**Status:** Accepted · 2026-09-20

> **Amended 2026-10-16 — a bottom view, and persp off the sheet.** The sheet
> is now front / right / top / bottom, still 1024² with 512 px tiles, so the
> look costs what it did. Persp is drawn beside it as `out/persp.png`, the
> picture a lobby row shows, and is not marked on. This gives up what persp on
> the sheet was for — how the parts read together — for the underside, which
> none of the four views showed. The reasons below for orthographic views
> stand, and are now the whole of what the sheet shows.

## Context

Per ADR 0001 the agent cannot see its output. Two error classes exist and they
are caught by different instruments: structural faults (wrong dimensions,
non-manifold, flipped normals, loose geometry) are caught by measurement and
often invisible in a render; arrangement faults (legs attached upside down) are
caught by a render and invisible to measurement.

Images cost roughly `width × height / 750` tokens — a 1024² sheet is ~1,400.

## Decision

Three tiers:

1. **Every build** — `verify.py` reads the spec and prints ~10 terse lines.
   ~50 tokens.
2. **At checkpoints only** — when the agent believes it is done or is stuck, a
   Workbench 4-view orthographic sheet (front / right / top / persp) at 1024²
   with a 1 m grid and a scale bar. ~1,400 tokens.
3. **Before any commit** — the human looks and approves.

Workbench is used, not EEVEE or Cycles: it needs no lights or materials, its
cavity shading reads form and topology directly, and it produces no denoising
artifacts the agent could misread as geometry. Measured on this machine
(2026-09-20): first Workbench render in a process 0.45 s, each subsequent render
0.02 s, a full four-view invocation ~1.7 s wall including Blender startup. EEVEE
measured 1.42 s on the same trivial scene, so on simple geometry Workbench is
**not** meaningfully faster — the reason to prefer it is the absence of a
lighting setup and of render noise, not speed.

All four views must be rendered inside a single Blender process; separate
invocations pay ~1.2 s of startup each for no benefit.
Orthographic views are used because a single 3/4 perspective hides misalignment
along the view axis, and the metre grid is present because a render carries no
absolute scale cue.

`fixtures/smoke/` is a trivial shape whose only job is to exercise every stage
of this pipeline in ~2 s via `./contour selftest`, so a broken toolkit is caught
on `master` rather than inside variant work.

## Consequences

- Both error classes are covered, and the expensive instrument is rate-limited.
- A 30-iteration session costs ~1.5k tokens of images instead of ~40k.
- Errors that are neither measurable nor visible at 512-per-view still reach the
  human gate. That is the gate's purpose.

## Rejected

- **Asserts only** — blind to visual nonsense that measures correctly.
- **Render every build** — ~40k tokens of images per session, and image context
  accumulates in history.
- **Human review only** — zero automated cost, but silent structural faults pass
  unnoticed and the human becomes the bottleneck on every iteration.
- **Golden-file mesh hashes on the fixture** — catches Blender-version drift,
  but float precision causes false alarms and invites rubber-stamping.
