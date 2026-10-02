# 38 — Create a variation of a space

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 4

## What to build

A *variation of this* action on each row of the **lobby**. A variation is a new
space, never a copy (ADR 0015; `beaky-lite`, `-fable` and `-solo` were all made
this way). So this is slice 37's create, with one difference: the first prompt
points the agent at the source space's `spec.yaml` and `build.py` **for
reference**.

Nothing is copied: not the spec, not `build.py`, not `refs/`. Reference images the
variation needs are brought in by the user in its own run. A copied spec would
arrive already agreed to, and the variation's contract has to be confirmed as its
own.

## Acceptance criteria

- [x] The new space contains exactly what `contour init` makes, and nothing from the source
- [x] The console's first prompt names the source space and its `spec.yaml` and `build.py` paths, as reference
- [x] The source space is not modified, and gets no presence from the new console
- [x] The default name suggests `<source>-` and must still be edited to something new

## What it came to

- A variation is `/create` with `of`, the source's path, which must be a space
  the lobby lists, as a rename's path must; anything else is refused before
  `init` runs. The source's name and path reach the console as
  `--begin variation --of <space>`, never as prompt text: the console refuses an
  `--of` with no `.contour/project` and exits 2, and writes the prompt itself
  from the source's layout. The prompt is the new-space prompt with the
  variation's lines in front, so the flow's steps are written once.
- The prompt says to read the source's `spec.yaml` and `build.py` for reference
  only, never to write in that space, and that this spec is confirmed as its
  own.
- On the page, each row gets *Variation of this…* where `create` is granted.
  It opens the create form with the name as `<source>-` and the location as the
  folder the source sits in. `<source>-` is a legal name, so it is the page that
  keeps Create disabled until the name is edited; the server would accept it.
- The new console's presence is on the new space only, and the source is
  byte-for-byte unchanged, both tested. Nothing was copied in the first place,
  so those tests guard rather than drive.
- Checked by hand by the user before the lobby branch landed, as was 37.

## Blocked by

- [37](37-create-a-space-from-the-lobby.md)
