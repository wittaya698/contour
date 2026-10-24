# 163 — `export` asks the glTF validator

**Type:** AFK · **Source:** a scan of the toolkit for tools and libraries, 2026-10-24

## What to build

`contour export` re-measures the `.glb` it wrote with `lib/glb.py`, which reads
the container without Blender (ADR 0006). That says the file measures right. It
does not say the file is valid glTF: an accessor's `min`/`max` that disagrees
with its data, a buffer view out of range, normals that are not unit length.
A game engine is entitled to refuse any of those, and nothing here would notice.

Khronos's [glTF-Validator](https://github.com/KhronosGroup/glTF-Validator) is
the reference check for that, and it shares no code with Blender's exporter.
When `gltf_validator` is on the `PATH`, `contour export` runs it on the file it
wrote and reports its errors as a failed check, by name. When it is not, the
report says the check was skipped and how to install it, and the export is
otherwise unchanged: the launcher stays stdlib-only and installs nothing
(README, Install).

Warnings and infos from the validator are not failures; only its errors are.

## Acceptance criteria

- [ ] With the validator present, a valid `.glb` passes and the report names the check (tested)
- [ ] With the validator present, a `.glb` it calls invalid fails `export`, and the report carries its first errors (tested, with a stand-in validator)
- [ ] Without the validator, `export` passes as today and says the check was skipped and how to get it (tested)
- [ ] The validator's own output does not reach the agent beyond that report (tested)
- [ ] README says what the check is and that it is optional

## Blocked by

None - can start immediately
