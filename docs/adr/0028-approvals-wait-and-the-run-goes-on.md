# 0028 — Approvals wait, and the run goes on

**Status:** Accepted, amended · 2026-10-11 · amended by [ADR 0034](0034-questions-are-a-form-the-chat-can-fill.md) (a question is a form a chat may fill; approving it is still the person's, on the page) · **amends ADR 0027 decisions 1, 4, 7, 8, 9 and 12, and its fifth consequence** ([0027](0027-the-unattended-run.md))

> **Accepted on its tracer bullet, with decisions 5 and 6 amended** (issue 100).
> Used by hand on 2026-10-11, from Claude Desktop, in a throwaway space,
> `beaky-0028`, made from beaky-0027's last commit with builds on its ask-list.
>
> - **The run goes on:** asked to make the beak 10% longer, a run edited, built
>   and finished with no page open and no banner. The chat dropped *and save it*
>   from the request, and the agent argued the spec change in its closing rather
>   than trying the write, so nothing was set aside (issue 102).
> - **The floor held against a relayed yes:** the chat's next request read *Yes to
>   the spec change you proposed in the last run, from the user*, against its
>   instructions. The write was set aside, not made. `spec.yaml` stayed at
>   revision 5 until the user allowed it on the page.
> - **Allow applies it later:** allowed on the page at 07:07, the spec went to
>   revision 6, depth 644 ±20, and the check the call ended with passed. Nothing
>   was left waiting.
> - **A save was set aside and denied:** asked to save the version, the run set
>   the commit aside, the chat asked *now or later* and opened nothing, and the
>   user denied it on the page. The veto is recorded. But the save was read as a
>   spec write, because its message mentions `spec.yaml`, so its act, the record
>   and the veto all said so (issue 103).
> - **No console URL** entered the conversation at any point.
>
> **Amended.** The chat broke decision 6's instruction three times: it relayed
> the yes, opened the console twice uninvited, and did not ask *now or later*
> until the ask was carried in the results it reads. Decision 6 now puts the ask
> in `status` and in a refused `request` whenever approvals wait, as well as in
> the instructions, and the instructions no longer invite `open`. Wording does
> not bind a chat, though: what holds is the floor. And the record's closing
> carried the agent's case to the chat, through a field ADR 0027 decision 8
> allowed, so decision 5 now withholds the closing of any run that set something
> aside. The spec write made through the shell showed the page no diff and no
> case (issue 101).
>
> **Not reported:** `status` on a space with nothing waiting, and the lobby's row
> once nothing waits. Both are covered by the suite. Rule 5's new wording,
> proposed in issue 100, was confirmed and is in both `CLAUDE.md` files.

## Context

ADR 0027 was put through its tracer bullet on 2026-10-10 and 2026-10-11, in
`beaky-0027`. Everything it rests on held. With no ceiling, a request was refused.
A run edited and built with no page open. Desktop's `open` brought the page up
and no console URL entered the conversation. A second request, made with the
page open, was refused in the lobby's words. `stop` ended a parked run. The floor
held where it matters most: the chat's last request said *"The user says: save
(commit) the current state now"*, and the save still asked on the page, where the
user answered it.

One part did not survive use. When the run reached a gate it parked, and the
console posted a banner: *beaky-0027 is waiting for you: Claude wants to build
the model to check its work*. The user's verdict: *"I really don't like when it
showed notification and said waiting for me to approve. I think it should show
and move on, and let the connector ask if I want to do those approvals now or
later."* Two findings sharpened it:

- **The banner leads nowhere.** It is posted through `osascript`, so macOS files
  it as Script Editor's, and clicking it opens Script Editor's file picker. No
  standard-library route gives it a click that opens the page.
- **A parked run is a run held hostage.** Everything after the first gate waits on
  the person, so a run asked for overnight does a few minutes' work and then
  nothing until morning, holding the space the whole time.

The connector cannot start a turn in Desktop: it answers when a chat calls a tool,
and never otherwise. So *let the connector ask* means the chat asks when it next
reads the space, not that anything interrupts the person.

## Decision

**1. In an unattended run, a gate the run cannot pass sets the act aside, and the
run goes on.** Nothing parks. The call is not made. It is kept, exactly as the
agent wrote it, as an **approval waiting**, together with what the gate would have
shown: the act in plain words, the diff, and the agent's case for it (rule 1's
argument, the text the gate already takes from `proposal()`). The agent is told the
act was set aside for the person, and that it should carry on with work that does
not depend on it and not try it again another way. An attended run is unchanged:
someone is there, so its gates still wait for them.

**2. A question is set aside the same way.** The agent is told the person will
answer later, and that it should finish what does not depend on the answer and
say in its closing what it could not do without one. Only the person answers it,
on the page, as ADR 0027 decision 12 says. Answering it later starts an attended
run in that console whose first message is the question and the answer, because
nothing resumes. This gives up ADR 0027 decision 12's reason for parking, which was to keep
the run's context over a one-word answer, in exchange for a run that does not stop
dead at its first question.

