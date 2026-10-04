# 0024 — The connector: Desktop reads and opens, never drives

**Status:** Accepted · 2026-10-04 · **amends [ADR 0019](0019-console-a-driven-agent-behind-a-gate.md) (its rejection of *a socket and any agent behind it*) and [ADR 0021](0021-the-lobby.md) (create carries references)**

> **Drafted Proposed, accepted the same day on the tracer bullet's result**
> (issue 63). Claude Desktop, registered by hand from the block `contour mcp
> --config` printed, read `beaky`, refused as decided, and made a space from
> pictures on disk, and no console URL reached the conversation.

## Evidence: the tracer bullet, 2026-10-04

`beaky`, checked and then filmstripped, so its last log was the filmstrip's:

| | asked in Desktop | what came back |
|---|---|---|
| registration | the printed block, pasted by hand | Desktop's config differed only by the paste |
| `status` | *beaky's status?* | the check's verdict, PASS 22/22, 4 marks open |
| `log` | *beaky's last log?* | its tail, written by `filmstrip` |
| `picture` | *beaky's sheet?* | the sheet, current, inside the tool call's expanded row |
| `open console` | twice | opened, then *already open in a console (pid …); its tab is the way in* |
| `open canvas` | with that console up | *already open in a console; its page can mark* |
| a tolerance | *change the width tolerance* | sent to the console; nothing changed |
| a pasted picture | *make a space from this* | asked for the file's path; no `create` |
| `create` | `beaky-63`, from `refs/front.jpg` and `refs/side.jpg` | the space, its console on the new-space flow |

The copies matched their originals byte for byte (`front.jpg` `10a4d64…`,
`side.jpg` `0206126…`, replayed through the same call once `beaky-63` had been
deleted). Two things the run showed that the decisions did not say: Desktop
shows a tool's image in the call's expanded row, not inline in the chat, which
the README now says; and the instructions grew a fourth line for pasted
pictures while issue 64 was built, which decision 4 already records.

## Context

Every surface Contour has is one somebody stands at: a terminal agent session,
the canvas, the console, the lobby. Wanted: to ask about a model from a Claude
Desktop chat — is it green, what failed, what does it look like, what did the
last run cost — and to be sent from there to the page where something can be
done about it.

A Desktop chat is not a Claude Code session. It reads no space's `CLAUDE.md`,
runs no `PreToolUse` hook, and discovers no skill — so ADR 0019 decision 19's
way of carrying the eight rules to an agent does not reach it. Whatever tools a
local MCP server offers it, the tool list *is* the policy, and a rule the list
leaves room for is a rule with no mechanism.

Three facts, measured on 2026-10-04, shape it:

- **No file holds the last verdict.** `.contour/report.json` is deleted at the
  start of every stage (`lib/cli.py`, `stage`), so after `contour filmstrip` it
  holds the filmstrip's lines — `beaky`'s did. `.contour/last-build.json` is
  written only by `check` and its docstring calls it *the last build's verdict*,
  but it stores `{"built": true}` and nothing else.
- **`last-build.log` is the last stage's log**, overwritten the same way. It
  opens with `$ <command>`, so it can at least say whose it is.
- **The lobby already opens a console without learning its secret.**
  `lib/enter.console` starts it detached and is told nothing back, and the
  lobby refuses a second console on a space whose presence names one
  (ADR 0021). The hazard ADR 0019 decision 39 closed — any local process
  holding a gate's key — is therefore already avoidable by reuse.

## Decision

**1. A *connector*, `contour mcp`, part of the launcher.** A stdio MCP server
speaking the three methods it needs — `initialize`, `tools/list`, `tools/call`
— in stdlib `json` over `sys.stdin`, with no resources, prompts or sampling. It
reads state by importing the Blender-free half of `lib/`, as the console does
(ADR 0019 decision 31), and so falls under that half's stdlib-only test. ADR
0019 decision 34 refused `contour console` as a subcommand because it would hide
an install boundary; a stdlib connector has none to hide, so the reason does not
carry. `contour selftest` covers it, and a bare clone serves it.

