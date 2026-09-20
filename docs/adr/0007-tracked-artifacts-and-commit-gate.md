# 0007 — What git tracks, and who commits

**Status:** Accepted · 2026-09-20

## Context

`.blend` is an opaque binary: git stores a full copy on every save, diffs are
meaningless, merges impossible. But it is also the deliverable. Because ADR 0001
makes builds deterministic, a `.blend` is *derivable* — committing one is
storing a build artifact.

Scale: a simple prop `.blend` is 1–5 MB per commit forever; a 512² PNG is ~150 KB.

## Decision

**Tracked:** `spec/`, `models/`, `lib/`, `verify.py`, `schema/`, `.claude/`,
`docs/`, and one 512px thumbnail per accepted commit at `renders/<variant>.png`.

**Ignored:** `out/`, `work/`, `exports/`.

**Archived:** at a release tag, the `.blend` is committed once, insulating the
deliverable from a future Blender changing rebuild behaviour.

**Commit gate:** the agent iterates without committing. When verify is green it
shows the report and the render sheet; on the user's explicit approval it
commits source plus thumbnail, with a message of the form:

```
<variant>: <what changed>

verify 8/8 | tris 4,210 | height 900mm
```

## Consequences

- The repo stays small and every diff is readable.
- `git log` is a visual timeline — thumbnails make "the version I liked"
  findable by scrolling rather than by rebuilding.
- Every commit is a state a human actually looked at and accepted.
- Good intermediate states that were never approved are lost. That is the
  intended trade: history as a record, not a log.
- A rebuild is required to open any past state, which is cheap now and depends
  on Blender behaviour staying stable — hence the tag archive.

## Rejected

- **Auto-commit every green build** — nothing is ever lost, but history fills
  with states nobody chose and near-identical thumbnails.
- **`.blend` in Git LFS every commit** — versioning an artifact that is already
  regenerable, at the cost of LFS setup and quota.
- **Commit everything plainly** — 200 commits × 3 MB ≈ 600 MB repo.
- **Human commits by hand** — full control, but committing becomes a chore and
  good states go unrecorded.
