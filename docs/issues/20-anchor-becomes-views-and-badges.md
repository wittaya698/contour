# 20 — `anchor.py` becomes views and badges

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0018

## What to build

`lib/anchor.py` is 206 lines doing four unrelated jobs: mark record transitions
(`apply`, `orphan`), camera-frame geometry (`aim`, `place`, the views.json
reader), badge placement (`badge_spot`, `nearest`), and a generic JSON reader that
`lib/panel.py` borrows for its own unrelated file.

Slice 16 took the JSON reader. Slice 18 took the transitions. What is left is two
modules wearing one name.

**`lib/views.py` — the sheet's camera frames.** Which of the four views a pixel
fell in, where a **pin** lands in world space, the views.json record the render
writes and `cmd_resolve` reads. Everything in it is about the **sheet**'s
geometry.

**`lib/badges.py` — where a label can go.** `badge_spot`'s spiral over background
pixels, and `nearest` finding a point on a named part for a mark that has none.
This gives ADR 0018's *the model is never covered by a remark about it* a module
of its own, which is the rule most likely to be quietly broken by a change
elsewhere.

**No new CONTEXT.md terms.** **sheet**, **pin** and **badge** already name
everything in both modules. **anchored** keeps its meaning and stops having a
module that shares its name while doing three other things.

**This disturbs the best-tested module in `lib/`** — seven test files reference
`anchor`. Their imports move; their assertions should not need to, and any that do
were testing past the interface.

## Acceptance criteria

- [x] `lib/anchor.py` is gone; `lib/views.py` and `lib/badges.py` each do one thing
- [x] `lib/views.py` owns views.json and the pixel-to-frame and pin-to-world maths
- [x] `lib/badges.py` owns placement and the nearest-point search
- [x] No module imports both for one operation that should have been in one of them
- [x] `tests/test_anchor.py` splits to follow, and no assertion changes meaning
- [x] `tests/test_lib_split.py`'s roster names `views` and `badges`, both free
- [ ] `contour render` output is byte-identical for the fixture and for a space
- [x] `contour selftest` green

## What it came to

**Two modules, and every moved function character-identical.** `views.py` takes
`aim`, `fingerprint`, `record`, `stale` and `place`; `badges.py` takes
`badge_spot`, `nearest` and the two helpers under them. The bodies were compared
against `anchor.py` at the previous commit with the docstrings stripped: nine
functions, nine identical, nothing added and nothing dropped. The prose moved and
the logic did not, which is what let the existing tests stand as the regression
net for the whole slice.

**`fingerprint` went to `views` because the sheet's header is what it is.** It is
also what `agent.addressed` stamps a mark with and what a promoted veto records,
and neither of those is about a camera frame — but both are asking *which build
is this*, which is the question the sheet's own record answers. Two spellings of
that number would be two numbers, so it has one home and the one that writes it
into a file keeps it.

**The name `views` was already taken, twice, inside its own callers.** `panel.state`
takes a `views` argument and `cmd_render.run` builds a `views` list, both meaning
the four frames — so in both the module was shadowed by its own subject. `panel`
already had the idiom for it one line above (`marks as marks_store`), and both
sites now import `views as sheet_views`. An AST sweep of `lib/` and `console/`
found every binding of either module name, which is how the second one was found
at all: `canvas.py` binds `views` twice and never imports the module, so it is
safe and would stop being safe the day somebody adds the import. This is a real
cost of the name and it is worth saying out loud — the module is named after the
file it owns, and that file is named after the thing every caller has a variable
for.

**The render shadowing was invisible to the unit suite.** `panel`'s surfaced as
five errors the moment the import changed, because the panel is served by a stub.
`cmd_render`'s could not: it needs Blender, so nothing outside `contour selftest`
runs that line. The suite was green and the render was broken, which is the
argument for criterion 8 being a criterion and not a courtesy.

**`tests/test_anchor.py` split three ways, not two.** Only `AimTest`,
`BuildWindowTest` and `BadgeTest` were ever about the module; `ResolveTest`,
`OrphanTest` and `CanvasResolveTest` never imported it and ask the record and the
canvas instead. They went to `tests/test_resolve.py`, because anchoring as a
lifecycle is a real subject that now names no module, and filing it under `views`
or `badges` would have been a worse home than the one it had. `FollowTest` was
the seam the old file was hiding: three `place` tests and one `badge_spot` test
under one heading, now in the two files they belong to. 344 tests before, 344
after, no assertion changed.

**Six mutants, all caught**, run after the move rather than before it — a moved
test that no longer reaches its code passes for the wrong reason, and nothing in a
rename says which. Breaking `aim`'s row flip, `place`'s translation column,
`fingerprint`'s answer, `badge_spot`'s clear check and `nearest`'s search each
failed the file that claims it, and filing `views` under the Blender half failed
the roster.

**The sheet is byte-identical and the fingerprint is not, and only one of those
is this slice's.** `sheet.png` and `mask.png` came out to the same bytes across
three renders — the previous commit in a worktree, and this tree twice — badges
and leader lines included, which is `place`, `nearest` and `badge_spot` all
exercised at once. `views.json` matches too but for its `build` field. That field
moved because `.blend` bytes are not reproducible: two builds of identical source
in the same tree differ in 8,323 bytes across 7,432 runs, same length, no paths
embedded, which is Blender writing pointers. So `fingerprint` identifies a build
*run*, not a geometry, and `stale` will refuse a sheet after any rebuild even one
that changed nothing. That is conservative in the safe direction and it is not
new here — the function is character-identical to the one that shipped — but the
docstring's claim that the bytes are "a fair stand-in for its geometry" is
stronger than what they do. A finding, raised, not fixed on the way past.

**Criterion 7's other half was not run.** Rendering a space calls
`marks.orphan`, which writes that space's `marks.json`, and the only space on
this machine with marks is beaky-solo — the same seven old-spelling records
slice 19 left for the user to migrate when they choose. Rewriting them to check a
refactor is the thing slice 19 was careful not to do. The fixture proves the
claim three times over; the space half is one command with the user watching.

## Blocked by

- [18 — The mark record gets an owner](18-the-mark-record-gets-an-owner.md)