**2. It reads and opens, and creates. It never builds, writes inside a space
that exists, marks or holds one.** `check`, `render` and `export` take the
space's hold, and under a console a build is a gated call whose gate is where
marks are anchored (ADR 0019 decision 14). A build from a chat would skip both.
The console is one `open` away. The one write it makes is a space that did not
exist a moment before, and decision 10 says what that write may contain.

**3. Eight tools, coarse on purpose** — every definition sits in Desktop's
context on every turn, and token usage is the second stated priority.

| Tool | Takes | Returns |
|---|---|---|
| `spaces` | — | every space and its health, as `contour spaces --json` says it |
| `status` | space | the last check's verdict and stats, open marks, uncommitted vetoes, `doctor` drift |
| `log` | space, `lines` (40) | the tail of `last-build.log`, and which stage wrote it |
| `picture` | space, `sheet` \| `filmstrip` \| `worksheet` | the image and the build it was drawn from, or *not drawn yet* |
| `spec` | space | `spec.yaml` as text |
| `spend` | space | the console's per-run cost from `spend.jsonl` |
| `open` | `lobby` \| `canvas` \| `console`, space | opens it, and says only that it did |
| `create` | name, reference paths | a new space with those references, its console open on the new-space flow |

A space is named in every call but `spaces` and `open lobby`, resolved as
`contour spaces <name>` resolves it: a chat stands in no directory.

**4. Its instructions describe the connector, not the rules.** Four lines in
`initialize`'s `instructions`: it reads and opens and changes nothing; a spec
changes only inside a space, argued from a span the user can see on the canvas;
to change the model, open its console; a picture pasted into the chat is not a
reference, so ask for its file's path (decision 10). `spec`'s result ends with
the second of those. This states facts about the connector, which cannot drift from
`CLAUDE.md` because they are not a copy of it — and it turns *Desktop argues
for a wider tolerance* into *Desktop sends you to draw a span*, which is where
rule 1 needs the argument to be had.

**5. `open` is the lobby's actions with the lobby's refusals, plus one.**
`open console` is `lib/enter.console`, refused when a console already serves
the space or no environment exists, in the lobby's own words. `open lobby` and
`open canvas` start their commands detached and do not wait — Done is the
user's, on the page. **The connector's own refusal: no canvas on a space a
console serves** — *already open in a console; its page can mark*. The console
page is a full canvas, so a second page would add a second writer to
`marks.json` and nothing else. The connector never sees a console's URL, so the
secret behind every gate never enters a conversation with an agent.

**6. `last-build.json` carries the whole check report.** Pass or fail, its
lines, its per-check results, its seconds, the build fingerprint and when — one
writer, `check`, as today. The file becomes what its docstring already says it
is, and the console's panel can show the verdict, not only whether it built.
`log` reads its own first line and says *this log is from `filmstrip`, not the
last check* rather than passing a later stage's log off as a failure's cause.
While a run holds the space, `status` says the verdict is from before it.

**7. Contour never writes Desktop's config.** `contour mcp --config` prints the
block to paste into `claude_desktop_config.json`, pointing at the `contour`
symlink rather than the checkout, so moving the toolkit is still a relink. That
file is the user's, lists servers that are not Contour's, and is rewritten by
Desktop's own settings; `install-hooks` writes outside the tree only because the
push guard must be enforced, and registration is a convenience.

**8. Model content goes to an API through the connector, by design, and this is
where that is stated.** Every space `contour spaces` finds is visible. Rule 8 is
a git boundary, and sharing a model's content out of band is its owner's call;
installing the connector is the deliberate act, and Desktop's per-tool
permission prompt is the per-call one. As with ADR 0019 decision 40, the point
is that it is named here, not that it is prevented.

**9. ADR 0019's rejection of *a socket and any agent behind it* is amended, not
reversed.** It was rejected on *no user today*; Desktop is the user. What it
gets is narrower than that rejection imagined — no agent drives through it —
which is why it fits in the launcher at all.

