# 57 — The connector answers `spaces`

**Type:** AFK · **Source:** ADR 0024, decisions 1, 3, 4 and 7 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

`contour mcp` exists and Claude Desktop can talk to it. It is a stdio MCP server
inside the launcher, stdlib only, speaking the three methods it needs —
`initialize`, `tools/list` and `tools/call` — and nothing else: no resources, no
prompts, no sampling. Anything else is answered with the protocol's own
method-not-found error, never a traceback.

`initialize` carries the connector's three-line instructions: it reads and opens
and changes nothing; a spec changes only inside a space, argued from a span the
user can see on the canvas; to change the model, open its console. They describe
the connector and restate none of the eight rules.

One tool, `spaces`: every space and its health, as `contour spaces --json` says
it. It is the thinnest path that proves the whole stack, from Desktop's config to a
tool result.

`contour mcp --config` prints the block to paste into
`claude_desktop_config.json`, pointing at the `contour` symlink rather than the
checkout. Contour never writes that file.

## Acceptance criteria

- [ ] `contour mcp` answers `initialize`, `tools/list` and `tools/call` over stdio, and refuses anything else as the protocol says to
- [ ] `initialize` carries the three-line instructions, and nothing in them is a copy of `CLAUDE.md`
- [ ] `spaces` returns what `contour spaces --json` returns
- [ ] `contour mcp --config` prints a block naming the symlink, and writes nothing
- [ ] The connector is covered by the stdlib-only test of `lib/`'s Blender-free half, and its tests need no Desktop
- [ ] `contour mcp` is a row in the command table, and `contour`'s help lists it
- [ ] The README says how to register it

## Blocked by

None - can start immediately
