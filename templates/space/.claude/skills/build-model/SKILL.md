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

**When the spec itself is wrong**, and the check is *green*, say so — *I'd like
to change the spec* — and bring the measurement that shows it. Illustratively: *depth reads 640 mm ±3 on span
m4, against a tolerance of 600 ±20*. That is the case this route exists for.

The measurement is a span, drawn with `contour measure` and named in the
proposal (rule 1). Every number in the proposal names its source, one of three:
- a span, by id;
- the user, who gave it;
- *not measurable*, said plainly.

A number from an unanswered **snapped** span is proposed as the agent's own
reading, beside its id. A number from an unanswered **by-eye** span is not
proposed until the user has answered it on the canvas.
`contour measure --standing <id>` says which a span is.

Run `contour worksheet` and look at it once, before you propose: every span on
its reference, with its id and number, so you can see each measures what it
says. Then propose the change, wait for the user to confirm it, and write it
with `revision:` bumped in the same edit. `contour check` goes red if the spec
moved and the number did not (ADR 0016).

## Topics

A topic is a word to find this model by — *creature*, *low-poly*. When
`contour check` says *first green: propose topics to find this model by*,
propose some, once: it is the model's first green build, the first moment you
know what it is. A first green from a check you were not there for is said to
the next run instead, in its first message; propose then. After that, propose
only when asked.

Under a console, propose with `topics_propose`: the words and why. It lists the
words other models already carry; reuse one wherever it fits. The user keeps or
strikes each word. In a terminal, say the words and why, and the user adds the
ones they keep with `contour topics add <word>`. A topic decides nothing about
the build and argues for no spec change.

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

Then show the user the verify report and the sheet, and say what changed — in
the words of *Speaking to the user* in `CLAUDE.md`: *matches the spec*, or *2
things don't match the spec* and what they are, never *green* or *red*.

When the spec has `clips:` and they are green, the sheet shows the rest pose
and nothing of the motion. At that checkpoint, and not before:

```
contour filmstrip [clip]
```

Six frames from the side and six from the front, evenly through the clip, on
the sheet's grid at one scale, labelled with the clip and the build. Look for
what the clip's numbers cannot catch: whether it reads as what `feel:` says —
a walk that shuffles, a limb swinging the wrong way, a part that should move
and does not. Show it to the user with the sheet. Never render one inside the
fix loop: the clip's angles, seams and crossings are checked by every build,
and a red check is fixed from its report, not from a picture. The next build
deletes the filmstrip, so one on disk is always of the build beside it.

Under a console the sheet is already on the page beside the transcript, redrawn
by every build and labelled with the build it came from (ADR 0019). Rendering
again there buys nothing and costs ~1400 tokens of your own context: say what
changed and what the report says, and let them look. The checkpoint is your
judgement that you are done or stuck, which is the same claim in either place.

## Commit

Only after the user explicitly approves. Ask *Save this version?* — never
*commit?* — and when they say yes:

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
