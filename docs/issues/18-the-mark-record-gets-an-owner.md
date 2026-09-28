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

- [x] `lib/marks.py` exposes constructors for the three births and a named transition for each ADR 0018 state change
- [x] `anchor.apply` and `anchor.orphan` no longer edit records or call `save`
- [x] `console/seed.py` asks one function which part a mark is about
- [x] No module outside `lib/marks.py` writes a record field; a test AST-walks for it and names the file and field when it fails
- [x] All eleven read sites go through an accessor
- [x] `tests/test_marks.py` covers every transition with no Blender and no canvas
- [x] `marks.json` written before this slice reads identically after it
- [x] `contour selftest`, `test_anchor.py`, `test_agent_marks.py`, `test_span.py`, `test_prune.py` and `test_console.py` green

## What it came to

**Three births and four transitions, all plain dicts.** `on_sheet`, `on_reference`
and `on_part` for the three ways a mark is born; `anchor`, `orphan`, `address` and
the existing `close` for every state change ADR 0018 defines. Eleven accessors
between them — `part`, `pin`, `pixel`, `reference`, `span_end`, `view`, `text`,
`is_open`, `orphaned`, `addressed`, `unresolved`. No class, no serialisation
layer, nothing new at the JSON edge.

**`address` takes a fingerprint and not a `.blend`.** Which build this is belongs
to `lib/anchor.py`, and `anchor` imports `marks`, so computing it here would close
the cycle. `agent.addressed` keeps the one line that hashes the build and hands
the string over; the transition is the record's.

**`anchor.py` stops importing `marks` entirely.** `apply`, `orphan` and
`unresolved` were record transitions wearing a geometry module's name, and with
them gone the module is geometry and a build fingerprint and nothing else — which
is the state slice 20 wants to find it in.

**A birth had to be found in two places the issue did not name.** `console/vetoes.py`
and the selftest's `anchor_check` both handed `append` a hand-built record, so the
roster of births is six call sites rather than four. The promoted veto's mark
carries a `from` field, which is a mark field; the veto's own `promoted` is not,
and had to stay out of the roster the guard walks.

**One predicate was restated, and it is the only behaviour change worth naming.**
`cmd_render.aimless` meant *has an anchor dict, with a part and no local*. With a
bilingual `part()` it becomes *knows a part, has no pin, and has no pixel awaiting
a ray* — the same set, because no birth makes a record with both a pixel and a
pin, but only the same set as long as that holds. `marks.orphan` needed the same
restatement and got the same guard. The selftest exercises the two reachable
sides (a resolved user mark, an agent mark) and `tests/test_marks.py` holds the
third by hand.

**Two clauses would not die under mutation, and they were treated differently.**
`orphan`'s *skip a mark on a photograph* was unreachable — a ref mark names no
part and keeps its pixel forever, so both other guards already exclude it — and
was deleted, with the ADR's requirement recorded in the docstring as something the
record delivers rather than a clause no test can falsify. `orphan`'s *skip a mark
that names no part* was also unreachable from any birth, but deleting it would let
a malformed record be reported as a part the build deleted, so it was kept and a
test with a hand-built record makes it falsifiable. Thirteen further mutants were
caught first time.

**Byte-identity was checked and not asserted.** A worktree at the previous commit
ran the old API through all six births and all four transitions; this slice ran
the new one through the same sequence; the two `marks.json` files are identical.

## Blocked by

- [16 — A JSON store, shared](16-a-json-store-shared.md)
