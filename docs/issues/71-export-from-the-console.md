# 71 — Export from the console, and the file handed over

**Type:** AFK · **Source:** ADR 0025, decision 5 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The console has an Export button. It runs `contour export` directly — the console
spawning the launcher, no agent turn. It is offered only when the last build is
green, says *fix the failing checks first* when it is red, and is disabled during
a run with *finish or end the run first*, since export takes the space's hold.

After any export, the button's or one Claude made inside a run, one card shows the
file: its name and size, who exported it, the round-trip as *checked: it reopens
the same as it was built* or what differed, Download, and Show in Finder. When a
newer build exists the card says *older than the last build — export again*.

## Acceptance criteria

- [x] The button exports with no agent turn, and only on a green build
- [x] During a run the button is disabled, worded as decided
- [x] An export by the agent in a run shows on the same card, saying so
- [x] The card states the round-trip outcome in plain words
- [x] Download hands over the `.glb` byte for byte, and Show in Finder reveals it
- [x] A build after the export marks the card as older than the last build

## Blocked by

- [66](66-the-verdict-in-plain-words.md)
