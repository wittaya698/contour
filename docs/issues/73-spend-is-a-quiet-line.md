# 73 — Spend is a quiet line

**Type:** AFK · **Source:** ADR 0025, decision 9 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The spend line reads *12 turns*. When gates have cost turns, it adds the outcome,
*3 stops cost 4 extra turns*, linking to issue 69's list of what runs unwatched.
The token breakdown — cached, fresh, out, weighted — sits behind a click, in the
units `tools/tokens.py` already uses. Still nothing before a turn is spent, and
still no limit.

## Acceptance criteria

- [x] The default line shows turns, and stops only when they cost turns
- [x] The stops phrase links to the unwatched list
- [x] The token breakdown is one click away and matches `tools/tokens.py`'s figures

## Blocked by

- [69](69-always-for-this-model.md)
