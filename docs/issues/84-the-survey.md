# 84 — The survey: a space as seen from outside it

**Type:** AFK · **Source:** architecture review, 2026-10-08; ADR 0024, decision 1 — [the connector: Desktop reads and opens](../adr/0024-the-connector-desktop-reads-and-opens.md); CONTEXT.md, **survey**

## What to build

What the lobby and the connector know about a space lives in the launcher's
dispatcher: `reading`, `viewed`, `worked`, `listing`, `status`, `log`,
`picture`, `spec`, `spent` and `out_of_step`, about 250 lines at the bottom of
`lib/cli.py`, with function-local imports to keep the shim light. Nothing
imports `cli.py`, so the only way to test a lobby row's *last worked on* or its
perspective tile is to spawn `contour spaces --json`. And `out_of_step` builds a
whole row — commit counts, remotes, presence — to answer one toolkit state.

`lib/survey.py` owns them: a space's row, its status, its log tail, its pictures
and what each is of, its spend, and how its copies stand (slice 83). It is
derived on every call and writes nothing. The connector imports it directly, as
ADR 0024 decision 1 already lets it import the Blender-free half of `lib/`;
`cli.py` keeps handing the connector its two acts, open and create, which are
not the survey's.

The survey returns data. The MCP shapes — an image with its state, the spec text
with the instructions' line after it — move into `lib/connector.py`. `named`,
which turns a space's name into its path, moves to `lib/space.py`, which already
answers where spaces are found. `cli.py` keeps the dispatching and the printing:
`contour spaces`'s text form prints the survey's rows.

What a row says that a writer used to answer comes with it, so the survey
reaches no writer: whether a rename is uncommitted (`rename.uncommitted`, now
`survey.renamed`, reading the spec's `model:` through `revision.model`), and the
trash and its listing (`delete.trash`, `delete.about`, `restore.deleted`), which
`delete` and `restore` now import from the survey. `doctor` stays in `cli.py`:
it is asked from inside a space, of its hooks and its PATH as well as its copies.

## Acceptance criteria

- [x] `lib/survey.py` exists and is in `tests/test_lib_split.py`'s `FREE`
- [x] `survey` imports none of `rename`, `delete`, `restore`, `update`'s writes, `enter` or `lobby`'s create, by test
- [x] The lobby-row tests call the survey in-process; none spawns `contour` to read a row
- [x] `out_of_step` reads only how the copies stand, not a whole row
- [x] The connector's tool results are unchanged, by its existing tests
- [x] `cli.py` holds no reading of a space beyond calling the survey

## Blocked by

- [83](83-one-answer-to-how-a-copy-stands.md) — the survey reports how a copy stands, and should not carry `drift` across only to lose it
