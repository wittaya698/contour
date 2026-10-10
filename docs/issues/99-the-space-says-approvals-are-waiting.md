# 99 — The space says approvals are waiting, and the chat asks now or later

**Type:** AFK · **Source:** ADR 0028, decisions 5, 6 and 7 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What to build

*Waiting for you* becomes something a space has rather than a state a run is in.
The lobby's row and the connector's `status` say *2 approvals waiting* and name the
acts, until none are left. `contour request` and the connector's `request` refuse
while any wait, naming the way in: *beaky has 2 approvals waiting; open its console
to answer them.* The connector's instructions tell a chat that finds approvals
waiting to say what they are and ask whether to answer them now or later. *Now* is
`open`. The chat never answers one, never relays the case for one, and never
writes *the user says yes* into a request. `open console` on a space whose run has
ended starts a console that shows its approvals.

## Acceptance criteria

- [ ] The lobby's row and `status` say how many approvals wait and for what, with no diff
- [ ] A request is refused while approvals wait, in the command's and the connector's words alike
- [ ] The connector's instructions say to ask now or later and never to answer
- [ ] `open console` after the run has ended brings up a page showing the approvals, and no URL enters the chat
- [ ] A stop or the ceiling ends a run and leaves what it set aside waiting

## Blocked by

- [97](97-approvals-answered-on-the-page.md)
