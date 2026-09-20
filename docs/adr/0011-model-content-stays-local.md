# 0011 — Model content stays local; git carries the toolkit

**Status:** Accepted · 2026-09-20 · **superseded in part by [ADR 0014](0014-toolkit-is-a-tool-a-model-is-a-project.md) and [ADR 0015](0015-model-spaces.md)**

> **Superseded in part 2026-09-20.** The invariant stands and was strengthened:
> model content never leaves via git, and `tools/hooks/pre-push` still refuses
> any ref but `master` and any push carrying model paths. What ADR 0014 and ADR
> 0015 changed is the arrangement underneath. Models are no longer variant
> branches of this repository; each is a model space, a repository of its own
> that is never pushed at all, and every space's pre-push stub refuses every
> push. So "the boundary is the branch", `verify.py`'s branch check and
> `./contour export <variant>` below describe the old arrangement — export now
> takes no name and runs inside the space. The *two repositories* option
> rejected below is the one that was adopted, once the `git merge master`
> mechanism it broke had been retired. A space is backed up as a git bundle
> rather than a copy of the working tree (ADR 0015). The text below is left as
> decided.

## Context

No remote is configured (open question 6), so nothing has leaked because
nothing can. This ADR is not fixing a live leak; it is pre-committing a rule
before the day a remote exists and the question is decided by reflex instead.

**Amended 2026-09-20 — that day arrived.** A private repository at
`github.com/wittaya698/contour.git` is now configured as `origin`, so the
paragraph above no longer describes this repo: the guard is live rather than
anticipatory. It was exercised the hour the remote was added, by feeding the
hook the stdin git supplies and making no connection at all — pushing `beaky`
refused, `--all` refused because one ref failed, `beaky`'s content aimed at
`master`'s ref refused with all three files named, a branch deletion allowed,
and `master` allowed. Nothing has been pushed.

One consequence for ADR 0012: when `BLOCKED` narrows to `^models/`, the
retired prefixes stay in the pattern. A path that used to carry model content
should stay blocked forever, or the second ground stops catching any commit
still holding the old layout.

The layout already segregates along the line that matters. Diffing the branches
on 2026-09-20, the only files `beaky` adds to `master` are exactly:

```
spec/beaky.yaml
models/beaky/build.py
renders/beaky.png
```

So ADR 0003's "`master` builds no model of its own" and "`master` is the
publishable half" are the same statement. The boundary is the branch, not a
directory — and `verify.py` already enforces the matching invariant at build
time, refusing to build a variant from any branch but its own.

**Threat model: accident, not adversary.** The failure guarded against is a
reflexive `git push --all`, or `git push -u origin HEAD` while standing on a
variant. Nobody is trying to exfiltrate anything. This choice is what makes a
ten-line hook a proportionate answer, and it is what the rest of this ADR
assumes; if the threat model ever changes, every decision below is reopened.

## Decision

**Publishable:** `master` — `lib/`, `verify.py`, `schema/`, `fixtures/`,
`docs/`, `.claude/`, `contour`, `tools/`. The toolkit is reusable and carries
no model content.

**Local-only:** every variant branch, and therefore all of `spec/`, `models/`
and `renders/`. These never travel over `git push`.

**The guard.** The tracked source is `tools/hooks/pre-push`; it is *installed*
by copying it to `.git/hooks/pre-push` (`./contour install-hooks`), which is
outside the working tree and therefore survives every checkout. It refuses a
push on two independent grounds, either sufficient:

1. the ref being pushed is not `master`; or
2. the commits being pushed touch `spec/`, `models/` or `renders/`.

It fails closed: a ref it cannot resolve a base for is refused, not waved
through. The second ground is not redundant — it catches model content that
reaches `master` by mistake, which the first ground would let past.

**Sharing a model is an export, not a push.** The sanctioned way to hand over a
model is `./contour export <variant>` and delivering the `.glb` directly. Git
is never the transport for model content, so the hook needs no exception and
none should be added. `exports/` is already ignored (ADR 0007).

**Backup is file-level, not a push.** Durability comes from copying the working
directory — including `.git`, every branch, every commit — to external media.
No `git push` is involved, so the rule above stays absolute and still survives
the disk dying.

**Pushing is gated like committing.** The agent shows the verify report and the
render sheet, the user says ship, and the agent then commits *and* pushes. This
extends CLAUDE.md rule 5 rather than adding a second kind of gate.

## Consequences

- The invariant is one sentence: model content never leaves via git.
- The guard is a backstop, not the control. The control is the approval gate;
  the hook catches the case where the gate was passed and the command was still
  wrong.
- Because the agent stays on the push path, hook correctness matters more than
  it otherwise would. Two cases must fail closed or the guard is theatre: a
  **new branch**, whose remote SHA is all zeros so there is no remote-side base
  to diff against, and **`git push --all`**, which delivers every ref at once.
- A legitimate toolkit topic branch cannot be pushed. Accepted: `master` is
  the only branch anyone would publish, and ground 2 keeps working if that
  changes.
- The hook must be installed once per clone, and nothing enforces that it was.
  `./contour install-hooks` is the step; a clone that skips it has no guard.
  This is the weakest joint in the design and is accepted knowingly.
- **What this does not close:** the agent reads `spec/` and `build.py` into
  model context, which leaves the machine. That is a deliberate, accepted
  consequence of an agent-built pipeline, not a gap — no git mechanism touches
  it, and closing it would mean abandoning the premise of this repo.

## Rejected

- **Two repositories, the model one given no remote** — a structural wall
  instead of a guard. Rejected because it breaks `git merge master` into
  variants, which is the mechanism ADR 0003 depends on, in exchange for
  stopping an adversary this threat model does not have.
- **Allowlist by remote URL rather than by branch** — more flexible, and would
  permit a trusted private remote later. Rejected because it requires auditing
  each URL, and a typo'd remote is precisely the accident being guarded
  against.
- **An env override (`CONTOUR_ALLOW_MODEL_PUSH=1`)** — two lines, greppable,
  hard to do by reflex. Rejected because an escape hatch that exists gets used,
  and then becomes habit; the export path already covers the real need.
- **No guard, relying on care** — the status quo. Rejected because the cost of
  the hook is ten lines and the cost of the accident is unbounded.
- **`core.hooksPath = tools/hooks`, so the hook is tracked and travels with
  `master`** — proposed first, and tested before acceptance. It fails open on
  precisely the dangerous branch: `core.hooksPath` resolves inside the working
  tree, so checking out a variant that has not yet merged `master` removes
  `tools/hooks/pre-push` from disk, the hook silently ceases to exist, and
  `git push origin <variant>` succeeds with every model file. Verified
  2026-09-20 in a throwaway clone. Installing to `.git/hooks/` instead costs
  the install step recorded above and has no such hole.
- **A private git remote for backup** — real off-machine history with branches
  intact, but it reopens the push rule it is meant to coexist with. File-level
  backup gets the same durability without touching the rule.
