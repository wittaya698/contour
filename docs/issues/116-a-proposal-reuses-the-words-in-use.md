# 116 — A proposal reuses the words in use

**Type:** AFK · **Source:** ADR 0030, decision 3 — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

When the agent proposes, it is given every approved topic across the spaces and
told to reuse a word wherever one fits. The page marks any proposed word that no
model carries yet as *new*, so growing the vocabulary is a choice the user sees
being made.

## Acceptance criteria

- [x] With `creature` on beaky, a proposal for a second animal offers `creature`, not a variant of it, on a real run
- [x] A word on no model is shown as *new*; a word on another model is not
- [x] What the agent is given holds names and topics only (ADR 0030, decision 8)

## Blocked by

- [114](114-a-space-carries-its-approved-topics.md)
- [115](115-spaces-are-found-by-topic.md)
