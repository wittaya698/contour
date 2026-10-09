# 85 — One shape for a command that confirms

**Type:** AFK · **Source:** architecture review, 2026-10-08; ADR 0021, decisions 5 and 6 — [the lobby](../adr/0021-the-lobby.md); ADR 0026, second amendment — [update](../adr/0026-update-brings-a-space-in-step.md)

## What to build

`rename`, `delete`, `update`, `purge` and `restore` share an interface: a
proposal that carries `refused`, an act that does what the proposal said, lines
for a terminal and `--json` for a client. Each handler in `lib/cli.py` still
parses its own flags, four ways: `delete` and `purge` take the first word as the
name whatever it says, so a typed `--yes` is a wrong name and never a confirm;
`rename` throws away anything starting `--`, which happens to be safe; `update`
acts by default and proposes with `--dry-run`; `restore` parses by hand. The
lobby repeats the pairing too — a propose route and a confirm route per command,
in `lib/lobby.py`.

A column in `lib/commands.py` marks a command that confirms, and one handler in
`cli.py` applies it: the first word is the name or id, verbatim; the flags are
`--yes` and `--json`, plus any a row declares (`restore`'s `--to`); without
`--yes` it proposes and writes nothing; a refusal is `FAIL <command>  <why>`.
Each act module keeps only what is its own — its refusals, its proposal, its
lines. `update` proposes by default and acts with `--yes`, and `--dry-run` is
gone (ADR 0026, second amendment). `restore` has no proposal and acts on its
own word, as today.

The lobby asks every one of them through one route, keyed by the table, and
each keeps only which word its page sends — `delete` re-reads the listed name,
`restore` and `purge` send an id.

## Acceptance criteria

- [x] One table-driven test runs every confirming command through propose, refuse and `--yes`
- [x] A name or id typed as `--yes` is refused as a wrong one, for every command
- [x] `contour update` with no flags changes nothing and names `--yes`; `--dry-run` is a usage error
- [x] The lobby's update preview and confirm still work, through the one route
- [x] `cli.py` has one handler for the five, and no command parses its own `--yes` or `--json`
- [x] No `--dry-run` remains: the help row in `commands.py`, `update.lines`' closing hint, the README's two mentions and `lobby.html`'s comment say `--yes`

## Blocked by

None - can start immediately
