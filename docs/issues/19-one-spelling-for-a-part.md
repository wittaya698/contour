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

- [x] Every new mark naming a part writes `part` at the top level; nothing writes `anchor.part`
- [x] `anchor` on a record holds a pin and nothing else
- [x] `contour doctor` reports the count of old-spelling marks in this space, and says nothing at zero
- [x] A migration command rewrites them, printing what it changed, and is idempotent
- [x] Nothing migrates on load; no command rewrites `marks.json` unless asked
- [x] A space left unmigrated still reads, renders, seeds and prunes correctly
- [x] A migrated `marks.json` diffs readably, one record per line as before
- [x] `tests/test_marks.py` covers a mixed file, a migrated file, and migrating twice
- [x] The four spaces on this machine are migrated only with the user watching, in a commit of their own

## What it came to

**Two writers, both in `lib/marks.py`, and the shape is settled at birth.**
`on_part` writes `{"part": ...}` and no anchor at all — an agent's mark never had
a pin, and now says so by carrying no anchor rather than by carrying one with no
`local` in it. `marks.anchor` splits what a ray found into its two answers: the
part it hit, written where every part name lives, and the point on it, which is
the anchor and the whole of it. Nothing else could have written either: slice
18's AST guard is what makes that a fact rather than a convention, which is the
dependency this slice was waiting on.

**The anchor keeps its `{"local": ...}` shape and does not become a bare list.**
`local` says the coordinates are in the part's own space, which is the one thing
about a pin worth naming — and leaving it means `pin()` is untouched and the
bilingual surface stays exactly one accessor, `part()`. That accessor is what
criterion 6 rests on, so widening it to two would have been widening the thing a
space that is never migrated depends on.

**The real file had records carrying both spellings at once, and that changed
the migration.** Four of beaky-solo's seven name the same part twice, top level
and under the anchor. They agree there — but nothing made them agree, and
`part()` has always answered with the top-level one, so a rewrite that took the
anchor's copy would change which part a finding is about in a file git tracks, in
a commit whose subject says the spelling was converged. The migration keeps the
answer every reader has been giving. Preferring the ray may well be the better
call; it is a finding to raise, not a thing to do on the way past.

**The record is rebuilt rather than edited, so the name takes the anchor's
place.** The first version appended it, which put the line that went and the line
that arrived in different hunks of the diff the user has to review. Criterion 7
asks for one record per line, which `lib/store.py` has never written — it
indents, so a mark is nine lines and always was. What the criterion is actually
about is whether the diff can be read, so that is what was built and what was
checked: a copy of beaky-solo's file, migrated in a scratch directory, is eight
hunks in which every record shows the name leaving the anchor and arriving above
it, and every `part` and every `pin` reads back the same as before.

**`doctor` counts and `migrate-marks` rewrites, and neither is the other.**
`doctor` says *n marks in the old spelling* and what to type, as a NOTE and not a
fault: an unmigrated space is working, not broken. `migrate-marks` names the ids
it moved and says to read the diff. Nothing runs on load — a check builds,
renders and reads the marks of an old-spelling space and leaves it byte-identical,
which is a test.

**Two of the changes this slice expected had already happened.** `anchor.nearest`
and the render's badge pass are named here as writers that would have to change;
neither writes a record any more. `nearest` answers where a badge goes and always
did, and slice 18 moved the writing out of the render entirely. What the issue
saw as four places to converge turned out to be two functions in one file, which
is what slice 18 was for.

**One space on this machine has marks at all.** beaky-solo, seven of ten in the
old spelling; beaky, beaky-fable and beaky-lite hold none. That migration is
criterion 9, and it was run on 2026-10-16 with the user watching: seven marks
moved, every part and pin read back the same, and a second run found nothing.
`marks.json` had never been committed in that space, so the migrated file is its
first commit there, by itself (beaky-solo 8c38e08).

## Blocked by

- [18 — The mark record gets an owner](18-the-mark-record-gets-an-owner.md)
