# 0030 — Topics label a model for finding, and leave only in a release

**Status:** Accepted, amended · 2026-10-16 · **adds to the acts [ADR 0028](0028-approvals-wait-and-the-run-goes-on.md) sets aside, and to what a [ADR 0013](0013-releases-are-versioned-folders.md) release contains**

> **Accepted on its tracer bullet, with decisions 4 and 6 amended** (issue 120).
> Used by hand on 2026-10-16, in throwaway copies of the seven spaces in
> `project/` and a new space, `crate`, with the user's own ask-list.
>
> - **The lobby pass:** four cards — beaky, beaky-fable, beaky-lite,
>   beaky-solo — and three skipped with their reasons: beaky-0028 because
>   approvals already waited in it, beaky-test-2 and trail-cube for having no
>   sheet. Answered on the page, `colored` struck on beaky. The first click's
>   act died having set nothing aside, and the page said nothing; the second
>   worked. The cause was not seen.
> - **One spelling:** thirteen words after the pass, none a variant of
>   another, five carried by all four. A later proposal for `crate` reused four
>   of them and kept away from *character* and *toy* on purpose.
> - **The filter:** asked *which models are creatures?*, Desktop answered from
>   topics — none labelled *creature*, four by *bird* and *character*, the
>   struck word left out — and *low poly* with beaky-lite alone. Against
>   spaces with no topics it had read six specs instead.
> - **The first green did not propose.** The ask-list asks before builds, so
>   the unattended run set its build aside. Allowed on the page, the check went
>   green with no agent to read *propose topics*, and stamped the first green
>   anyway: no proposal, and none would ever come unprompted. Decision 4 is
>   amended for it.
> - **A waiting proposal blocked a request,** with its reason, and the request
>   started once it was answered. The user's verdict: *just in the way.*
>   Decision 6 is amended for it.
> - **A struck word stayed struck:** asked again, the agent proposed *box,
>   cube, storage, web*, and not *bevelled*. It never tried it, so the
>   backstop was not exercised. *web* is the spec's export target: a proposal
>   can borrow a field that describes nothing.
> - **The release** `crate` v1 carries its twelve topics as root `extras`; the
>   working export beside it carries none, and the geometry is the same.

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
   build, and after that only when asked. *Amended (issue 121):* a first green
   that comes from an approved check, with no agent there to read it, sets the
   proposal's ask aside in the space for the next run to make, rather than
   telling it to nobody. Under an ask-list that asks before builds, every
   unattended first green comes that way.
5. **A struck word is remembered against that model** and never proposed for it
   again. It is not a **veto**: it refuses a word, not a call, and asks no why.
6. **An unanswered proposal is an approval waiting** (ADR 0028), and blocks a
   new request to its space until answered, like a spec write. *Amended (issue
   122):* it waits, and blocks nothing. A request starts with a proposal
   waiting, and the person answers it whenever they open the space. Tried on
   `crate`, the block held up *make the slats thicker* for a label that had
   nothing to do with it, and the user found it in the way.
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
- ~~Starting the lobby pass blocks every unlabelled space for requests until its
  proposal is answered.~~ *Amended (issue 122):* it blocks nothing; a request
  runs beside a proposal waiting.
- ~~A topic proposal pending in a space holds up modelling work it has nothing to
  do with.~~ *Amended (issue 122):* the cost taken instead is the one this ADR
  first rejected — two kinds of waiting, an approval that blocks and a proposal
  that does not — chosen on the tracer bullet's evidence.
- A space with approvals waiting is skipped by the lobby pass (decision 7), and
  stays unlabelled until they are answered and the pass is started again:
  beaky-0028 did.
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
  *Reversed on acceptance (issue 122):* tried, the block was in the way.
- **One run per space for the backfill.** Keeps ADR 0027's rule literal and
  defeats decision 3.
- **A struck topic as a veto, with a reason.** Treats a label like a spec
  decision.
- **A set as its own concept.** Nothing acts on a group yet; a set designed
  before that need would be designed blind.
