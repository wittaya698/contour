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

## Batch 4 — agent spans

From [ADR 0022](../adr/0022-the-agent-reads-the-references-in-spans.md), accepted
2026-10-03 (issue 43). The agent draws spans on the references, with ends placed by
measurement; the user answers each one; and a number from a reference names the
span it came from. Two HITL slices and five AFK.

Batch 3 is the lobby, slices 28–38, from ADR 0021, and 39 was found in flight,
which is why these start at 40.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [40](40-a-snapped-agent-span-from-a-scanline.md) | A snapped agent span from a scanline | AFK | — |
| [41](41-snapped-spans-from-a-silhouette-or-a-region.md) | Snapped spans from a silhouette or a region | AFK | 40 |
| [42](42-the-user-answers-an-agent-span.md) | The user answers an agent span | AFK | 40 |
| [43](43-accept-adr-0022.md) | Accept ADR 0022 | HITL | 41, 42 |
| [44](44-a-by-eye-agent-span.md) | A by-eye agent span | AFK | 43 |
| [45](45-contour-worksheet.md) | `contour worksheet`: the spans drawn onto the references | AFK | 43 |
| [46](46-the-proposal-names-its-spans.md) | The proposal names its spans | HITL | 44, 45 |

### Shape of the graph

**40–42 are ADR 0022's tracer bullet,** and 43 is the verdict on it. The three
numbers the bullet reproduces need both kinds of reading — 168 is a scanline, 888
and 597 are silhouette extents — which is why 40 and 41 are both in it.

**40 is unblocked and already visible.** The canvas draws an agent's marks in
their own colour, so the first snapped span shows on the page with no page work.

**46 is last on purpose,** as 14 was. Rule 1's new clause names by-eye spans, and
the skills tell the agent to look at the worksheet; a rule describing a mechanism
that does not exist is worse than the wording it replaces.

**Nothing here checks a proposal mechanically.** A proposal is prose in a
conversation, so there is no file for a command to read. That waits for proposals
to be data, which is the scaffold ADR 0022 sets aside.

## Batch 5 — a rig and its clips

From [ADR 0023](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md), proposed
2026-10-03. A model's rig and clips are built, checked and exported with its shape:
the spec states the tree and the key poses, pivots are measured from seams, and the
agent sees motion as a filmstrip. Three HITL slices and seven AFK.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [47](47-bones-without-operators.md) | Bones without operators, probed on 5.2.1 | HITL | — |
| [48](48-the-spec-carries-a-rig-tree.md) | The spec carries a rig tree | AFK | — |
| [49](49-seams-and-pivots-measured-at-rest.md) | Seams and pivots measured at rest | AFK | 48 |
| [50](50-beaky-gets-its-rig.md) | `beaky` gets its rig | HITL | 49 |
| [51](51-an-armature-built-from-the-tree.md) | An armature built from the tree | AFK | 47, 49 |
| [52](52-clips-keyed-from-the-spec.md) | Clips keyed from the spec | AFK | 51 |
| [53](53-no-part-enters-another.md) | No part enters another, at any frame | AFK | 52 |
| [54](54-the-round-trip-carries-the-rig.md) | The round-trip carries the rig | AFK | 52 |
| [55](55-the-filmstrip.md) | The filmstrip | AFK | 52 |
| [56](56-beaky-walks.md) | `beaky` walks, and ADR 0023 is accepted | HITL | 50, 53, 54, 55 |

### Shape of the graph

**47 and 48 are both unblocked, and only 51 waits on the probe.** The tree, the
seams and the pivots are geometry at rest, so 48–50 go ahead whatever 47 finds —
and `beaky`'s real faults, a head with no seam and four origins off their pivots,
surface in 50 before any armature exists. They are worth fixing even if the
animation never lands.

**52 fans out.** The collision check, the round-trip and the filmstrip each need a
keyed clip and nothing from each other.

**The HITL slices are where a rule needs the user:** 47 may add a line to the
operator whitelist (rule 4), and 50 and 56 write `beaky`'s spec (rule 1), each
with tolerances the agent may draft but not choose. 56 is the verdict on ADR 0023,
as 43 was on ADR 0022.

**Every new check ships with a fixture that makes it fail** (ADR 0009).

