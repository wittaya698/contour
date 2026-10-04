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

- [x] `contour mcp` answers `initialize`, `tools/list` and `tools/call` over stdio, and refuses anything else as the protocol says to
- [x] `initialize` carries the three-line instructions, and nothing in them is a copy of `CLAUDE.md`
- [x] `spaces` returns what `contour spaces --json` returns
- [x] `contour mcp --config` prints a block naming the symlink, and writes nothing
- [x] The connector is covered by the stdlib-only test of `lib/`'s Blender-free half, and its tests need no Desktop
- [x] `contour mcp` is a row in the command table, and `contour`'s help lists it
- [x] The README says how to register it

## Blocked by

None - can start immediately

## What it came to

Done, 2026-10-04, in `lib/connector.py`. The protocol is the three methods; any
other is -32601, a line that is not JSON is -32700 and the session goes on, and
a tool that raises comes back with `isError` rather than ending the pipe. The tools
are handed to `serve` by the launcher, so the connector imports nothing of it.
`--config` names the link and nothing else: an interpreter beside it would have
been the checkout's `.venv`, so the link's own shebang chooses (`/usr/bin/python3`).
With no link on `PATH` it prints the block for `~/.local/bin/contour`, says how to
make the link, and exits 1. `ping` is not answered; the spec says a server should,
and the ADR names three methods.
