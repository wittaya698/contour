# 08 — A gated run, end to end

**Type:** AFK · **Source:** ADR 0019 decisions 1, 3, 13, 17, 20

## What to build

The heart of the design, and the reason the slices before it exist. Prose in, a
driven agent, every call gated, a transcript on the page.

**The console owns the agent loop** through the Claude Agent SDK, and drives
rather than observes. A passive window would have made marks the only intervention
channel, and marks are deliberately asynchronous; driving is the opposite bet —
that being present at the moment a decision is made is what was missing.

**It is a control surface, not a progress bar.** Tailing the log and refreshing
the sheet would be nearly free and would answer *what is it doing*. It does not
answer *stop*. The gate is the feature; the progress view is the by-product.

**The agent inherits the space's configuration.** The SDK is pointed at the space
directory and discovers what Claude Code discovers — `CLAUDE.md`, the space's
`.claude/settings.json` and its skills. The console does not restate the
discipline, because a hand-rolled system prompt yields an agent that follows
whichever rules its author remembered, in a second place that drifts.

**A gate offers allow and deny-with-a-reason,** and the reason goes back as the
tool result — the cheapest correction channel in the system: a sentence, at the
moment it applies, instead of a paragraph after the fact.

**A gate deliberately cannot edit the call.** Editing it would make the user the
author of a change attributed to the agent, in the commit and in every later
reading of why two builds differ. The user says a sentence; the agent writes the
code.

**A gate waits indefinitely,** and the console never answers one on the user's
behalf in either direction. Silence is not a verdict. The practical case is worse
than the principled one: a refused agent works around the refusal, so an
unattended run would spend its time productively doing the wrong thing. **A
pending gate suppresses the idle timeout** — otherwise slice 06's lifetime rule
ends the run at an unanswered gate and quietly becomes the timeout policy this
rejects.

**The guard keeps denying and the ask-list only asks.** A `refs/` write must never
be approvable; routing it through a dialog makes it something a tired user can
click through. Decisions made in advance stay denials; decisions needing presence
become asks.

**A run starts from prose.** The space's skills self-trigger on their
descriptions, so making the user pick one first moves a decision from the agent,
which reads it from context, to the user, who has not described the task yet. It
also has no answer for a run that is neither skill.

**The spec is read from disk, never recalled.** A gated run is long and the
harness will compact it, and a compacted spec is the goalpost moved by the harness
rather than by the agent. Tool results are regenerable and the contract is not: a
stale report or an old build log comes back by running the command again, while
the spec can only be re-read. A run that ends at a gate and starts again never
reaches compaction at all, which is why **end run** gets as much prominence on the
page as continue.

**A context limit does not end the run,** for the same reason a timeout does not:
a limit the user did not choose interrupting work they were watching.

Because the default ask-list is empty, the first working version gates everything.
That is the designed starting point, not a stub — there is no merged state in
which a driven agent can commit unwatched.

## Acceptance criteria

- [x] A prose prompt starts a run and the transcript streams to the page
- [x] Every classified call raises a gate; allow proceeds, deny returns the reason as the tool result
- [x] A denied agent visibly receives the sentence and responds to it
- [x] The gate dialog offers no way to edit the call
- [x] An unanswered gate blocks forever and the idle timeout does not fire
- [x] A `refs/` write is denied by the existing guard and never appears as a gate
- [x] The agent demonstrably discovered the space's `CLAUDE.md` and skills, with no restated rules in the console's source
- [x] **End run** is as prominent as continue
- [x] The run holds slice 02's lock; a terminal `contour check` during a run is refused
- [x] Model content reaching the API is the named purpose of the command, stated where the user starts a run
- [x] A run that reaches a context limit continues

## Blocked by

- [05 — The ask-list is read, and silence means ask](05-ask-list-silence-means-ask.md)
- [06 — `contour-console` exists and serves the page](06-contour-console-serves-the-page.md)
