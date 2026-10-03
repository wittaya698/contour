# 48 — The spec carries a rig tree

**Type:** AFK · **Source:** ADR 0023, the spec carries intent as numbers — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

A spec states its **rig** as a `parent:` on each `parts:` entry: the name of the
part it hangs from. Part names are written once, so the tree cannot disagree with
the part list.

```yaml
parts:
  - { name: torso,  count: 1 }                 # no parent: the root
  - { name: neck,   count: 1, parent: torso }
  - { name: arm_L,  count: 1, parent: neck }
```

The schema says so, and verify checks it: exactly one part has no parent; every
parent names a part; the tree has no cycle. A spec with no `parent:` anywhere has
no rig, and nothing here applies to it, so every existing space stays green
without a revision.

As every check must (ADR 0009), each of these has a fixture spec that fails it.

## Acceptance criteria

- [x] The schema documents `parent:` on a part
- [x] A spec with no `parent:` at all builds and verifies exactly as before
- [x] Two roots, an unknown parent and a cycle are each red, with one line naming the part
- [x] Each of those failures is shown by a fixture, so the check proves it can fail

## What it came to

- `checks.rig` judges the tree over the spec alone, straight after `spec` and
  before any geometry, as the verdict `rig`. On green it reads `14 parts from
  torso`; on red, one line naming every problem: `2 roots: tail, torso`,
  `hand_L's parent 'arm_L' is not a part`, `cycle: a, b`.
- A spec with no `parent:` anywhere gets no `rig` verdict at all, so the smoke
  fixture's report is unchanged at 17/17 and every existing space stays green.
- A rigged part with a `count` other than 1 is red, `toe x4: one bone per part,
  count must be 1` — four instances under one name have no one bone to be, and a
  rule the verifier cannot enforce fails rather than guesses (ADR 0009). The ADR
  did not say this; it is what *one bone per part* comes to.
- The spec check accepts `parent:` on a part and refuses one that is not a name.
- The fixtures are specs written by hand in `tests/test_checks.py`, as ADR 0020
  has the other checks' counterparts; and a fourteenth mutant, *rig with two
  roots*, proves the verdict reaches the report end to end. `contour selftest`
  PASS, `mutants 14/14`.

## Blocked by

None - can start immediately.
