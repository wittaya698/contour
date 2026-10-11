# 115 — Spaces are found by topic

**Type:** AFK · **Source:** ADR 0030, decision 8 — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

Filtering by topic wherever spaces are listed: `contour spaces`, the
**connector**, and the **lobby**. The answer is space names with their approved
topics and nothing else — no spec, no reference, no sheet — so an agent in one
space can read the vocabulary without reading another model.

## Acceptance criteria

- [ ] `contour spaces` shows each space's topics and filters on one
- [ ] The connector answers *which models are `creature`?* with names and topics only
- [ ] The lobby filters its rows by a topic
- [ ] A space with no topics is listed unfiltered and missed by every filter
- [ ] Nothing in the answer comes from a space's spec, refs or sheet

## Blocked by

- [114](114-a-space-carries-its-approved-topics.md)
