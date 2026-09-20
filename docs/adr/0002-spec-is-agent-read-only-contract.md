# 0002 — The spec is an agent-read-only contract

**Status:** Accepted · 2026-09-20

## Context

If the agent owns both the goal and the test, it will eventually relax the goal
to turn a red check green. This is the most common silent failure in agent
loops, and it is undetectable from the outside because everything reports
success.

## Decision

`spec/<variant>.yaml` states the user's intent in numbers and words:
dimensions with tolerances, parts, topology and engine constraints. The agent
**reads it and never writes it**. `verify.py` reads it and enforces it
mechanically; `build.py` never reads tolerances to satisfy them cheaply.

Spec changes are proposed in chat and made by the user.

## Consequences

- The goalposts cannot move without a human moving them.
- Git diffs intent (`spec/`) separately from attempt (`models/`), so "what did I
  ask for" and "what did it do" are distinguishable in history.
- The user must express intent numerically, which is more work up front than
  saying "make it look nicer".
- Some real intent is not numeric. Those go in the spec as prose notes that
  `verify.py` cannot check, and are judged by the human at the approval gate.

## Rejected

- **Assertions in a pytest file** — expressive, but agent-editable, so the
  goalposts move silently.
- **`SPEC = {...}` at the top of `build.py`** — cheapest context, same problem.
- **Prose-only Markdown spec** — nothing enforced, checks re-derived from prose
  every session, drifting each time.
