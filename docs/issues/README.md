# Issues

One file per independently-grabbable slice. Each is a thin vertical cut through
every layer it touches — launcher, page, agent loop, tests — not a horizontal cut
through one of them. A finished slice is demoable or verifiable on its own.

**HITL** needs the user: a decision, a wording, a review. **AFK** can be
implemented and landed without one.

Two batches so far, and a third section for what the work itself turned up. Each
file cites what it comes from; read that before arguing with a slice.

## Batch 1 — the console

From [ADR 0019](../adr/0019-console-a-driven-agent-behind-a-gate.md), which holds
the reasoning and the rejected alternatives. Two HITL slices and thirteen AFK.

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

## Batch 2 — the deepening program

From the architecture review of 2026-09-28, which found the toolkit deep in most
places and named seven where it is not. Only one of them is a decision rather than
an implementation: slice 23 rests on
[ADR 0020](../adr/0020-checks-are-pure-over-a-measurement.md), which is Proposed.
Two HITL slices and ten AFK.

The through-line is **one owner per concept**. Every slice here takes a thing the
toolkit knows in several places — what a call means, where a space keeps its files,
what a mark is, what a measurement is, which commands hold the space — and gives it
one home. None of them adds a feature.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [15](15-the-guard-asks-what-a-call-means.md) | The guard asks what a call means | AFK | — |
| [16](16-a-json-store-shared.md) | A JSON store, shared | AFK | — |
| [17](17-the-space-layout-is-a-function-of-a-space.md) | The space layout is a function of a space | AFK | — |
| [18](18-the-mark-record-gets-an-owner.md) | The mark record gets an owner | AFK | 16 |
| [19](19-one-spelling-for-a-part.md) | One spelling for a part, and a migration | HITL | 18 |
| [20](20-anchor-becomes-views-and-badges.md) | `anchor.py` becomes views and badges | AFK | 18 |
| [21](21-one-formula-one-git-wrapper.md) | One weighting formula, one git wrapper | AFK | — |
| [22](22-accept-adr-0020.md) | Accept ADR 0020 | HITL | — |
| [23](23-the-measurement-becomes-data.md) | The measurement becomes data | AFK | 22 |
| [24](24-the-launcher-becomes-a-table-and-a-shim.md) | The launcher becomes a table and a shim | AFK | — |
| [25](25-the-selftests-assertions-become-tests.md) | The selftest's assertions become tests | AFK | 24 |
| [26](26-the-untested-free-modules-get-tests.md) | The untested free modules get tests | AFK | — |

### Shape of the graph

**15, 16, 17, 21, 22 and 26 are all unblocked,** and each is worth having even if
nothing else in the batch lands. 15 closes a hole in a shipped rule-1 mechanism. 21
fixes two divergences that are defects waiting. 26 puts a test on the parser that
defines what *correct* means. None of them needs the rest.

**16 is first among equals.** It was originally part of slice 21's duplication
work, gated on the mark record — and slice 18 then routes the record's reader into
it, which is a cycle. Pulled out ahead of both, it is a few dozen lines with four
callers waiting.

**19 is HITL because it rewrites tracked user data** in four spaces. Slice 18's
reader is bilingual, so 19 can wait indefinitely without blocking anything; what
it needs is the user watching, in a commit of its own, under rule 5.

**22 is HITL and is a tracer bullet, not a review.** ADR 0020 claims every check
can be arithmetic over summary numbers. One check rewritten answers that. Starting
23 first risks six rewrites against a shape that turns out wrong — the precedent is
ADR 0017, whose bullet disagreed with what was expected and was worth more for it.

**24 is the wide one.** It moves 803 lines and touches every subcommand, so it
wants a green suite in front of it and nothing else in flight. It is placed late for
that reason alone, not because anything blocks it — and 17 and 19 both remove work
from it if they land first.

**Nothing here is a feature.** Every acceptance list ends with output that is
byte-identical and a green `contour selftest`, because a deepening that changes what
the toolkit says is a deepening that has changed the toolkit.

## Batch 3 — the lobby

From [ADR 0021](../adr/0021-the-lobby.md), which is Proposed. One page above the
model spaces, from which a space is listed, created, renamed, deleted, restored
and entered. One HITL slice and ten AFK.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [28](28-spaces-speaks-json.md) | `contour spaces --json`: the list and its health | AFK | — |
| [29](29-contour-lobby-serves-the-list.md) | `contour lobby` serves the list | AFK | 28 |
| [30](30-an-open-page-leaves-a-presence.md) | An open page leaves a presence | AFK | — |
| [31](31-contour-rename.md) | `contour rename`: it proposes, then does the rename | AFK | 30 |
| [32](32-rename-from-the-lobby.md) | Rename from the lobby | AFK | 29, 31 |
| [33](33-accept-adr-0021.md) | Accept ADR 0021 | HITL | 32 |
| [34](34-delete-leaves-a-bundle.md) | Delete leaves a bundle | AFK | 33 |
| [35](35-restore-a-deleted-space.md) | Restore a deleted space | AFK | 34 |
| [36](36-enter-a-space.md) | Enter a space | AFK | 33 |
| [37](37-create-a-space-from-the-lobby.md) | Create a space from the lobby | AFK | 36 |
| [38](38-create-a-variation.md) | Create a variation of a space | AFK | 37 |

### Shape of the graph

**28–32 are ADR 0021's tracer bullet, built as slices,** because it crosses the
launcher, a split server, a new page and a new record. 33 is the verdict on it,
as 22 was for ADR 0020, and nothing after 33 starts against a proposal.

**28 and 30 are unblocked,** and each is worth having if the lobby never ships.
28 gives every client, not just a page, the list the launcher already derives. 30
answers *is anything open on this space?*, which has no answer today.

**31 is the CLI and 32 is the page,** split because ADR 0021 decision 3 makes the command
the contract: 31 is verifiable from a terminal alone. 34 is not split, being
smaller. The page holds none of the rules in either case.

**31 and 34 add launcher commands, and slice 24 has not landed.** Whichever lands
second fits around the other. Neither blocks 24, and 24 does not block them.

**36 before 37,** because creating a space ends by entering it.

## Found in flight

Not from either review — a defect the work turned up, filed where the rest of the
sliced work is.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [27](27-a-terminated-console-lets-go.md) | A terminated console lets go of the space | AFK | — |

**27 came out of slice 17's own suite runs.** `contour-console` forwards `SIGINT`
and not `SIGTERM`, so every console a test terminates leaves its server running —
holding a port, and holding the space if a run was under way. About 57 per suite
run, and at a thousand the machine stops forking and the suite goes red for
reasons that have nothing to do with the change being tested. It is placed before
24 for that reason: a wide slice wants a suite whose red means something.
