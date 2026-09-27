---
name: build-model
description: The iterate loop for building or changing a Contour model — build, verify, fix, checkpoint, commit. Use when working on any model in this repo, changing geometry, or responding to a failing check.
---

# Build a Contour model

## Before you start

1. Read `spec.yaml`, and look at `refs/`. It is the definition of done. `refs/`
   is never yours to edit; `spec.yaml` only by the route below, never casually.
2. Read `build.py` if it exists.

Do **not** read the toolkit's `docs/` or the ADRs unless a decision is genuinely
in question — `CLAUDE.md` already carries the rules.

## The loop

```
contour check
```

That is build + verify in one command, reporting in ~10 lines. Repeat it after
every change. Do not render, do not export, do not commit inside this loop.

**On failure:** the report names the failing check and the actual value. Fix
`build.py`. Only read `.contour/last-build.log` if the report is not enough — for a
traceback or a Blender-level error.

**Never** relax a tolerance, widen a budget, or edit the spec to make a check
pass. While a check is red the spec is not on the table at all: fix `build.py`,
or report the failure and stop.

**When the spec itself is wrong**, and the check is *green*, say so — and bring
the measurement that shows it. `beaky` sat at `depth 612.4` inside a tolerance
of 600 ±20, for a reference that measures about 620: the build was right and
the contract was not. That is the case this route exists for. Propose the
change, wait for the user to confirm it, then write it with `revision:` bumped
in the same edit. `contour check` goes red if the spec moved and the number did
not (ADR 0016).

## Writing geometry

- `bmesh` and the data API. `bpy.ops` only from the toolkit's
  `lib/ops_whitelist.py`, and only via `lib.ctx_override` (ADR 0004).
- **Check unfamiliar calls before writing them:** `contour api bmesh.ops.inset_region`.
  This Blender postdates your knowledge cutoff; a recalled signature is a guess
  and a guess-fail-retry costs ~100x what the lookup costs.
- Consult `references/bpy-recipes.md` for patterns already proven here. Anything
  marked UNVERIFIED must be confirmed with `contour api` before use.
- Build from an empty scene every time. Never rely on existing scene state.
- Name every object exactly as `parts:` in the spec names it. Naming is checked.

## Checkpoint

When verify is green, or when you are stuck and need to see what you built:

```
contour render
```

Look at the 4-view sheet. Check specifically for what measurement cannot catch:
parts in the wrong place or orientation, gaps, intersections, proportions that
read wrong against the 1 m grid.

Then show the user the verify report and the sheet, and say what changed.

Under a console the sheet is already on the page beside the transcript, redrawn
by every build and labelled with the build it came from (ADR 0019). Rendering
again there buys nothing and costs ~1400 tokens of your own context: say what
changed and what the report says, and let them look. The checkpoint is your
judgement that you are done or stuck, which is the same claim in either place.

## Commit

Only after the user explicitly approves. Then:

```sh
git add -A
git commit
```

Message:

```
<NAME>: <what changed>

verify 8/8 | tris 4,210 | height 900mm
```

Never commit `out/`, `exports/` or `work/` — they are
ignored by design (ADR 0007, ADR 0012).

## When a fix belongs to the toolkit

If the bug is in `verify.py`, `lib/`, `schema/` or `contour` — **stop**. None
of that is in this repository, and it is not yours to patch from here
(ADR 0015). Tell the user. The fix belongs in the toolkit checkout, where
`contour selftest` must pass before it is committed; `contour doctor` prints
the path.

Never work around a toolkit bug by changing the model. A wrong check that
passes is worse than one that fails.
