# 89 — `contour request` starts an unattended run

**Type:** AFK · **Source:** ADR 0027, decisions 3, 4, 5, 6, 10 and 11 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

`contour request <space> "<prose>"` starts that space's console detached,
with no browser, on the prose, and prints JSON: started, or why not. It is
refused when the space is held, when a console is open on it (in the lobby's
words), and when no ceiling is set. The prose is all a request carries.

The console it starts lives as long as its run, not a page: finished or
stopped with no page open, it exits; a page opened meanwhile takes over the
page's rule. In that run a spec write, a reference write and saving a version
always gate, whatever the ask-list says, and that holds to the end even with
the page open. The page says *this run was asked for by <requester>; some
actions always ask you*.

This slice stays whole for issue 08's reason: split, it leaves a merged state
in which an unattended run exists without its floor or its ceiling.

## Acceptance criteria

- [ ] A request on an idle space starts a run with no browser and says so in JSON
- [ ] Refused, each in its own words: space held, console open, no ceiling
- [ ] The run's process exits when the run ends and no page is open, and outlives an idle clock while a gate is parked
- [ ] With an ask-list that lets everything through, a spec write, a reference write and saving a version still gate
- [ ] Opening the page mid-run does not lift that floor
- [ ] The record and the page both name who asked

## Blocked by

- [86](86-a-space-records-its-latest-run.md)
- [88](88-a-ceiling.md)
