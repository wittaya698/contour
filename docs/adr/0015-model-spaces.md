# 0015 — Model spaces: how the tool/project split actually works

**Status:** Accepted · 2026-09-20

## Context

ADR 0014 decided the direction and deferred it "to the first time a second
model space is wanted", so that the scaffolding would be designed against a
real second model rather than a guess. That deferral is overtaken: the split is
being built now, with one model. The reasoning behind the deferral stands and
is not withdrawn — it is simply no longer the chosen trade.

Everything below was measured on 2026-09-20 rather than assumed, because each
point decides a piece of the design.

**A symlinked launcher already works.** `contour` computes
`ROOT = Path(__file__).resolve().parent`, and `.resolve()` follows symlinks, so
a link on `PATH` finds its own toolkit. `selftest` run through such a link from
`/tmp` passed all four stages. No code change is needed for installation.

**The extraction works, and loses one thing.** `git subtree split -P
models/beaky` produces exactly the flat shape this ADR wants — `spec.yaml`,
`refs/`, `build.py`, `sheet.png` at the root — carrying three commits. It
cannot carry `42ee2aa`, the branch's first commit, which added
`spec/beaky.yaml` alone with no geometry: that path was outside the prefix
because `models/beaky/` did not exist yet. So an extracted space cannot show
that the contract was accepted *before* any vertex existed, which is the
discipline ADR 0002 exists to enforce.

**Copied guards are not merely at risk of drift — they are wrong on arrival.**
Both were run against a flat space:

| Guard, copied into a model space | Result |
|---|---|
| `guard-spec.py` on a tracked `spec.yaml` | **allowed** — it matches `models/*/spec.yaml` and silently no-ops |
| `guard-spec.py` on tracked `refs/front.jpg` | **allowed** — same |
| `guard-branch.py`, space on `master` | allows everything, harmlessly, by luck |
| `guard-branch.py`, space on `main` | **denies every write in the space** |

Rule 1's mechanism would vanish in the one place a spec lives, and whether the
space works at all would depend on `init.defaultBranch`, a machine-level git
setting. On this machine it is unset, giving `master`; a collaborator's git
would likely give `main`.

## Decision

**A model space is found from the working directory.** `contour init` writes a
`.contour/` directory into the space, and the tool walks up from the cwd to
find it, as git does with `.git`. Commands lose their variant argument —
standing in the model, there is nothing to name. `--fixture` is unchanged and
still points inside the toolkit.

**Identity comes from the spec, checked against the directory.** `spec.yaml`'s
`model:` field must equal the space's directory name. This replaces the
`branch == variant` check in `verify.py`, which ADR 0014 retires along with
branch-per-variant.

**Installation is a symlink on `PATH`.** Nothing is pinned inside a space, so
the toolkit can be moved or renamed and only the link is relinked.

**Scaffolding splits by what has to be local.** `CLAUDE.md` and
`.claude/skills/` are copied, because the agent reads them from the working
directory; they are therefore the only things that can drift, and
`contour doctor` compares them against the toolkit. **Executables are never
copied.** The space's `.claude/settings.json` invokes `contour hook <name>`
through `PATH`, and `.git/hooks/pre-push` is a two-line stub that does the
same. The guard is always the installed version, so there is nothing to drift
and nothing to keep in step.

**A model space refuses every push.** There is no legitimate push from a model
space, so there is no case to reason about: the stub hook says no. This is
stronger than relying on no remote being configured, which holds only until
somebody runs `git remote add` — the accident ADR 0011 was written for.

**`guard-branch.py` is retired.** It enforces "shared files on `master` only",
which is ADR 0003's rule. Once models leave the repository, every branch in the
toolkit repo is a toolkit branch, and a guard permitting only `models/` would
block all legitimate work. It is deleted in the same commit that removes
in-repo model support, not merged forward.

**In-repo models are removed entirely, with no dual mode.** `models/`
disappears from `paths.py`, `.gitignore` and the docs. There is deliberately no
fallback to branch-per-variant.

*Corrected during implementation:* `models/` **stays** in the push guard's
`BLOCKED` list. An earlier draft of this ADR said it should be removed, which
contradicts ADR 0011's amendment that a path which ever carried model content
stays blocked forever. The guard's job is to catch content arriving where it
should not be, so the retired prefix is exactly the one worth keeping.

