# 74 — The vetoes panel says *You said no to*

**Type:** AFK · **Source:** ADR 0025, decision 7 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The panel's heading is *You said no to*. Each veto is the plain act from issue
68's table and the user's reason. *Promote to a mark* becomes *Pin this to a
part*, with the part chosen as now, and a pinned veto says *pinned to beak*.

The *n vetoes uncommitted* count leaves the page. A veto still rides the next
commit, and nothing about how it gets there changes.

## Acceptance criteria

- [x] The heading and each line read as decided
- [x] Pin this to a part makes the same mark promotion made
- [x] No count of uncommitted vetoes is shown
- [x] A veto still reaches git with the next approved commit

## Blocked by

- [68](68-a-gate-says-the-act.md)
