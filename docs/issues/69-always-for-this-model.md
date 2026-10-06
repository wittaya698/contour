# 69 — Build gates can be allowed for good, and undone

**Type:** AFK · **Source:** ADR 0025, decision 6 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

A build gate gains a third answer, *Always for this model*. It allows this call
and writes this space's ask-list entry so the next build runs unwatched. The
per-space list replaces the global one whole, so what is written is the list as
it currently resolves for this space plus `build` — never `build` alone, which
would silently drop whatever the global list let through.

The write is a `contour` command with machine-readable output, and the page is one
client of it (ADR 0021, decision 3); the agent never calls it, since an agent
widening its own permissions is what the ask-list exists to prevent. Spec
writes, reference writes and saving a version never offer *Always*. Push is never
offered at all.

The page lists what runs without asking for this model, each with Undo, which
writes the list back without it. Silence still means ask (ADR 0019, decision 36).

## Acceptance criteria

- [x] A build gate offers Allow, Always for this model, and Deny; no other category offers Always
- [x] Always writes the resolved list plus `build` for this space, and `contour asks` shows it
- [x] A global entry survives a per-space Always
- [x] The page lists what runs unwatched for this model, and Undo removes one
- [x] The command that writes the list is not callable by the console's agent

## Blocked by

- [68](68-a-gate-says-the-act.md)
