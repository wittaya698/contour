# 165 — The suite is measured before it runs in parallel

**Type:** AFK · **Source:** a scan of the toolkit for tools and libraries, 2026-10-24

## What to build

`python3 -m unittest discover -s tests` takes about 240 s for 1625 tests. A
parallel runner (`pytest-xdist`, `unittest-parallel`) is the obvious answer,
and may be the wrong one: the suite starts real consoles and servers on real
ports (issues 27, 94, 95), and if a few tests hold most of the time, running
the rest at once saves little and risks the clashes those issues fixed.

Measure first, with the `slow-suite` skill, on a quiet machine with no other
run of the suite going: per-test and per-module time, and how much of it is
waiting rather than work. Write the finding into this issue. Then, only if it
says the time is spread across many tests that share nothing, add a runner as
a developer tool. A bare clone's `unittest discover` keeps working as it does
today, and nothing shipped depends on the runner.

If the finding is a handful of slow tests instead, each is fixed on its own or
marked slow on purpose with the reason, and no runner is added.

## Acceptance criteria

- [ ] The finding is written here: where the 240 s goes, measured on a quiet machine
- [ ] Either a runner is added as a developer tool, the suite passes under it and under `unittest discover`, and README says how to run it; or the finding says why not
- [ ] No suite timeout is raised

## Blocked by

None - can start immediately
