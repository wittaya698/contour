# 88 — A ceiling

**Type:** AFK · **Source:** ADR 0027, decision 13 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

The user sets a ceiling, in weighted tokens, the unit the spend line already
speaks. It lives in `~/.contour` beside the ask-list, written by a command
meant for the person and not the agent, as `contour asks --always` is. A run
that carries a ceiling stops on reaching it, through 87's stop: no gate is
answered, the edits stay, and the record says *stopped: reached your limit of
N*. An attended run carries none, which keeps ADR 0019 decision 37 as it is for
a run somebody is watching.

## Acceptance criteria

- [ ] The ceiling can be set, shown and removed, and nothing in a space writes it
- [ ] A run carrying a ceiling stops at the first turn that reaches it, and not before
- [ ] Reaching it is a stop: no gate answered, edits kept, the record says why
- [ ] An attended run is never stopped by a ceiling

## Blocked by

- [87](87-a-stop-that-answers-no-gate.md)
