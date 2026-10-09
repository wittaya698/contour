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

- [ ] The tracer bullet run end to end, each step as written or the difference recorded
- [ ] No console URL in the Desktop conversation
- [ ] Rule 5's wording proposed and confirmed or declined
- [ ] ADR 0027's status says accepted, amended or withdrawn, with the evidence

## Blocked by

- [90](90-a-question-parks-the-run.md)
- [92](92-the-connector-asks-and-stops.md)
