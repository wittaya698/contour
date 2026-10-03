# 49 — Seams and pivots measured at rest

**Type:** AFK · **Source:** ADR 0023, where a part turns is measured, not declared — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

For every part with a parent, verify measures its **seam** — the ring along which
its surface crosses its parent's — and its **pivot**, the seam's centre. Then:

- a joint with no seam is red: the part has floated off, or only touches at a
  tangent point, which is no seam (ADR 0023);
- a part whose origin is further from its pivot than the spec's tolerance is red.

The tolerance is a spec field, the user's like every other. A spec with a rig and
no tolerance is red for the missing field, not silently lenient.

This needs no bones: it is geometry at rest, and a measurement the checks stay
pure over (ADR 0020). It is what makes `build.py`'s hand-placed origins checked
rather than trusted.

## Acceptance criteria

- [x] Each joint's seam and pivot are measured from the built geometry
- [x] No seam is red, naming the part and its parent
- [x] An origin off its pivot beyond tolerance is red, with the distance in mm
- [x] A rig with no origin tolerance is red for the missing field
- [x] A fixture shows each failure: a floating part, a tangent part, an origin off its pivot

## What it came to

- The gather records, for **every** pair of parts and not only the joints (it
  reads no spec), the points where an edge of one passes from strictly inside the
  other to strictly outside, and their mean as the seam's centre. A vertex within
  1 µm of the other surface is neither in nor out, so a part flush on its parent
  or tangent to it has no crossing — the face-to-face case is caught as surely as
  the point. Each part record also gains its world `origin`.
- `seams` is red per joint with no crossing, saying why as far as the two boxes
  can: `neck has no seam with torso: floats 50.0mm off`, or `touches at most,
  does not cross` when the boxes meet. `pivots` is red per origin past tolerance,
  `neck origin 137.0mm off its pivot (tolerance 1mm)`, and skips a joint with no
  seam, which `seams` has already named. Both read only for a rigged spec.
- The tolerance is `transform.pivot_tolerance_mm`, beside `origin`; a rig without
  it is red, `rig needs transform.pivot_tolerance_mm`, with no default.
- The seam's centre is the mean of crossing points, not a length-weighted ring:
  where edges are dense on one side the centre leans that way. Symmetric parts
  read true; the tolerance absorbs the rest, and 50 will show whether it must.
- The smoke fixture is now rigged: the pillar reaches 5 mm into the plinth and
  the cap, and each origin sits on its seam (`kit.add` gained `pivot_mm`, the
  promise table in `tests/test_kit.py` updated with it). The tree hangs from the
  **cap**, because a root has no pivot and the anchor tests measure from the
  cap's origin at its sphere's centre. Four mutants — floating part, tangent
  part, origin off its pivot, no pivot tolerance — and *rig with two roots* now
  removes a parent. Green report: `seams 2 joints | pivots 0.0/1mm`,
  `mutants 18/18`; `beaky`, unrigged, unchanged at 17/17.

## Blocked by

- [48](48-the-spec-carries-a-rig-tree.md)
