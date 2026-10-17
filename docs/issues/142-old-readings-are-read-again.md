# 142 — Old readings are read again

**Type:** AFK · **Source:** ADR 0032, decision 7 — [a span is measured through the camera](../adr/0032-a-span-is-measured-through-the-camera.md)

## What to build

Readings made by the foreground box say so. When their reference's
foundations are answered, each is read again through the camera.

- **The spec never moves on its own.** A spec number whose reading moved by
  more than its `±` becomes a proposal in the ordinary way: the span, the old
  number and the new, for the user to confirm (ADR 0016).
- **Nothing is deleted.** The old reading is closed as superseded, as a
  correction's is.
- `contour doctor` counts a space's readings still made the old way.

## Acceptance criteria

- [ ] An old reading is labelled as made the old way, on the page and in the list
- [ ] Answering a reference's foundations reads its old readings again
- [ ] A spec number that moved beyond its `±` is proposed, never written
- [ ] `contour doctor` says how many old readings a space still has

## Blocked by

- 141
