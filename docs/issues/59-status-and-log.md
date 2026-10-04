# 59 — `status` and `log`

**Type:** AFK · **Source:** ADR 0024, decisions 3 and 6 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

Two connector tools that answer *is it green, and if not, why*.

`status` takes a space and returns its last check's verdict and stats, read from
`last-build.json`; how many marks are open; how many vetoes are uncommitted; and
whether `contour doctor` finds the space out of step with the toolkit. While a run
holds the space, it says the verdict is from before that run. A space never
checked says so, rather than reporting nothing as green.

`log` takes a space and a line count, 40 by default, and returns the tail of
`last-build.log`. It reads the log's own first line and says which stage wrote it,
so a log from `filmstrip` is never passed off as the cause of a red check.

## Acceptance criteria

- [ ] `status` returns the last check's lines and results, even after a later stage has run
- [ ] `status` counts open marks and uncommitted vetoes, and reports `doctor` drift
- [ ] `status` on a held space says a run is live and the verdict is from before it
- [ ] `status` on a space never checked says so
- [ ] `log` returns at most the asked number of lines, and names the stage that wrote them
- [ ] `log` on a log not from `check` says it is not the last check's
- [ ] A space name that `contour spaces` does not resolve is refused, in its words

## Blocked by

- [57](57-the-connector-answers-spaces.md)
- [58](58-the-last-build-keeps-its-verdict.md)
