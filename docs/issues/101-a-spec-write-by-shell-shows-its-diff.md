# 101 — A spec write made through the shell shows its diff and its case

**Type:** HITL · **Source:** [issue 100](100-accept-adr-0028.md)'s tracer bullet, against ADR 0028, decision 1 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

In `beaky-0028`, an unattended run wrote the spec with a `Bash` call (a Python
heredoc that replaced three strings in `spec.yaml`, then ran `git diff` and
`contour check`), not with `Edit`. The gate classified it as a spec write and set
it aside, as it should. But the approval it kept had:

- **no diff:** the gate's words diff only an `Edit` or a `Write` of `spec.yaml`,
  so `changes` was empty;
- **no case:** the agent said nothing just before the call, and its argument
  came afterwards, in its closing.

The page therefore shows *Claude wants to change the spec* above a raw script,
which is less than ADR 0028 decision 1 promises: the act, the diff, and the case.
Allowing it runs the whole script, `contour check` included.

## Options (to decide)

- Refuse a spec write that is not an `Edit` or a `Write`, telling the agent to
  make it as one, so the diff can be read before it happens.
- Or run the script against a copy of the space, when the approval is set aside,
  and diff the copy's spec.
- And for the case: take the agent's last text before the call *or* its closing,
  or tell the agent, when a spec write is set aside, to put its case in the text
  before the call.

## Acceptance criteria

- [ ] An approved spec write shows the person what it changes, whatever tool made it
- [ ] It shows the case for it, or says plainly that the agent gave none
