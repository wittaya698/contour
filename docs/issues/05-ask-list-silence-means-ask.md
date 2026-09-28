# 05 — The ask-list is read, and silence means ask

**Type:** AFK · **Source:** ADR 0019 decisions 6, 7, 8, 36

## What to build

The policy the gate consults. A reader, a file format, and a scope rule — no
console yet, so this is verifiable on its own.

**It lives in `~/.contour`.** Outside the toolkit and outside every model space,
so an agent working in a space has no in-scope reason to touch it. This does not
make tampering impossible — an agent with Bash can write any path — it makes
tampering stop being a plausible edit. The agent may *propose* a wider list; the
console performs the write, never the agent. A mechanism that let the agent
perform it would be authorised by the very list it widens.

**It is an allow-list with no presets: silence means ask.** The file names only
the categories the user has chosen to let through; a category the toolkit knows
and the file does not mention is gated. A preset's meaning changes underneath the
user — when a later toolkit version adds a category, a file saying `normal`
silently denotes a different set and no decision was ever made about the new
thing. Writing down what to *gate* fails the same way: a category forgotten is a
category running unwatched.

**Two levels, replace not merge.** A global default and a per-space override.
Merging two permission lists can silently *narrow* the result — an override that
reads as adding a rule can shadow one, invisibly in both files — so a space's
list replaces the default whole.

**An unrecognised space gets the strictest list**, which is the empty one, so
nothing has to define *strictest* and no fallback table can disagree with one. A
space has no identity today, so the key is the filesystem path; fail-closed turns
a moved or renamed space from *permissions silently widened* into *the console
asks about more than expected*.

The cost is accepted: a first run gates everything and is tuned downward, so the
first session is spent writing the file rather than building.

## Acceptance criteria

- [x] A category absent from the file is gated
- [x] A space with no entry resolves to the empty allow-list, not to the global default
- [x] A per-space list replaces the global one; no key merges
- [x] The resolved list for a given space path is printable, for auditing against slice 04's enumeration
- [x] An unparseable file fails closed, with a message, and never resolves to a wider list
- [x] Nothing in the toolkit or a model space is read as policy
- [x] A category in the file that the toolkit no longer knows is reported, not ignored

## Blocked by

- [04 — The launcher classifies a call's intent](04-launcher-classifies-intent.md)
