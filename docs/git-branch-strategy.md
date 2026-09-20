# Branch strategy

## Model

```
master          toolkit only — lib/, verify.py, schema/, .claude/, fixtures/, docs/
                builds no deliverable model
  │
  ├─> oak-chair     + spec/oak-chair.yaml   + models/oak-chair/build.py
  ├─> steel-chair   + spec/steel-chair.yaml + models/steel-chair/build.py
  └─> ...
```

Variant branches are **long-lived and never merge back**. They coexist
permanently; each is a different model, not a different version of one model.

## The rule that makes it work

A variant branch adds exactly two files and **touches nothing else**. Shared
code is never edited from a variant.

Because variants only add files that no other branch has, `git merge master`
into a variant is conflict-free by construction. If you ever hit a merge
conflict on a variant branch, it means someone broke this rule — find the shared
file that was edited on the variant and move that change to `master`.

## Workflows

**New variant**
```sh
git checkout master && git checkout -b <variant>
# add models/<variant>/ only — spec.yaml, refs/, build.py (ADR 0012)
```

**Fixing shared code**
```sh
git checkout master
# edit lib/ verify.py schema/ .claude/ ...
./contour selftest          # must be green before this leaves master
git commit
# then, per variant you care about:
git checkout <variant> && git merge master && ./contour check <variant>
```

**Propagating**: a variant is not obliged to take every toolkit change
immediately, but a variant that has not merged `master` in a long time is
running old checks. Merge forward before any release.

## Commit rules

- A commit lands only after the user has seen the verify report and the render
  sheet and approved it. Every commit on a variant branch is therefore a state
  a human looked at.
- A commit carries source **and** the updated `models/<variant>/sheet.png`,
  so history is visually scannable.
- Commit message format:
  ```
  <variant>: <what changed>

  verify 8/8 | tris 4,210 | height 900mm
  ```
- `out/*.blend` is never committed except at a release tag, where it is
  committed once as the archived deliverable (see `release-model` skill).

## Notes carried over

A previous incarnation of this repo used a three-tier `master` ← `dev` ←
feature policy and had a local `.git/hooks/post-merge` that could produce
duplicate merge commits. **Neither applies here**: there is no `dev` tier, and
no hooks are installed. If a `post-merge` hook is ever added, check
`git log --oneline -3` after any `--no-ff` merge before pushing.
