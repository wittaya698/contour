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

- [x] `contour spaces --json` prints one JSON document listing every space the text form lists, and no others
- [x] Each entry carries name, path, toolkit state, commit count, remotes, and doctor's drift findings
- [x] A space with a remote is reported in the JSON too, and the command still exits non-zero, as the text form does
- [x] No spaces is an empty list and exit 0, not an error
- [x] `contour spaces` and `contour spaces <name>` print byte-identical output to before
- [x] Tests cover both forms from spaces built in a temporary directory, with no Blender

## What it came to

**One reading, two renderings.** `reading(root)` in `lib/cli.py` reads one space;
the text form and `--json` both print it. The text form was pinned byte for byte
against the old code before anything moved, and still matches.

```json
{"roots": ["…"],
 "spaces": [{"name": "beaky", "path": "…/project/beaky",
             "toolkit": {"commit": "72876fe", "state": "behind"},
             "commits": 8, "remotes": [],
             "scaffold": {"drift": ["CLAUDE.md"], "missing": []},
             "rules": true}]}
```

`state` is `current`, `behind` or `unknown`; `commit` is null when the marker
names no toolkit. **Doctor's scaffold comparison is `scaffold(root)`**, asked by
`doctor` of the space it stands in and by `spaces` of every space. **`rules`** is
open question 13 as data: the space has a `CLAUDE.md` of its own, or the
toolkit's is above it.

`SpacesTest` in `tests/test_launcher.py`: 8 tests over spaces `contour init`
makes in a temporary directory. Five mutants, each caught. The suite runs 518
tests, 6 skipped.

**Found, not fixed:** every space on this machine has drifted in three or four
scaffold files, `CLAUDE.md` and `.claude/settings.json` among them, which the
text form never showed. A marker that literally says `toolkit: unknown` (what
`init` writes when git cannot say) still reads as `behind`, because changing it
would change the text form.

## Blocked by

None — can start immediately.
