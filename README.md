# Contour

Code-authored Blender game assets. A model is a Python script, not a file you
sculpt — so it is diffable, reproducible, and mechanically checkable.

Every build starts from an empty scene and runs `build.py`. `verify.py` then
measures the result against a spec you wrote and reports pass or fail per
check. There is no hand-editing step to forget or repeat.

## Install

You need **Blender** and **Python 3** on `PATH`. Nothing else — no virtualenv,
no `pip install`, no dependencies. `./contour` is a stdlib launcher that shells
out to Blender and runs everything inside Blender's own bundled Python.

```sh
git clone <this repo> Contour
cd Contour
./contour install-hooks              # required, see below
./contour selftest                   # proves the install works end to end
ln -s "$PWD/contour" ~/.local/bin/   # so you can run it from a model space
```

`selftest` builds a fixture, verifies it, renders it, exports a `.glb` and
re-imports it, and deliberately corrupts the build in 19 ways to prove the
checks can actually fail. If it passes, you are installed.

**`install-hooks` is not optional.** It copies `tools/hooks/pre-push` into
`.git/hooks/`, which is what stops model content ever reaching a remote
(ADR 0011). It is per clone, and nothing else enforces it — run it before you
add a remote, not after.

### Blender location

The launcher looks for Blender at
`/Applications/Blender.app/Contents/MacOS/Blender`. Anywhere else, point
`$BLENDER` at the binary:

```sh
export BLENDER=/path/to/blender
```

Developed against **Blender 5.2.1 LTS**. Other versions may work, but the
toolkit assumes API signatures it can check at runtime rather than recall —
see `./contour api` below. A build that takes longer than 300 s is killed.

### Why the symlink

Models do not live in this repository (ADR 0015). You work inside a *model
space* — its own directory, its own git repo — and run `contour` there, so the
launcher needs to be on `PATH`. It resolves its own location through the
symlink, so the toolkit can be moved later and only the link needs relinking.

## Make a model

A model is a directory of its own, anywhere you like, with its own git
history. It is never pushed. Spaces are found by their marker, not their
path, so the location is yours to choose — `project/` under the toolkit and a
sibling directory both work, and a space can be moved between them at any time
with `mv`.

If you keep them under the toolkit, note that `git clean -xdff` there deletes
them. Plain `git clean -xdf` does not — it skips nested repositories.

`contour init` makes the directory in the current one, runs `git init`, writes
the `.contour/project` marker and copies in the agent's rules: a `CLAUDE.md`,
the spec guard's settings, and the `build-model` and `release-model` skills. It
also installs a pre-push stub that refuses every push. It never overwrites a
file that already exists, so it can adopt a directory you have started.

```sh
cd ~/Workspace                     # or project/ under the toolkit, or anywhere
contour init chair && cd chair
cp ~/photos/*.jpg refs/            # whatever you are working from
cp /path/to/Contour/schema/spec.schema.yaml spec.yaml
$EDITOR spec.yaml                  # dimensions + tolerances, parts, budgets
$EDITOR build.py                   # bmesh + the data API, authored in mm
contour doctor                     # is the space in step with the toolkit
contour check                      # no model name: you are standing in it
```

`check` prints one line per failure and a two-line report when it passes:

```
chair PASS  verify 17/17 | tris 4,210 | height 900mm
  width 420.0 | depth 480.0 | quads 96% | parts 5/5 | mat_slots 2/2 | origin base_center
```

Then look at it, and ship it when it is right:

```sh
contour render                     # 4-view sheet -> sheet.png
contour export                     # .glb, re-imported and re-measured to prove it
git add -A && git commit
```

`lib/kit.py` has the helpers a `build.py` uses — millimetre conversion,
materials from hex, boxes, spheres, cylinders, and `add()` to turn a bmesh
into a placed object. `fixtures/smoke/build.py` is a complete example in ten
lines.

## Commands

