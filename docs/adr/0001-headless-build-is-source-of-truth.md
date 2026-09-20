# 0001 — Headless build; `build.py` is the source of truth

**Status:** Accepted · 2026-09-20

## Context

An agent can drive Blender three ways: a live session it sends commands to, a
headless script run, or the `bpy` pip module. The choice decides whether a model
has a reproducible origin at all.

## Decision

Every build is `blender --background --python models/<variant>/build.py`,
starting from an empty scene. `build.py` is the source of truth. `out/*.blend`
is disposable output. Blender's own bundled Python is used, never a venv.

## Consequences

- Same input always produces the same output. A commit fully describes a model.
- Diffs are readable Python, not binary blobs.
- The agent is **blind** — it cannot see what it built. This is what forces
  ADR 0005 (tiered verification) to exist.
- A hand-edit to a generated file is destroyed on the next build. This is what
  forces the linked working-file pattern: `out/<v>.blend` is read-only, and
  `work/scene.blend` links its collection, holding materials, lights and camera
  so they survive rebuilds.

## Rejected

- **Live Blender via an MCP addon** — pleasant to work with, but the scene
  accumulates invisible state, so "what produced this file" becomes
  unanswerable. That defeats version tracking outright.
- **`bpy` as a pip module** — nicer Python tooling, but the wheel's version must
  track Blender 5.2.1 exactly or the `.blend` produced will not match the app
  that opens it.
- **`.blend` as source of truth after a bootstrap** — abandons reproducibility
  and diffs after day one.
