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

**Amended 2026-09-20 — creation is not a change.** The failure above is mutation:
relaxing a goal that already exists to turn a red check green. At creation there is
no red check yet, and requiring the user to hand-write ~60 lines of YAML from a
schema front-loads exactly the cost this ADR already admits under Consequences. So
the agent may draft a *new* spec when asked, for the user to accept; from its first
commit rule 1 applies to it in full.

This moves one risk rather than removing it: a tolerance the agent invents at birth
is as loose a goalpost as one it widens later, and the user has no independent
reading to judge it against. Hence the obligation to list back every
agent-chosen number, tolerances first — the guard is disclosure, not the gate.
The mechanical form of the rule is: a `spec/*.yaml` git already tracks is
never written again.

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
