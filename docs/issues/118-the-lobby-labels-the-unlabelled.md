# 118 — The lobby labels the unlabelled

**Type:** AFK · **Source:** ADR 0030, decision 7 — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

One act the user starts in the **lobby**: for every space with no topics, read
its last sheet and propose topics for all of them together, on one page, from
one vocabulary. It edits and builds nothing and is not a **run**, so it holds no
space. Each space's proposal is an approval waiting there until answered.

## Acceptance criteria

- [ ] Started on the seven spaces under `project/` (or copies), one page shows a proposal per unlabelled space — one card per space is tested with a scripted agent; the real agent on the real spaces is issue 120's
- [ ] One word is proposed in one spelling across all of them — one session from one vocabulary, words kept in one spelling (tested); what the real agent proposes is issue 120's
- [x] Approving or striking a word is per space; the user can strike `creature` for trail-cube and keep it for beaky
- [x] A space already labelled is skipped
- [x] While a proposal waits, its space refuses a request; once answered, it takes one
- [x] No space's files change before its proposal is answered

## Blocked by

- [116](116-a-proposal-reuses-the-words-in-use.md)
