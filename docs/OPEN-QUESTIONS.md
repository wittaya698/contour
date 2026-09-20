# Open questions

Decisions deliberately deferred. Each says what is blocked by it and what
happens by default if nobody decides.

## 1. What the first model is — BLOCKING

Nothing exists under `spec/` or `models/` yet because the object has not been
named. Needed: what the thing is, overall dimensions in mm with tolerances, a
triangle budget, and a named parts list.

**Blocks:** the first variant branch, and the realism of `fixtures/smoke/`.
**Default if undecided:** `master` stands as a toolkit with a trivial fixture;
no deliverable is produced.

## 2. Target engine — deferred on purpose

`web` / glTF only is implemented (ADR 0006). Unity and Unreal are table entries
plus a transform when wanted.

**Blocks:** nothing today. Engine-specific spec fields — origin convention,
unit scale, material slot budget — stay at glTF defaults until a target lands.

## 3. Triangle budget and UV rules per variant

`schema/spec.schema.yaml` carries the fields; the values are per-variant and
come from the user or from a proposed-and-flagged assumption.

**Blocks:** meaningful `verify.py` output — a budget of 0 fails everything.

## 4. Headless UV unwrapping — the main technical risk

UV operations are likely `bpy.ops.uv.*` only, and operator context under
`--background` is exactly the failure class ADR 0004 avoids elsewhere. Not yet
attempted on this install.

**Blocks:** `uv.required: true` in any spec.
**If it proves unworkable headlessly:** either compute UVs directly in `bmesh`
(more work, fully deterministic), or declare UVs a manual step done in the
linked working file and drop the check. Decide only when a model needs UVs.

## 5. Whether `fixtures/smoke/` needs a golden-file hash

Rejected for now (ADR 0005) as brittle. Revisit if a Blender update ever
silently changes geometry output.

## 6. Remote

No remote is configured. Nothing is backed up off this machine.
