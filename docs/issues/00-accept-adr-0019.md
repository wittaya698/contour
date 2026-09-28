# 00 — Accept ADR 0019

**Type:** HITL · **Source:** [ADR 0019](../adr/0019-console-a-driven-agent-behind-a-gate.md)

## What to build

Nothing is built here. ADR 0019 is **Proposed**, and no slice below should start
against a proposal: every one of them cites a numbered decision in it, and a
decision that can still move is not a specification.

Two inconsistencies in the index are settled in the same motion.
`docs/adr/README.md` marks ADR 0018 **Proposed** while `0018-*.md` records
**Accepted** and the canvas is built and shipping. Whichever is right, the index
and the file agree afterwards.

## Acceptance criteria

- [x] ADR 0019's status line reads Accepted, or the ADR is revised and this slice
      is reopened against the revision
- [x] `docs/adr/README.md` and each ADR file state the same status for 0018 and 0019
- [x] The decision numbers cited by slices 01–14 still exist and still mean what
      those slices say they mean

The third one did not hold, and closing it was most of this slice. ADR 0019's
decisions were never numbered, so none of the hundred and seventy-four citations
across the repo resolved to anything. Recovered by subject, the old citations of
ADR 0019 decisions 20 and 22 turned out to mean each other, and the old citation of
ADR 0019 decision 31 meant its thirty-ninth. The decisions now carry numbers, in the numbered-list idiom ADR 0009 and ADR 0020
already use; every citation was remapped by what it claims; eleven that named no
ADR at all now name one; and `tests/test_adr_citations.py` holds it together, so
an ADR cited by number has to number its decisions and a citation has to land
inside the range.

## Blocked by

None — can start immediately.
