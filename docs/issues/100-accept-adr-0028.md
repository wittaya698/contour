# 100 — Accept ADR 0028

**Type:** HITL · **Source:** ADR 0028, the tracer bullet — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What to build

ADR 0028 used by hand and given its verdict, in a throwaway space with builds on
its ask-list. Claude Desktop requests *make the beak 10% longer and save it*. The
run edits, builds and argues a spec change with no page open, sets the spec write
and the save aside, and finishes. No banner appears. Desktop's `status` reads
*finished: 2 approvals waiting*, names both acts and shows no diff, and the chat
asks whether to answer them now or later. A second request is refused while they
wait. *Later*, then `open`: the console shows both, in order, with the argument and
the diff. Allow the spec write; deny the save. The veto is recorded, nothing is
left waiting, and the lobby's row says so. Also try `status` on a space with
nothing waiting, which issue 93 did not reach.

Then propose rule 5's new wording, in the toolkit's `CLAUDE.md` and in
`templates/space/CLAUDE.md`: under a console the panel is current once someone has
opened it, and an unattended run's save is answered by the person on that page, so
the saying happens there, at whatever time they open it.

**Accept, amend or withdraw** ADR 0028 on what that shows.

## Acceptance criteria

- [x] The tracer bullet run end to end, each step as written or the difference recorded (in ADR 0028's status)
- [x] No console URL and no diff in the Desktop conversation — no URL ever; the case reached it once, through the record's closing, now withheld
- [x] Rule 5's wording proposed and confirmed or declined — confirmed, in both `CLAUDE.md` files
- [x] ADR 0028's status says accepted, amended or withdrawn, with the evidence

## Blocked by

- [98](98-a-question-is-set-aside.md)
- [99](99-the-space-says-approvals-are-waiting.md)
