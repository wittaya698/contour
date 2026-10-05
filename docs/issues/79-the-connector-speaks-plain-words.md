# 79 — The connector speaks plain words, and a pasted picture opens the drop form

**Type:** AFK · **Source:** ADR 0025, decision 11 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The connector's instructions gain a line: its answers are read as a page reads,
in plain words. `status` returns issue 66's sentences beside the report lines.
A picture pasted into the chat is answered by opening the lobby with the create
form ready, and the name filled in if one was given, where the file can be
dropped; `open` gains that. A path offered is still taken by `create`.

## Acceptance criteria

- [ ] `status` carries the plain sentences
- [ ] `open` can open the lobby on its create form with a name
- [ ] The pasted-picture instruction sends the user to the form, not for a path
- [ ] `create` from paths is unchanged

## Blocked by

- [66](66-the-verdict-in-plain-words.md)
