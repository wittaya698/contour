# 97 — Approvals answered on the page, later

**Type:** AFK · **Source:** ADR 0028, decision 3 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What to build

Any console opened on a space with approvals waiting shows them before it takes a
new prompt, in the order they were set aside, each with what its gate would have
shown: the act, the argument and the diff. **Allow** applies the call then, as it
was written. **Deny** records a veto, as a gate's deny does. A call that no longer
applies (an edit whose old text is gone, a save with nothing to save) is shown as
*no longer applies* and dropped, and it is not a veto. Each is answered only after
the one before it. Nothing times out. When none are left, the space has nothing
waiting.

## Acceptance criteria

- [ ] A console opened after the run has ended shows its approvals, oldest first
- [ ] Allowing a spec write applies the agent's edit as written, and `contour check`'s revision guard still applies to it
- [ ] Allowing a save makes the commit, after the person has seen the diff and the panel
- [ ] Denying records a veto with the call, the reason and the build, as a gate's deny does
- [ ] A call that no longer applies is dropped, said so on the page, and is not a veto
- [ ] An approval cannot be answered before the one set aside ahead of it

## Blocked by

- [96](96-a-gate-sets-its-act-aside.md)
