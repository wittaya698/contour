# Issues

One file per independently-grabbable slice. Each is a thin vertical cut through
every layer it touches — launcher, page, agent loop, tests — not a horizontal cut
through one of them. A finished slice is demoable or verifiable on its own.

**HITL** needs the user: a decision, a wording, a review. **AFK** can be
implemented and landed without one. There are two HITL slices and thirteen AFK.

These come from [ADR 0019](../adr/0019-console-a-driven-agent-behind-a-gate.md),
which holds the reasoning and the rejected alternatives. Each file cites the
decisions it implements; read the ADR before arguing with a slice.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [00](00-accept-adr-0019.md) | Accept ADR 0019 | HITL | — |
| [01](01-canvas-server-authenticates.md) | The canvas server authenticates | AFK | — |
| [02](02-a-run-holds-the-space.md) | A run holds the space | AFK | — |
| [03](03-lib-split-becomes-a-test.md) | The `lib/` split becomes a test | AFK | — |
| [04](04-launcher-classifies-intent.md) | The launcher classifies a call's intent | AFK | — |
| [05](05-ask-list-silence-means-ask.md) | The ask-list is read, and silence means ask | AFK | 04 |
| [06](06-contour-console-serves-the-page.md) | `contour-console` exists and serves the page | AFK | 01 |
| [07](07-page-asks-its-host.md) | The page asks its host what it can do | AFK | 06 |
| [08](08-a-gated-run-end-to-end.md) | A gated run, end to end | AFK | 05, 06 |
| [09](09-the-sheet-panel-labelled.md) | The sheet panel, labelled | AFK | 08 |
| [10](10-build-is-a-gated-call.md) | A build is a gated call, and that gate resolves marks | AFK | 08, 09 |
| [11](11-a-veto-is-recorded.md) | A veto is recorded | AFK | 08 |
| [12](12-marks-seed-a-run.md) | Marks seed a run | AFK | 08, 09 |
| [13](13-spend-is-live.md) | Spend is live, and `tools/tokens.py` can read it | AFK | 08 |
| [14](14-rules-become-mechanism-neutral.md) | Rules 1 and 5 become mechanism-neutral | HITL | 08, 10 |

## Shape of the graph

**01, 02, 03 and 04 are all unblocked and all land in the launcher.** That is
deliberate: every one of them is worth having even if the console never ships.
02 fixes a race that predates this design, 01 closes a hole in shipped behaviour,
03 names two properties nothing currently checks, and 04 builds a classifier the
launcher wants anyway.

**08 is the wide one,** and it stays whole. Splitting it would produce a merged
state in which a driven agent runs ungated, and an ungated agent can commit.
Because the default ask-list is empty, the first working version of 08 gates
everything — the designed starting point, not a stub.

**14 is last on purpose.** The eight rules change when the console lands, not
before; a rule describing a mechanism that does not exist is worse than the
honour-system wording it replaced.
