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

- [x] `lib/space.py` exposes `find`, the two layouts, `parse`, `display`, `MARKER`, and the space walk
- [x] No module-level env read; every layout call takes the space it is about
- [x] The layout returns a NamedTuple; no caller subscripts it by string
- [x] `contour`, `contour-console`, `console/server.py` and `console/vetoes.py` all read the layout instead of joining paths
- [x] The selftest's hard-coded fixture table is gone, replaced by the fixture layout
- [x] `PROJECT or ROOT` appears nowhere
- [x] `tests/test_lib_split.py`'s roster names `space` and not `paths`
- [x] `tests/test_space.py` covers both layouts, the walk-up, and a space that is not one
- [x] CONTEXT.md's **model space** entry names the module
- [x] `contour selftest` green; `contour spaces`, `doctor` and `canvas` behave identically

`display` is a method on the layout, `P.display(P.blend)`, rather than a module
function taking one. The layout already holds both roots it decides between, so
nothing is passed twice — and the ordering it decides by is worth stating: the
toolkit is asked first, and owns only the fixture, because a model space is never
inside the toolkit and the push guard refuses one that is. That is what keeps the
selftest's lines reading `fixtures/smoke/out/sheet.png`, where *which fixture* is
the part worth printing.

`parse` reads the environment, and is the only thing here that does. It reads it
when called, not at import, which is the whole difference: the module is now
askable from the launcher and the console, and `$CONTOUR_PROJECT` is simply how
the launcher tells a Blender process which space it was started for. `layout` and
`fixture` take their root and consult nothing.

**The layouts gained a third difference the criteria did not name.** `mutants`
runs against the fixture and must run nowhere else, and `cmd_build` reached that
decision through the boolean `paths.parse` used to return. It is now `P.fixture`,
derived from where the layout sits rather than remembered from a flag — so there
is no way to hand `mutants` a space's layout that claims to be the fixture. A
user's space that happens to live in a directory called `fixtures` is still a
space; it is the toolkit's own that counts.

**What `PROJECT or ROOT` was hiding, now that it is gone.** `cmd_measure` was its
one caller, and outside a space it would have measured a reference relative to the
toolkit — which is the toolkit's own directory passing for a model space, the one
thing `need_project` exists to prevent. It now refuses, by asking `space.parse`
the same question every other Blender-side command asks.

**`console/vetoes.py` keeps its own root join.** `vetoes.json` sits at the space's
root, and `Path(space) / NAME` is not a restatement of ADR 0015 — the space's root
is the space. What the two apologising comments were restating was *where the
build is* and *where the parts table is*, and those are the layout's answers now.

**The space layout was verified through Blender, not only the fixture.** The
selftest exercises the fixture layout on every run and the space layout on none,
which is the shape of gap slice 16 found at `contour:650`. So a throwaway space
was built from the fixture's own `build.py` outside the repo: `check`, `export`,
`mark`, `resolve` and `run` all land where a space puts things — `sheet.png` at
the root, `out/probe.blend`, `exports/probe.glb`, `marks.json` at the root — and
the export line reads `exports/probe.glb`, relative to the space. Worth keeping in
mind for slice 25: nothing in the unit suite or the selftest would have caught a
space-layout mistake.

## Blocked by

None. Slices 18, 20, 24 and 26 all read better after it, but none is strictly
blocked by it.
