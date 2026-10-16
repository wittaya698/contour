# 121 — An approved first green still proposes

**Type:** AFK · **Source:** ADR 0030, decision 4 as amended on acceptance (issue 120) — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

A model's first green can come from an approved check: the run set its build
aside, the person allowed it on the page, and the check ran with no agent there.
Today that check stamps the first green and tells *propose topics* to nobody, so
the model is never offered topics unprompted. Under an ask-list that asks before
builds, that is every unattended first green.

When the first green comes from an approved check, the space keeps that it is
owed a proposal, and the next run in it is told to propose, once. The stamp is
spent only when an agent has been told.

## Acceptance criteria

- [x] An approved check that goes green for the first time leaves the space owing a proposal, and the approval's outcome says so
- [x] The next run in that space is told to propose, once; the run after it is not
- [x] A first green under an agent still proposes there and then, as issue 117 has it (`test_first_green`, unchanged)
- [x] A space already past its first green is owed nothing

## Blocked by

None - can start immediately
