# 137 — Accept ADR 0032

**Type:** HITL · **Source:** design session 2026-10-18 — [a span is measured through the camera](../adr/0032-a-span-is-measured-through-the-camera.md)

## What to build

ADR 0032 read and given its verdict before any code depends on it. It reverses
ADR 0017's *perspective error is disclosed, not corrected*, and makes the anchor
a span rather than the spec's height over the foreground's box. Accepted,
amended, or sent back; the issues below follow whatever it becomes.

## Acceptance criteria

- [x] ADR 0032's status says Accepted (or amended, with what changed)
- [x] `CONTEXT.md`'s **direction** and **anchor** match what was accepted

## Blocked by

None - can start immediately
