# 23 — The measurement becomes data

**Type:** AFK · **Source:** [ADR 0020](../adr/0020-checks-are-pure-over-a-measurement.md) · ADR 0009, ADR 0005

## What to build

The rest of ADR 0020, once slice 22 has accepted it.

`verify.measure()` gathers once from the evaluated scene and then hands back live
`bpy` objects and open `bmesh` handles, so every check iterates geometry in place.
`verify.py` consequently has no test file at all, its pure `report()` and `stats()`
included; `measure`/`release` is a lifetime obligation that `lib/cmd_render.py`
does not honour, leaking every `bmesh` on a raise; and `cmd_render` pays a full
`bmesh` build of every mesh to read two corners of a bounding box, while
`cmd_roundtrip` passes the `verify` module itself as an argument for want of a
handle.

**`lib/measure.py`** gathers per-part summary records and frees every `bmesh`
before returning. `release()` ceases to exist, and the leak goes with it — removed,
not fixed.

**`lib/checks.py`**, in the Blender-free half, holds the six checks plus
`check_spec`, which was already pure. Slice 03's roster proves a check that
acquires a Blender import is a red selftest.

**`verify.py` keeps `run`, `report` and `stats`.** ADR 0002 and ADR 0009 name the
path; it stays what Blender-side code calls, and `report()` gets its first test —
which is where ADR 0005's token budget becomes checkable rather than intended.

**`bounds()` is a separate cheap call** for the render, which asks for what it
needs and pays a depsgraph walk instead of a bmesh per mesh.

**Every mutant stays.** Pure tests join them; they do not replace them. A mutant
proves the gather, the checks and the report are wired together, which no pure
test can show. Each of ADR 0009's thirteen gains a counterpart: the same defect as
a measurement, asserted straight against the check.

**`cmd_roundtrip` stops taking `verify` as a parameter,** because a measurement is
now a thing it can hold.

## Acceptance criteria

- [x] No `bpy` object or `bmesh` handle survives a gather; `release()` does not exist
- [x] Every check is a pure function over a measurement, in the Blender-free half
- [x] `lib/cmd_render.py` calls `bounds()` and builds no bmesh
- [x] `_tris_now(verify)` is gone
- [x] `tests/test_checks.py` covers every check from hand-written measurements, with no Blender
- [x] `report()` and `stats()` have tests, including the green line's token budget
- [x] All thirteen ADR 0009 mutants still fail their named checks
- [x] `tests/test_lib_split.py`'s roster names `checks` free and `measure` Blender-side
- [x] `contour check` output is byte-identical for the fixture and for a green space
- [x] `contour selftest` green

## What it came to

**ADR 0020 implemented in full.** `verify.py` is fifty-four lines and imports no
Blender: `run` gathers a measurement and hands it to `lib/checks.py`, and
`report` and `stats` are what is left beside it. `release()` is gone, so the
leak in `cmd_render` went with it — removed, not fixed, as ADR 0020's decision 2
said.

**One thing the ADR did not draft.** ADR 0020's decision 1 describes the
measurement as one
record per part, and that is not quite enough: the parts check judges *every*
object, and the mutant that proves it adds an empty called `Cube`. So the
measurement carries `objects` — every object name — beside `parts`, and each
check names which of the two it reads. An addition to the shape rather than a
correction to it, and noted on the ADR.

**`bounds()` earns its separate call twice over.** The sheet wanted two corners
and paid a `bmesh` of every mesh to get them; it now walks the evaluated
vertices and builds nothing. The sheet came out at the same 93KB from the same
framing, which is the check that the two readings agree.

**`rotation_rad` is one number for Blender's two spellings.** The old check
asked `rotation_euler` *or*, under `QUATERNION` mode, `rotation_quaternion.angle`.
What the spec asks is `rotation_applied` — whether the object carries any
rotation at all — so the gather answers the largest angle it is turned by and
which spelling held it stops being the check's business. The same rule slice 22
recorded: gather the reading the spec is compared against.

**Twenty-two mutants, and two of them found real gaps.** The first run caught
twenty. The survivors were a scene with nothing in it passing its stated
dimensions, and a UV rule nothing implements being skipped — both the
never-skip rule, which is `verify.py`'s oldest and the one a move is most
likely to drop quietly. Tests added, then 22/22.

**What is unchanged, and had to be.** `contour check` prints byte-identical
output for the fixture and for `beaky-fable` — a fourteen-part, five-material
green space, which exercises the parts, materials and UV paths far harder than
the fixture does. Read before and after against the same build.

**What this slice did not do.** `lib/cmd_roundtrip.py` still defines its own
`_res` beside the `checks.result` it now imports; one verdict shape defined
twice is worth a line, but not in a slice that is already this wide.

## Blocked by

- [22 — Accept ADR 0020](22-accept-adr-0020.md)
