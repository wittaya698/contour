# 146 — Accept ADR 0034

**Type:** HITL · **Source:** design session 2026-10-23 — [The agent's questions are a form, and a chat can fill it](../adr/0034-questions-are-a-form-the-chat-can-fill.md)

## What to build

ADR 0034 read and given its verdict before any code depends on it. It loosens
three lines drawn on purpose: a chat may now send answers in (ADR 0027
decision 12, ADR 0028 decision 6), Claude may suggest the size, and rule 1
gains *Claude's guess, approved* as a source. Accepted, amended, or sent back;
147–150 follow whatever it becomes.

## Acceptance criteria

- [x] ADR 0034's status says Accepted (or amended, with what changed)
- [x] The headers of ADR 0027, 0028, 0024 and 0033 name the amendment

## Blocked by

None - can start immediately
