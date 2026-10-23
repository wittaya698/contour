# 155 — A new spec is written whole the first time

**Type:** AFK · **Source:** the console run that checked issue 151, 2026-10-23

## What to build

A new-space run's first spec write was refused twice before the gate showed
it: once for having no `revision:` line (*a spec write is the whole change,
revision bump included*), then for a case that did not name `10000, 0.01, 0.1,
1024`. Both refusals were right. Together with two refused calls before them,
the page said *4 stops cost 38 extra turns*.

`NEW_SPACE` step 4 says to draft `spec.yaml` and flag every number, but not
that a new spec carries `revision: 1` nor that its case names every number it
sets, the toolkit's usual ones included. Say both there, in the words the
refusals use, so the first write is the one shown.

## Acceptance criteria

- [x] `NEW_SPACE` step 4 says a new spec is written with `revision: 1`
- [x] It says the write's case names every number the spec sets, with why, the toolkit's usual values too
- [x] Looked at in a real console: a new space's first spec write reaches the gate without a refusal

## Found (2026-10-23)

`NEW_SPACE` step 4 now says a new spec is written whole, with `revision: 1`,
and that its case names every number it sets, with why, the toolkit's usual
ones too (`test_plain_voice.FirstWriteTest`).

Looked at in a console the same day, in a new space with the walkie-talkie
photo. The first spec write carried `revision: 1` and a case that named
every number, the usual ones with why. It was still refused once: *your case
names what it sets: 8000*, for a case that said *About 8,000 triangles*, which
is how *Speaking to the user* tells the agent to say a triangle budget. The
gate read `8,000` as 8 and 000. It now reads a number with its thousands
marked by a comma or a space as well, beside the plain reading, so it lets
more cases through and refuses none (`test_gate.NamedAsWrittenTest`). The
second write, *8000 triangles*, reached the gate.

Looked at again with the gate fixed, in a second new space: the first spec
write carried `revision: 1` and a case saying *About 6,000 triangles*, and it
reached the gate with no refusal before it.

## Blocked by

None - can start immediately
