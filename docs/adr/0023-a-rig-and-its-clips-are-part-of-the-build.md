# 0023 — A rig and its clips are part of the build

**Status:** Proposed · 2026-10-03

> **Accept on a probe, then a tracer bullet.** First: on Blender 5.2.1, an armature's
> bones can be created through `Armature.edit_bones.new` with no `bpy.ops` beyond one
> `object.mode_set` called through `lib.ctx_override` — or not at all. Then: `beaky`
> carries a rig and an on-the-spot `walk`, green on every check below, round-tripped
> through `.glb`, and approved from its filmstrip.

## Context

`beaky`'s spec has said *"Rigged later: each part's pivot at its joint, neutral pose
as in the refs"* since it was written, and its `build.py` already places every part's
origin where it judged that joint to be. Nothing checks either. Every instrument
Contour has — measurement, the sheet, the round-trip — looks at one pose.

The question was whether animation belongs in this toolkit at all, or in a repository
of its own. A rig is part of the asset: the `.glb` must carry mesh, skin and clips
together, so a separate pipeline would have to import Contour's output and add to it
— two sources of truth for one model, against ADR 0001.

## Decision

**Animation is in the build.** One space, one `build.py`, one `.glb`: mesh, rig and
clips rebuilt together from an empty scene. An animated model is the same model, not
a variation (ADR 0015), so it is the same space. The machinery — rigging, keying,
the clip checks — lives in the toolkit, as `lib.kit` does; a space's `build.py`
only declares.

**The spec carries intent as numbers.**

- The **rig** is a `parent:` on each `parts:` entry. One part has none and is the
  root; a second part without one is red. Part names are written once.
- A **clip** is a `clips:` entry: frames, fps, `loop`, a one-line `feel`, and
  **key poses** as degrees per bone, in its parent's frame, from rest, with a
  tolerance. A looping clip's closing frame is implied by `loop: true`, not written.
- The rig and clips arrive through rule 1 like any spec change, bumping `revision:`.

**Where a part turns is measured, not declared.** A part's **seam** is the ring
along which its surface crosses its parent's; its **pivot** is the seam's centre.
Every joint must have a seam, so parts overlap slightly rather than merely touch.
`build.py` still places each origin at the pivot, and the origin is *checked*
against the seam centre — one answer to where a part turns, and it follows the shape.

**The bind is an armature with rigid weights**, one bone per part, each part's
vertices wholly on its bone, built through the data API. If the probe shows bones
cannot be made with at most one whitelisted `object.mode_set`, the fallback is
node animation — parts parented as objects, clips keyed on the objects — which
needs no `bpy.ops` and no armature, and is a dead end only for a mesh that bends.

**What is checked.** Shape checks keep measuring the rest pose and do not change.
On every build, beside them:

- a seam exists at every joint, and each origin sits on its seam's centre;
- each clip's length, its loop closing, and every key pose within tolerance;
- no part enters another at **any** frame, except a part and its parent at their
  seam — and that seam may not grow beyond a tolerance as the part turns, which is
  what catches a wrong pivot without a picture.

On export, the round-trip re-measures **counts** (bones, clips, frames) and **where
every part ends up** — world-space bounding-box corners at each key and at frames
between them, `.glb` against `.blend`. Not angles: the glTF importer re-orients
bones, so an angle comparison would be red on a correct file. Angles check intent
against the spec; positions check fidelity against the build.

**What is seen.** At a checkpoint only, a **filmstrip** — six side and six front
frames on the sheet's grid, one 1024² image, labelled with its build — at the cost
of one sheet. Never on every build (ADR 0005).

## Consequences

- `beaky`'s hand-placed origins meet a check for the first time. By arithmetic
  over its constants, four of them disagree with their seam (neck by ~137 mm, hand
  ~73, leg ~34, arm ~27) and the head has no seam at all — its bottom and the
  neck's top are both at z 1310. All are `build.py` fixes; the spec's
  "pivot at its joint" is what the seam makes precise, so no spec change.
- Four new tolerances — key-pose angle, seam growth, origin-to-seam, and
  round-trip position — are the user's. Any drafted are flagged as the agent's,
  loudest of all.
- `object.mode_set` may become the whitelist's fourth line, with the reason that
  bone creation has no data-API path outside edit mode.
- The first slice is the probe, then `walk` on `beaky`.

## Deferred

- **Root motion.** `walk` is on the spot. Whether travel belongs to the clip or to
  the game is its own decision.
- **Playback.** Seeing the clip move, in the canvas or console, means a glTF viewer
  on a page of a stdlib-only toolkit (ADR 0010). The filmstrip is what is approved
  from until then.
- **More clips.** `idle` (a subtle loop) and `wave` (a non-looping clip on one
  chain) follow once `walk` is green and round-tripped.

## Rejected

- **A separate repository for animation.** Two pipelines over one asset, with the
  second importing the first's output; it would rebuild the runner, the whitelist,
  the export round-trip and the push guard.
- **A second build stage in the same space** (`animate.py` over `build.py`'s
  output). Rebuilding from empty means it saves no time, and a mesh change could
  silently break a bind built by a different file.
- **Pose references in `refs/`.** Measuring a 3D joint angle off a 2D picture is a
  harder problem than spans, for intent the spec states better as numbers.
- **Pivots as numbers in the spec.** Fourteen coordinates that go stale the moment
  the shape changes.
- **Collisions checked only at key poses.** Mid-swing, between keys, is where a
  hand passes closest to the torso.
