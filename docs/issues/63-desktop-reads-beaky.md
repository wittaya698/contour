# 63 — Desktop reads `beaky`, and ADR 0024 is accepted

**Type:** HITL · **Source:** ADR 0024, the tracer bullet — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

The connector, registered in Claude Desktop from the block `contour mcp --config`
prints, used by hand on `beaky`, and ADR 0024 given its verdict.

Run `contour check` on `beaky`, then `contour filmstrip`. In Desktop: ask for
`beaky`'s status, and get the check's verdict lines and not the filmstrip's; ask
for its log, and be told it is from `filmstrip`; ask for its sheet and see it. Open
its console, then ask again: the console refuses in the lobby's words and the
canvas in the connector's own. Ask Desktop to change a tolerance, and see where it
sends you. Then hand it a picture pasted into the chat and ask for a new space:
it asks for a path. Give it the paths of pictures on disk: a new space opens in a
console on the new-space flow, its `refs/` holding those files byte for byte.

**Accept, amend or withdraw** ADR 0024 on what that shows.

## Acceptance criteria

- [ ] Desktop is registered from the printed block, and Contour wrote nothing to its config
- [ ] `status` gives the check's verdict after a filmstrip has run
- [ ] `log` names its stage
- [ ] Both refusals are seen, worded as decided
- [ ] No console URL appears anywhere in the Desktop conversation
- [ ] A pasted picture is answered with a request for a path, and never saved
- [ ] `create` from paths gives a space whose references match the originals byte for byte
- [ ] ADR 0024's status says accepted, amended or withdrawn, with the evidence

## Blocked by

- [59](59-status-and-log.md)
- [60](60-picture.md)
- [61](61-spec-and-spend.md)
- [62](62-open.md)
- [64](64-create.md)
