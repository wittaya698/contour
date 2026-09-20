# 0013 — Releases are versioned folders, prepared by the tool

**Status:** Accepted · 2026-09-20 · **superseded in part by [ADR 0015](0015-model-spaces.md)**

> **Superseded in part 2026-09-20.** The decision stands; only two literals
> changed under ADR 0015. The release folder is `release/v<N>/` at the root of
> the model space, not `models/<v>/release/v<N>/`, and the command takes no
> model name, so `./contour release <variant>` is `contour release` run inside
> the space. The tag keeps its form, `<variant>-v<N>`, with the space's name as
> `<variant>`. `contour release` is still not built; `release-model` does the
> assembly by hand.
>
> **One rejection reopened, 2026-09-21.** "A `version:` field in the spec" was
> rejected below as *structurally impossible*, because bumping it is a write to
> a tracked spec. [ADR 0016](0016-specs-from-references-and-revision.md) removed
> that ground, and a spec now carries an optional `revision:`. The decision
> here is **unchanged**: `revision:` counts accepted changes to the contract,
> not releases. A release stays a folder and a tag, for the reason given below
> that ADR 0016 does not touch — those are readable from backup media with no
> git at all, which a field inside a tracked file can never be.

## Context

Nothing has ever been released. `git tag -l` is empty, and the scheme in
`release-model` — an annotated `<variant>-v<N>` tag plus
`git add -f out/<v>.blend` — is designed but unexercised. ADR 0012 moves that
archive to `models/<v>/release/` and deliberately leaves two questions open:
what a version contains, and what happens at the second one.

Three facts constrain the answer.

**The version cannot live in the spec.** Bumping a `version:` field would mean
writing a spec git already tracks, which rule 1 forbids and ADR 0002 states
mechanically. Whatever names a version, it is not the model's own contract.

**The `.glb` is the thing an engine consumes, and it is only nominally
derivable.** ADR 0007 archives the `.blend` because a future Blender may
rebuild differently. That argument is *stronger* for the export: reproducing
v1's `.glb` years later needs the exporter of that era, not merely the file it
was made from.

**What is on disk is what survives.** Open question 6 resolved backup as
file-level copying of the working directory, and ADR 0011 forbids git as the
transport for model content. A record that needs `git show` to read is a record
a backup drive cannot hand back by itself.

## Decision

**A release is a folder, and it accumulates.**

```
models/<v>/release/
    v1/  <v>.blend   <v>.glb   sheet.png
    v2/  <v>.blend   <v>.glb   sheet.png
```

Each folder holds the archived source asset, the deliverable the engine ate,
and the sheet that was approved — the three things that together say what was
released. Folders are never overwritten and never removed by tooling.

**The tag `<variant>-v<N>` carries the same N.** This is two records of the
same fact, on purpose: the folder is readable with `ls` and survives on backup
media with no git at all, and the tag ties the release to the commit that
produced it. The cost is that they can disagree, which the next decision
addresses.

**`./contour release <variant>` prepares a release; it never concludes one.**
It reads the tags and the folders, **refuses if they already disagree**, takes
N as one past the highest, then runs build and verify, export and round-trip,
and render, and writes the folder only if all of them pass. It prints the
`git add`, `commit` and `tag` commands for the user to run. It does not commit,
tag or push — rule 5 is unchanged, and ADR 0011 gates pushing the same way.

**ADR 0007's archive scope is amended** from the `.blend` alone to the package
above. Its `git add -f` exception is retired; ADR 0012 already moved the path
into tracked space, so the force-add has nothing left to override.

**`out/` and `exports/` stay ignored working output.** The release folder is
the only tracked copy of either, so `.gitignore` must ignore
`models/*/exports/` without catching `models/*/release/`.

## Consequences

- Every release costs its `.blend` plus its `.glb` plus ~170 KB, on disk and in
  every clone, forever. At 1–5 MB a blend that is roughly 3–6 MB a release; ten
  releases of one model is tens of megabytes that never shrink. This is the
  price paid for a record that reads without git.
- A release folder can be handed to someone, or copied to a drive, as-is.
- Drift between folders and tags is possible and is caught at the *next*
  release, not silently — `./contour release` refuses rather than guessing
  which source is right.
- A new stage joins the CLI (ADR 0008), so the command table in `CLAUDE.md` and
  `README.md` gains a line, and `release-model` stops describing the assembly
  by hand.
- Deleting a release is two steps, a folder and a tag, and nothing enforces
  doing both.
- Nothing verifies that an old release folder still matches its tag's commit.
  Accepted: these are archives, not sources, and re-deriving them is exactly
  what the archive exists to avoid depending on.
- The first use of this will also be the first test of it. None of it is
  exercised until a release actually happens.

## Rejected

- **Overwrite a single `.blend`; let the tag carry the version** — matches
  ADR 0007's one-sheet rule, keeps the working tree a constant size, and git
  still stores every version. Rejected because reading the record then requires
  `git show <tag>:<path>`, which the backup story (open question 6) cannot do.
- **Flat versioned filenames, `<v>-v2.blend` beside `<v>-v2.glb`** — one level
  less nesting. Rejected because a release is a set, and a folder says so;
  flat names also leave the approved sheet with nowhere to sit.
- **Archive the `.blend` only, as ADR 0007 has it** — smallest footprint, and
  formally the `.glb` is derivable. Rejected: it is derivable only with the
  exporter of its era, which is the exact dependency the archive exists to
  remove.
- **A `version:` field in the spec** — the obvious place to look for it.
  Rejected as structurally impossible: bumping it is a write to a tracked spec
  (rule 1, ADR 0002). The tag is the version *because* the spec cannot be.
- **`./contour release` commits and tags for you** — fewer steps, no chance of
  a half-done release. Rejected under rule 5: the tool prepares evidence, the
  user decides.
- **A warning in `./contour check` instead of a release command** — cheaper,
  and it surfaces drift on every build rather than once per release. Rejected
  because it detects a mistake without preventing one, and leaves assembling
  the package as a manual checklist, which is where the mistake comes from.
- **Keep it manual in `release-model`** — releases are rare, and a checklist
  may be honest sizing for something that has never happened. Rejected because
  the checklist now has to keep two records in step, which is precisely the
  work a machine should do.
