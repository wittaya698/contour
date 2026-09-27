# 19 — One spelling for a part, and a migration

**Type:** HITL · **Source:** architecture review 2026-09-28 · ADR 0018, rule 5

## What to build

A mark that is about a part stores that part's name in two different places
depending on how the mark was born: top-level `part`, or nested under `anchor`.
`console/seed.py` reads both. Slice 18 hides that behind one accessor; this slice
ends it.

**`part` is top-level, always. `anchor` holds only the pin.** That is the cleaner
reading of ADR 0018: a **pin** is a position in the hit part's own coordinates,
and a part's *name* is not a position. They stop sharing a key.

**Why this is HITL.** `marks.json` is tracked, and it holds the user's own
findings across four spaces. Rewriting it is a state the user has to choose and
see — rule 5 — not something that rides along inside a refactor commit. So:

**An explicit migration command, reported by `contour doctor`.** `doctor` says
this space holds *n* marks in the old spelling; a command migrates them when the
user asks. Nothing rewrites tracked data on load, and no diff appears that the
user did not cause.

**Spaces stay mixed until someone runs it, and that is fine** — slice 18's reader
is bilingual, so a space that is never migrated keeps working. What ends is new
marks being written either way.

**The migration is only sound because of slice 18's AST-walk test.** Converging
the storage while any caller can still write the old spelling would mean rewriting
user data for a guarantee that does not hold.

**`anchor.nearest` and the render's badge pass both change what they write,**
since both currently produce a mark naming a part.

## Acceptance criteria

- [ ] Every new mark naming a part writes `part` at the top level; nothing writes `anchor.part`
- [ ] `anchor` on a record holds a pin and nothing else
- [ ] `contour doctor` reports the count of old-spelling marks in this space, and says nothing at zero
- [ ] A migration command rewrites them, printing what it changed, and is idempotent
- [ ] Nothing migrates on load; no command rewrites `marks.json` unless asked
- [ ] A space left unmigrated still reads, renders, seeds and prunes correctly
- [ ] A migrated `marks.json` diffs readably, one record per line as before
- [ ] `tests/test_marks.py` covers a mixed file, a migrated file, and migrating twice
- [ ] The four spaces on this machine are migrated only with the user watching, in a commit of their own

## Blocked by

- [18 — The mark record gets an owner](18-the-mark-record-gets-an-owner.md)
