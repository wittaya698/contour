# 28 — `contour spaces --json`: the list and its health, machine-readable

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decisions 3, 9

## What to build

ADR 0021 makes the command line the contract for the **lobby**, and for any other
client: the page is one client among them. The first thing every client needs is
the list of spaces, which `contour spaces` already derives from the markers and
prints for a person.

Give it a machine-readable form that carries what a lobby row shows:
- each space's name and path;
- whether its toolkit is current, behind or unknown;
- its commit count;
- any remotes;
- the drift `contour doctor` would report: scaffolding that differs from the
  toolkit, and whether the space can see the rules (open question 13).

It is derived on every call, as the text form is, and never stored.

The text output does not change. The two forms are two renderings of one reading,
so they cannot disagree about which spaces exist or which ones are behind.

## Acceptance criteria

- [ ] `contour spaces --json` prints one JSON document listing every space the text form lists, and no others
- [ ] Each entry carries name, path, toolkit state, commit count, remotes, and doctor's drift findings
- [ ] A space with a remote is reported in the JSON too, and the command still exits non-zero, as the text form does
- [ ] No spaces is an empty list and exit 0, not an error
- [ ] `contour spaces` and `contour spaces <name>` print byte-identical output to before
- [ ] Tests cover both forms from spaces built in a temporary directory, with no Blender

## Blocked by

None — can start immediately.
