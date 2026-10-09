# 87 — A stop that answers no gate

**Type:** AFK · **Source:** ADR 0027, decision 9 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

`contour stop <space>` ends the run in that space, and so does the page's own
stop. Stopping answers no gate: a parked call never happens, the agent is not
told no and so has nothing to work around, the run ends, and the edits made so
far stay uncommitted in the space. The record says *stopped*, by whom and why.
The hold's refusal to anyone else, while a gate is parked, names the space, the
act and that the run can be opened or stopped.

## Acceptance criteria

- [ ] `contour stop` ends a running run and a run parked at a gate, and gives back the hold
- [ ] A parked call stopped this way is neither allowed nor recorded as a veto
- [ ] The edits made before the stop are still in the space afterwards
- [ ] The record says *stopped* and why
- [ ] With a gate parked, the hold's refusal reads *<space> is waiting for you: <act>*

## Blocked by

- [86](86-a-space-records-its-latest-run.md)
