# 15 — The guard asks what a call means

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0019 decision 20, ADR 0012, rule 1

## What to build

Rule 1's definition of a **ref write** exists twice, in two languages, and the two
copies disagree. `lib/intent.py:path_intent` calls any path with a `refs`
component not under `.git` a `ref-write`. `tools/guards/spec.py` protects `refs`
only as the first component, only when git tracks it, and reads only
`tool_input.file_path` — so a `Write` to a nested `refs/` is gated by the console
and allowed by the guard, and `cat > refs/side.jpg` is invisible to the guard
entirely.

**This matters because the guard is the layer rule 1 actually rests on.** A
space's `PreToolUse` hook fires before the SDK consults the console's
`can_use_tool`, which is why ADR 0019 decision 20 has the guard keep denying while
the ask-list only asks, and why the console deliberately carries no `ref-write`
special case. The strict layer being the narrower one inverts that.

**The guard asks `lib.intent` for the category.** It keeps its own policy — a
tracked ref write is denied, an untracked one is how a space starts — and stops
having its own notion of which paths rule 1 is about. It reaches `lib/` the way
`contour` does: `contour hook spec` execs it, so it puts the toolkit root on
`sys.path` and imports. `lib/intent.py` is in the Blender-free half and imports
only `re`, `shlex` and `pathlib`, which slice 03's roster already proves stays
true on a bare clone.

**The broader reading wins.** A rule-1 mechanism fails safe, so a nested `refs/`
becomes protected rather than the root one becoming unprotected.

**`intent` gains a path reader beside `classify`.** A Bash call carries a category
but no path, so the guard could not ask git about trackedness — and that
distinction is load-bearing, because `cp ~/Downloads/side.jpg refs/` in a fresh
space is a write the guard is supposed to allow. So `intent` grows a companion
returning the `refs/` paths a call names, and the guard checks each one. The
console's gate gets the same thing for free and can say *which* reference.

**`tracked()` stays the guard's own.** It denies on any git error, which is
correct here and wrong in the four wrappers slice 21 consolidates. Keeping it
local keeps the reason for it next to the deny. Revisit once both have landed:
`lib.git.tracked` with an explicit fail-closed argument would be one definition
again, and the guard is already importing from `lib/` by then.

**The docstring shrinks.** It currently explains the revision rule the guard no
longer enforces, which makes it a third copy of ADR 0016's decision. It becomes
what this guard does, pointing at ADR 0016 for why the spec half left.

No new **category**, no new vocabulary: `ref-write`, **gate** and **ask-list**
already cover every term this touches.

## Acceptance criteria

- [ ] `tools/guards/spec.py` asks `lib.intent` for a call's category and holds no path rule of its own
- [ ] A `Write` to a nested `refs/` path that git tracks is denied
- [ ] A Bash call writing a tracked `refs/` path is denied, naming the path
- [ ] A Bash or `Write` call to an untracked `refs/` path is still allowed
- [ ] A Bash call that only *reads* under `refs/` is allowed
- [ ] `intent` exposes the `refs/` paths a call names, and `tests/test_intent.py` covers it
- [ ] `tracked()` still denies when git cannot be asked, with that reason stated in place
- [ ] The guard's docstring describes only what the guard does, citing ADR 0016
- [ ] `contour selftest` green; the Blender-free roster unchanged

## Blocked by

None — can start immediately, and is worth having whether or not the rest of this
batch lands.
