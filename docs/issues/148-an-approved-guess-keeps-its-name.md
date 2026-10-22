# 148 — An approved guess keeps its name

**Type:** AFK · **Source:** ADR 0034, decision 4 — [The agent's questions are a form](../adr/0034-questions-are-a-form-the-chat-can-fill.md)

## What to build

A size Claude guessed and the user approved stays named as a guess wherever it
is used next, since a wrong one shows nowhere else (ADR 0016).

- **The anchor span's question names it.** `lib/span.py`'s *is this the width
  you told me, 300 mm?* becomes *is this the 150 mm height you approved from
  Claude's guess?* when 147's record says the size answer was *Claude's guess*.
  Any other source keeps today's wording.
- **Rule 1 gains a fourth source**, *Claude's guess, approved*, in
  `CLAUDE.md`, `templates/space/CLAUDE.md` and the new-space skill, which stop
  saying the anchor is never guessed: a guessed anchor is the user's only once
  approved, and is named as a guess wherever it is used.
- **A spec write's case names it**: the new-space skill's *every number names
  its source* lists the fourth.

## Acceptance criteria

- [ ] An anchor span whose size was an approved guess asks with *approved from Claude's guess*
- [ ] An anchor span whose size the user typed asks as today
- [ ] Rule 1, the space template and the new-space skill list the fourth source, and say the same thing

## Blocked by

- 147
