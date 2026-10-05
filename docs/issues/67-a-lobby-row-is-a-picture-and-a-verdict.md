# 67 — A lobby row is a picture and a verdict

**Type:** AFK · **Source:** ADR 0025, decision 10 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

Each model in the lobby is a row someone can read without the glossary: a
thumbnail of its last sheet, or one of its references before it was ever built;
its name; the verdict in issue 66's words; when it was last worked on; and Open.
Rename, *a new model from this one* and Delete move into a menu on the row. The
page's heading is *Models*.

*Toolkit* and *Commits* leave the row. Health says nothing when nothing is wrong,
and when something is it says the outcome: *has a remote — a model is never
pushed* as a warning. Drift is shown as *needs an update* with no action yet;
issue 81 gives it one. The empty state's terminal hint goes.

## Acceptance criteria

- [x] A row shows thumbnail, name, plain verdict, last worked on, and Open
- [x] A never-built model shows a reference as its picture and says *not built yet*
- [x] Rename, new model from this one, and Delete sit in a menu and behave as before
- [x] No row shows a toolkit commit or a commit count
- [x] A healthy model shows no health text; a remote is a warning; drift reads *needs an update*
- [x] The empty state no longer suggests a terminal command

## Blocked by

- [66](66-the-verdict-in-plain-words.md)
