# 86 — A space records its latest run

**Type:** AFK · **Source:** ADR 0027, decision 8 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

Every run a console drives, attended or not, leaves one record in its space:
what was asked and who asked it, and a state, *running*, *waiting for you* with
the act in the gate's plain words, *finished* or *stopped* and why. At the end
it adds the verdict (read from the last check, not copied), the agent's closing
message, the spend and the vetoes. Only the newest run is kept, and it is
git-ignored. The connector's `status` returns it, and the launcher gains the
same read as JSON for a client without MCP.

It never holds a gate's diff or the argument behind it: the case for a change
is made on the page (rule 1).

## Acceptance criteria

- [ ] A run in a console writes the record, and every change of state rewrites it
- [ ] A parked gate reads *waiting for you* and names the act, never the diff or the call's arguments
- [ ] A finished run carries the verdict, the closing message, the spend and the vetoes
- [ ] A second run replaces the first; nothing resumes from the record
- [ ] The connector's `status` and the launcher's JSON read return it, and a space with no run says so

## Blocked by

None — can start immediately.
