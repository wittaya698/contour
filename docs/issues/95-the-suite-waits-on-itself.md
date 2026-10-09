# 95 — The suite waits on itself

**Type:** AFK · **Source:** timing the suite, 2026-10-09 · issue [94](94-the-signal-tests-red-in-the-full-suite.md) (same timing, different finding)

## What to build

A full `unittest discover -s tests` takes 301 s for 1079 tests, and very little
of that is work. Run file by file, the files sum to 308 s, so nothing is lost
*between* files. The time is spent inside them, and two causes account for most
of it. Neither has anything to do with what a test checks.

Measured 2026-10-09, Python 3.14.7, macOS, this machine:

| File | Alone | Tests |
|---|---|---|
| `test_console` | 80 s | 91 |
| `test_connector` | 23 s | 49 |
| `test_lobby` | 20 s | 66 |
| `test_canvas` | 13 s | 24 |
| `test_panel` | 13 s | 14 |
| `test_launcher` | 11 s | 26 |
| everything else | ~148 s | |

**1. Every page server takes half a second to stop.** `Page.start`
([lib/page.py](../../lib/page.py)) runs `serve_forever()` with its default
`poll_interval=0.5`, and `Page.stop` calls `shutdown()`, which waits for the
serving loop to notice, so it blocks for up to 0.5 s. The canvas, the lobby and
the console all stop through it. You can see it in `--durations`: a long run of
tests at a flat 0.51–0.53 s, whatever they assert. A console subprocess
measured 0.09 s to come up and 0.56–0.62 s to go down.

Patching only the default to `poll_interval=0.02` (in a scratch venv, with no
change to the repo), with everything passing:

| | Before | After |
|---|---|---|
| `test_canvas` | 13.1 s | 0.9 s |
| `test_lobby` | 20.1 s | 8.6 s |
| `test_console` | 81 s | 43 s |
| full suite | 301 s | **184 s**, 1082 tests, OK |

The same patch also makes `contour canvas` return sooner after Done, a console
let go of its port sooner, and so on: it is a real latency, not a test artefact.

**2. macOS checks a new executable the first time it runs.** A script written
and `chmod`ed a moment ago costs about 0.25 s on its first `exec`; the same file
costs 0.008 s afterwards, and `/bin/sh script` pays nothing even the first
time. Tests write such a file in `setUp` all over the suite: `stub_blender`
([tests/test_launcher.py](../../tests/test_launcher.py)), the `quiet` browser
in the lobby files, `open`/`git`/trash shims, and others (`grep -n
"chmod(0o755)" tests/`). In `test_connector` a `contour check` against a fresh
stub took 0.56 s the first time and 0.07 s the second, almost all of it spent
waiting on the stub. This is why `test_connector` did not move under (1).

The fix is in the tests, not the launcher: write each stub once per class or
module rather than per test, or invoke it through its interpreter where the
code under test allows that. `$BLENDER` and the browser hatch are run as
programs, so caching per class is likely the general answer. Don't change how
the launcher execs Blender to suit a test.

**3. Deliberate waits, recorded and left alone.** A few tests sleep to prove
that nothing happens: `test_an_unanswered_gate_waits_and_holds_off_the_idle_timeout`
(6 s, *three idle timeouts' worth*), `test_a_hidden_tab_at_a_gate_never_ends_the_console`
(4 s), the 2 s hidden-grace tests in `test_console` and `test_lobby`, and the
`time.sleep(1)` after a refusal in `test_connector`, `test_lobby_enter`,
`test_lobby_create` and `test_lobby_variation`, which checks that no console
starts late. Together these come to roughly 25–30 s. They are evidence, not
waste. Shorten one only by shortening the timeout it is outlasting, through the
env hatches that already exist (`CONTOUR_CONSOLE_GRACE` and the like), never by
sleeping less than the thing it is proving.

**Take the numbers again on an idle machine.** Some of these runs overlapped another
session's suite runs on the same machine. The two that matter here were these
runs: the overlap is what issue 94 turned out to be. The mechanisms were each
measured in isolation and stand: 0.09 s up and ~0.6 s down for a console, 0.25 s
against 0.008 s for a first and a second exec. The per-file and full-suite wall
times are only indicative, and the 184 s run started after 94 landed and was
probably alone. The before/after this slice writes down must come from runs with
nothing else on the machine (README, *one suite run per machine at a time*).

**Not a fix:** parallel runs, which the README rules out, since `SignalTest` counts
every `console.server` on the machine (94), or sharing one server across a
class. That one makes cross-test leaks likelier and harder to see, and neither
removes a wait. Neither does skipping slow tests, or dropping
a test's `finish`/`stop` so it does not wait for shutdown.

No new vocabulary.

## Acceptance criteria

- [ ] Stopping a `Page` no longer waits out a 0.5 s poll, and the console, the lobby and the canvas each still let go of their port and their space on every path issue 27 covers
- [ ] No test pays first-exec cost for a stub it could have written once; `--durations` shows no flat ~0.25 s or ~0.5 s floor that comes from either cause
- [ ] Every deliberate wait in (3) still outlasts what it proves, and says so in a comment where it does not already
- [ ] Full `unittest discover -s tests` green twice in a row, alone on the machine, with the wall time before and after written down here
- [ ] `contour selftest` green

## Blocked by

None.
