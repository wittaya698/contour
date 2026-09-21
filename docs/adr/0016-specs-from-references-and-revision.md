# 0016 — Specs drawn from references, and revised under a counter

**Status:** Accepted · 2026-09-21 · **amends [ADR 0002](0002-spec-is-agent-read-only-contract.md), reopens one rejection in [ADR 0013](0013-releases-are-versioned-folders.md) · worked example corrected by [ADR 0017](0017-scaffold-measured-from-references.md)**

> **The depth example below is wrong, found 2026-09-21 by measuring it
> mechanically.** `refs/side.jpg` gives **597 mm**, not "about 620". The spec's
> `depth: 600 ±20` matches the references within 3 mm — it is very nearly the
> best number available — and the build's 612 is what drifted. So the
> conclusion "the contract is what is wrong" is inverted.
>
> **The decision this ADR makes stands unchanged**, and one part of it is
> strengthened rather than weakened. Tolerance conflating measurement error with
> intent, the `revision:` counter, propose-confirm-write, never-from-red, and
> *measure the image, do not recall it* are all untouched — a spec still needs a
> sanctioned way to be corrected, and `beaky`'s depth now turns out to need one
> *less* than this ADR believed. What the example actually demonstrates, better
> than it meant to, is this ADR's own last consequence: **nothing measures a
> reference image.** The number that motivated the argument was produced by the
> instrument the argument was written to distrust. ADR 0017 builds the
> instrument.

## Context

The request: hand the agent a set of reference photographs and have it draw up
a spec to propose. Half of that already exists — ADR 0002 was amended so a
*new* spec may be drafted, and `new-space` step 4 saves the references first,
then lists back every number the agent chose. `beaky` was built exactly this
way, from four images in `refs/`.

So the question is not whether the agent may draft from pictures. It is what
happens afterwards, and `beaky` is a complete record of that.

**Drafting from pictures produced wrong numbers, three times.** Its `NOTES.md`
records each correction: the legs were called bowed and are straight; the dark
outlines on every part were read as geometry and are a toon render pass; the
beak was called too long when it was too thin. All three were claims made by
eye. All three were corrected only by measuring the image in pixels against a
known dimension. The file states the lesson three times — *measure the image,
do not recall it.*

**One wrong number cannot be corrected at all.** The spec says
`depth: 600 ±20`. Measured properly on 2026-09-20, `refs/side.jpg` gives about
620 mm. *(Corrected 2026-09-21: it gives 597 mm. See the note at the head of
this file — the premise of this paragraph does not hold.)* The build sits at 612, passing, on 60% of a tolerance the agent
invented rather than the user. `NOTES.md` open question 1 concludes: *"There is
no change to `build.py` that improves this."* The contract is what is wrong,
and rule 1 freezes it. The defect is recorded, permanently, in the one file
nothing verifies.

**The tolerance was doing two jobs at once.** How well the photograph was
measured, and how far the build may stray from intent, are different
quantities. `±20` was sized to cover the agent's own uncertainty and then read
by everything downstream as a statement of intent. That conflation is what
made a number nobody could judge.

**The mechanical position, read 2026-09-21.** `TOP` in `verify.py` is a closed
set, so any new spec key fails `check_spec`. Three commands load a spec
(`cmd_build`, `cmd_render`, `cmd_roundtrip`) and each reads only the keys it
wants, so none would notice one more. `tools/guards/spec.py` is binary —
tracked denies, untracked allows — and is wired on `Write|Edit`. A space has
exactly one git hook, the pre-push stub, which refuses unconditionally.

**`report.json` cannot answer "was the last check red?"** `write_report` is
called by *every* command into one file, carrying no command name and no
timestamp. `beaky`'s copy on 2026-09-21 held the residue of an `api` lookup:
`{"ok": true, ...}`. Rule 7 actively encourages `contour api`, so routine work
erases the record of a failure.

## Decision

**Pictures carry proportion, never scale.** The user states one real-world
dimension per reference set — the *anchor*. Every other size is a pixel ratio
against it. Without an anchor the agent does not draft `dimensions` at all; it
asks. A guessed scale is uniformly wrong across every dimension, so verify goes
green on a model that is the wrong size throughout, and only the human at the
gate would catch it.

**A measured number is proposed with its error bar.** The agent computes
mm-per-pixel from the anchor and states the precision beside the number it
justifies. `depth 620 ±6 measured, proposing tol 15` is something the user can
push back on; `tol: 20` alone is not. This is the disclosure ADR 0002 already
demands, made checkable: a `tol` tighter than the error bar reads as a claim,
and a looser one reads as padding.

**`tol` expresses intent, not measurement error.** The two quantities are named
separately in the proposal even though only one reaches the spec.

**A tracked `spec.yaml` may be revised, on the user's explicit confirmation.**
Rule 1 changes from *never write* to *propose, confirm, then write*. This is
the gate rule 5 already uses for the other irreversible act, commits, which has
never had a mechanism behind it. `refs/` is unchanged and stays hard-denied:
those are the user's photographs, and no measurement argument justifies the
agent rewriting them.

**Never from red.** A spec change may not be proposed while the last check
failed. Every legitimate case observed is green — the build passes and the
contract is simply inaccurate, as `beaky`'s depth is. The failure ADR 0002
names is the mirror image: red, one tolerance widens, green, and the model
never changed. The rule is prose, because nothing on disk can currently answer
which state the space is in.

