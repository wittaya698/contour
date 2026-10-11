# 105 — A run whose approvals are answered sends nobody to its page

**Type:** AFK · **Source:** [issue 104](104-a-spec-write-is-the-whole-change.md)'s retry, against ADR 0028, decisions 1, 5 and 6 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

In `beaky-0028`, with the last run's one approval denied and nothing waiting, a
fresh Desktop chat was asked to *make the beak 10% longer and save it*. It made
no request. It read `status`, and then opened the console:

> An earlier run already got this exact request… it set something aside for you
> instead of saving… I didn't start a new run, because it would stop at the same
> approval.

Two things led it there:

- **The withheld closing never changes.** *This run set something aside for you,
  so what it did is told on its console's page* reads the same after everything it
  set aside has been answered, and the chat believed it over `approvals: []`.
- **Nothing told the chat that a spec change is made by a request.** The run sets
  the spec write aside and the person answers it on the page (ADR 0028,
  decision 1). The chat took a run that would stop at an approval as a reason not
  to start one, and sent the person to the console.

## Decided

- **The withheld closing says where things stand.** While any approval waits, as
  now. Once none do: *this run set something aside, and all of it has been
  answered on its console's page; nothing waits.* Still withheld, as issue 100
  left it.
- **The connector's third line** says a run is requested even when it will need a
  spec change, since the run sets that aside for the user to answer on the page.
  Line 2 stays as it is.

## Acceptance criteria

- [x] A finished run's withheld closing says nothing waits once its approvals are answered, and still points at the page while any wait
- [x] The connector says to request a run for a change that needs a spec change, and to open the console only when asked
