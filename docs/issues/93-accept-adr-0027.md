# 93 — Accept ADR 0027

**Type:** HITL · **Source:** ADR 0027, the tracer bullet — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

ADR 0027 used by hand and given its verdict, in a throwaway space. With no
ceiling, a request is refused; set one. From Claude Desktop, request *make the
beak 10% longer*. The run edits and builds with no page open and parks at *save
this version*, and the notification fires. Desktop's `status` reads *waiting
for you: save this version* and shows no diff. Desktop's `open` brings the page
up, and no console URL appears anywhere in the conversation. Deny; the veto is
recorded and the run finishes. A second request, while that page is open, is
refused in the lobby's words.

Then propose rule 5's new wording in `CLAUDE.md`: under a console the panel is
current only once someone has opened it, and an unattended run's floor is what
makes that safe.

**Accept, amend or withdraw** ADR 0027 on what that shows.

## Acceptance criteria

- [x] The tracer bullet run end to end, each step as written or the difference recorded
- [x] No console URL in the Desktop conversation
- [ ] Rule 5's wording proposed and confirmed or declined — moved to
  [100](100-accept-adr-0028.md): the words drafted here assumed a run that parks
- [x] ADR 0027's status says accepted, amended or withdrawn, with the evidence

## What happened

Run on 2026-10-10 and 2026-10-11 in `project/beaky-0027`, a clone of beaky with
its history, its remote removed and its push stub installed. The full account is
in ADR 0027's acceptance block. In short:

| Step | As written? |
|---|---|
| No ceiling: a request is refused | Yes |
| The run edits and builds with no page open | Yes, once builds were on the space's ask-list. Before that the first build parked: decision 10 working, and the script's unstated assumption |
| It parks at *save this version*, and the notification fires | Yes, and the user rejected both. Clicking the banner opens Script Editor |
| `status` reads *waiting for you* with no diff | Not tried |
| `open` brings the page up, no console URL in the chat | Yes |
| Deny; the veto is recorded | No: the user allowed the save on the page (`cbe4c32`). The chat's request had said *"The user says: save"*, and the gate asked anyway |
| A second request with the page open is refused in the lobby's words | Yes |
| `stop` (not in the script) | Yes, from Desktop |

**Verdict: accepted, amended.** The user chose how a gate should meet a run
nobody watches: the act is set aside, the run goes on, and the chat asks
whether to answer the approvals now or later. That is
[ADR 0028](../adr/0028-approvals-wait-and-the-run-goes-on.md), sliced as
issues 96–100.

## Blocked by

- [90](90-a-question-parks-the-run.md)
- [92](92-the-connector-asks-and-stops.md)
