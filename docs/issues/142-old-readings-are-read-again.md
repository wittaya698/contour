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

- [x] An old reading is labelled as made the old way, on the page and in the list
- [x] Answering a reference's foundations reads its old readings again
- [x] A spec number that moved beyond its `±` is proposed, never written
- [x] `contour doctor` says how many old readings a space still has

## What was built

- **Read again inside the answer that completes the foundations.** It is 141's
  re-read, extended (`span.reread`). A span holding a reading made at a flat
  scale is read through the camera, and only once that gives millimetres.
  Then `marks.supersede` closes the old reading as `superseded` and keeps it,
  adds the new one with `was` naming the old, and drops the span's `scale`.
  From then on it is a camera span like any other. Until the camera gives
  millimetres, the old reading stays open and labelled. The answer's slip
  holds all of it, so an undo puts it back byte for byte.
- **Labelled on the page.** A reading is recognised as made the old way by
  its text, *(246 px at 0.500 mm/px)*, which only the foreground box's scale
  wrote. The card shows its number with *made the old way, by the foreground
  box: read again once this picture's directions and anchor span are
  answered*. The list labels it the same way, or *read again through the
  camera* once superseded.
- **Proposed, never written.** Nothing records which spec number a span
  backs; the agent's own comments in `spec.yaml` say that. So the toolkit
  gives the agent the argument, and the skill tells it to make the proposal.
  `contour measure --standing <id>` gives the new number and *was 123 mm ±1
  mm, made by the foreground box (m6)*. The build-model skill says a number
  that moved by more than its ± is a proposal like any other, naming the span
  and both numbers. Re-reading writes only `marks.json`.
- **`contour doctor`** counts open readings made at a scale: *NOTE 2 readings
  made the old way, by the foreground box: each is read again through the
  camera once its reference's foundations are answered on the canvas*. A span
  drawn with no anchor kept no scale and read pixels, so it is not counted.

`tests/test_old_readings.py`, and the doctor case in `tests/test_launcher.py`.
Looked at in the canvas, driven headless, on the painted angled box with one
span drawn at 0.5 mm/px. Before the foundations were answered, the card and
the list said *52 mm ±1 mm* was made the old way. After they were answered,
it read *204 mm ±16 mm* through the camera, against a true 200 mm. The old
reading stayed in the list, labelled as read again.

## Blocked by

- 141
