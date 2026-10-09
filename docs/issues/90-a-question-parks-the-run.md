# 90 — A question parks the run

**Type:** AFK · **Source:** ADR 0027, decision 12 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

In an unattended run, a question from the agent parks the run the way a gate
does: *waiting for you: Claude has a question*. The person answers on the page,
and the run carries on with its context. The record carries the question's
text so a requester can relay it, and there is no way for a requester to
answer it. A parked question, like a parked gate, holds the console alive.

## Acceptance criteria

- [ ] A question in an unattended run parks it, and the record shows the question's text
- [ ] An answer on the page resumes the same run, not a new one
- [ ] No command or connector tool answers a question
- [ ] An attended run's questions are unchanged

## Blocked by

- [89](89-contour-request.md)
