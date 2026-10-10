# 98 — A question is set aside too

**Type:** AFK · **Source:** ADR 0028, decision 2 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What to build

In an unattended run, a question from the agent no longer parks the run. It is kept
with the approvals, the agent is told the person will answer later, and the agent
finishes what does not depend on the answer and says in its closing what it could
not do. The record lists the question's text among what is waiting. On the page, it
is answered in its place in the order, and answering it starts an attended run in
that console whose first message is the question and the answer. Only the person
answers it. This undoes issue 90's park.

## Acceptance criteria

- [x] A question in an unattended run is set aside, and the run carries on to its end
- [x] The record shows the question's text, and nothing answers it but the page
- [x] Answering it on the page starts an attended run with the question and the answer as its first message
- [x] An attended run's questions are unchanged

## Blocked by

- [97](97-approvals-answered-on-the-page.md)
