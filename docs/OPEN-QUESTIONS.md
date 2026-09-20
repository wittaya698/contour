# Open questions

Decisions deliberately deferred. Each says what is blocked by it and what
happens by default if nobody decides.

## 1. What the first model is — RESOLVED 2026-09-20

`beaky`: a 1.7 m stylised character of 14 separate parts, target `web`, rigged later.
Its spec lives on the `beaky` branch, not here, because `master` builds no model.

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

## 6. Remote and backup — PARTLY RESOLVED 2026-09-20

**Resolved: what a remote may ever receive.** Only `master`, the toolkit. Model
content — `spec/`, `models/`, `renders/` — never leaves via git, enforced by
`tools/hooks/pre-push` (ADR 0011). Sharing a model means `./contour export`.

**Resolved: how work survives the disk.** File-level backup of the whole
working directory including `.git`, to external media. No `git push` involved,
so the rule above stays absolute. **Not yet set up — this is the live risk.**
`beaky`'s spec and `build.py` exist on one disk today.

**Still deferred: whether to have a remote at all.** Nothing needs one. If one
is added it will be for the toolkit, and the hook already decides what it may
take.

**Blocks:** nothing. **Default if nobody decides:** no remote, and no backup
either — which is the part worth deciding on purpose rather than by drift.

## 7. Sheet size versus "512px thumbnail" — RESOLVED 2026-09-20

Kept the single 1024² sheet. Measured at 93 KB (fixture) and 169 KB (`beaky`), about
34 MB over 200 commits, so the size constraint that motivated 512px did not bind. ADR
0007 and the README now describe what `./contour render` writes.

**Revisit if:** a model's sheet passes ~400 KB. `lib/cmd_render.py` already holds the
pixels as an array, so writing a second, downscaled file to `renders/` is a few lines.

## 8. What `materials.max_slots` limits

Implemented as the number of distinct materials in use across the whole model. The
schema comment says "engine draw-call budget", which fits, but a per-object reading
is also plausible. Decide before a spec depends on the difference.

## 9. Spec fields `verify.py` rejects as unsupported

Deliberately failing, not skipped (ADR 0009): named `dimensions` sub-measurements
(the schema's `seat_height`/`part:` example has no defined measurement), `origin:
world_origin` (no defined meaning for a whole model), UV overlap checking (question 4)
and `udim`. Each needs a definition before it can be enforced.

## 10. `base_center` is the bounding box footprint centre

`verify.py` reads `origin: base_center` as: bounding box minimum Z at 0, and the centre
of its X/Y extent at the origin. For an asymmetric model, such as one with a beak, that
centre is not the midpoint between the feet. Say so if a rig needs the feet centre.
