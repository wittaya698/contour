# 117 — The first green build proposes

**Type:** AFK · **Source:** [ADR 0030](../adr/0030-topics-label-a-model-for-finding.md), decision 4

## What to build

The agent proposes topics unprompted once in a model's life: at its first green
**build**, the first moment it knows what the model is. After that it proposes
only when asked. A model already past its first green — every space today — is
not prompted by this; issue 118 covers those.

## Acceptance criteria

- [ ] A new space's first green build leads to one proposal
- [ ] A later green build, or a red then green, leads to none
- [ ] Asked *suggest topics*, the agent proposes at any time
- [ ] An existing space that is already green is not prompted

## Blocked by

- [114](114-a-space-carries-its-approved-topics.md)