**3. Approvals are answered on the page, in the order they were set aside, at
whatever time the person chooses.** They are kept in the space's `.contour/`,
git-ignored, so any console opened on the space shows them before it takes a new
prompt. They are not kept in the process, which still exits when its run ends
(ADR 0027, decision 4). Each shows what its gate would have shown. **Allow**
applies the call then, as it was written. **Deny** records a veto, as a gate's deny
does. A call that no longer applies, such as an edit whose old text is gone or a
save with nothing left to save, is not applied. It is shown as *no longer applies*
and dropped, and it is not a veto, because nobody considered it. Order matters
because a save set aside after a spec write should not be answered before it.
Nothing waiting times out: silence is still not a verdict.

**4. No banner.** ADR 0027 decision 7's notification is withdrawn. Reaching the
person no longer depends on a requester relaying anything, because nothing is
blocked while they are away. The work is done, and what needs them stays put until
they look. The channel stays exactly as it was. `open console` and the lobby's
enter still ask the console to show its own page, and they now reach a console
started just to show approvals, when the run has already ended.

**5. The record says how many approvals are waiting and for what, and never
why.** When the run ends, the record says *finished* (or *stopped*) and lists the
acts waiting, in ADR 0025 decision 6's plain words (*Claude wants to change the
spec*, *Claude wants to save this version*), and the text of any question. It never
holds a diff or an argument, for ADR 0027 decision 8's reason. *Waiting for you*
stops being a state a run is in and becomes something a space has: the lobby's row
and Desktop's `status` say *2 approvals waiting* until none are. *Amended
(issue 100):* the closing of a run that set anything aside is withheld from a
requester for good, because it is the case for what waits, and stale once that is
answered. `status` says the account is on the console's page.

**6. The connector's instructions tell a chat to ask, never to answer.** When a
space has approvals waiting, the chat tells the person what they are, in the
record's words, and asks whether to answer them now or later. *Now* is `open`.
*Later* is nothing at all. The chat never answers one, never relays the case for
one, and never puts *the user says yes* into a request. ADR 0027's floor already
makes that last worthless, as the tracer bullet showed. *Amended (issue 100):* the ask
is also carried in every result that says approvals wait, `status` and a refused
`request`, because a chat told once at the start did not keep to it. And
`open` is called only on the person's *now*: the instructions no longer tell a chat
to bring the person to a gate.

**7. A request is refused while approvals wait.** A second run would build on a
tree the person has not approved, and the waiting edits would go stale under it.
The refusal names the way in: *beaky has 2 approvals waiting; open its console to
answer them.* A stop does not answer them, and neither does the ceiling. Both still
end the run, and what was set aside stays waiting.

**8. Unchanged:** the floor (ADR 0027, decision 10) and why it holds with the page
open (ADR 0027, decision 11); the ceiling (13); a requester never answering anything (2); a
request being prose alone (5); refusal while a console is open (6); the record
being a status, not a history (8); and stop (9), except that a run no longer parks
for it to interrupt.

## Consequences

- **An unattended run does all the work it can.** A run asked for overnight edits,
  builds, checks and argues its proposals, then waits only for decisions. The cost
  is work that depends on an approval, such as rebuilding against a new depth:
  that waits for the next run, and the closing says so.
- **The same edit's case is read hours after it was made.** The argument and the
  diff are kept with the approval, so what the person reads is what the gate would
  have shown then. The panel is current once the console is opened, as for any
  console.
- **Rule 5, in a space's `CLAUDE.md` and the toolkit's, needs new words.** *Under a
  console the panel is already current* is true once someone has opened the
  console, and for an unattended run's save that is when the person answers it,
  not when the run made it. The words are proposed in this ADR's acceptance.
- **The Script Editor finding goes away with the banner** rather than being fixed.
- **`notify.py` and its hatch go,** along with the tests that pin what a banner
  says.
- **Approval state exists on disk,** beside the run record. Like the record, it is
  per space and git-ignored. Unlike the record, it holds the call and the diff, so
  the survey and the connector never read it. Only a console does. An agent with a
  shell could read it, as it could read the console's secret (ADR 0027's last
  consequence).

## Rejected

- **Keeping the park and dropping only the banner.** It answers the click finding
  and leaves the hostage one. A run overnight still stops at its first gate.
- **A banner the user can turn off.** It is the smallest change and leaves the
  run parked. The user's complaint was being waited on, not only being told.
- **A dialog with a Show button.** It gives the banner somewhere to go, but
  dialogs pile up on a machine left alone and interrupt whatever is in front of
  the person.
- **A notifier app bundled with the toolkit.** It is a signed bundle to build and
  install, against the bare-clone, standard-library launcher (ADR 0024,
  decision 1).
- **Pushing a message into Desktop.** MCP over stdio has no way for a server to
  start a chat turn, and a chat that interrupted the person would be the banner
  again.
- **Applying approvals in any order the person likes.** A save answered before the
  spec write it follows would save a version without it, and the page would show a
  diff that is not what gets saved.
- **Letting a second request run past waiting approvals.** Its edits would make
  the waiting ones stale or wrong, and the person would approve against a tree that
  had moved.
- **Answering a waiting question by resuming the original run.** Nothing resumes
  (ADR 0019 decision 17, ADR 0027 decision 8), and keeping a process alive
  indefinitely for one is the park under another name.
