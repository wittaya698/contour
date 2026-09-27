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

- [ ] `lib/anchor.py` is gone; `lib/views.py` and `lib/badges.py` each do one thing
- [ ] `lib/views.py` owns views.json and the pixel-to-frame and pin-to-world maths
- [ ] `lib/badges.py` owns placement and the nearest-point search
- [ ] No module imports both for one operation that should have been in one of them
- [ ] `tests/test_anchor.py` splits to follow, and no assertion changes meaning
- [ ] `tests/test_lib_split.py`'s roster names `views` and `badges`, both free
- [ ] `contour render` output is byte-identical for the fixture and for a space
- [ ] `contour selftest` green

## Blocked by

- [18 — The mark record gets an owner](18-the-mark-record-gets-an-owner.md)
