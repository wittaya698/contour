# 46 — The proposal names its spans

**Type:** HITL · **Source:** ADR 0022 decisions 6, 7, 9 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

The mechanisms exist after slices 40–45. This slice changes what the agent is
told, which is the part that makes *measure, never recall* checkable.

**Rule 1 gains its clause.** The wording the user approved on 2026-09-30, recorded
in ADR 0022:

> A measurement read off a reference is a **span** — the user's, or an agent
> span — and the proposal names it. A number from a reference with no span
> behind it is not an argument, and a by-eye agent span argues nothing until the
> user has answered it.

It goes into the toolkit's `CLAUDE.md` and the space template together.

**The two skills say how.** Drafting a spec, and arguing a revision, both change:
- every number from a reference names its source: a span by id, the user, or
  *not measurable*, said plainly;
- a number from an unanswered **snapped** agent span is listed as the agent's
  own reading;
- a number from an unanswered **by eye** span is not proposed;
- the agent draws its spans with `contour measure`, which the new-space skill
  does not name today;
- the agent looks at the **worksheet** once, at the **checkpoint** where it
  believes its reading is finished, before proposing.

**Three stale examples are settled.** Rule 1, the new-space skill and the
build-model skill each use `beaky`'s depth of 620 as a worked example. ADR 0017
measured it at 597 and found the conclusion drawn from it inverted. The
build-model skill states that conclusion as fact: *the build was right and the
contract was not*. No verified case of a measurement showing a spec wrong is on
record to replace it, so the user decides: a real case, or wording that is
plainly an illustration.

**HITL because** it changes a hard rule, and because the template change puts
every existing space into drift until it is refreshed, in each space's own
repository, under rule 5.

## Acceptance criteria

- [x] Rule 1 carries the approved clause, in the toolkit's `CLAUDE.md` and in the space template, identically
- [x] The new-space skill and the build-model skill state the three sources, the two span rules, and the worksheet checkpoint
- [x] The new-space skill names `contour measure` as how a reference is measured
- [x] No skill or rule states that `beaky`'s reference depth is 620, or that its contract was wrong about depth
- [x] The user chose the replacement for the 620 example
- [ ] `contour doctor` reports the drift in each existing space, and each is refreshed only on the user's say

## What it came to

- Rule 1 carries the clause, word for word, in the toolkit's `CLAUDE.md` and the
  space template, after the sentence on gates. `tests/test_rule_one_spans.py`
  holds both to the wording ADR 0022 records.
- The user chose wording that is plainly an illustration over a real case,
  since none is on record (2026-10-03). Rule 1's example is now *depth reads
  640 mm ±3 on span m4, against a tolerance of 600 ±20*, and the two skills use
  the same numbers. Nothing names `beaky`, or says its contract was wrong.
- The new-space skill names `contour measure` with a snapped example of each
  kind and the by-eye spelling, then the three sources, the two span rules with
  `--standing`, and the worksheet checkpoint. The build-model skill says the
  same for arguing a revision.
- The space template's command table gains `contour measure` and
  `contour worksheet`, the second held back from slice 45.
- `contour doctor` reports `CLAUDE.md` and the build-model skill as drift in all
  six spaces. Four also had older drift in `.claude/settings.json`, and `beaky`
  in its release-model skill. No space has been refreshed: each is a commit in
  that space's own repository, waiting on the user.

## Blocked by

- [44](44-a-by-eye-agent-span.md)
- [45](45-contour-worksheet.md)
