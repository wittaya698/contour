# 78 — Claude speaks in plain words

**Type:** HITL · **Source:** ADR 0025, decisions 2 and 3 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The template `CLAUDE.md` and the `build-model`, `release-model` and `new-space`
skills tell the agent to speak to the user by the tiers in *On the page*:
*Save this version?*, not *commit?*, and the commit message stays exact. The
new-model prompt asks in plain words — how big it is in real life, where it will
be seen — and makes tolerances and the triangle budget its own flagged
proposals. Its stale step, *save the user's reference images*, goes: since
issue 65 they are in `refs/` before the console opens.

HITL because the wording is the decision: the user reads the new voice before it
lands.

## Acceptance criteria

- [x] The template `CLAUDE.md` and the skills carry the voice, and the eight rules are unchanged in meaning
- [x] The new-model prompt asks in plain words and no longer asks to save references
- [x] A new space's first run asks for size without the word anchor
- [x] The user has read and approved the wording

## Blocked by

None - can start immediately
