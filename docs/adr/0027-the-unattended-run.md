# 0027 — The unattended run: a request, a channel, and a gate nobody else can answer

**Status:** Proposed · 2026-10-09 · **amends ADR 0019 decisions 11, 17 and 37, and ADR 0024 decisions 2, 3 and 4 and its first consequence** ([0019](0019-console-a-driven-agent-behind-a-gate.md), [0024](0024-the-connector-desktop-reads-and-opens.md))

> **To be accepted on a tracer bullet**, in a throwaway space. With no ceiling
> set, a request is refused. With one set, Claude Desktop requests *make the beak
> 10% longer*. The run edits and builds with no page open and parks at *save this
> version*, and the notification fires. Desktop's `status` reads *waiting for you:
> save this version* and shows no diff. Desktop's `open` brings the page up, and
> no console URL appears anywhere in the conversation. The user denies; the veto
> is recorded and the run finishes. A second request, made while that page is
> open, is refused in the lobby's words.

## Context

Every run so far has a person standing at it. ADR 0019 decision 17 made that the
definition: *"a run is attended by definition… no run state on disk, no resume, no
notification path. The console is an instrument someone is holding."* The
connector lets an agent read a space and open its pages, and nothing else (ADR
0024 decision 2).

Wanted, decided in a grilling session on 2026-10-09: an agent on this machine, or
the user from a chat, can ask a space for work and come back for the result, with
nobody watching while it happens. Every approval stays a person's: a spec write, a
reference write and saving a version are signed by a human and by nothing else.
When a person is needed, the agent that asked can bring them to the page, but it
cannot sign for them.

Three facts, read from the code on 2026-10-09, shape it:

- **A console's life is its page's.** `console/server.py` ends it when the page
  closes, when it has been idle too long, or when the process that launched it is
  gone. A pending gate suppresses only the idle clock. A console with no page would
  end at the first of these and take its run with it.
- **The console's URL is the key.** It carries the per-session secret that every
  gate's *Allow* is checked against (ADR 0019 decision 39). The connector never
  sees it, and that is stated as the reason the secret never enters a conversation
  with an agent (ADR 0024 decision 5).
- **Nothing outside a console's process knows what its run is doing.** The
  transcript lives in that process. `last-build.json` holds the last check's
  verdict, and `spend.jsonl` holds the cost per turn, but no file says *running*,
  *waiting* or *finished*.

## Decision

**1. An *unattended run* is a run that nobody is watching, and its gates are as
attended as ever.** The agent edits, builds and checks on its own, and every gated
call parks until a person answers it. The run may be unattended; a gate never is.
It is not the agent settling its own doubts: a by-eye agent span still argues
nothing until the user has answered it (rule 1).

**2. A *requester* is on this machine.** That means an agent here, or the user. A
requester asks for runs and reads their results. It never answers a gate or a
question, even when it is an agent the user trusts. A requester on another machine
needs a listening endpoint, a stable port and a stored credential, which ADR 0021
decision 3 holds back until a real consumer exists. That is open question 15.

**3. The backend is a console that nobody has opened yet, not a new process.** A
request starts `contour-console` in the space, detached and with no browser. Its
gates, ask-list, vetoes, hold, presence and spend are the console's own, so none of
them is written twice. There is no daemon and no queue: one request is one run in
one space, and a space already held refuses it, in the words `contour check`
uses. A requester with five things to do sequences them itself.

**4. An unattended console lives as long as its run, not its page.** ADR 0019
decision 11 ended a console when its page said done. With no page, the run's end
is the end: when the run finishes or is stopped and no page is open, the process
exits. If a page is open by then, the console falls back to the page's rule and
ends when that page closes. A parked gate keeps the process alive indefinitely, as
a pending gate already suspends the idle clock.

**5. A request goes through the command line, and the connector wraps it.**
`contour request <space> "<prose>"` prints JSON: started, or why not. It is the
contract (ADR 0021 decision 3). The connector gains `request` with the same
arguments, and `stop` (decision 9). That takes ADR 0024 decision 3's eight tools to
ten. Folding `stop` into `request` would save one definition, but a tool that both
starts and stops runs is one an agent will call wrongly. **A request is prose and
nothing else.** It carries no spec change and no reference; those stay gated calls
inside the run, so asking for something is never the same as approving it.

**6. A request is refused while a console is open on the space.** A console with a
page is a person's workspace, and a requester does not start work in it. The
refusal is the lobby's and the connector's existing one: *already open in a
console; its tab is the way in.* The person types the request into that page
themselves, and it is an ordinary attended run.

**7. A *channel* is a pointer, never a key.** When a requester needs to bring the
person to a parked gate, it asks Contour to show them the page. That is the
connector's `open console` or the lobby's enter, now reaching a console that is
running unattended. Contour asks the console to open its
own page, and the request carries nothing. The console opens its URL in this
machine's browser itself, so the secret goes from console to browser and never
passes through an agent. A requester that misuses a channel can make a page appear
on the screen, where the gate still needs a person's click. **When a gate parks,
the console also posts a system notification of its own.** It names the space and
the act in plain words and holds no link, so reaching the person never depends on
the requester bothering to relay anything.

**8. A space records its latest run, and a requester reads it.** The console
writes one record per space in `.contour/`, git-ignored, holding the newest run
only. It holds the request's prose and who asked (as the requester described
itself), and a state: *running*; *waiting for you*, with the act in ADR 0025
decision 6's plain words (*Claude wants to save this version*), or the text of a
parked question; *finished*; or *stopped*, and why. At the end it adds the verdict
(read from `last-build.json`, not copied), the agent's closing message, the spend
and the vetoes. The connector's `status` returns it, and the launcher gains the same read, as
JSON, for a requester without MCP. It
is a status, not a history, and nothing resumes from it, so ADR 0019 decision 17's
*no resume* stands. **It never holds a gate's diff or the argument behind it.**
Rule 1 says the proposal is the argument and a gate is a confirm. A requester that
saw *depth 600 → 640* without the span would argue it in chat, and the person would
approve on an agent's summary. The case for a change is made on the page.

