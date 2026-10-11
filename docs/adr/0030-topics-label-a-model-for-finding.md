# 0030 — Topics label a model for finding, and leave only in a release

**Status:** Proposed · 2026-10-11 · **adds to the acts [ADR 0028](0028-approvals-wait-and-the-run-goes-on.md) sets aside, and to what a [ADR 0013](0013-releases-are-versioned-folders.md) release contains**

## Context

Seven spaces exist and the lobby lists them by name only. The user wants every
model to carry arbitrary words — *creature*, *low-poly*, *forest* — that an
agent proposes and the user approves, so that both can filter by them.

The obvious word was *tag*, and it was already taken: a **release tag** is a git
tag, and as of the same conversation it is `v<N>` and nothing else (ADR 0013,
amended). A word that labels the model and a word that marks a point in its
history would be confused the first time someone said *tag beaky*. These are
**topics**.

Three things a topic could have been, and is not:

- **Intent.** An agent reading *chibi* could argue a head should be 50% of
  height against a span that says 38%. Rule 1 already says a number with no span
  behind it is not an argument; a topic would be a way round it.
- **Part of the spec.** Every relabel would be a propose → confirm write
  bumping `revision:`, for a change that alters no geometry.
- **A set.** A pack of models that belong together is, until something acts on
  the group, models sharing a topic.

## Decision

1. **A topic is a free word for finding a model, and nothing else.** It steers no
   build and argues for no spec change. It is not in `spec.yaml`; it is a tracked
   record in the space, and reaches git with the next save, like `marks.json`.
2. **The agent proposes, the user approves word by word.** The user may add or
   strike a topic directly with no gate: the approval is a check on the agent,
   not on the user.
3. **Reuse before growth.** A proposal reads the topics every space already
   carries, reuses a word wherever one fits, and names any word no model has yet
   as *new*. A filter only finds what was spelled the same; an agent proposing
   on different days drifts into *creature* / *creatures* / *fauna* unless
   reuse is the default and growth is visible.
4. **When.** The agent proposes once unprompted, at the model's first green
   build, and after that only when asked.
5. **A struck word is remembered against that model** and never proposed for it
   again. It is not a **veto**: it refuses a word, not a call, and asks no why.
6. **An unanswered proposal is an approval waiting** (ADR 0028), and blocks a
   new request to its space until answered, like a spec write.
7. **Spaces made before topics are labelled by one lobby act**, which reads each
   unlabelled model's last sheet and proposes for all of them together. It is not
   a **run** — it edits and builds nothing — so ADR 0027's *one request, one run,
   one space* is untouched. Done as one run per space, each would propose against
   an empty vocabulary and the reuse rule would mean nothing.
8. **Across spaces, a filter answers with space names and approved topics
   only** — to an agent, to the connector, to the lobby. Never a spec, a
   reference or a sheet: reading the vocabulary is not one space reading another.
9. **Topics leave Contour only inside a release.** The `.glb` in `release/v<N>/`
   carries the topics as they stood when it was released, as glTF `extras`, and
   keeps them. A working `contour export` carries none. Changing a topic never
   forces a release and never turns a check red.

## Consequences

- Words written into a released `.glb` cannot be recalled from whoever was
  handed it. Decision 9 limits that to moments the user already approved.
- Starting the lobby pass blocks every unlabelled space for requests until its
  proposal is answered. They are answered on one page, so the wait is short, but
  an unattended request in the meantime is refused.
- A topic proposal pending in a space holds up modelling work it has nothing to
  do with. Chosen over a non-blocking queue for one rule about what waits.
- No hierarchy and no fixed list. If filtering needs *bird* to find under
  *animal*, that is a later decision, made from the words actually in use.

## Rejected

- **A topic steers choices the spec leaves open.** Withdrawn before it was
  decided: the user wants topics for finding, and a label with any authority
  over the build is one more way past rule 1.
- **Topics in the spec.** A contract change for a label, gated and revisioned.
- **Every export carries topics.** A working `.glb` handed over mid-work would
  ship words nobody approved for release. Adding them later to every export is
  easy; recalling them is not.
- **Topics stay inside Contour.** Simplest, but the user wants the engine to see
  them, and a release is already the moment the user approves what leaves.
- **A topic proposal never blocks.** Kept a label from stalling work, at the
  cost of a second kind of waiting beside approvals. The user chose one.
- **One run per space for the backfill.** Keeps ADR 0027's rule literal and
  defeats decision 3.
- **A struck topic as a veto, with a reason.** Treats a label like a spec
  decision.
- **A set as its own concept.** Nothing acts on a group yet; a set designed
  before that need would be designed blind.
