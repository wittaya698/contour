# 68 — A gate says the act and what changes

**Type:** AFK · **Source:** ADR 0025, decision 6 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

A gate reads as what Claude wants to do, in plain words from one table keyed by
category: *Claude wants to change the spec*, *…change your reference pictures*,
*…build the model to check its work*, *Save this version?*. Under it, what would
change: for a spec write, each field that moves, in millimetres where it is one,
*seat depth 600 → 640 mm*, and the span the proposal names. The raw call stays
one click away.

The answers are Allow and Deny with a *why not* sentence, as now — the call is
still not editable (ADR 0019, decision 13). *Save this version?* answers Save and
Not yet. A category the table does not know shows its own name.

## Acceptance criteria

- [x] Every category `contour intents` prints has a plain sentence, and a test fails when a new one has none
- [x] A spec-write gate lists each field that changes, old → new, and the span it names
- [x] The raw call is reachable from the gate and not shown by default
- [x] The call still cannot be edited from the gate
- [x] A commit gate reads *Save this version?*

## Blocked by

None - can start immediately
