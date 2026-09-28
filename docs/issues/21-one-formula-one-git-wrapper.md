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

- [x] `tools/tokens.py` contains no weighting arithmetic and no raw SDK key name
- [x] A run weighed through the console and read through `tools/tokens.py` reports the same figure
- [x] `tests/test_tokens.py` asserts that equality directly
- [x] `lib/git.py` exposes named questions; no caller outside it builds a git argv
- [x] Each function states its own error policy, and the three that disagreed now say why
- [x] `lib/marks.py:_git`, `console/vetoes.py:_git` and `contour:git_out` are gone
- [x] `tools/guards/spec.py:tracked` is untouched and still fail-closed
- [x] `tests/test_lib_split.py`'s roster names `git`, free
- [x] `contour selftest` green; `spaces`, `doctor` and veto exposure behave identically

## What it came to

**The weighting.** `tools/tokens.py` now holds no arithmetic and no SDK key at
all. `iterations()` translates each turn through `spend.counts` and weighs the
result with `spend.weigh`, and even the footer that explains the formula is
built from `spend`'s own multipliers rather than printing three literals that
could drift from them. The re-exported `CACHE_READ_MULT` and friends are gone;
they were a second name for one number.

The divergence was not theoretical. The SDK sends a figure a turn did not spend
as `null`, not by leaving the key out, and `spend.counts` reads that as nothing
while the accounting read it raw — so `None` went into the arithmetic and the
tool exited 1 on a transcript the console would have priced without blinking.
Two tests now hold that shut, on the null and on the figure.

There was a fifth key. `output_tokens_details.thinking_tokens` is the line under
the table — thinking against output — and it was the last raw spelling here.
`spend.thinking()` names it, beside `counts` and for the same reason, with a
docstring saying why it is not one of `FIGURES`: the console does not record it,
because thinking is already inside `output` and the page weighs what was spent.

**The git wrapper.** `lib/git.py` exports eight named questions and one private
`_ask` that is the only place in the toolkit assembling a git argv. Every
caller outside it now asks a question by name; `lib/marks.py:_git`,
`console/vetoes.py:_git` and `contour:git_out` are gone, and so are the eight
ad-hoc `subprocess.run(["git", ...])` calls in the launcher, which lost 1,062
characters in the exchange.

Each function states its own error policy in its own docstring, and the three
that had quietly disagreed now say which way they go and why. `show` answers
None and never `""`, because the launcher reads *no answer* as *this spec is
new, and creation is not mutation* where an empty answer would be a spec
somebody emptied — the one distinction the old wrappers threw away by stripping
stdout. `commits` answers 0 rather than None, because it is printed in a column
of numbers and a fresh space genuinely holds nothing. `remotes` answers `[]` on
any failure, which is safe in the one direction that matters: it can miss a
remote the pre-push guard still stops, but it can never invent one.

`start` is the odd one and is marked as such — the only write, and so the only
one that reports instead of shrugging. Everything else here treats *not a
repository* as an ordinary state, because it is one; a space before
`contour init` is not an error to raise at a page. A space created without a
repository is not a space (ADR 0015), so that failure comes back and the caller
stops on it.

`tools/guards/spec.py:tracked` was not touched, by slice 15's decision, and the
diff shows it. That leaves *tracked* defined twice, differing only in error
policy, which is what the issue said it would leave. Worth reconciling once
somebody wants to; not by making the fail-closed one inherit a shared default.

**What was proven.** The unit suite went 344 → 367 and stayed green;
`contour selftest` PASS (90.3s) with `mutants 13/13` and `roundtrip 6/6`.
Fourteen mutants were run against the new code, listed in the commit.

Three weaknesses surfaced and were fixed. Two were in the tests: `head`'s, where
`full.startswith(got)` is satisfied by the whole hash and by the empty string,
and `thinking`'s, which only ever asserted zero. The third was in a *mutant* —
`--sort=refname` happens to put `v0.10.0` first anyway, so it survived for the
wrong reason and said nothing about the sort. The tag test now uses two tags
whose version order and date order disagree, which is the only shape that can
tell the two keys apart, and all three sort mutations are caught.

**Issue 27 collected its debt during this slice.** Twelve mutant runs meant
twelve full suites, each leaving about 57 orphaned console servers behind, and
the machine stopped being able to fork. The selftest then failed with 95 errors
whose first line was `FAIL git init: [Errno 35] Resource temporarily
unavailable` — which reads as a defect in the `git.start` written an hour
earlier. Issue 27 had already named this exact failure, down to the count and
to *the worst kind of red, because it accuses the change in flight*, and it was
still convincing. Killing the strays cleared it; nothing here was wrong.

One smaller instance of the same leak turned up on the way and belongs with it:
`tests/test_panel.py:176` cleans up a `contour canvas` with `proc.kill()` and
never waits, so the suite reports `ResourceWarning: subprocess N is still
running` and leaves one more process per run. Not fixed here — it is slice 27's
subject, and a fix landing in this slice would be untestable by the suite it
breaks.

`spaces` and `doctor` were captured before and after — the changes stashed, the
commands run, the changes popped — and both are byte-identical. Veto exposure is
covered by the console suite. The launcher's git calls are otherwise exercised
by `selftest`, which installs hooks and reads the toolkit commit on the way
through.

## Blocked by

None.
