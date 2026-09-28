# 12 — Marks seed a run

**Type:** AFK · **Source:** ADR 0019 decision 21

## What to build

Selecting open marks composes them into the run's prompt. Marks are the one place
the user's intent is already located, authored and tracked, so a run seeded from
them starts from something better than a re-typed paragraph.

**It makes `addressed` checkable.** The agent may attach *addressed in build N*,
which dims the badge, and only the user closes a mark — so an agent claim has
always been unverified by construction. The console knows which marks were in
scope for the run, so one left unaddressed at the end is visible rather than
silently dropped.

This does not close anything and does not weaken the rule that only the user
closes. It reports.

## Acceptance criteria

- [x] Open marks are selectable on the page, and the selection composes into the prompt
- [x] A run can also start from prose with no marks selected
- [x] At run end the page names every seeded mark left unaddressed
- [x] A mark addressed during the run shows as addressed, not closed
- [x] The console closes no mark, by any path
- [x] A seeded mark whose part the run deletes is reported as orphaned, not as addressed
- [x] Ref marks can seed a run as well as sheet marks

## Blocked by

- [08 — A gated run, end to end](08-a-gated-run-end-to-end.md)
- [09 — The sheet panel, labelled](09-the-sheet-panel-labelled.md)
