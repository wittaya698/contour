# 0019 — The console: a driven agent behind a gate

**Status:** Accepted · 2026-09-25 · **amends [ADR 0010](0010-miniyaml-no-dependencies.md) (the no-install promise is now bounded to the launcher) and [ADR 0018](0018-marks-a-canvas-over-the-sheet.md) (its daemon rejection is answered, and mark resolution moves to pre-rebuild)**

## Context

ADR 0018 built the return path: the user can point at the sheet, the agent can
pin a finding, and neither has to re-describe *which* thing first. It left two
gaps, and they are the reason this ADR exists.

**Between commands there is no signal at all.** `contour` is a launcher that
shoots and prints: every byte of Blender's output goes to
`.contour/last-build.log` and the conversation gets one terse line (ADR 0008).
That is exactly right for token cost and it means a build runs for tens of
seconds with nothing observable. The agent disappears and returns with a claim.

**Two of the eight hard rules are enforced by good behaviour.** Rule 1 says a
`spec.yaml` changes only as propose → user confirms → write. Rule 5 says never
commit or push without approval. Both are real gates and neither is mechanical:
they happen because the agent asks in prose and the user types yes.
`tools/guards/spec.py` is a `PreToolUse` hook and *does* intercept every tool
call — but it has two verdicts, allow and deny, and its own docstring records
what that cost: for `spec.yaml`, *"Prevention became detection, knowingly."*
ADR 0016 made that trade because a blanket deny would have refused the
sanctioned path. The missing verdict is **ask**, and the missing thing is
somewhere to ask it.

**The instrument for asking already half-exists.** `contour canvas` serves a
page on localhost, takes structured records from it, and stops when the page
says done. It is already the command whose lifetime the page decides. What it
does not do is drive anything.

## Decision

**A *console* sits above the launcher and drives the agent.** It owns the agent
loop through the Claude Agent SDK, gates the agent's tool calls against a
user-owned policy, and renders the sheet, the report and the marks on one page.

