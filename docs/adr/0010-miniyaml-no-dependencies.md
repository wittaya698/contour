# 0010 — A small in-repo YAML reader instead of PyYAML

**Status:** Accepted · 2026-09-20

## Context

Specs are YAML (ADR 0002) and are read inside Blender's bundled Python, which has no
`yaml` module. The README promises no virtualenv, and ADR 0001 rejects a `bpy` pip
module partly to keep Blender's own Python the only interpreter. The system Python
(3.14) has no `yaml` either.

## Decision

`lib/miniyaml.py` reads the YAML subset the spec schema uses: block mappings and
sequences, one-line flow collections, quoted and plain scalars, `>` and `|` block
scalars, comments. Anything outside the subset (tabs, anchors, aliases, tags,
multi-document streams, `? ` keys, a nested mapping on one line) raises `YamlError`
instead of being guessed at. It was checked value-for-value against Ruby's YAML on
`schema/spec.schema.yaml`, a real spec and an edge-case file. The one known
difference is `-2.5e1`, which this reads as a float (YAML 1.2) and Psych as a string.

## Consequences

- No install step. Specs load identically in the wrapper and in Blender.
- Specs must stay inside the subset. A construct outside it is a loud error, and the
  fix is to extend the reader and add a test, not to loosen it.
- The reader is ~270 lines the project now owns.

## Rejected

- **Vendor PyYAML** — 100+ files into `lib/` for a config file with a dozen keys.
- **JSON or TOML specs** — TOML is in the stdlib since 3.11 and would work, but the
  schema, the spec and every doc already read as YAML, with comments carrying intent.
- **`pip install` into Blender's Python** — mutates the app bundle; not reproducible.
