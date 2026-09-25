# 13 — Spend is live, and `tools/tokens.py` can read it

**Type:** AFK · **Source:** ADR 0019 decision 32

## What to build

Token cost is the second of the three stated priorities, and `tools/tokens.py`
measures it by parsing the Claude Code transcript for this project. A console run
produces no such transcript — so without this slice, the one tool serving that
priority goes blind in the same change that makes runs longer and adds a turn per
gate.

The console has strictly better data than the transcript ever did: the SDK returns
usage per turn, cache reads included. It appends that per turn, and
`tools/tokens.py` learns to read it alongside what it already reads.

**The live display has a second job.** A gate that fires often costs a turn of
re-explanation every time, and seeing that cost is what makes *tune the ask-list
downward* an informed act rather than an irritated one.

**A per-run budget that ends the run was rejected,** on the same symmetry as the
idle timeout and the context limit: silence is not a verdict, and neither is a
threshold set before the user knew what the run involved. With an attended run the
stop is the user.

**A pre-run cost estimate was rejected outright:** it cannot be known, and a wrong
one is worse than none.

## Acceptance criteria

- [ ] Per-turn usage, cache reads included, is recorded where `tools/tokens.py` reads
- [ ] `tools/tokens.py` reports a console run and a terminal iteration in the same units
- [ ] The page shows spend for the run, updating per turn
- [ ] The cost attributable to gate re-explanation is legible
- [ ] No budget, threshold or limit ends a run
- [ ] No pre-run estimate is shown
- [ ] `tools/tokens.py` still reports correctly for a project with no console runs

## Blocked by

- [08 — A gated run, end to end](08-a-gated-run-end-to-end.md)
