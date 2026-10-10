# 96 — A gate sets its act aside, and the run goes on

**Type:** AFK · **Source:** ADR 0028, decisions 1, 4 and 5 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What to build

In an unattended run, a gate the run cannot pass, whether it is on the floor or
not on the ask-list, no longer parks. The call is not made. It is kept in the
space's `.contour/`, git-ignored, as an **approval waiting**: the call exactly as
the agent wrote it, the act in plain words, the diff, and the agent's case for it.
The agent is told the act was set aside for the person, to carry on with what does
not depend on it, and not to try it another way. When the run ends, the record says
*finished* and lists the acts waiting, in the gate's plain words, with no diff and
no argument. No banner is posted: `lib/notify.py`, its hatch and `tests/quiet.py`
go. An attended run's gates still wait for the person, as before.

## Acceptance criteria

- [x] A floor gate in an unattended run sets its act aside, the call is not made, and the run carries on to its end
- [x] A gate for a category not on the ask-list does the same
- [x] What is kept holds the call as written, the act, the diff and the agent's case; the run record holds only the act
- [x] The agent's tool result says the act was set aside for the person
- [x] No notification is posted, and nothing in the toolkit posts one
- [x] An attended run's gates are unchanged

## Blocked by

None - can start immediately