## Batch 6 — the connector

From [ADR 0024](../adr/0024-the-connector-desktop-reads-and-opens.md), proposed
2026-10-04. Claude Desktop reads a space's results and opens the pages where the
user acts, through `contour mcp`, and makes a new space from reference files on
disk; inside a space that exists it never builds, writes or holds. The lobby's
create takes dropped references the same way. One HITL slice and eight AFK.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [57](57-the-connector-answers-spaces.md) | The connector answers `spaces` | AFK | — |
| [58](58-the-last-build-keeps-its-verdict.md) | The last build keeps its verdict | AFK | — |
| [59](59-status-and-log.md) | `status` and `log` | AFK | 57, 58 |
| [60](60-picture.md) | `picture` | AFK | 57 |
| [61](61-spec-and-spend.md) | `spec` and `spend` | AFK | 57 |
| [62](62-open.md) | `open` | AFK | 57 |
| [64](64-create.md) | `create` | AFK | 57 |
| [65](65-references-dropped-on-create.md) | References dropped on the lobby's create | AFK | — |
| [63](63-desktop-reads-beaky.md) | Desktop reads `beaky`, and ADR 0024 is accepted | HITL | 59, 60, 61, 62, 64 |

### Shape of the graph

**57 and 58 are both unblocked.** 58 is a toolkit fix the connector found and does
not need: no file held the last check's verdict once a later stage ran, which the
console's panel can use whether or not the connector lands.

**57 fans out.** Every tool after it needs the protocol and nothing from the others.
60 is apart from 61 because an image is the one result shape new to the connector.
64 and 65 were added after the rest were sliced, which is why they are numbered
after 63. 65 needs nothing from the connector: it is the lobby's half of the same
rule, that a reference is the original file.

**63 is the only slice that needs Desktop, or the user.** Everything before it is
tested without Desktop installed; 63 is the verdict on ADR 0024, as 56 was on 0023.

## Batch 7 — pages for someone who has never opened a terminal

From [ADR 0025](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md) and
[ADR 0026](../adr/0026-update-brings-a-space-in-step.md), both since accepted,
amended (issues 70 and 82). Three HITL slices and fourteen AFK.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [66](66-the-verdict-in-plain-words.md) | The verdict, in plain words, on the console's page | AFK | — |
| [67](67-a-lobby-row-is-a-picture-and-a-verdict.md) | A lobby row is a picture and a verdict | AFK | 66 |
| [68](68-a-gate-says-the-act.md) | A gate says the act and what changes | AFK | — |
| [69](69-always-for-this-model.md) | Build gates can be allowed for good, and undone | AFK | 68 |
| [70](70-accept-adr-0025.md) | A plain lobby and a plain gate, and ADR 0025 is accepted | HITL | 67, 69 |
| [71](71-export-from-the-console.md) | Export from the console, and the file handed over | AFK | 66 |
| [72](72-the-transcript-shows-activity.md) | The transcript shows activity, not calls | AFK | — |
| [73](73-spend-is-a-quiet-line.md) | Spend is a quiet line | AFK | 69 |
| [74](74-you-said-no-to.md) | The vetoes panel says *You said no to* | AFK | 68 |
| [75](75-span-questions-one-at-a-time.md) | Claude's span questions, one at a time | AFK | — |
| [76](76-one-look-and-a-way-back.md) | One look, and a way back to the lobby | AFK | 66 |
| [77](77-shown-terms-are-taught.md) | Shown terms are taught where they first appear | AFK | 76 |
| [78](78-claude-speaks-plain-words.md) | Claude speaks in plain words | HITL | — |
| [79](79-the-connector-speaks-plain-words.md) | The connector speaks plain words, and a pasted picture opens the drop form | AFK | 66 |
| [80](80-contour-update.md) | `contour update` replaces only what nobody edited | AFK | — |
| [81](81-update-from-the-lobby.md) | Update from the lobby | AFK | 67, 80 |
| [82](82-accept-adr-0026.md) | `beaky` is updated, and ADR 0026 is accepted | HITL | 78, 81 |

**66 is the root.** Its wording table, one sentence per check id, is what the
lobby row, the export card, the header and the connector all say, so it lands
first. 68, 72, 75, 78 and 80 are unblocked beside it.

