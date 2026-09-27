# 16 — A JSON store, shared

**Type:** AFK · **Source:** architecture review 2026-09-28

## What to build

Four modules independently implement *read this JSON file or a default*, *write it
back*, and *what is the next id*. `lib/marks.py` and `console/vetoes.py` are
near-copies of each other down to the compiled id regex; `lib/anchor.py:load` is a
generic reader that `lib/panel.py` borrows, which is the only reason `panel`
depends on the anchoring module at all.

**Three functions, no class:** `load(path, default)`, `save(path, data)`,
`next_id(records, prefix)`. That matches how `marks` and `vetoes` already work and
keeps the repo's function-and-dict idiom, so nothing acquires a serialisation
layer it did not have.

**Each caller keeps its own `NAME` and its own prefix.** The store owns the
mechanics of a JSON file, not the knowledge of which files exist — `m1` and `v1`
stay facts about marks and vetoes. A store that listed every file in the system
would be the thing every other slice in this batch is trying to undo.

**It lives at `lib/store.py`, in the Blender-free half,** so `console/vetoes.py`
imports it exactly as it imports `lib/marks`. Slice 03's roster gains it and
proves it stays stdlib-only.

**It serves marks, vetoes, panel and views.** `panel` stops borrowing
`anchor.load`, which removes the dependency and is a prerequisite for slice 20
splitting `anchor.py` at all.

**This slice is first on purpose.** Slice 18 routes the mark record's reader here
and slice 21 consolidates the store duplication, so left in either of those two
it would be a cycle. Pulled out ahead of both, it is a few dozen lines with four
callers waiting.

No CONTEXT.md entry: it names no domain concept, and a term nobody types is
furniture.

## Acceptance criteria

- [ ] `lib/store.py` exposes `load`, `save`, `next_id` and nothing else
- [ ] `lib/marks.py`, `console/vetoes.py`, `lib/panel.py` and the views reader all use it
- [ ] `lib/anchor.py:load` is gone, and `lib/panel.py` no longer imports `anchor`
- [ ] `marks.json` and `vetoes.json` are byte-identical before and after for the same data
- [ ] Id allocation still refuses to reuse an id, for both prefixes
- [ ] `tests/test_lib_split.py`'s `FREE` roster names `store`
- [ ] `tests/test_store.py` covers a missing file, an unreadable one, and id allocation over a gap
- [ ] `contour selftest` green; `tests/test_marks.py`, `test_prune.py` and `test_console.py` unchanged in behaviour

## Blocked by

None.
