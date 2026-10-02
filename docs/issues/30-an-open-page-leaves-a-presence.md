# 30 — An open page leaves a presence

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 8

## What to build

A console holds its space only during a run, and a canvas never holds it (open
question 11). So a console left idle, or a canvas left open, is invisible: nothing
on disk says a page is still serving the space. Anything that moves or removes the
space would leave that page writing marks to a path that no longer exists.

While a console or a canvas session serves a space, it writes a **presence**
record in that space's `.contour/`. The record has the same pid-and-host shape as
the run's hold, and is judged alive by the same rule: a dead process on this
machine is not present, and a record from another machine is never judged dead.
The session removes it when it ends, including on the signal paths issue 27 made
orderly.

Presence **blocks nothing**. It is not a hold: a second run, a build and a mark
all behave exactly as before. Its one reader is `contour spaces --json`, which
reports it per space, for the lobby to act on in slices 31 and 34.

This slice is worth having if the lobby never ships: *is anything open on this
space?* has no answer today.

## Acceptance criteria

- [x] An open console and an open `contour canvas` each leave a presence record, removed when the session ends normally, on SIGTERM, on SIGHUP and on Ctrl-C
- [x] A presence whose process is gone is reported as absent, with no manual cleanup
- [x] `contour spaces --json` reports each space's live presences: which kind of page, and which pid
- [x] Nothing refuses, waits or changes behaviour because of a presence; the run-lock tests pass unchanged
- [x] The presence file is ignored by the space's git, like the run lock

## What it came to

- `lib/presence.py`, stdlib-only: `present(space, kind)` writes one file per
  session under `.contour/presence/` — one per session rather than one per
  space, since two canvases can be open on one space — and removes it on every
  path out; `live(space)` judges each record with `lock.alive`, the hold's own
  rule, and deletes nothing, because the lobby that asks promises to write
  nothing.
- `contour spaces --json` reports `presence: [{kind, pid, host}]` per space; the
  text form is unchanged.
- The console server writes its presence before printing its URL, inside the
  signal handling issue 27 added. `contour canvas` had only Ctrl-C: SIGTERM or
  a closed terminal killed it where it stood. It now has all three raised and
  ends on them as it does on Ctrl-C, with the same report.
- Already ignored: the space template's `.gitignore` ignores `.contour/*`
  except the marker, so this pins that rule rather than adding one.
- `tests/test_presence.py`, 9 tests. Six mutants run against them (alive
  ignored, other host judged gone, no `finally`, presence refusing a check,
  `.contour/*` narrowed to the run lock, wrong pid); all six caught.

## Blocked by

None — can start immediately.