**78 is HITL because its wording is the decision.** It is the agent's voice, so
the user reads it before it lands. 70 and 82 are the verdicts on the two ADRs,
as 63 was on 0024; 70 needs only a plain lobby and a plain gate, and the other
page slices can land on either side of it.

## Batch 8 — the launcher's leftovers

From an architecture review on 2026-10-08, of the complexity batch 2 left behind
in `lib/cli.py`. The decisions are in CONTEXT.md (**update**, **survey**) and in
ADR 0026's second amendment. All AFK.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [83](83-one-answer-to-how-a-copy-stands.md) | One answer to how a copy stands | AFK | — |
| [84](84-the-survey.md) | The survey: a space as seen from outside it | AFK | 83 |
| [85](85-one-shape-for-a-command-that-confirms.md) | One shape for a command that confirms | AFK | — |

**83 fixes a defect, so it lands first.** An edited copy reads as *needs an
update* on the lobby's row forever, because the update rightly leaves it alone.
84 moves the survey out of `cli.py` and should carry 83's states, not `drift`.
85 stands alone, but changes `update`'s spelling, so a terminal habit of
`contour update` stops acting until it says `--yes`.

## Batch 9 — the unattended run

From [ADR 0027](../adr/0027-the-unattended-run.md), which is Proposed and holds
the reasoning and the rejected alternatives; the words are in CONTEXT.md
(**unattended run**, **requester**, **request**, **channel**). Seven AFK and one
HITL.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [86](86-a-space-records-its-latest-run.md) | A space records its latest run | AFK | — |
| [87](87-a-stop-that-answers-no-gate.md) | A stop that answers no gate | AFK | 86 |
| [88](88-a-ceiling.md) | A ceiling | AFK | 87 |
| [89](89-contour-request.md) | `contour request` starts an unattended run | AFK | 86, 88 |
| [90](90-a-question-parks-the-run.md) | A question parks the run | AFK | 89 |
| [91](91-the-channel.md) | The channel | AFK | 89 |
| [92](92-the-connector-asks-and-stops.md) | The connector asks and stops | AFK | 89, 91 |
| [93](93-accept-adr-0027.md) | Accept ADR 0027 | HITL | 90, 92 |

**86, 87 and 88 are worth having even if no request ever arrives.** The record
covers attended runs, the stop is the page's too, and a ceiling is inert until a
run carries one.

**89 is the wide one, and stays whole,** for issue 08's reason: split, there is
a merged state in which an unattended run exists without its floor or its
ceiling, and with a hand-loosened ask-list that state saves versions overnight.

## Found in flight

Not from either review — a defect the work turned up, filed where the rest of the
sliced work is.

| # | Slice | Type | Blocked by |
|---|---|---|---|
| [27](27-a-terminated-console-lets-go.md) | A terminated console lets go of the space | AFK | — |
| [39](39-a-background-tab-is-not-a-closed-one.md) | A background tab is not a closed one | AFK | — |
| [94](94-the-signal-tests-red-in-the-full-suite.md) | The signal tests go red in the full suite | AFK | — |

**27 came out of slice 17's own suite runs.** `contour-console` forwards `SIGINT`
and not `SIGTERM`, so every console a test terminates leaves its server running —
holding a port, and holding the space if a run was under way. About 57 per suite
run, and at a thousand the machine stops forking and the suite goes red for
reasons that have nothing to do with the change being tested. It is placed before
24 for that reason: a wide slice wants a suite whose red means something.

**39 came out of checking 36 by hand.** The lobby and the console take 10 seconds
without a beat to mean their tab closed, and browsers stop the beats of a tab in the
background. So entering a space and going back to the list killed the console, and
leaving the browser behind the terminal killed the lobby. 36's manual check waits on
it.

**94 came out of timing the suite.** Three of `SignalTest`'s five tests fail in a
full `discover` and pass alone, as does all of `test_console.py` — so a process
from another file reaches them through `servers()`, which counts the whole
machine. Either 27's no-leak guarantee has slipped or the comparison is racy; the
slice finds out which, and does not loosen the assertions to get there. It was
neither: a second suite run on the same machine. The README now says one at a time.
