# 117 — The first green build proposes

**Type:** AFK · **Source:** ADR 0030, decision 4 — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

The agent proposes topics unprompted once in a model's life: at its first green
**build**, the first moment it knows what the model is. After that it proposes
only when asked. A model already past its first green — every space today — is
not prompted by this; issue 118 covers those.

## Acceptance criteria

- [ ] A new space's first green build leads to one proposal — `check` says so once (tested); the proposal on a real build is issue 120's
- [x] A later green build, or a red then green, leads to none
- [x] Asked *suggest topics*, the agent proposes at any time
- [x] An existing space that is already green is not prompted

## Blocked by

- [114](114-a-space-carries-its-approved-topics.md)
