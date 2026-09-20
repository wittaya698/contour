# 0012 — One directory per model

**Status:** Accepted · 2026-09-20

## Context

Model content is split by artifact type across three top-level directories:
`spec/<v>.yaml`, `models/<v>/build.py`, `renders/<v>.png`. Because a variant
lives alone on its own branch (ADR 0003), each of those directories holds
**exactly one entry**. They are single-entry directories whose only job is to
sort a set of one.

`fixtures/smoke/` already uses the opposite layout — `spec.yaml` and `build.py`
together in one per-model directory — and it reads better. `lib/paths.py`
carries a fork to serve both shapes.

Two pressures made the split expensive rather than merely untidy:

- **Reference images have nowhere to go.** The four images `beaky` was built
  from exist only as base64 blobs inside a Claude session log, outside the repo
  and prunable. They are the one input that cannot be regenerated from source,
  and the "two files per variant" rule left no place to put them.
- **The pre-push guard has a hole.** ADR 0011 blocks `spec/`, `models/` and
  `renders/`, but ADR 0007 archives a release `.blend` at `out/<v>.blend` with
  `git add -f`. That is model content outside every blocked prefix, so ground 2
  cannot catch it.

This is the cheapest moment this change will ever have: one variant exists, and
its whole footprint is three files.

## Decision

**One directory holds everything about one model.**

```
models/<v>/
    spec.yaml      tracked    the user's intent      (agent-read-only)
    refs/          tracked    the user's references  (agent-read-only)
    build.py       tracked    the agent's attempt
    sheet.png      tracked    evidence, per accepted commit (ADR 0007)
    NOTES.md       tracked    deferred refinements and open questions
    out/           ignored    <v>.blend and render scratch
    exports/       ignored    <v>.glb
    release/v<N>/  tracked    archived release packages (ADR 0013)
```

`spec/` and `renders/` cease to exist. **ADR 0003's "adds only two files" is
amended to: a variant branch adds only `models/<v>/`.** That is a stronger
invariant than the one it replaces — one path prefix instead of three.

**Run plumbing moves to `.contour/`.** `last-build.log` and `report.json` are
written for every command, including `api` and `selftest`, which have no
variant at all; they cannot live under a model. Keeping the name `out/` for
them would leave two directories called `out/` meaning different things.

**The fixture keeps its place and gains the same shape.** `fixtures/smoke/`
does **not** move to `models/smoke/`: the push guard blocks `models/` on every
ref, so a fixture there would make `master` itself unpushable. Both layouts
become `<base>/<variant>/{spec.yaml, build.py, out/}`, which collapses the fork
in `lib/paths.py` to the choice of base.

**References join the spec's trust class.** `refs/` is the user's statement of
intent in pictures, exactly as `spec.yaml` is in numbers, so ADR 0002 applies
to it unchanged: the agent reads it and never writes it. Stored at original
fidelity (~0.9 MB for `beaky`), committed once, never churning — ADR 0007's
per-commit argument does not reach them.

**Rule 1 gets a mechanism.** ADR 0002 already states the predicate — *"a spec
git already tracks is never written again"* — but nothing implemented it. A
`PreToolUse` hook now refuses a write to a tracked `models/*/spec.yaml` or
`models/*/refs/**`, and permits an untracked one, which is precisely the
amended rule: creation is allowed, mutation is not.

**The guard hole closes as a side effect.** `BLOCKED` becomes the single prefix
`^models/`, and the archive moves from `out/` to `models/<v>/release/`, so it is
ordinary tracked model content that the hook catches without a special case.
ADR 0007's `git add -f` exception is retired. What an archive *contains*, and
how versions are numbered, is ADR 0013.

**Migration is ordered so no commit is ever broken.** The toolkit and docs land
on `master` first; then on `beaky`, `git merge --no-commit master`, `git mv` the
three files, and one commit. The merge commit touches only `beaky`'s own files,
so ADR 0003's shared-file rule holds.

## Consequences

- One prefix describes model content, for the hook, for `.gitignore`, for the
  branch rule and for a human reading the tree.
- Deleting a variant is `rm -rf models/<v>` and a branch delete.
- Tracked and ignored files now interleave in one directory. `git add models/`
  stays correct, since ignored paths are not added, but the tree no longer
  sorts cleanly into "all tracked" and "all derivable" at a glance.
- `.contour/` is a new hidden directory, and every doc that said
  `out/last-build.log` now says `.contour/last-build.log`.
- `NOTES.md` is the only artifact here that nothing verifies. It uses the
  `docs/OPEN-QUESTIONS.md` format — what each item blocks, and the default if
  nobody decides — because that format makes a stale entry resolve itself
  rather than sit.
- The spec guard is the first `PreToolUse` hook in this repo, so
  `.claude/settings.json` is new. It is a Claude Code hook, not a git hook, and
  `./contour install-hooks` does not install it; it applies because `.claude/`
  is tracked and merges outward to every variant.
- **What this does not fix:** a clone still has to run `install-hooks`, the
  weak joint ADR 0011 already accepted. Nothing here changes that.

## Rejected

- **Keep the split by type** — zero churn, and `spec/` at top level made "the
  user's directory" visible at a glance. Rejected because the cue was never a
  control: rule 1 was prose either way, and the split left references homeless
  while costing an extra two prefixes everywhere a prefix is enumerated.
- **Consolidate tracked content only, leaving `out/` and `exports/` flat** —
  smaller diff, and it keeps derivable output visibly separate from source.
  Rejected because it leaves the release `.blend` outside `models/`, so the
  ADR 0011 hole survives and needs its own hook patch.
- **Keep `out/` at top level for the log and report** — no new directory name,
  and the docs' `out/last-build.log` line survives. Rejected: `out/` would mean
  the log at the root and the build inside a model, a distinction every future
  reader has to learn for no benefit.
- **A compatibility fallback in `paths.resolve`, trying the new path then the
  old** — lets the toolkit and the move land in any order. Rejected because it
  buys flexibility that one variant does not need, in exchange for dead code
  that has to be removed later, or silently is not.
- **Accept one broken commit on `beaky` between the merge and the move** —
  simplest history, and the window is seconds. Rejected because a commit that
  does not build is a poor thing to leave in a repo whose premise is that any
  commit rebuilds from source.
- **Keep the references outside the repo, beside it** — keeps the tracked tree
  purely textual. Rejected because they are the one input nothing can
  regenerate, and an untracked folder is exactly the storage that just failed
  them.
- **A plain `TODO.md` checklist** — familiar and quicker to skim. Rejected in
  favour of the format the repo already runs on, which forces an item to carry
  its own default.
- **Move `fixtures/smoke/` to `models/smoke/` for one layout everywhere** —
  tempting, and it would delete the last fork in `paths.py`. Rejected: the push
  guard blocks `models/`, so `master` could never be pushed again.
- **Do nothing until a second variant exists** — the split's cost is only
  visible with one model, so waiting would make the evidence stronger.
  Rejected because waiting also makes the migration strictly more expensive:
  every variant born under the old layout is another branch to move.
