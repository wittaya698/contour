# 66 — The verdict, in plain words, on the console's page

**Type:** AFK · **Source:** ADR 0025, decision 4 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The console's panel says whether the model is right, under the sheet and beside
the label that already says which build the sheet is of. Green is one quiet
line, *matches the spec*. Red is *2 things don't match the spec*, then one plain
sentence per failing check — what, what it measured, what the spec wants:
*Height is 1640 mm; the spec wants 1700, give or take 5*. Passing checks stay
collapsed behind the line. A build that never got as far as being judged gets a
sentence of its own.

The sentences come from one wording table keyed by check id, read from the last
build's verdict, which `check` already keeps whole (issue 58). The table has one
owner, because the lobby row, the export card, the page header and the connector
will all say these same sentences. A check id the table does not know is shown
as its report line, never dropped — a check added to the toolkit later arrives
visible.

Nothing is drawn on the sheet. A check knows a number, not a place (ADR 0019,
decision 13).

## Acceptance criteria

- [ ] Green shows one line, *matches the spec*, with the passing checks behind it
- [ ] Red names each failing check as one plain sentence: what, measured, wanted
- [ ] A build that died before verify says so in its own words
- [ ] Every check id `verify` can report has a sentence, and a test fails when a new id has none
- [ ] An id the table does not know is shown as its report line, never hidden
- [ ] Nothing about the verdict is drawn on the sheet

## Blocked by

None - can start immediately
