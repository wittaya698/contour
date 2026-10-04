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

- [x] `status` returns the last check's lines and results, even after a later stage has run
- [x] `status` counts open marks and uncommitted vetoes, and reports `doctor` drift
- [x] `status` on a held space says a run is live and the verdict is from before it
- [x] `status` on a space never checked says so
- [x] `log` returns at most the asked number of lines, and names the stage that wrote them
- [x] `log` on a log not from `check` says it is not the last check's
- [x] A space name that `contour spaces` does not resolve is refused, in its words

## What it came to

Both tools live in `lib/cli.py` beside `spaces`, and `lib/connector.py` only
lists them. A space is resolved by `named`, which is `contour spaces <name>`:
a name that does not resolve fails the call with that command's own `FAIL`
line, and a call that names no space is refused rather than read as all of
them.

`status` returns `verdict` (the whole `last-build.json`, or null), `held`
(who holds the space, or null), `marks` (open ones), `vetoes` (uncommitted),
`doctor` (toolkit `current`/`behind`, scaffold `drift` and `missing`, the
comparison `doctor` and `spaces` already make), and `said`: sentences for the
chat, *never checked* or *a run is live; this verdict is from before it*.

The uncommitted-veto count moved down into a new read-only `lib/vetoes.py`,
because the launcher may never import the console. `console/vetoes.py` asks
it too, so the page and a chat count the same way, and the console is still
the only writer of a veto.

`log` maps the log's first line `$ build` to `check` and names any other stage
as itself. A log that is not the check's says *this log is from <stage>, not
the last check*. A space where nothing has ever run returns no stage and says
so, and `lines: 0` returns no lines, not the whole log.

## Blocked by

- [57](57-the-connector-answers-spaces.md)
- [58](58-the-last-build-keeps-its-verdict.md)
