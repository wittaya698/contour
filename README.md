# Contour

Code-authored Blender game assets. A model is a Python script, not a file you
sculpt — so it is diffable, reproducible, and mechanically checkable.

## How it works

```
models/<variant>/
    spec.yaml     your intent, in numbers    (agent-read-only)
    refs/         your intent, in pictures   (agent-read-only)
    build.py      the agent's attempt        (rebuilt from an empty scene)
    sheet.png     the 4-view render you approved
    NOTES.md      what is deferred, and what is undecided
    out/          generated, READ-ONLY, git-ignored
verify.py         reads the spec, judges the build
  ↓ linked collection
work/scene.blend  YOUR file — materials, lights, camera (git-ignored)
```

Rebuild the asset and your scene file picks up the new geometry. Nothing you
did by hand is lost, because you never worked inside the generated file.

## Daily use

```sh
./contour check <variant>     # build + verify, fast loop
./contour render <variant>    # 4-view orthographic sheet with a 1m grid
./contour export <variant>    # .glb, re-imported and re-measured to prove it
./contour selftest            # prove the toolkit itself still works
```

## Branches

`master` is the toolkit — `lib/`, `verify.py`, `schema/`, `.claude/`,
`fixtures/`. It builds no deliverable.

Each model variant is a long-lived branch that adds only its own directory,
`models/<variant>/` (ADR 0012).
Shared fixes land on `master` and travel outward with `git merge master`.
Variants never merge back. See [docs/git-branch-strategy.md](docs/git-branch-strategy.md).

## What git tracks

Source, specs, reference images, and the render sheet (1024², ~170 KB) per accepted
commit — so `git log` doubles as a visual timeline. The `.blend` is derivable and stays
ignored, except in a release package, where it is committed once alongside the `.glb`
and the approved sheet (ADR 0013).

Model content is never pushed. Only `master`, the toolkit, reaches a remote; a
`pre-push` hook refuses the rest (ADR 0011). To share a model, `./contour export`
and hand over the `.glb`.

## Requirements

- Blender 5.2.1 LTS at `/Applications/Blender.app` (uses its bundled Python)
- No virtualenv needed — `./contour` shells out to Blender

## Decisions

Every structural choice here has a short ADR in [docs/adr/](docs/adr/) with the
alternatives that were rejected and why. What has *not* been decided yet, and
what each gap blocks, is in [docs/OPEN-QUESTIONS.md](docs/OPEN-QUESTIONS.md).
