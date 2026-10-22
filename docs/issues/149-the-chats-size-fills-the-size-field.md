# 149 — The chat's size fills the size field

**Type:** AFK · **Source:** ADR 0034, decision 6 — [The agent's questions are a form](../adr/0034-questions-are-a-form-the-chat-can-fill.md)

## What to build

ADR 0033's `--said` becomes a prefill. It stays on the launch line; what the
console does with it changes.

- **The `is_size` field is filled from `--said`**, as *from the chat*, when the
  new-space run's first `ask` arrives, by ADR 0034 decision 3's precedence:
  it beats Claude's guess, and an identical guess stays *Claude's guess*.
- **The sentence ADR 0033 decision 4 added to `NEW_SPACE` is withdrawn**, with
  `lib/said.py`'s `sentence`.
- **`create`'s answer** still says the size was passed on as a suggestion.

## Acceptance criteria

- [x] A new space made with `--said width:300` shows its size field as *300 mm wide*, *from the chat*
- [x] With `--said` equal to Claude's guess, the field says *Claude's guess*
- [x] The new-space prompt no longer carries the said sentence

## Blocked by

- 147
