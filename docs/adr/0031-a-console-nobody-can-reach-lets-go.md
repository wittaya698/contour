# 0031 — A console nobody can reach lets go

**Status:** Proposed · 2026-10-16 · **amends ADR 0027 decisions 6, 7 and 9, and the lobby's row of ADR 0021** ([0027](0027-the-unattended-run.md), [0021](0021-the-lobby.md))

## Context

On the afternoon ADR 0030 was tried (issue 120), a console held `crate` four
times after its person had lost the way into it. Each time the lobby said *open
in a console — its tab is the way in*, `contour stop crate` said *no run to
stop*, and the space was freed only by killing a process on the user's word.

A console's tab closing ends it. That was confirmed the same afternoon: ⌘W on
one ended it at once. A tab left in the background does not: a hidden tab gets
an hour, and a hidden tab at a gate is never ended by silence, on purpose,
because ending it would answer the gate (ADR 0019 decision 17, issue 39). So
the person who switched away has a console they cannot find, and a space it
keeps.

Two things already existed and reached only part of the way:

- ADR 0027 decision 7's signal, which has a console open its own page in this
  machine's browser. The lobby sends it only to a console running an
  unattended run.
- `contour stop`, which ends a console's run (ADR 0027 decision 9). A console
  with no run going holds no lock, so `stop` saw nothing there to end.

## Decision

**1. The way in is given back before anything is ended.** On this machine, the
lobby's row for a space open in a console offers *Open its page* for every
console, not only one running unattended. The console opens its own page with
ADR 0027 decision 7's signal: the URL, which holds its secret, still goes from console to
browser and nowhere else. The person is back on the page, with any gate in
front of them, and answers it or closes the tab as usual. A console on another
host is named, with no action, because this machine cannot signal it.

The connector's `open console` is the same door, so it shows an attended
console's page too. This takes back the line drawn at ADR 0027 decision 6: an
attended console is no longer a page a requester must not bring up. A misused
channel still does no more than ADR 0027 decision 7 already allows. A page appears, and
a gate in it still needs the person's click. A request into a console's space
is still refused (ADR 0027 decision 6), now in words that name both ways back: *Open in
the lobby brings its page back, and `contour stop <space>` closes it.*

**2. `contour stop <space>` ends a console that has no run going.** The console
closes as if its tab had closed, and gives the space back. With a run going,
`stop` ends the run as before (ADR 0027 decision 9), and a second `stop` ends
the console. It is the same function for the command and the connector, in the
same words. Ending an idle console loses nothing: the edits stay in the space,
and approvals stay in its store.

**3. A gate waiting when a run is stopped from outside its page is set aside,
not dropped.** It becomes an approval, exactly as an unattended run's gate does
(ADR 0028 decision 1), and a question becomes a waiting question. The run still
ends. Nobody answered the gate: the person who stopped the run never saw it,
and silence is not a verdict (ADR 0019 decision 17). The call waits on the
console's page for whenever the person next opens it. This amends ADR 0027
decision 9's *it answers no gate: the call never happens* for a stop from
outside. A run ended from its own page is unchanged: the person was looking at
the gate when they ended it, so nothing is kept.

**4. An unattended run's console that nobody opened still ends with its run.**
This is ADR 0027 decision 4, unchanged, and tested. The console seen holding
`crate` after its request had finished had been opened to answer a build, then
left in the background. It was the hidden-tab case that decisions 1 and 2 are
for.

## Consequences

- The lobby never sends a person to a tab they may not have.
- `contour stop` can free any space a console on this machine holds, with one
  call or two.
- Stopping a run at a gate from outside can add an approval. The person meets
  it on the console's page, oldest first, like any other.

## Rejected

- **Refuse `stop` while a gate waits, and say *open its page*.** This is
  stricter, but it leaves the person stuck again whenever the page will not
  open.
- **End a hidden tab at a gate after a longer silence.** That answers the gate
  by silence, which ADR 0019 rules out.
