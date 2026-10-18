# 0032 — A span is measured through the camera

**Status:** Accepted, amended · 2026-10-18 · **amends ADR 0017's "perspective error is disclosed, not corrected", and the anchor of ADR 0016 and `lib/span.py`** ([0017](0017-scaffold-measured-from-references.md), [0016](0016-specs-from-references-and-revision.md), [0022](0022-the-agent-reads-the-references-in-spans.md))

## Context

A span's millimetres are its pixel length times one scale per reference: the
spec's `dimensions.height` over the height of the foreground's box
(`lib/cmd_measure.py`, `Scale`). That holds three assumptions no one states to
the user: the picture is straight on, the object stands upright so its height
in the picture is its height, and the background is one flat colour so the
foreground is the object.

A real reference broke all three on 2026-10-18. `nexus-probe`'s reference is a
three-quarter photograph, from above, of a megaphone lying on a textured wooden
deck. Its anchor is a *width*, 300 mm, which `span.anchor_mm` does not read, so
every span there reported pixels only — while the glossary defined the anchor
as any one real dimension. Had it been a height, the scale would have come from
a foreground box that is mostly deck.

ADR 0017 disclosed perspective error and did not correct it: the references
then were flat-colour renders, nearly orthographic, and the bias was small. On a
photograph it is not small, and a `±` of one pixel per end beside it claims a
precision the picture does not have.

## Decision

1. **A span is measured through the camera, recovered from the picture.**
   Not from a file's lens data, which an AI-made or captured reference does not
   carry, and not by fitting the build, which is circular before there is one.
   Both may later check the answer; neither is the source.
2. **The camera is read from directions.** A **direction** is lines along
   edges parallel in the real object; where they converge is how the camera saw
   that direction (single-view metrology). The agent proposes them, its lines on
   edges measurement found — meaning from the agent, arithmetic from code (ADR
   0017, ADR 0022) — and the user answers each as an agent span: adopt, correct
   or reject. Unanswered, a direction argues for nothing, nor does any span
   along it.
3. **The anchor is a span.** One real dimension the user states, of any kind,
   and on each reference the span it is the length of, proposed by the agent
   and answered by the user. The foreground box no longer sets a scale. A
   straight-on reference is the case where the directions do not converge, not
   a second method.
4. **Three square directions give the camera; ties to the anchor give the
   scale.** Three directions square to each other in the object recover the
   lens and the camera's turn. That fixes a span's direction in the object but
   not its distance from the camera, and a length in the picture shrinks with
   distance. So the anchor scales a span only where the span is tied to it: it
   shares an end with the anchor or with a span already measured, or it lies
   on a plane through one of the anchor's ends, spanned by two of the
   directions. With fewer than three directions, a span along the anchor's
   direction is measured under the same tie, and any other says which
   direction it needs. A span along no direction (a diagonal) gives no number
   and says so, and so does a span tied to nothing, which says what would tie
   it. (Amended on acceptance, 2026-10-18: this said one anchor scales spans
   along any of the directions, which holds only at the anchor's own
   distance.)
5. **The `±` carries the lines.** Every traced line and both span ends are
   moved a pixel each way and the span read again; the `±` is that spread. A
   steep photograph earns a wide one, and a reading too wide to settle a
   tolerance says so by its own number.
6. **Foundations are asked first.** Per reference, the card asks its
   directions, then its anchor, then its spans; a span shows millimetres only
   once its foundations are answered, so a person never answers a span by a
   number that changes after.
7. **Old readings are labelled, then read again.** A reading made by the
   foreground box says so. When its reference's foundations are answered it is
   read again; a spec number that moved by more than its `±` becomes a proposal
   in the ordinary way (ADR 0016). The spec never moves on its own.

## Consequences

- **The lens is ideal.** No distortion is corrected: a phone's wide angle bends
  straight edges, which this reads as perspective. Small at ordinary zoom, and
  disclosed rather than corrected, as ADR 0017 did for perspective itself.
- **The picture's centre is taken for the lens's.** Recovering the lens from
  directions assumes the camera's optical centre is the middle of the picture.
  A cropped photograph, a screenshot or a generated image may not have it, and
  its readings drift by how far off it is. This is disclosed rather than
  corrected, as lens distortion is. A fourth direction, where the object gives
  one, lets the centre be checked rather than assumed. (Added on acceptance,
  2026-10-18.)
- **A picture with no parallel edges measures only along its anchor.** A smooth
  object on a plain background has no directions to give; a second real size
  the user knows can serve as a second anchor.
- **More questions before the first number.** Each reference asks two to four
  foundations before its spans read in millimetres. That is the cost of a
  number that means what it says.

## Rejected

- **Only straight-on references measure.** Honest and cheap, and it would have
  left most photographs a person has unable to give a millimetre.
- **Measure anything, with a warning.** A warning on every span stops being
  read, beside a number whose error nobody measured.
- **The user traces the directions.** Tedious, and edge-finding is what
  measurement already does well; the agent proposes and the user answers, as
  with spans.
- **One real size per direction.** Asks for numbers people often do not know;
  kept only as the fallback in decision 4.
