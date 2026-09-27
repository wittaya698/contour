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

- [ ] `tests/test_miniyaml.py` covers every feature the docstring claims
- [ ] It covers every refusal the docstring promises, each failing loudly with the field named
- [ ] `tests/test_glb.py` covers truncation, bad magic, chunk order and padding
- [ ] A committed fixture `.glb` proves the parser reads what Blender wrote
- [ ] `lib/kit.py`'s pure half is in the free roster and tested
- [ ] A test fails when a module in the `FREE` roster has no test file
- [ ] The whole suite still runs on a clone with nothing installed
- [ ] `contour selftest` green

## Blocked by

None. The `lib/space.py` part lands with
[17](17-the-space-layout-is-a-function-of-a-space.md).
