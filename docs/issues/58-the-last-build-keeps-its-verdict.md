# 58 — The last build keeps its verdict

**Type:** AFK · **Source:** ADR 0024, decision 6 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

`last-build.json` becomes what its docstring already says it is: the last build's
verdict. Today it stores whether the build got as far as being judged and nothing
else, and `report.json` — the only file holding check lines — is deleted at the
start of every stage, so a filmstrip or a render run since the last `check`
leaves no record of what that check said.

`check` writes the whole report there: pass or fail, the report lines, the
per-check results, the seconds it took, the build fingerprint, and when. One
writer, as today. A stage that died is still recorded as not built.

## Acceptance criteria

- [x] After `contour check`, `last-build.json` holds pass or fail, the lines, the results, the seconds, the fingerprint and the time
- [x] After a later `contour filmstrip` or `contour render`, it still holds that check's verdict unchanged
- [x] A build that died before verify is recorded as not built, with its lines
- [x] `check` is still its only writer
- [x] The console's panel still reads it, and still labels a failed build as before

## Blocked by

None - can start immediately

## What it came to

Done, 2026-10-04. `panel.record` saves `built`, `ok`, `lines`, `results`, `secs`,
`build` and `when`, and the panel still reads only `built`. A build that died
names no build (`build` is null), because the `.blend` on disk is the one from
before it, and naming it would repeat the mistake `built` was written to prevent.
The verdict is written before the sheet is drawn, so a failed render's `warn` lines
are the report's and not the verdict's.
