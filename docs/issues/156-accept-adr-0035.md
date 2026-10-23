# 156 — Accept ADR 0035

**Type:** HITL · **Source:** design session 2026-10-23 — [A run waits on its by-eye spans](../adr/0035-a-run-waits-on-its-by-eye-spans.md)

## What to build

ADR 0035 read and given its verdict before any code depends on it. It
changes when a run stops: the worksheet checkpoint, under an attended
console, now waits for the user's answers to by-eye spans. Accepted,
amended, or sent back; 157–159 follow whatever it becomes.

## Acceptance criteria

- [x] ADR 0035's status says Accepted (or amended, with what changed)
- [x] ADR 0022's header names ADR 0022 decision 8 as amended by ADR 0035

## Blocked by

None - can start immediately
