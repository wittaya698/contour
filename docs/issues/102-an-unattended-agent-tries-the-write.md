# 102 — An unattended agent tries the spec write rather than asking in prose

**Type:** HITL · **Source:** [issue 100](100-accept-adr-0028.md)'s tracer bullet, against ADR 0028, decision 1 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

The first run in `beaky-0028` lengthened the beak, rebuilt, and found depth at
644 mm against 615 ±20. It then argued the spec change in its closing — *I haven't
written this yet and need your yes first* — and never tried the write. That is
rule 1 as a terminal session keeps it, and the reason it never reached a gate.
Nothing was set aside, so nothing waited for the person to answer.

The space's rules say where the confirm lands — *prose in a terminal, a gate under
a console* — but not that an unattended run's gate is where the write must be
tried, so that it is kept with its case for the person.

Related: the chat that requested the run then wrote *Yes to the spec change… from
the user* into a second request. The floor held, and the write was set aside
rather than made, but that relay is the cost of a run that asked in prose.

## To decide

- Wording for rule 1 in the toolkit's `CLAUDE.md` and `templates/space/CLAUDE.md`:
  under a console, run unattended, the case is made in the text just before the
  write and the write is tried, so its gate keeps both.
- Or say it in what the console tells an unattended run's agent at the start.

## Acceptance criteria

- [ ] An unattended run that finds a spec change warranted tries the write, with its case just before it
- [ ] Its closing names what it set aside, and argues nothing that is not on the page