**`revision:` counts accepted changes to the contract.** An optional integer at
the top of a spec; absent means 0, so nothing existing has to change. It is
**not** a release version — ADR 0013's `v<N>` tag keeps that job, and the two
move at completely different rates.

**The launcher enforces the counter, and says nothing when clean.** Before
dispatching to Blender, `check`, `render` and `export` — the three model
commands, which all read the spec — compare the working `spec.yaml` against
`git show HEAD:spec.yaml`. Content differs and `revision` did not increment →
red. It sits at the same insertion point for all three, so covering them costs
less code than special-casing `check` would. This is the first mechanism in the
repo that can detect a spec edit nobody approved. Silent on success, so it
costs nothing on the command the agent runs dozens of times a session.

## Consequences

- **Rule 1's mechanism weakens from impossible to detectable.** The guard used
  to make an unapproved spec edit unachievable. Now it makes one noisy. That is
  a real reduction, accepted in exchange for the ability to fix a contract that
  is wrong — which `beaky` has needed since the day it was written.
- The counter is the only part of this that has teeth. Prose disclosure,
  `NOTES.md` and commit messages are all self-reported: the agent can edit a
  number and simply not mention it, and nothing catches that. A bump git
  cross-checks cannot be skipped silently.
- **Detection, not prevention.** There is a window where `spec.yaml` differs
  from `HEAD` with no bump and nothing has fired. Rule 5 puts the user between
  disk and history regardless, so nothing reaches a commit unseen. A
  `pre-commit` hook in the space would close it properly and is deferred, not
  rejected.
- Cost measured at roughly **30–50 tokens per session**: one or two lines in
  each `CLAUDE.md`, one line in a spec. About 3% of a single `contour render`.
  Zero per check, because the check is fail-only.
- `beaky`'s spec carries no `revision`, so it is revision 0 and its first
  correction makes it 1. The depth question can finally be answered rather than
  recorded.
- `fixtures/smoke/spec.yaml` is untouched, because the field is optional. The
  selftest and mutant counts do not move.
- **Both repositories change together.** `CLAUDE.md` is copied into every space
  and `contour doctor` compares the copy against the toolkit's, so a toolkit
  edit puts every existing space into DRIFT until it is refreshed.
- **"Never from red" stays unenforceable.** It needs `report.json` to carry the
  command, the outcome and a timestamp. Until then the rule rests on the same
  discipline as rule 5.
- **Nothing measures a reference image.** mm-per-pixel is the agent's own
  arithmetic on an image nothing else reads, and a wrong anchor reading is
  invisible to every check here. This ADR improves how that number is
  *disclosed*, not how it is *verified*, and the human at the gate remains the
  only check on it.

## Rejected

- **Keep the hard deny; the user types every spec edit.** The genuinely free
  option — zero tokens, and an unapproved edit stays impossible. Rejected
  because it is the status quo that left `beaky` with a defect it can only
  record: a contract known to be wrong, frozen, with the correction living in
  the one file nothing verifies.
- **Confirmation alone, with no counter.** Saves ~15 tokens a session against
  the accepted design. Rejected because it is the same trust with the
  enforcement removed: a behavioural rule costs *more* prose to state, not
  less, and catches nothing when the agent simply doesn't follow it.
- **YAML comments beside each number**, recording who chose it. Closest to the
  number and needs no schema change. Rejected twice over: `miniyaml` strips
  comments before verify sees the file, so nothing can ever check one, and the
  guard is file-level — there is no way to permit fixing a stale comment
  without permitting a write to the spec it sits in.
- **A `src: measured` key per dimension.** Would pass verify today by accident,
  since dimensions are checked as a subset (`{"value","tol"} <= set(...)`).
  Rejected: it reaches only `dimensions` — `parts` entries allow just `name`,
  `count` and `notes` — and rule 1 would freeze a label that later turns out
  wrong, with no way to correct it.
- **A `version:` field meaning the release version.** ADR 0013 rejected this as
  *structurally impossible*, because bumping it is a write to a tracked spec.
  That ground, and only that ground, is removed by this ADR. It stays rejected
  on the rest of ADR 0013's reasoning: a folder and a tag are deliberately two
  records readable from backup media with no git at all, which a field inside a
  tracked file cannot be. A contract revision and a release version also move
  at different rates, so fusing them guarantees one of the two is lying.
- **Enforcing the counter in the `PreToolUse` guard**, which is the only option
  that prevents rather than detects. Rejected on what the guard can see: on a
  `Write` it gets the full content and could parse it, but on an `Edit` it gets
  only `old_string`/`new_string` and cannot know the resulting file's revision
  without reimplementing Edit's semantics. Making it work means forcing
  whole-file rewrites of a 2 KB spec to change one number, which costs more
  tokens than the entire enforcement story saves, and it would deny a correct
  end state because of the order the agent reached it in.
- **Enforcing in `verify.py`.** It runs inside Blender and checks geometry
  against a spec; whether the spec is in step with git is not a geometry
  question, and the launcher already shells out to git for `doctor`, `spaces`
  and `toolkit_commit`.
- **The user sets every tolerance; the agent proposes values only.** The safest
  reading of ADR 0002. Rejected because it front-loads exactly the cost the
  ADR 0002 amendment existed to remove — hand-writing the numeric half of a
  ~60-line contract from a schema.
- **Tolerance derived purely from measurement precision.** Honest and
  mechanical. Rejected because it systematically produces loose goalposts,
  which is the specific harm ADR 0002 warns about: a tolerance loose at birth
  moves the goalposts just as surely as one widened later.
