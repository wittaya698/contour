# 124 — A console nobody can reach lets go

**Type:** HITL · **Source:** found in flight, issue 120; beside [39](39-a-background-tab-is-not-a-closed-one.md)

## What to build

Four times in one afternoon a console held a space after its person had lost the
way into it: the console of a finished unattended run started with
`--no-browser`, whose tab nobody ever had, and consoles whose tab was left in the
background — a hidden tab gets an hour, and one at a gate is never ended by
silence (issue 39, on purpose). The lobby says *its tab is the way in*, `contour
stop` says *no run to stop*, and the person cannot free the space short of
killing a process.

Decide, with the user, how a person ends a console they cannot reach — from the
lobby, from `contour stop`, or both — and what that does to a gate it is waiting
at (ADR 0019 rules out answering one by silence). Then build it.

**Decided:** [ADR 0031](../adr/0031-a-console-nobody-can-reach-lets-go.md). Open in the
lobby brings any console's page back, `contour stop` closes a console with no
run, and a gate waiting when a run is stopped from outside is set aside. The
fourth criterion already held, and was tested: the console seen outliving its
request had been opened, then hidden.

## Acceptance criteria

- [x] The way to end an unreachable console is decided and recorded
- [x] A person can end a console from where they are told it holds the space
- [x] A gate pending in it is not answered by ending it
- [x] A finished unattended run's console, never opened, does not outlive its run

## Blocked by

None - can start immediately
