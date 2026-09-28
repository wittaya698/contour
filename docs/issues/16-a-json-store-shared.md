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

- [x] `lib/store.py` exposes `load`, `save`, `next_id` and nothing else
- [x] `lib/marks.py`, `console/vetoes.py`, `lib/panel.py` and the views reader all use it
- [x] `lib/anchor.py:load` is gone
- [ ] `lib/panel.py` no longer imports `anchor` — not this slice's to finish; see below
- [x] `marks.json` and `vetoes.json` are byte-identical before and after for the same data
- [x] Id allocation still refuses to reuse an id, for both prefixes
- [x] `tests/test_lib_split.py`'s `FREE` roster names `store`
- [x] `tests/test_store.py` covers a missing file, an unreadable one, and id allocation over a gap
- [x] `contour selftest` green; `tests/test_marks.py`, `test_prune.py` and `test_console.py` unchanged in behaviour

Criterion 4 was written as one thing and is two. `anchor.load` is gone, but
`lib/panel.py` also calls `anchor.stale` and `anchor.unresolved`, so the import
survives it — the reader was never the whole of that dependency. Moving the other
two here would be slice 20 done early and under a different name, so the reader
moved and the import stayed. **Slice 20 inherits the second half.**

`anchor.load` had a fifth caller nobody had counted: `contour:650`, in
`anchor_check`, which `contour selftest` runs and the unit suite does not. It
surfaced as a crash after 296 unit tests were green, which is the one place in
this repo where that can still happen. Routed to the store with the rest.

`lib/agent.py:known` is a sixth reader of the same shape — read `parts.json` or
None — and it is left alone. It reads `.values()` off the result rather than the
result, so routing it is a change to what `known` returns on an absent file, not
a change of mechanics, and this slice was scoped to the four the review named.

`load` raises on a file that is not JSON, which is what all four callers did
already, and `tests/test_store.py` now says so on purpose. The fail-soft reading
is the one that loses data: the default would be believed by the next `append`,
which writes the whole file back, so every mark in a truncated file would be
deleted by the tool that was keeping them.

`panel.record` now writes `.contour/last-build.json` through the store, so that
file gains indentation. It is untracked and only ever read by `json.loads`.

## Blocked by

None.