| Command | Does |
|---|---|
| `contour check` | build from an empty scene, verify against the spec |
| `contour render` | 4-view orthographic sheet with a 1 m grid and rulers |
| `contour export` | `.glb`, re-imported into a clean Blender and re-measured |
| `contour api <symbol>` | the real signature from the installed Blender |
| `contour selftest` | the fixture through every stage, plus 19 mutants |
| `contour init <name>` | create a model space |
| `contour doctor` | is this space still in step with the toolkit |
| `contour spaces [name]` | list model spaces, or print one's path |
| `contour install-hooks` | install the push guard into this clone |

The first three run inside a model space and take no model name. Outside one
they refuse and say so, rather than guessing.

Blender's stdout is 2–5k tokens of banner per run, so it goes to
`.contour/last-build.log` and only a terse report is printed. Read the log on
failure.

`api` exists because recalled signatures are guesses:

```sh
$ ./contour api bmesh.ops.create_cube
bmesh.ops.create_cube: BMeshOpFunc bmesh.ops.create_cube(bmesh, size=0.0,
    matrix=Matrix(), calc_uvs=False) -> dict(verts=[])
```

## Layout

A model space, anywhere on disk, its own git repository:

```
<space>/
    spec.yaml     your intent, in numbers    (the agent reads, never writes)
    refs/         your intent, in pictures   (the agent reads, never writes)
    build.py      the attempt                (rebuilt from an empty scene)
    sheet.png     the 4-view render you approved
    NOTES.md      what is deferred, and what is undecided
    CLAUDE.md     the agent's rules          (copied from the toolkit; `contour doctor` flags drift)
    .claude/      the spec guard's settings, and the build and release skills
    .contour/     the marker, plus logs               (git-ignored)
    out/          generated .blend and scratch        (git-ignored)
    exports/      generated .glb                      (git-ignored)
    release/v<N>/ archived .blend + .glb + sheet      (tracked, at a tag)
    work/scene.blend  YOUR file — materials, lights, camera (git-ignored)
```

Rebuild the asset and your scene file picks up the new geometry, because you
never worked inside the generated file.

## Branches

This repository is the toolkit — `lib/`, `verify.py`, `schema/`, `fixtures/`,
`tools/`. It builds no deliverable of its own and carries no model content on
any branch, which is what makes it shareable (ADR 0015).

Models are not branches here. Each one is its own repository — under
`project/`, which this repo ignores and the push guard blocks, or anywhere
else you like — with its own history, and it is never pushed. Earlier versions of Contour kept
models on long-lived branches; see
[docs/git-branch-strategy.md](docs/git-branch-strategy.md) for that history and
ADR 0015 for why it changed.

## What git tracks, and what never leaves

Source, specs, reference images, and the render sheet (1024², ~170 KB) per
accepted commit — so `git log` doubles as a visual timeline. The `.blend` is
derivable and stays ignored, except in a release package where it is committed
once alongside the `.glb` and the approved sheet (ADR 0013).

**Model content is never pushed.** Only `master`, the toolkit, reaches a
remote; the `pre-push` hook refuses everything else and refuses any push
carrying model paths, including onto `master` by mistake (ADR 0011). To share
a model, run `./contour export` and hand over the `.glb`.

Backup is therefore file-level: copy the working directory, including `.git`,
to external media. A push will never protect the part that matters.

## Working with an agent

`CLAUDE.md` holds the operating rules an agent must follow here — always the
`./contour` commands and never raw `blender`, never `bpy.ops` outside a
whitelist, never weaken a check to make it pass, and never commit or push
without being asked to. `.claude/skills/new-space` is the workflow for starting
a model. The iterate and release workflows are in `templates/space/.claude/skills/`,
and `contour init` copies them into each model space.

Two of those rules are enforced rather than trusted: `tools/hooks/pre-push`
blocks model content leaving via git, and `tools/guards/spec.py` — which a space
runs as `contour hook spec` — refuses writes to a spec or a reference image that
git already tracks. A spec is the definition of correct, so it is not the
agent's to adjust.

## Decisions

Every structural choice here has a short ADR in [docs/adr/](docs/adr/) with the
alternatives that were rejected and why. What has *not* been decided yet, and
what each gap blocks, is in [docs/OPEN-QUESTIONS.md](docs/OPEN-QUESTIONS.md).