**9. A parked gate waits indefinitely, and anyone but the run's agent may stop the
run.** This is ADR 0019 decision 17 kept: silence is not a verdict. *Stop* is
available from the page, from `contour stop <space>`, and to the requester for its
own request. It answers no gate: the call never happens, the run ends, and the
edits made so far stay uncommitted in the space for the person to look at. The
hold's refusal to anyone else names the reason and the way in: *beaky is waiting
for you: Claude wants to change the spec.*

**10. In an unattended run, a spec write, a reference write and saving a version
always gate, whatever the ask-list says.** The ask-list is the user's, and they may
loosen it by hand (ADR 0019 decision 5). But rules 1 and 5 depend on a person
having seen the argument and the sheet, and in an unattended run nobody has seen
anything yet, so no list entry can stand in for that person. Builds and edits
follow the list as usual. Push is never possible from a space (rule 8).

**11. A run is unattended because of how it started, and stays so to the end.**
Opening the page mid-run does not lift decision 10's floor. An open tab is
presence, not attention: ADR 0021 says presence stops nothing, and ADR 0019
decision 11 has an idle timeout because of the tab left open on Friday. A floor
that lifted whenever a tab was open would disappear exactly when the person had
walked away from one. The page says so: *this run was asked for by `<requester>`;
some actions always ask you.*

**12. A question from the agent parks the run, and only the person answers it, on
the page.** It is shown as *waiting for you: Claude has a question*. The requester
may read the question in the run record and relay it, but it never answers,
because an answer becomes intent. *The anchor is 300 mm*, given by an agent,
reaches a spec write whose gate shows the diff and not where the number came from,
and rule 1 says scale needs an anchor the user gives. Ending the run on a question
instead would throw away its working context over a one-word answer, since nothing
resumes.

**13. An unattended run's cost is bounded by a ceiling the user sets beforehand.**
It is in weighted tokens, the unit `tools/tokens.py` and the spend line already
use, and lives in `~/.contour` beside the ask-list, out of the agent's and the
requester's reach for ADR 0019 decision 6's reason. Reaching it is decision 9's
stop: no gate is answered, the edits stay, and the record says *stopped: reached
your limit of N*. **There is no default.** With no ceiling set, an unattended run
is refused, so the user's first one makes them choose a number instead of Contour
choosing one for them. This amends ADR 0019 decision 37 on its own reasoning: that
decision rejected a per-run budget because *"with an attended run the stop is the
user"*. With nobody there, the stop has to be a decision the user made in advance.

## Consequences

- **A chat can now be the cause of a build.** ADR 0024's first consequence (*a
  Desktop chat can never be the cause of a build, a spec write or a commit*) holds
  for spec writes and commits, which are floor gates, and no longer for builds,
  which pass the user's own ask-list.
- **The connector's instructions change.** *It reads and opens and changes
  nothing* stops being true. The connector now reads, opens and asks for runs; it
  never answers a gate or a question; and it sends the person to the page with
  `open`.
- **Run state exists on disk for the first time.** It is one record per space,
  overwritten by the next run. It is not a transcript, and it is not resumable.
- **An unattended run sends a space's references and spec to a model provider with
  nobody watching.** ADR 0019 decision 40 permits this as the owner's call. Here the
  owner makes that call by setting a ceiling and by registering the connector; a
  requester on another machine would make it someone else's, which is one reason
  open question 15 is open.
- **Rule 5's *under a console the panel is already current* does not hold
  unattended.** Decision 10 is what makes that safe; the `CLAUDE.md` wording should
  say so when this is accepted.
- **The run record joins the survey,** as a space seen from outside it: the lobby's
  row can say *waiting for you*.
- **One machine cannot make a key unreachable.** An agent with a shell, running as
  the user, could dig the secret out of the console's process or files. As with ADR
  0019 decision 6, the design makes approving stop being a plausible act and become
  a deliberate break-in. A second factor only a person can give (Touch ID, say) is
  the upgrade if that ever needs to be impossible rather than implausible.

## Rejected

- **A remote requester now.** No consumer, and it needs a listening port, a stored
  credential and a daemon (open question 15).
- **A long-lived daemon above all spaces, with a queue.** It would duplicate or
  call into every rule the console already holds. A daemon was already rejected
  twice, as *a thing to remember to kill* (ADR 0018, ADR 0019 decision 11).
- **The relayed link as the key, short-lived and single-use.** Once is enough to
  approve a commit.
- **A second factor on every gate.** It is the strongest option, and it is new
  machinery for a threat this machine's other boundaries already accept.
- **A requester that answers the agent's questions.** Answers become intent, and
  the gate that follows cannot show whose intent it was.
- **The requester sees the full transcript, or the gate's diff.** Then the case for
  a change would be argued in chat, away from the span.
- **A parked gate that times out**, into *stopped* or into a deny. A limit the user
  did not choose ends work on their behalf; a deny is silence as a verdict (ADR
  0019 decision 17).
- **Lifting the floor while a page is open**, or once the person answers a gate.
  Both confuse presence with attention.
- **A separate ask-list for unattended runs.** A second permission file that can
  drift from the first, where three fixed categories say the same thing.
- **A ceiling the requester sets per request.** The party asking for the work would
  control what it costs.
- **A default ceiling.** That would be Contour choosing a number for the user.
