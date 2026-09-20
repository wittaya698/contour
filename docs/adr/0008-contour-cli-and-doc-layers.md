# 0008 — One CLI wrapper, three documentation layers

**Status:** Accepted · 2026-09-20

## Context

Two standing token costs dominate this repo, and both are structural rather
than incidental.

First, a headless Blender run prints a startup banner, addon registration, and
depsgraph and I/O chatter — roughly 2–5k tokens of noise per invocation, ~60k
across a 30-iteration session.

Second, `CLAUDE.md` is injected into every session and every turn, so each line
is paid for whether or not it is relevant. Skills cost only their one-line
description until invoked; reference files cost nothing until read.

Third, Blender 5.2.1 was built 2026-08-25, after the assistant's knowledge
cutoff, so recalled `bpy` signatures are guesses — and a guess-fail-retry cycle
costs 1–2k tokens where a lookup costs ~15.

## Decision

**One entrypoint.** `./contour` with subcommands `check`, `render`, `export`,
`api`, `selftest`. It swallows Blender's stdout into `out/last-build.log` and
prints only a compact report. Raw `blender` invocation is banned in `CLAUDE.md`.

**`./contour api <symbol>`** introspects the installed Blender for a symbol's
real signature, arguments and enum values. The agent looks up before writing an
unfamiliar call.

**Three doc layers.** `CLAUDE.md` stays ~40 lines: hard rules, the command
table, and pointers. Workflows live in `.claude/skills/`, loaded on invocation.
Bulky know-how lives in `references/`, read only on demand.

**`references/bpy-recipes.md`** accumulates patterns that have actually run
successfully here, each marked verified or unverified, so the second use of a
pattern costs nothing.

## Consequences

- A green run reports in ~60 tokens instead of thousands; failure detail is
  still one file read away.
- Baseline session cost is ~400 tokens of always-on docs rather than ~5k.
- The wrapper is a dependency: if `./contour` breaks, everything breaks. This is
  what `./contour selftest` and the fixture guard.
- Recipes must be marked honestly. An unverified recipe asserted as fact is
  worse than no recipe, because it looks authoritative.

## Rejected

- **Raw `blender`, read all output** — signal buried in banner text.
- **Raw plus `2>/dev/null | tail -20`** — free, but the filter is a guess that
  can eat the actual traceback.
- **Makefile targets** — equivalent on cost, clumsy argument passing.
- **Everything in one large `CLAUDE.md`** — nothing missed, but a permanent
  per-turn tax, and long files get partially ignored.
- **Vendored Blender API docs (~300 MB)** — authoritative and complete, but
  bulky and grep hits return token-heavy HTML.
