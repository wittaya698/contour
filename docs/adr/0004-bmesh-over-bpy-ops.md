# 0004 — `bmesh` and the data API over `bpy.ops`

**Status:** Accepted · 2026-09-20

## Context

`bpy.ops.*` is what every tutorial, and the GUI's own Python console, produces —
so it dominates the examples an agent has seen. It also depends on context: the
active object, the selection, the area type. Under `--background` that context
is frequently wrong or absent, producing `poll() failed, context is incorrect`
or, worse, silently operating on the wrong object.

## Decision

Geometry is built with `bmesh` and direct data assignment. Modifiers are added
through `object.modifiers`, not operators. `bpy.ops` is used only for calls
listed in `lib/ops_whitelist.py`, and then only through `lib.ctx_override`.

## Consequences

- An entire class of headless failures — including the silent ones — disappears.
- `build.py` reads as a description of the mesh rather than a recording of clicks.
- More verbose code, and fewer matching examples in the wild, so the agent
  leans harder on `./contour api` and the recipes file (ADR 0008).
- Some operations genuinely have no `bmesh` equivalent. The whitelist is the
  pressure valve; adding to it requires a note saying why.

## Rejected

- **`bpy.ops` freely** — fastest to write, most examples, silent context bugs.
- **Geometry Nodes built by script** — genuinely the modern Blender approach and
  non-destructively tweakable afterwards, but node-graph construction in Python
  is verbose, diffs badly, and is awkward to author blind. Worth revisiting if
  parametric tweaking inside Blender becomes a requirement.
- **Mixed with a context-override helper and no default** — drifts to
  ops-everywhere, because that is what the examples look like.
