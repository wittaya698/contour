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

- [ ] `R=refs/x.png; contour measure $R …` reads *Measured the x picture*
- [ ] A variable set nowhere in the line reads *Measured a picture*
- [ ] `contour measure refs/x.png` reads as it does now

## Blocked by

None - can start immediately
