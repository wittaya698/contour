# 14 — Rules 1 and 5 become mechanism-neutral

**Type:** HITL · **Source:** ADR 0019 decision 24 and its first consequence

## What to build

The documentation change that lands when the console lands, and deliberately not
before: until the console works, rewriting the rules describes a mechanism that
does not exist.

**Rules 1 and 5 say what must hold, not how.** Rule 1 is propose → user confirms →
write; rule 5 is show the report, wait for ship, then commit. A proposal and a gate
are not duplicates — the proposal carries the argument, *depth measures 620 against
a tolerance of 600 ±20*, which no gate can show. The *confirm* is what duplicates,
and a ritual performed twice is one that stops being read. So the rules keep saying
propose → confirm → write, and the confirm is prose in a terminal and a gate under a
console. One rule, true in both places. The concrete route stays in the
`build-model` skill.

Injecting a console clause at runtime was rejected: it would contradict the decision
that the console discovers its discipline rather than restating it, it would live in
the console's source invisible to anyone reading `CLAUDE.md`, and it would diverge
the first time a rule changed.

**`README.md`'s promise gains a boundary.** *Nothing else — no virtualenv, no `pip
install`, no dependencies* is still true of `./contour` and false of the console. The
README must say which, and the two-name split exists precisely so that the promise
stays true of the thing that was typed instead of needing a footnote.

This is HITL because the eight rules are the operating contract and their wording is
the user's, not an agent's.

## Acceptance criteria

- [ ] Rules 1 and 5 state what must hold and name no mechanism
- [ ] Neither rule is weakened: the confirm is still required, in both places
- [ ] The concrete terminal route is in the `build-model` skill, not in the rules
- [ ] No rule text lives in the console's source
- [ ] `README.md` scopes the no-dependency promise to `./contour`
- [ ] `docs/CONTEXT.md` still agrees with both rules
- [ ] A reader of `CLAUDE.md` alone can tell what is required of them under either mechanism

## Blocked by

- [08 — A gated run, end to end](08-a-gated-run-end-to-end.md)
- [10 — A build is a gated call, and that gate resolves marks](10-build-is-a-gated-call.md)