**10. `create` is the lobby's create, plus the references, and nothing else.**
It refuses any path that is not a readable image file, runs `contour init
--new`, copies each file byte for byte into the new space's `refs/`, and starts
its console with `--begin new-space` through `lib/enter.console` — or, with no
console environment, says how to go on from a terminal, as the lobby does. It
drafts no spec and writes nothing else: the anchor, the spans and the
tolerances are the console's, under its gates (ADR 0021 decision 4). The copy
does not meet rule 1, because a reference becomes guarded when git first tracks
it, and nothing in a space that new is tracked. **A picture pasted into the
chat is never a reference.** The model holds what it saw, not the file, and a
tool argument is text, so anything it wrote out would be a picture it made up —
which `contour measure` would then read as precisely as a real one, giving
spans of nothing that argue the spec toward an image the user never supplied.
Handed one, the connector's answer is to ask for the file's path.

**11. The lobby's create takes references too, dropped onto its form.** The
browser holds the file itself, so the bytes the page sends are the original's —
read raw, never drawn or resized, which would re-encode them — base64 inside the
JSON every Contour page POST already must be (ADR 0019 decision 39). They travel
with the create request and are all checked, as images and under a size cap,
before `contour init` runs, so a bad drop never leaves half a space. **Only on
create, never onto a space that exists:** a reference added after a spec was
argued from the old set changes what spans can measure, which is why `ref-write`
is a gated category, and a lobby button would go round that gate. Adding one
later belongs in that space's console.

## Consequences

- **A Desktop chat can never be the cause of a build, a spec write or a
  commit.** Rules 1, 2, 3 and 5 have no path through the connector to cover, so
  nothing restates them there. Its one write makes a space, and the spec in it
  is drafted where the gates are.
- **The connector is a versioned surface.** Tool names and result shapes are
  what a Desktop config and a user's habits depend on, and change as an
  interface does.
- **`last-build.json` grows**, and its one writer is unchanged.
- **Content leaves through a third door.** The console sends it to a provider
  as its purpose (ADR 0019 decision 40), `export` hands over a `.glb`, and now a
  chat can ask for a sheet. All three are deliberate; none is via git.

## Rejected

- **A third executable, `contour-mcp`, on the MCP Python SDK.** Less protocol
  owned, and Desktop would stop working on a clone with no environment — for
  three methods.
- **The connector inside `contour-console`.** Puts it in the dependency layer,
  and it would exist only while a console was running.
- **Building from a chat.** Skips the hold and the gate that anchors marks, and
  races a console's run.
- **Fine-grained tools** — `marks`, `vetoes`, one per file. Each costs context
  on every Desktop turn; counts belong in `status` and details on the canvas.
- **Folding `log` into `status`.** Every red `status` would pay for a tail.
- **No `spec` tool.** Reading the contract is harmless; arguing about it without
  a span is the risk, and decision 4 answers that.
- **Silence as instructions.** The tool list stops writes, not advice: a chat
  would propose spec changes with no span behind them, and the user would make
  them by hand.
- **`CLAUDE.md` as instructions.** No drift, and forty lines for a builder that
  mostly do not apply, on every turn.
- **Reading `report.json` and labelling its stage.** No toolkit change, and
  *what does the last check say* would often be answered *unknown*.
- **A second verdict file.** Two records of one check, and a panel and a
  connector that can disagree.
- **`contour install-desktop`, merging into Desktop's config.** The toolkit
  writing a file that is neither its own nor a space's, where a bad merge breaks
  servers that are not Contour's.
- **A `.mcpb` bundle.** A packaged copy of something that imports `lib/`, which
  is ADR 0019 decision 35's drift in a new wrapper.
- **An opt-in list of shared spaces in `~/.contour`.** Guards against what the
  owner has ruled is theirs to do, in a second policy file with nothing to
  check it.
- **Read and open only, with no `create`.** Kept the connector write-free, and
  left a person with pictures on disk going through the lobby and copying
  them into `refs/` by hand — the step most likely to be skipped, on the one
  input nothing can regenerate.
- **A pasted picture saved as a reference.** The model cannot hand back the file
  it was shown; what it wrote out would be invented, measured as if it were
  real, and guarded as the user's intent from its first commit.
- **Dropping references onto a space that exists, from the lobby.** A
  `ref-write` with no gate in front of it.
- **Multipart uploads.** Easier for large files, and the one way round the
  JSON-only rule that keeps a cross-site form from reaching a handler.
- **A canvas beside a console from the connector.** Allowed elsewhere today; not
  started from here, because nothing asked for two writers.
