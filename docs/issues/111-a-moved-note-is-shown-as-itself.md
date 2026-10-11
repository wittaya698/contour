# 111 — A moved note is shown as itself, not the whole list

**Type:** AFK · **Source:** [issue 109](109-a-spec-write-carries-its-case.md)'s runs

## What was found

Runs `d1ce99f5` and `d625e6e9` each changed one entry of `beaky-0028`'s
`notes:`, the beak's *~170 proud* to *~187* and *~191*. The approval showed, under
*depth 615 → 648 mm*, one line holding all nine notes before and all nine after,
so the person had to find the changed word in two lists.

`lib/gate.py` flattens a spec to one value per named scalar, and a list is one
value, since its items have no names (`flat`). So any list that moves is shown
whole.

## What to build

A list whose length did not change shows each item that moved, as *notes 6:
~170 → ~191 proud …*, enough of the item to read it, and the rest not at all. A
list that grew or shrank says what was added or removed. Issue 106's check on
numbers is unchanged: a number inside a note is prose.

## Acceptance criteria

- [x] A spec write that changes one note shows that note, before and after, and no other
- [x] One that adds or removes a note says which
