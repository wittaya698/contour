# 17 — The space layout is a function of a space

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0015

## What to build

`lib/paths.py:resolve()` already *is* the table of where a space keeps its files.
It is unusable by the two hosts that need it most, because the module reads
`CONTOUR_ROOT` and `CONTOUR_PROJECT` into globals at import time — so it answers
only for the process Blender is running in. The launcher and the console
therefore re-derive the same conventions by hand.

`out/<name>.blend` is spelled in five places. `out/parts.json` in five. The path
to `marks.json` in nine. `console/vetoes.py` carries a comment at each of its two
copies apologising for restating ADR 0015. The selftest hard-codes the fixture's
own copy of the whole table a sixth time.

`find()` is the clean counter-example: one walk-up, two callers, no drift. The
friction is entirely that *layout* was made process-global while *discovery* was
made a function.

**`lib/paths.py` becomes `lib/space.py`,** holding what a space is, what it
contains, and where spaces are found — so `space_roots` and `find_spaces` come out
of the launcher, where "where spaces are" currently lives apart from "what a space
is" and is unreachable from `contour-console`.

**Two named layouts, no flag.** A space puts `marks.json` at its root; the fixture
puts it under `out/`. That is two layouts, and `resolve(variant, fixture)` hides
the second behind a boolean. They become separate entry points, which also
retires the `PROJECT or ROOT` fallback: `paths.parse` already returns the fixture
flag, so the Blender side picks a layout from argv and the launcher and console
only ever call the space one. Nothing is left guessing that the toolkit directory
might be a model space — the thing `need_project` exists to prevent.

**It returns a NamedTuple.** Five hosts reading `P["blend"]` is the same failure
mode as slice 19's two spellings of a part, one level up: a typo is a `KeyError`
or a silent `None` rather than an `AttributeError` at the call site.

**Layout owns directories; stores keep their filenames.** The layout answers
where a space is and where its `.contour` is; `lib/lock`, `lib/panel`,
`console/spend` and `console/vetoes` each join their own `NAME`. A store that lost
its own filename would have gained nothing and lost ownership.

**CONTEXT.md's **model space** entry gains a line** saying one module answers
where a space is, what it contains, and where spaces are found — written when the
module lands, not before. A vocabulary entry describing a module that does not
exist yet is the drift ADR 0016 is about.

## Acceptance criteria

- [ ] `lib/space.py` exposes `find`, the two layouts, `parse`, `display`, `MARKER`, and the space walk
- [ ] No module-level env read; every layout call takes the space it is about
- [ ] The layout returns a NamedTuple; no caller subscripts it by string
- [ ] `contour`, `contour-console`, `console/server.py` and `console/vetoes.py` all read the layout instead of joining paths
- [ ] The selftest's hard-coded fixture table is gone, replaced by the fixture layout
- [ ] `PROJECT or ROOT` appears nowhere
- [ ] `tests/test_lib_split.py`'s roster names `space` and not `paths`
- [ ] `tests/test_space.py` covers both layouts, the walk-up, and a space that is not one
- [ ] CONTEXT.md's **model space** entry names the module
- [ ] `contour selftest` green; `contour spaces`, `doctor` and `canvas` behave identically

## Blocked by

None. Slices 18, 20, 24 and 26 all read better after it, but none is strictly
blocked by it.
