# 0014 — The toolkit is a tool; a model is a project

**Status:** Accepted · 2026-09-20 · **direction only, implementation deferred**

## Context

A private remote now exists at `github.com/wittaya698/contour.git`. The intent
behind it is specific: **share the toolkit with other people, and never share
models — mine or theirs.**

Today that intent is served by a guard rather than by structure. ADR 0003 makes
every model a branch of the toolkit repository, so model content lives inside
the tree that is meant to be handed out, and ADR 0011 keeps it from leaving via
a `pre-push` hook. That hook was verified against the real remote on
2026-09-20 and refused every dangerous case. But ADR 0011 names its own weakest
joint plainly: the hook must be installed once per clone, and nothing enforces
that it was. A person who clones the toolkit and starts a model has no guard
until they run `install-hooks`.

Two things have since made a different shape available.

**ADR 0012** makes each model one self-contained directory, so a model is now
extractable as a unit — `git subtree split -P models/<v>` lifts it into its own
repository with its history intact. Under the old three-directory layout that
was not possible.

**The code is already decoupled.** `lib/entry.py` takes its root from
`CONTOUR_ROOT` rather than assuming the checkout it lives in, so separating
"where the code lives" from "where the model lives" is a second environment
variable and a change to `paths.resolve`.

## Decision

**The target architecture is a tool and a project.** The toolkit is something
you install and share, the way `cargo`, `hugo` or `terraform` are. A model
space is an ordinary private repository — `spec.yaml`, `refs/`, `build.py`,
`sheet.png`, `NOTES.md`, `release/` — created by `contour init` and operated on
by the installed tool. **The two never share a remote.**

**This ADR decides direction only. Nothing is implemented yet.** It exists so
the question is settled rather than resurfacing in every future structural
conversation. ADR 0003 and ADR 0011 remain in force until it is implemented.

**Implementation is deferred to the first time a second model space is
wanted.** That model proves the design; `beaky` moves only afterwards, by
subtree split, with its history.

**ADR 0012 lands first regardless.** It is the prerequisite, not a detour: it is
what makes the extraction clean.

**When it lands, these retire:** branch-per-variant and `git merge master` into
variants (ADR 0003), and the `branch == variant` check in `verify.py`. The
push guard stays as a backstop and stops being the control, because a shared
toolkit checkout has no model directory to leak.

**Two obligations the implementation must carry.** Both are failure modes of
this shape, not afterthoughts:

1. **Scaffolding, because the agent's rules live in the toolkit.**
   `CLAUDE.md`, `.claude/skills/` and the spec-guard hook are read from the
   working directory. A model space that lacks them gets an agent with no
   rules. `contour init` must write them into the space, and `contour doctor`
   must report when a space's copies no longer match the toolkit they came
   from. Copies drift; the answer is detection, not hope.
2. **Provenance, because skew goes silent.** Today a variant sits on an old
   toolkit deliberately, and a merge is how it moves. With an installed tool, a
   model gets whatever version happens to be on the machine and nothing records
   which one verified it. A space records the toolkit commit it was built
   against, and ADR 0013's `release/v<N>/` includes it — an archive that cannot
   say what built it is half an archive.

## Consequences

- The shared repository becomes publishable by construction rather than by
  discipline. This is the point of the change.
- Until implemented, nothing changes at all, and this ADR is a promise rather
  than a fact.
- Backup covers two locations instead of one, and open question 6's backup half
  is still unbuilt. The split makes that gap wider, not narrower.
- A model commit stops being atomic with the toolkit state that verified it.
  Provenance is the compensation, and it is weaker than atomicity.
- Other people's models become invisible to this repository by construction,
  which was the requirement.
- `contour` needs an install story — a symlink on `PATH`, or invocation by
  absolute path — which the single-checkout shape never needed.

## Rejected

- **A git submodule at `models/`** — the toolkit commit would record exactly
  which model commit it was verified against, which is real reproducibility.
  Rejected because `.gitmodules` and a gitlink are pushed to the shared repo,
  and submodules cost detached heads, forgotten `--init` and stale pointers
  every day to buy something provenance gives for a line of text.
- **Two sibling repositories, the toolkit as the parent checkout** — simpler
  than a submodule, and the toolkit can simply ignore `models/`. Rejected
  because it still hands other people a repository that expects models inside
  its own tree; it fixes leaking without fixing sharing.
- **Implement it now, in the same motion as ADR 0012** — `beaky` would migrate
  once instead of twice. Rejected: it means designing multi-user scaffolding
  before a second model or a second person exists, and the scaffolding is the
  part most likely to be wrong.
- **Keep the status quo** — branches plus the proven guard. Rejected because it
  leaves the protection behavioural, dependent on a per-clone install step that
  nothing enforces, in a repository now intended for other people.
- **Keep branch-per-variant after the split** — familiar, and it preserves the
  deliberate-skew property. Rejected as incoherent: once a model is its own
  repository there is nothing to merge master into.
