# 92 — The connector asks and stops

**Type:** AFK · **Source:** ADR 0027, decision 5 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

The connector gains `request` and `stop`, the same arguments and answers as
the commands, which takes it to ten tools. Its instructions stop saying it
changes nothing: it reads, opens and asks for runs; it never answers a gate or
a question; and to bring the person to one, it uses `open`.

## Acceptance criteria

- [ ] `request` starts a run and returns the command's refusals in its words
- [ ] `stop` ends a run as `contour stop` does
- [ ] The instructions say what the connector does now, and nothing claims it changes nothing
- [ ] No tool answers a gate or a question, and no result carries a console URL

## Blocked by

- [89](89-contour-request.md)
- [91](91-the-channel.md)
