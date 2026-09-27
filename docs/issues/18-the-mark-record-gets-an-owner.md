# 18 — The mark record gets an owner

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0018

## What to build

`lib/marks.py` is the only module that touches `marks.json`, and that part is
right. But it never mentions `anchor`, `pixel`, `ref`, `to`, `orphaned` or
`addressed` — the fields carrying every invariant ADR 0018 states. The store owns
the bytes and nothing owns the record.

The consequences are already visible. Three writers bypass `append` and call
`marks.save` directly after editing records in place — `anchor.apply`,
`anchor.orphan`, `agent.addressed`. Eleven sites read the fields. `console/seed.py`
has to know **both** spellings of where a part name lives, because nothing decided
which one a mark has. So the lifecycle CONTEXT.md describes in one paragraph —
pixel to **pin** to **badge**, **orphaned** when the part goes, **addressed** but
never closed — is enforced across fourteen files, and its transition rules are
comments in whichever module happens to perform them.

**The record joins the store in `lib/marks.py`.** One file for everything about a
mark, and no `mark`/`marks` pair to misread in an import line.

**Plain dict, named accessors and transitions.** `marks.py` gains functions for
the three ways a mark is born — a **sheet mark** from a pixel, a **ref mark**, an
agent mark that names a part and no point on it — and for each transition ADR 0018
defines: anchor this to a pin, orphan it, stamp it addressed against a build. No
class, no serialisation layer, nothing new at the JSON edge.

**Enforced by a test that AST-walks for direct field writes.** Exactly the idiom
`tests/test_console.py` already uses three times: walk `lib/` and `console/` for
subscript writes of the record's field names outside `marks.py` and fail, with the
roster of permitted writers readable in the test. That is what makes convention
load-bearing without a class — and it is what slice 19's migration depends on,
because a spelling converged by convention alone is a spelling the eleventh reader
un-converges.

**This slice reads both spellings of a part and writes neither exclusively.**
Choosing one is slice 19, because it rewrites tracked user data and that is the
user's call, not a refactor's.

**The transitions move here from `anchor.py`.** `apply` and `orphan` are record
transitions wearing a geometry module's name; the geometry they leave behind is
slice 20's subject.

## Acceptance criteria

- [ ] `lib/marks.py` exposes constructors for the three births and a named transition for each ADR 0018 state change
- [ ] `anchor.apply` and `anchor.orphan` no longer edit records or call `save`
- [ ] `console/seed.py` asks one function which part a mark is about
- [ ] No module outside `lib/marks.py` writes a record field; a test AST-walks for it and names the file and field when it fails
- [ ] All eleven read sites go through an accessor
- [ ] `tests/test_marks.py` covers every transition with no Blender and no canvas
- [ ] `marks.json` written before this slice reads identically after it
- [ ] `contour selftest`, `test_anchor.py`, `test_agent_marks.py`, `test_span.py`, `test_prune.py` and `test_console.py` green

## Blocked by

- [16 — A JSON store, shared](16-a-json-store-shared.md)
