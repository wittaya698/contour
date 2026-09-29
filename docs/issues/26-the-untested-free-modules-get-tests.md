# 26 — The untested free modules get tests

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0010, ADR 0006

## What to build

Four modules the pipeline's correctness rests on have no test on their interface.
Every test file referencing them is `tests/test_lib_split.py`, which proves only
that they import.

**`lib/miniyaml.py`** reads `spec.yaml` — the definition of correct. Its own
docstring says *"If a spec needs those, extend this file and its test"*, naming a
test that does not exist. A misparse does not fail loudly; it silently changes what
the **spec** says, which is the one thing ADR 0002 and rule 1 exist to keep still.

Tested with hand-written cases: one per feature the docstring claims — block maps,
a sequence at its key's indent, flow forms, quoted and plain scalars, `>` and `|`
with both chompings, comments — and one per promised refusal: tabs, anchors,
aliases, tags, multi-document streams, `?` keys. **A refusal that quietly stopped
refusing is the failure mode here**, and it is the half nothing currently exercises.
Hand-written rather than differential against PyYAML, because a test that skips on
a bare clone is a test that mostly does not run, and the bare clone is the
constraint ADR 0010 exists for.

**`lib/glb.py`** is the basis of the export **round-trip**, ADR 0006's only proof
an export is correct. Hand-built bytes for the parsing edges — truncation, bad
magic, wrong chunk order, padding — plus one small `.glb` exported from
`fixtures/smoke/` and committed, so something proves the parser reads a file
Blender actually wrote. The fixture is not model content, so rule 8 is untouched.

**`lib/kit.py`** has the most out-of-repo callers of anything here: every space's
`build.py`. It is in the Blender half, so no pure test can import it. Whatever in
it is naming, arithmetic or validation splits into the free half and gets ordinary
tests; the `bmesh` and data-API calls stay and the fixture's build exercises them.
A signature change there currently breaks four spaces before anything says so.

**`lib/space.py`** gets its test with slice 17, which is what changes its shape.

**A structural guard so the gap cannot reopen:** a test asserting that every
module in slice 03's `FREE` roster has a test file. Same idiom as the roster check
itself — a new Blender-free module without a test becomes a finding rather than an
oversight. Not a coverage threshold: a coverage tool is a dependency, and having
none is the property the roster protects.

## Acceptance criteria

- [x] `tests/test_miniyaml.py` covers every feature the docstring claims
- [x] It covers every refusal the docstring promises, each failing loudly with the field named
- [x] `tests/test_glb.py` covers truncation, bad magic, chunk order and padding
- [x] A committed fixture `.glb` proves the parser reads what Blender wrote
- [x] `lib/kit.py`'s pure half is in the free roster and tested
- [x] A test fails when a module in the `FREE` roster has no test file
- [x] The whole suite still runs on a clone with nothing installed
- [x] `contour selftest` green

## What it came to

**The roster guard is `untested` in `tests/test_lib_split.py`.** A free module
counts as tested when a `tests/test_*.py` other than that file imports it; a
helper such as `tests/client.py` does not count. Turned on, it named five, not
two: `glb` and `miniyaml`, and also `ops_whitelist`, `refs` and `signals`, which
were exercised only through the canvas and the console or not at all. Each
now has a test on its own interface.

**`miniyaml` was not refusing `?` keys.** `? w: 1` came back as a key called
`? w`, and `? w` as a value or a sequence item came back as text: three of the
six promised refusals were a spec silently saying something else. A tab after a
`- ` became part of a string. Now every refusal names its construct and the
line it is on (`line 2: aliases are not supported — 'depth: *big'`), and a
`---` or `...` anywhere is refused as a second document rather than reported as
unparsed content. `tests/test_miniyaml.py`: 19 feature cases, 11 refusal cases.

**`glb.load` read a damaged file as a smaller one.** A BIN chunk cut short came
back as a shorter buffer, a file longer than its header said was read, BIN
before JSON was accepted, and a second JSON chunk replaced the first. It now
refuses all of those, a misaligned chunk, and truncation anywhere, as
`ValueError` saying what is wrong instead of a `struct.error`. Unknown chunk
kinds are still skipped, as the format requires. `tests/data/smoke.glb` is
`contour export` of the fixture, and its test measures it against the fixture's
`build.py` numbers, not against an earlier answer from the parser.

**`kit`'s pure half is `lib/units.py`**, in the free roster: `mm`, a `size` that
must be three positive lengths, and `linear` for a six-digit hex colour. `kit`
calls it and re-exports `mm` and `MM`, so no space's build changes; every colour
and box size in the spaces on this machine was checked against the new
validation first. `tests/test_kit.py` pins `kit`'s public signatures by reading
its source, so a change breaks a test here before it breaks four spaces.

**`ops_whitelist` became rule 4 as a check** on the toolkit's own code: every
`ctx_override.call` names a listed operator, nothing else in `lib/` or the
fixture's build reaches `bpy.ops`, and every entry gives ADR 0004's reason.

36 mutants over the new code, each caught by the file that claims it. The first
pass left four alive (ints read as floats, a chunk lying about its own length
behind an honest header, a chunk header cut at the end, a container with no
chunks), and each got a test. With `python3 -S` and no `$BLENDER`, the suite
runs 510 tests with 6 skips (`FixtureTest`). `contour selftest` PASS.

**Found, not fixed:** a repeated key in a spec is still silently last-wins,
which the docstring does not promise to refuse. `kit.cylinder_bm` and
`kit.bake_transform` are pinned but not exercised by the fixture's build, and
the committed `.glb` has no rotated node, so `glb`'s rotation arithmetic is
tested only by the round-trip's mutants.

## Blocked by

None. The `lib/space.py` part lands with
[17](17-the-space-layout-is-a-function-of-a-space.md).
