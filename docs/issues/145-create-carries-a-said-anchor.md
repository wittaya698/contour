# 145 — `create` carries a said anchor

**Type:** AFK · **Source:** ADR 0033, decisions 1–5 — [`create` carries a said anchor](../adr/0033-create-carries-a-said-anchor.md)

## What to build

`create` takes an optional `anchor`, and the console's new-space run opens its
*how big is it?* question with that size as the suggestion. The size is never
written anywhere and never taken as the anchor.

- **`create`'s schema gains `anchor: {dimension, mm}`** in `lib/connector.py`,
  with `dimension` one of `height`, `width`, `depth`. Refused before
  `contour init` runs when either part is wrong, in plain words, like a bad
  path.
- **`lib/enter.console` passes `--said <dimension>:<mm>`** after
  `--begin new-space`. The launcher refuses `--said` on any other flow and any
  value that does not parse back to the three and a positive number.
- **`console/server.py` adds the toolkit's sentence to `NEW_SPACE` step 1**
  (ADR 0033 decision 4's wording). `BEGIN`'s docstring says why a value is not words.
- **No console environment:** the terminal instruction `create` prints
  includes `--said`.
- **`create`'s answer says it was passed on as a suggestion**, e.g. *the
  console will ask whether it is 300 mm wide*.
- README's connector paragraph says so.

## Acceptance criteria

- [x] `create` with `anchor` makes the same files as without it: only `refs/`
- [x] A bad dimension or a non-positive or non-finite number is refused, and no space is made
- [x] The new-space run's first prompt names the size as the chat's, and asks it
- [x] `--said` on `--begin variation`, or with no `--begin`, is refused
- [ ] Looked at in a real console from Desktop: the size is asked, and answering *no, 320* gives an anchor span claiming 320 mm

## Blocked by

- 144
