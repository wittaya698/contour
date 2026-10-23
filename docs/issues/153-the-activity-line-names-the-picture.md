# 153 — The activity line names the picture

**Type:** AFK · **Source:** the console run that checked issue 151, 2026-10-23

## What to build

A run set `R=refs/1-walkie-talkie-orange-and-yellow-same-body.png` and then
called `contour measure $R …` three times in one line. The page said
*Measured the $R picture* each time. `activity.contour` takes the first word
after `measure` as the picture and prints its stem, so a shell variable is
shown as itself.

When the word is a variable the same line assigned (`R=…;`), name that
picture. When it cannot be known, say *Measured a picture*: never show the
user a `$` word.

## Acceptance criteria

- [x] `R=refs/x.png; contour measure $R …` reads *Measured the x picture*
- [x] A variable set nowhere in the line reads *Measured a picture*
- [x] `contour measure refs/x.png` reads as it does now

## Found (2026-10-23)

`activity.assigned` reads `$R` or `${R}` back to the last `R=…` before it in
the same line, past a `;` or an `&&`. A word that still holds shell after
that, a variable set elsewhere, `refs/$NAME.png`, a glob or a `$(…)`, reads
*Measured a picture*. `test_activity.TableTest` holds both.

## Blocked by

None - can start immediately
