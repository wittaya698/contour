# 72 — The transcript shows activity, not calls

**Type:** AFK · **Source:** ADR 0025, decision 8 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

Each tool call in the transcript becomes one plain activity line from a table
keyed by tool and, for `contour`, by command: *Changed the build script*,
*Measured the side picture*, *Built the model — 2 things don't match*. The raw
call is one click away. Consecutive calls that only read fold into one line,
*Looked at 3 files*. Claude's own words, the prompt, and gates are unchanged.

A tool or command the table does not know is shown raw, never hidden.

## Acceptance criteria

- [ ] Every `contour` command has an activity line, and a test fails when a new one has none
- [ ] Each line expands to the raw call
- [ ] Consecutive read-only calls fold into one line
- [ ] A reloaded tab shows the same lines as before the reload
- [ ] An unknown tool shows its raw call

## Blocked by

None - can start immediately
