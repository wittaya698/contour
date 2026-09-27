# 02 — A run holds the space

**Type:** AFK · **Source:** ADR 0019 decision 18; resolves [open question 11](../OPEN-QUESTIONS.md)

## What to build

Two agents over one model space race on `build.py`, and the loser's work
disappears silently into a file the other one overwrote. This is already true of
two terminals and has nothing arbitrating it.

A lock in the space's `.contour/`, git-ignored beside `report.json` and
`last-build.log`. A second caller — console or terminal — is refused with a
message naming what holds it, rather than proceeding.

Two properties are load-bearing and are the reason this slice is not the obvious
one-liner:

**The launcher takes and enforces the lock, not the console.** A lock the console
owned would put privilege in the single layer allowed to carry dependencies, and
would leave terminal-versus-terminal — the case that races today — unprotected.

**It is scoped to a run, not a build.** What actually races is the `build.py`
editing *between* builds. A build-scoped lock would look like a fix and not be
one.

A stale lock — the holder died — must be recoverable without the user reading
about file formats.

## Acceptance criteria

- [x] A second `contour check` in a held space is refused with a message, not queued
- [x] The refusal names what holds the lock
- [x] The lock is released when the holder exits, including on failure and on interrupt
- [x] A lock whose holder is gone does not permanently wedge the space
- [x] The lock file is git-ignored
- [x] Two terminals reproduce the refusal, with no console involved
- [x] Open question 11 is marked resolved and says how

## Blocked by

None — can start immediately. Fixes a race that predates the console.