**Migration order, and the one irreversible step.** Extract, verify the space
builds green, **bundle the branch**, then delete it:

```sh
git subtree split -P models/beaky -b beaky-only
git bundle create ~/backup/beaky-history.bundle beaky   # before the delete
git branch -D beaky
```

The bundle is one file of about a megabyte holding the whole branch, `42ee2aa`
included. It keeps no model content in any ref of the toolkit repo, so the
goal is untouched, and it makes the delete reversible. The space's `NOTES.md`
records in words what the bundle holds in commits: that the spec was written
and accepted before any geometry.

## Consequences

- The shared repository becomes publishable by construction. No ref in it
  carries model content, and the push guard becomes a backstop for a case that
  can no longer arise from this machine.
- **The ordering evidence is gone from the space's own history.** The spec
  appears to arrive in a merge commit. Only the bundle and a sentence in
  `NOTES.md` say otherwise.
- **There is no fallback.** If the space design is wrong when a second model
  arrives, the answer is to fix it, not to fall back to branches. That is the
  cost of building it before the second model existed, and it is accepted
  knowingly.
- Backup is now doubly overdue. Two locations to protect, and the extraction
  does not create a second copy of anything — it moves the only one.
- `contour` gains `init`, `doctor` and `hook`. `hook` is not a user command; it
  is how the copied-nothing pattern is possible at all.
- `contour doctor` is the only thing standing between a space and silently
  stale rules. Nothing forces anyone to run it.
- Spaces must never depend on their branch name. The evidence above is what
  that rule is made of.
- A space with no `.contour/` is not a space. Discovery failing must say so
  plainly rather than falling back to the toolkit's own directory, or a stray
  `contour check` in the wrong place will build something unexpected.

## Rejected

- **Copying the guards into each space, rewritten for the flat layout** — each
  space would then work even with the toolkit missing. Rejected on the evidence
  above: it means two implementations of rule 1, and the failure mode is
  silence, not an error.
- **A registry of spaces in the toolkit**, so `contour check beaky` keeps
  working from anywhere. Rejected: global mutable state outside either
  repository, stale the moment a directory moves, and covered by no backup.

  *Revisited 2026-09-20.* All three objections stand, and all three are
  objections to **storing** a list. The need behind the registry — "where are
  my spaces?" — was dismissed along with the mechanism, and it was a real
  need. `contour spaces` answers it by **deriving** the list: every space
  already carries `.contour/project`, so the markers are a registry that is
  distributed, moves with the directory, cannot go stale and needs no backup.
  `$CONTOUR_SPACES` names where to look, not what exists, so it cannot drift
  either. The scan is bounded because it has to be: one workspace of 21
  entries resolves in under a second, while `$HOME` at depth 4 did not finish
  in two minutes. It lists and it warns — notably about a space that has
  acquired a remote, which nothing else would catch without visiting each one.
  It deliberately does **not** restore `contour check <name>`: commands take
  no model name so that exactly one model can be meant.
- **An explicit path or `CONTOUR_PROJECT`** on every invocation. Rejected as
  correct but tiring; it becomes an undocumented shell alias within a day.
- **A launcher stub in each space**, preserving `./contour check`. Rejected: it
  hard-codes the toolkit's path into every space, so moving the toolkit breaks
  all of them at once.
- **Keeping the `beaky` branch after extraction** — `42ee2aa` exists nowhere
  else, and the branch is local and unpushed, so it costs nothing toward the
  goal. Rejected in favour of a toolkit repository with no model content in any
  ref at all; the bundle carries the history instead.
- **Rewriting history with `git filter-repo`** to map the old paths across all
  commits, which is the only option that both keeps `42ee2aa` in the space and
  lets the branch go. Rejected for now: it is not installed, and
  `filter-branch` is deprecated and easy to get wrong. This remains the right
  answer if the ordering evidence is ever wanted in the space itself.
- **Relying on no remote being configured** instead of a push stub. Rejected:
  it is true only until it is not, and the failure is silent.
- **Keeping branch-per-variant as a second supported mode.** Rejected because
  two modes means every path, guard and document carries a fork forever, to
  support a mode ADR 0014 already decided against.