**The console is above `contour`, not inside it.** It shells out to `./contour`
exactly as `contour` shells out to Blender, and the launcher stays stdlib-only.
This is the whole containment: `README.md`'s promise — *no virtualenv, no `pip
install`, no dependencies* — becomes false for the console and stays true for
the pipeline. `contour selftest` still proves a bare clone works, which is what
ADR 0010 actually bought and what makes the toolkit shareable at all. The stack
is console → agent → `contour` → Blender, each layer a subprocess of the one
above, and the only dependency at the top.

**The console drives rather than observes.** A passive window would have made
marks the only intervention channel, and marks are deliberately asynchronous —
ADR 0018 chose that so findings survive across turns. Driving is the opposite
bet: that being present at the moment a decision is made is what was missing.
Both bets are now available, which is the point.

**It is a control surface, not a progress bar.** Tailing the log and refreshing
the sheet would have been nearly free and would have answered *what is it
doing*. It does not answer *stop*. The reason to be present is to catch a bad
decision before it lands, so the gate is the feature and the progress view is
the by-product.

**What is gated is a tunable ask-list, per tool and per path.** Gating every
tool call is unusable — an agent makes dozens of reads per turn and the user
would be clicking, not watching. Gating only the eight rules was the tempting
answer, since that list has been argued out across eighteen ADRs, but it is a
policy the user cannot tighten for a released model or loosen for a scratch one.

**The ask-list lives in `~/.contour`, and the agent may only propose.** It is
outside both the toolkit and every model space, so an agent working in a space
has no in-scope reason to touch it. This does not make tampering impossible —
an agent with Bash can write any path — it makes tampering stop being a
plausible edit. ADR 0015 used the same reasoning when it made the git boundary
structural rather than guarded, and the guard stays anyway as the backstop. The
agent may *propose* a wider list; **the console performs the write.** A
mechanism that let the agent perform it would be authorised by the very list it
widens, and every self-amending permission system has that bug.

**This is rule 2 applied to permissions.** An ask-list is a check. Never weaken
a check to make it pass — and never let the party being checked hold the pen.
It is ADR 0002's reasoning about the spec, in a second costume.

**Scope is layered, two levels, replace not merge.** A global default plus a
per-space override, both in `~/.contour`. Merging two permission lists can
silently *narrow* the result — an override that reads as adding a rule can
shadow one, invisibly in both files — so a space's list replaces the default
whole. **An unrecognised space gets the strictest list, not the default.** A
space has no identity today: `.contour/project` carries `toolkit`,
`toolkit_path` and `created`, and nothing unique, so the only available key is
the filesystem path. Fail-closed turns a moved or renamed space from *permissions
silently widened* into *the console asks about more than expected*, which is
annoying in the right direction.

**One page, and `canvas.html` is reused.** Two surfaces that both render the
sheet is how the user ends up marking on one and watching the other, and ADR
0018's whole argument is that the sheet is the one surface both parties point
at. The toolkit keeps serving it for `contour canvas`; the console serves the
same file.

**Mark resolution moves from session close to pre-rebuild.** ADR 0018 resolved
at close because the ray must hit the geometry the sheet was drawn from, and
called it a window to be kept shut. A console that rebuilds would open that
window on every build. But the console *owns* the build, so it knows the instant
before geometry changes — which is a strictly better place to cast rays than
session close ever was. The window is deleted rather than managed.
`views.json` already carries a fingerprint of the build its cameras drew
(`lib/anchor.py`), so the staleness test exists and needs only to be moved.

**The console ends when the page says done.** Last tab closes, process exits —
which is how `contour canvas` already works. ADR 0018 rejected a daemon as *"a
thing to remember to kill and a thing to serve a stale sheet"*; the second half
is now impossible, because the console owns the build, and the first half is
answered by keeping the canvas's own lifetime rule and letting it say done
later. An idle timeout catches the tab left open on Friday.

**A gate offers allow and deny-with-a-reason.** The reason goes back to the
agent as the tool result, which makes a gate the cheapest correction channel in
the system — a sentence, at the moment it applies, instead of a paragraph after
the fact. **A gate deliberately cannot edit the call.** Editing it would make the
user the author of a change attributed to the agent, in the commit and in every
later reading of why two builds differ; this repo tracks authorship everywhere
else (a mark carries an author, `addressed` is not a close) and the gate does not
become the one place it is laundered. The user says a sentence; the agent writes
the code.

**The page is an equal split: transcript and sheet.** The transcript is where
decisions are visible and where a gate fires; the sheet is where a build is
verified and where marks live. The sheet changes only when a build finishes, so
the panel **states which build it is drawn from** — `views.json` already carries
a fingerprint of the build its cameras drew, so a stale sheet is labelled rather
than quietly authoritative.

**A build is a gated call, and that gate is the resolution point.** Because the
sheet is always on screen it can always be clicked, and an agent rebuild would
otherwise invalidate marks mid-typing. Putting the build on the ask-list means
the only thing that can invalidate a mark is a call the user personally
approved — so decision 8's *resolve before rebuild* and the ask-list compose
into one mechanism, and there is no second concurrency story to own. The cost is
a click per build, which is the most-pressured gate in the system; the sanctioned
relief is a deliberate per-space ask-list entry, never a button on the dialog.

**A denial is recorded as a *veto*, tracked in the space.** A veto carries the
call, the reason, the author and the build it happened against. It is not a mark:
a mark has a position, and ADR 0018 rejected position-less marks because they
collapse *the left of the beak* back to *the beak* and return the conversation to
prose. A veto is a third thing — not *the build is wrong* and not *here is what I
meant*, but *not this* — and it is the user's authority against one call, which
is why only the user has it, exactly as only the user closes a mark. It is
tracked for ADR 0018's reason and not as a log: a veto is why two builds differ,
and an untracked one vanishes on a clean checkout taking the reasoning with it.
**A veto about a part may be promoted to a sheet mark**, which is what gives it a
position and turns a fact about a moment into an open question about the model.

**A run is attended by definition, and a gate waits indefinitely.** The console
never answers a gate on the user's behalf, in either direction. ADR 0018 rejected
auto-closing a mark on a green check and rejected the agent closing its own,
because *a finding is not disposed of by the party it is aimed at*; a timed-out
gate that denies is the same move mirrored, and silence is not a verdict. The
practical case is worse than the principled one: a refused agent works around the
refusal, so an unattended run would spend its time productively doing the wrong
thing. **A pending gate therefore suppresses the idle timeout** — otherwise the
lifetime rule would end the run at an unanswered gate and quietly become the
timeout policy this rejects. What this buys: no run state on disk, no resume, no
notification path. The console is an instrument someone is holding.

**A space is held by a lock, and the lock lives in the launcher.** While a run is
live the space is held; a second caller — console or terminal — is refused with a
message rather than silently overwriting `build.py`. The lock is **not** the
console's, because decision 4 makes the console a client of the toolkit with no
privileged access: a lock the console owned would put privilege in the one layer
allowed to carry dependencies, and would leave terminal-versus-terminal, which
races today, unprotected. It is scoped to a **run**, not a build, because the
thing that actually races is the `build.py` editing *between* builds; a
build-scoped lock would look like a fix and not be one. The lock file lives in
`.contour/`, git-ignored beside `report.json` and `last-build.log`.

**The console's agent inherits the space's configuration, and the ask-list is
additional.** The SDK is pointed at the space directory and discovers what Claude
Code discovers — CLAUDE.md, `.claude/settings.json` (which wires `contour hook
spec` on `Write|Edit`), and the space's `build-model` and `release-model` skills.
The console does not restate the discipline; it discovers it, because a hand-rolled
system prompt yields an agent that follows whichever of the eight rules its author
remembered, in a second place that drifts.

**The guard keeps denying and the ask-list only asks.** These are not two
implementations of one idea. A `refs/` write must never be approvable — ADR 0012
and the guard itself say no measurement argument justifies rewriting a reference —
and routing it through a dialog makes it something a tired user can click through.
Decisions made in advance stay denials; decisions needing presence become asks.

**A run starts from prose, and marks may seed it.** The space's skills already
self-trigger on their descriptions — `build-model` says it is for *any* model work
or a failing check — so making the user pick a skill first moves a decision from
the agent, which reads it from context, to the user, who has not described the
task yet. It also has no answer for a run that is neither skill: *why is the neck
269 and not 280* is a measurement, not a build loop. Selecting open marks composes
them into the prompt, because marks are the one place the user's intent is already
located, authored and tracked. **A run seeded from marks makes `addressed`
checkable:** the console knows which marks were in scope, so one left unaddressed
at the end of a run is visible rather than silently dropped.

**The ask-list is written in Contour's vocabulary, not in tool globs.** A category
is an intent — a spec write, a commit, a push, a build, a ref write — and the
launcher is asked what a call means, rather than the console pattern-matching the
call's text. A glob is brittle exactly where the stakes are: the gated build is
`./contour check`, `contour check`, a `cd` into the space first, or `contour
render`, which also builds — one intent, four spellings, and a permission list that
needs four rules will still have a hole. A gap in this list is a rule that has
silently stopped being enforced. Semantic categories are also what make decision
10's fail-closed default definable at all: *strictest* means every category gated,
which is finite and checkable, where a glob list can never be known to be complete.
The cost is that the console classifies calls and therefore knows the launcher's
command table — coupling to the one surface in this system that is already
authoritative and already exhaustive.

**`contour canvas` survives, and the page degrades to its host.** Served by the
launcher it is marks-only; served by the console it is the full surface. Keeping
the launcher stdlib-pure means nothing unless the pipeline is fully usable without
the console, and marking is not a nicety — ADR 0018 made the sheet the surface both
parties point at and `marks.json` the tracked record of why two builds differ. If
marking required the venv, the zero-dependency toolkit would lose a capability it
already has, and *clone it, run `selftest`, mark up a sheet* would stop being a
complete story for anyone the toolkit is shared with. The mechanism is one
endpoint: `lib/canvas.py` already serves `/marks`, `/parts.json` and `/mask.png`,
and the page asks its host what it can do rather than assuming. **Two pages sharing
components was rejected as a bundler with a delay** — ADR 0018's own signal that
the scope went wrong. If `canvas.html` outgrows one file, the console's extra views
are served beside it, not bundled into it.

**Every build renders for the page; only a checkpoint renders for the agent.** ADR
0005 rate-limited renders because a sheet entering the conversation costs ~1400
tokens — a cost to the agent's context, not to the render. A sheet going to a page
costs neither, so the panel decision 12 made permanent can be current instead of
labelled stale; labelling was the fix for unavoidable staleness, and this staleness
is avoidable. The agent's budget is untouched: it still may not pull a sheet into
context except at a checkpoint.

**And *checkpoint* keeps its meaning while losing its trigger.** It no longer means
*render now*; it means only *the agent believes it is done, or is stuck* — which is
the part with no mechanical replacement, since green is not the same as finished and
*stuck* has no signal at all. Retiring the word was rejected because it is the
agent's own judgement, and this design keeps the agent's judgements and the user's
authority distinct everywhere else: a mark has an author, `addressed` is not a
close, only the user vetoes. Deleting checkpoint would leave that pairing one-sided.
The cost accepted: four extra Workbench passes and the identity mask on every
build, felt on every gated click, and the lever if it hurts is a lower-resolution
panel render, never a less frequent one.

**Rules 1 and 5 become mechanism-neutral, and the confirm happens once.** A
proposal and a gate are not duplicates: the proposal carries the argument — *depth
measures 620 against a tolerance of 600 ±20* — which no gate can show. The
*confirm* is what duplicates, and a ritual performed twice is one that stops being
read. So the rules keep saying propose → confirm → write, and the confirm is prose
in a terminal and a gate under a console. One rule, true in both places. The
alternative of injecting a console clause at runtime was rejected as contradicting
this ADR's own decision that the console discovers its discipline rather than
restating it: an injected rule lives in the console's source, invisible to anyone
reading `CLAUDE.md`, and diverges the first time a rule changes. **This means
`CLAUDE.md` changes when the console lands** — the concrete route stays in the
`build-model` skill, and the rule says what must hold rather than how.

**A veto lives in its own tracked file, not inside `marks.json`.** Their retention
policies are opposite: ADR 0018 prunes resolved marks older than the last release
tag and leaves the archive to git, which is coherent because a mark gets resolved
and closed. **A veto is never resolved** — it is a fact about a moment, already
true when it happened — so pruning one would delete the only record that something
was prevented, which is why decision 15 tracked it. Two opposite retention rules in
one file means the pruner must tell them apart, and the first bug is that it does
not. Their writers differ too: `marks.json` is written by the agent through `contour
mark` and by the user through the canvas, while a veto is only ever written by the
console at a gate — fewer writers per file matters more now that a run holds a lock.
**`contour check` gains no veto line.** ADR 0018 was careful that marks report one
line when open and nothing at zero; a veto is never open, so a veto line would never
go away, and a status line that is always present is furniture nobody reads.

**A failed build leaves the last good sheet in the panel, labelled.** A red build
produces no geometry, and red is the common state inside a fix loop — so the panel
shows the last successful sheet with its build fingerprint and an explicit
not-current label. This is the job decision 12's labelling was actually for.
**Rendering a partially built scene was rejected as the most dangerous option
available:** it produces a picture of a model that has never existed, in the panel
where every other picture is real, and ADR 0018 rejected pixel pins in exactly these
terms — authoritative while lying. Overlaying the failing check was rejected because
a check knows a number, not a location, so overlays would appear for some failures
and not others and teach the reader to distrust their absence. **And because no
resolution happened, the page says so** — *marks not resolved: last build failed* —
rather than leaving marks silently pending, which would return ADR 0018's window
through a side door as a mark that looks pinned and is not.

**The console reads state by importing `lib/`, and acts by spawning `./contour`.**
`lib/` already has two halves: ten Blender-free modules — `marks`, `anchor`, `mask`,
`span`, `refs`, `paths`, `miniyaml`, `glb`, `agent`, `canvas` — and the `bpy`-bound
`cmd_*`, `kit`, `scene`, `mutants`, `ctx_override` that run inside Blender.
`lib/canvas.py` is already a launcher-side consumer of the first half, and the
console is a second one. ADR 0008 is not breached: its rule is that every *stage*
goes through `contour`, a stage is a Blender run, and reading `marks.json` is not
one. Parsing the files independently was rejected because it puts *what a mark is*
in two places that drift silently, both still parsing the old shape. Growing read
subcommands on the launcher was rejected as new surface with one consumer, a process
spawn per read, for what an import already gives.

**Two properties become load-bearing, and are named here because nothing names them
today.** The Blender-free half of `lib/` must stay stdlib-only — it is today, and a
single pip-installed import there would break `contour` on a bare clone, which is the
whole of decision 4. And the console must never import a `bpy`-bound module. That
split is currently legible only by reading imports; it now deserves a test.

**A veto reaches git with the change it prevented, and the console shows the
exposure.** Tracked is not committed: decision 15 tracked vetoes so they survive a
clean checkout, and an uncommitted one dies exactly as an ignored one would. The
console does not commit them itself — that is rule 5 flat, and decision 18 already
established the console gets no privilege a terminal would not get, including over
its own records. **Nor does it propose a records-only commit at run end**, because
`docs/CONTEXT.md` records that version control bought *a commit fully describes a
model* and *every commit is a state you chose*; a veto-only commit describes no model
state and would have to be skipped past by anyone reading history to understand how
the model got here. Riding along is also semantically right: *I stopped you widening
that tolerance* belongs in the commit where the tolerance did not get widened — a
reason attached to a state, not an event of its own. What the console adds is
visibility, on the page and not in `contour check`: *n vetoes uncommitted*. The
residual risk is stated rather than solved — a `git checkout .` with uncommitted
vetoes loses them, which is already true of `marks.json` and which ADR 0018 accepted.

**The console is its own executable, `contour-console`, beside `contour`.** A
`contour console` subcommand is structurally defensible — the launcher already spawns
a heavy external process it does not link against, via `$BLENDER` — and was rejected
because it hides the install boundary at the exact point someone meets it. Two names
are self-documenting: `contour` needs nothing, `contour-console` needs an
environment, and `README.md`'s promise stays true of the thing that was typed instead
of needing a footnote. It also keeps the process tree honest: `contour-console →
contour → Blender` is the stack decision 4 describes, where `contour → console →
contour → Blender` has the launcher pretending to be a peer of what it launched.
**A pip-installed console was rejected on version drift** — it imports `lib/` and
classifies the launcher's command table, so it is bound to this checkout by design,
and shipping it separately invites a mismatch neither side can detect. And because
the console needs an interpreter `contour` does not, a missing environment must fail
as *no console environment* with the command to create one, not as a traceback about
an import.

**The ask-list is an allow-list with no presets: silence means ask.** The file names
only the categories the user has chosen to let through, and a category the toolkit
knows but the file does not mention is gated. Presets were rejected because a preset's
meaning changes underneath the user: when a later toolkit version adds a gated
category, a file saying `normal` silently denotes a different set and no decision was
ever made about the new thing. Under an allow-list a new category arrives as a gate
that is noticed and then decided — decision 10's fail-closed principle applied to time
instead of to space. Writing down what to *gate* was rejected for the same reason
globs were: a category forgotten is a category running unwatched. **And *the strictest
list* stops needing a definition — it is the empty list**, which is what an
unrecognised space naturally has, so decision 10 needs no preset to name and no
fallback table that could disagree with one. The cost is that a first run gates
everything and is tuned downward, which is the right direction and does mean the first
session is spent writing the file rather than building. Because the file is meaningful
only against the current set of categories, **the console must be able to enumerate
them** — a list that cannot be printed cannot be audited.

**The console shows spend live and records it where the existing accounting can read
it.** `tools/tokens.py` measures per-iteration cost by parsing the Claude Code
transcript for this project; a console run produces no such transcript, so the one
tool serving the second stated priority would go blind in the same change that makes
runs longer and adds a turn per gate. The console has strictly better data than the
transcript ever did — the SDK returns usage per turn, cache reads included — so it
appends that per turn and `tools/tokens.py` learns to read it. The live display has a
second job: a gate that fires often costs a turn of re-explanation every time, and
seeing that cost is what makes decision 30's *tune it downward* an informed act rather
than an irritated one. **A per-run budget that ends the run was rejected on decision
17's symmetry:** silence is not a verdict and neither is a threshold set before the
user knew what the run involved — the console does not decide for the user in either
direction, and with an attended run the stop is the user. A pre-run cost estimate was
rejected outright: it cannot be known, and a wrong one is worse than none.

**The spec is never a memory, and a run is meant to be short.** A gated run is long —
a turn per gate, a report per build — so the harness will compact it, and a compacted
spec is the goalpost moved by the harness rather than by the agent: the same failure ADR
0002 exists to prevent, with nobody to blame. The distinction that makes this
manageable: **tool results are regenerable and the contract is not.** A stale report, an
old build log, a superseded diff all come back by running the command again, so losing
them costs time and nothing else; the spec cannot be re-derived, only re-read. So the
rule is not *do not compact* but *the spec is read from disk, never recalled* — which is
already how the `build-model` skill opens. And because a gate is a natural boundary, a
run that ends at one and starts again never reaches compaction at all, which makes *end
run* worth as much prominence on the page as *continue*. **Ending a run at a context
limit was rejected** for the third appearance of decision 17's objection: a limit the
user did not choose interrupting work they were watching. **Relying on the harness alone
was rejected as the quiet risk** — the agent would keep working against a summary of the
contract while `verify.py` kept reading the real spec from disk, so the build would stay
honest and the agent's understanding would drift: correct output, wrong model of why.

**The console's endpoints are authenticated, and not by locality.** A per-session
secret in the URL the console opens, checked on every request; an explicit bind to
`127.0.0.1`; an `Origin` / `Sec-Fetch-Site` check; and a required JSON content type so
a simple cross-site POST cannot reach a handler at all. *Localhost is private* is false
for a server taking state-changing POSTs — a page on any site can send one without a
preflight, and DNS rebinding defeats a hostname check used alone. The canvas ships
unauthenticated POSTs today and the blast radius is why that was acceptable and is not
now: an unauthenticated mark is noise that gets noticed and deleted, an unauthenticated
*allow* is a spec write or a commit the user did not make, arriving through the one
mechanism built to prevent exactly that. Decision 7 put the ask-list beyond the agent's
reach; an open gate endpoint would let any local process do what the agent was
prevented from doing. A Unix socket would isolate better and is unavailable, because
browsers cannot connect to one and the point is a page. **Because the token belongs in
the server rather than in the console, `contour canvas` gains it too** — a change to
shipped behaviour, and ADR 0018's surface stops resting on trust-by-locality.

**Model content goes to an API, by design, and this ADR is where that is
stated.** Rule 8 is a git boundary: a model space is never pushed, and sharing a
model means `contour export`. Driving an agent over a model space sends its
references and spec to a model provider, which that boundary permits and which
is the user's call. ADR 0018 rejected a published Artifact *as a default*
because it shipped sheets off-machine as a side effect. The console does it as
the deliberate, named purpose of the command, not as a side effect — but it is
not a silent consequence of a UI, and it does not become one.

## Consequences

- **`README.md:12` gains a boundary.** *No virtualenv, no pip install* is still
  true of `./contour` and false of the console, and the README must say which.
- **The console and a terminal agent are peers.** Both drive the same launcher
  over the same space; neither is privileged. Both can write `build.py`, and
  nothing arbitrates that — see `docs/OPEN-QUESTIONS.md`.
- **`spec.yaml` gets prevention back.** With an ask verdict there is no trade to
  make: the write pauses, the diff and the proposed `revision:` bump are visible,
  and ADR 0016's *knowingly* becomes unnecessary rather than accepted.
- **Rules 1 and 5 stop being honour-system.** Rules 3, 4 and 8 were already
  mechanical — the whitelist, the pre-push hook, `contour check`'s revision test
  — and need no user in the loop.
- **A second Python appears, and stays out of the pipeline.** The Agent SDK
  cannot live in Blender's bundled Python (ADR 0010 rejected pip-installing
  there as mutating the app bundle), so it lives above the launcher or nowhere.
- **The gate has a cost when nobody is at the keyboard.** A gated call blocks
  until answered, so an unattended run stalls at the first gate rather than
  proceeding wrongly. That is the intended failure direction and it is still a
  failure.
- **First dependency, first auth, first billing in this toolkit.** Accepted
  deliberately and confined to one layer. If the pipeline ever needs the venv,
  the containment has failed and that is the signal, exactly as a bundler was
  the signal in ADR 0018.

## Rejected

- **Keep answering in prose between commands.** Free, and it is the gap named
  above: an agent that disappears and returns with a claim.
- **Observe-only — a window that watches files change.** Cheap, composes with
  everything ADR 0018 built, and cannot stop anything. Rejected once the pain was
  named as catching a bad decision rather than not knowing what was happening.
- **Observe now, with a seam for driving later.** Rejected as a comfortable lie:
  owning an agent loop changes what the page is, not how it gets its data.
- **The `claude` CLI as a subprocess, streaming JSON.** Genuinely attractive and
  the shape the repo is already built from — a thin launcher orchestrating a fat
  subprocess, zero new dependencies, `subprocess` and `json` already imported.
  Rejected for in-process control: permission callbacks, hooks and session
  objects are the feature here, and driving them through a pipe is a second
  protocol to own.
- **A socket and any agent behind it.** Maximum generality, no user today.
- **The SDK inside `contour`.** One `pip install` and every command — `check`,
  `api`, `spaces`, `selftest` — needs an environment or fails at import.
- **A lazy import inside `contour`.** Better, and still puts a conditional
  dependency in the one file whose job is *there is exactly one sanctioned way to
  run this*, with a `--help` that lists a command which may not work.
- **Gate every tool call**, and **gate every write**. The first is unusable; the
  second gates `build.py`, which is the agent's main job.
- **Gate exactly the eight hard rules.** The curated list already exists and is
  the right default — but it is not tunable, and a released model and a scratch
  space deserve different lists.
- **An ask-list inside the model space.** Agent-writable, and it is ADR 0016's
  `NOTES.md` failure: true, important, in a file nothing verifies.
- **The agent performing its own widening write, gated.** Circular: the
  mechanism authorising a wider list is the list.
- **A space id written into `.contour/project`.** The only thing that survives a
  rename, and rejected because that file is tracked, inside the space and
  agent-writable — letting the agent select which permission set applies to it
  without ever touching a permission file. If rename-durability is wanted, the id
  belongs in `~/.contour` pointing at the path, not in the space pointing at a
  policy.
- **Deep-merging global and per-space lists.** Rejected on readability of the
  result: a merged permission rule can narrow what either file appears to say.
- **Two browser surfaces, one for marks and one for control.** Rejected against
  ADR 0018's central claim that the sheet is the shared surface.
- **Absorbing the canvas upward into the console layer.** Would drag a stdlib,
  in-toolkit page into the dependency layer for no gain; the file is served by
  both instead.
- **A console bound to one run**, exiting when the agent stops. Rejected because
  the page is wanted *between* runs — reading the last report, looking at the
  sheet, leaving marks — and that gap is where marks get made.
- **A console the user must remember to kill.** Rejected as simply accepting ADR
  0018's objection rather than answering it.
- **A gate that lets the user edit the tool call.** Rejected on authorship: the
  change would be the user's and the attribution the agent's.
- **An "always allow this shape" button on the gate.** Rejected because it widens
  permissions at the moment of maximum annoyance, which is when the user is least
  careful about what is being agreed to. Widening stays a deliberate edit to the
  ask-list, which only the console writes.
- **A transcript-primary page with the sheet demoted to a panel.** Argued for on
  rate-of-change grounds and rejected in favour of the equal split; the staleness
  objection is answered by labelling the sheet with its build fingerprint instead.
- **Letting a rebuild discard an in-progress mark**, and **letting an
  in-progress mark block the agent indefinitely**. The first loses stated intent
  silently, which is the failure ADR 0016 exists about; the second is a lock held
  by an unattended text field.
- **Pixel-only marks during a run, anchored later.** Already rejected by ADR 0018
  on migration grounds, and reintroducing it for the live case reintroduces the
  same defect at the moment marks matter most.
- **Recording a denial in the transcript only.** Ephemeral, and it is ADR 0016's
  `NOTES.md` failure in a nicer font: the reasoning dies with the process.
- **Making a denial a mark with no position.** Rejected to protect the word:
  `mark` earns its meaning from having a position, and a position-less one is
  prose with an id.- **Timing a gate out into a denial.** Rejected by symmetry with ADR 0018: if the
  console may not close a finding for the user, it may not refuse a call for them.
- **Timing a gate out into a clean end with a resumable run.** Coherent, and it
  buys a transcript-on-disk and a resume path that an attended-only console does
  not need. Available later if runs stop being attended.
- **Notifying the user and waiting.** Not rejected on the merits; unnecessary once
  a run is attended by definition.- **Letting the console hold the space and lock a terminal out.** Nearly the same
  in practice, and it writes privilege into the launcher to buy what symmetry
  gives for free.
- **Two agents in a space by convention, uncoordinated.** Today's behaviour and
  the hazard open question 11 described. This ADR closes that question.
- **A division of labour between console and terminal by convention.** Enforced by
  the agent's good behaviour, which is the thing this ADR exists to stop relying on.- **A console-defined system prompt and hook set.** Self-contained and explicit,
  and it forks the eight rules into a second copy that drifts from the first.
- **The ask-list replacing the `PreToolUse` guard.** One mechanism instead of two,
  and it converts a hard deny on `refs/` into a dialog — which is a thing a tired
  user clicks through.- **Requiring every run to name a skill.** Makes the console a menu and overrides
  a judgement the agent already makes correctly from the space's own descriptions.
- **An ask-list of tool-and-glob patterns.** Familiar from `settings.json`, and
  brittle in the place that matters: one intent has several spellings, and the
  list can never be shown to be complete.- **Retiring `contour canvas`**, or making it an alias that needs the venv. Both
  walk back decision 4 by moving an existing zero-dependency capability behind an
  install.
- **Two pages sharing components.** Needs a bundler about a week later, which ADR
  0018 named as the signal that the scope has gone wrong.- **Rendering only at checkpoints and labelling the panel stale.** Correct when
  staleness is unavoidable; here it is avoidable.
- **Retiring *checkpoint* because the console shows everything.** It would delete
  the agent's own judgement from a design that keeps that judgement distinct from
  the user's authority in every other place.- **Asking in prose and gating as well.** Defensible — rule 1 already pairs a
  `revision:` counter with a check that fails when it is skipped, so belt-and-braces
  is the habit here. Rejected because both confirms carry identical information.
- **A console clause inside rule 1**, and **an instruction injected by the console
  at runtime.** The first lengthens the file whose length is a design constraint
  (ADR 0008); the second forks the discipline into a place no reader of `CLAUDE.md`
  can see.- **Vetoes as a second collection inside `marks.json`.** One file, two opposite
  retention rules, and a pruner that has to know the difference.
- **Vetoes as entries in a run transcript**, or in one combined history file. Both
  bury a category whose value is being listable: *what have I refused in this space*
  is a question git should be able to answer.- **Rendering a partial scene after a failed build.** A picture of a model that has
  never existed, shown where every other picture is real.
- **Overlaying the failing check on the sheet.** A check knows a number, not a
  location; inconsistent overlays teach distrust of their absence.
- **An empty panel on a red build.** Discards the comparison most wanted — what it
  looked like before this broke — and flickers across a fix loop.
- **The console parsing the space's files itself.** Two answers to *what is a mark*,
  drifting silently.
- **Read subcommands on the launcher for the console's benefit.** New versioned
  surface with a single consumer, and a process spawn per read.- **The console committing vetoes itself.** A commit without approval, and a
  privilege decision 18 declined to give it.
- **A records-only commit at run end.** Degrades the artifact ADR 0007 and ADR 0018
  were protecting: a history that reads as model states with reasons attached.- **`contour console` as a subcommand.** Hides the install boundary behind the one
  command whose promise is that it has no install, and inverts the layering in the
  process tree.
- **The console as a pip-installable package.** It is bound to this checkout by
  design; a separately versioned copy can drift from the toolkit it drives.- **Named presets, in any number.** A preset is a word whose meaning changes when
  the toolkit adds a category, silently and without a decision.
- **A gate-list rather than an allow-list.** A forgotten category runs unwatched,
  which is the hole semantic categories were chosen to close.- **A per-run token or cost budget that ends the run.** The console deciding for the
  user, which decision 17 already refused in the other direction.
- **Spend shown but not recorded.** Blinds `tools/tokens.py` and the second stated
  priority with it.
- **A cost estimate before a run.** Unknowable, and a wrong estimate is worse than
  no estimate.- **Relying on the harness's context management alone.** Silent: the build stays
  correct while the agent's model of the contract drifts.
- **Ending a run when context fills.** A limit the user did not choose, interrupting
  work they were watching.- **Trusting localhost, as the canvas does today.** Acceptable when the worst case is
  a spurious mark; not when it is an approved commit.
- **A Unix domain socket.** Better isolation, and browsers cannot connect to one.
