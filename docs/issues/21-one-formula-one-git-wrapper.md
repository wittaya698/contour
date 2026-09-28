# 21 — One weighting formula, one git wrapper

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0019 decision 37

## What to build

Two small duplications, each of which is a defect waiting rather than an untidiness.

**One weighting formula.** `console/spend.py:weigh()` and an inline copy in
`tools/tokens.py` are the same arithmetic written twice — in a module whose own
comment says *"One definition, because a run read here and watched there must not
come out as two prices (ADR 0019, decision 37)."* It already imports the three
multipliers from `spend` for exactly that reason and then re-expresses the formula
around them. There are also two spellings of the SDK's usage keys: `spend.counts`
translates them, `tools/tokens.py` reads `cache_creation_input_tokens` and
`output_tokens` raw, so a key the SDK renames breaks one path and silently
miscounts the other.

`tools/tokens.py` calls `spend.counts` and `spend.weigh`. This adds no dependency —
it already does `from console import spend`, and `console/__init__.py` is
docstring-only — so it is finishing an intent that is already written down.

**One git wrapper.** Five hand-rolled wrappers ask git questions:
`lib/marks.py:_git`, `console/vetoes.py:_git`, `contour:git_out`,
`tools/guards/spec.py:tracked`, plus eight ad-hoc `subprocess.run(["git", "-C",
...])` calls inside `contour`. Three of them independently decide that a non-zero
exit means *no answer* rather than an error. The duplication was never the bug;
the divergence is.

`lib/git.py`, in the Blender-free half, with **named question functions** — no
caller assembles argv, no caller interprets a return code, and each function's
error policy is stated once where the question is asked.

**The guard's `tracked()` stays out,** by slice 15's decision: it denies on any
git error, which is correct there and wrong in the other four, and the reason for
it belongs next to the deny. That leaves *tracked* defined twice, differing only
in error policy. Worth reconciling once both have landed — `lib.git.tracked` with
an explicit fail-closed argument — but not by making the safe one inherit a shared
default.

## Acceptance criteria

- [ ] `tools/tokens.py` contains no weighting arithmetic and no raw SDK key name
- [ ] A run weighed through the console and read through `tools/tokens.py` reports the same figure
- [ ] `tests/test_tokens.py` asserts that equality directly
- [ ] `lib/git.py` exposes named questions; no caller outside it builds a git argv
- [ ] Each function states its own error policy, and the three that disagreed now say why
- [ ] `lib/marks.py:_git`, `console/vetoes.py:_git` and `contour:git_out` are gone
- [ ] `tools/guards/spec.py:tracked` is untouched and still fail-closed
- [ ] `tests/test_lib_split.py`'s roster names `git`, free
- [ ] `contour selftest` green; `spaces`, `doctor` and veto exposure behave identically

## Blocked by

None.
