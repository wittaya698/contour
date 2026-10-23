# 152 — Reading a reference is not changing it

**Type:** AFK · **Source:** the console run that checked issue 151, 2026-10-23

## What to build

A new-space run raised *Claude wants to change your reference pictures* four
times for calls that only read the photo:

- `contour measure refs/….png --help 2>&1 | head -80; sips -g pixelWidth -g pixelHeight refs/*.png`
- a `python3 - <<EOF` script that opened the reference and saved an enlarged
  copy to the scratchpad
- `sips -z 1491 546 refs/….png --out $S/big.png >/dev/null`

`intent.writes` takes any `>` or `<<` in the line as a write, and `python3`
and the rest of `WRITING` as writers, so `2>&1`, `>/dev/null` and a heredoc
each made a read a write. `mentioned` then found `refs/` in the line and
called it `ref-write`, the floor's gate. A warning the user learns to click
through is worse than none: the one that means it reads the same.

Narrow the cases that are plainly not writes to a reference, and keep the
floor for everything else. A redirect into `/dev/null` or onto a descriptor
(`2>&1`) writes no file. A redirect, `--out` or `-o` whose target is not under
`refs/` writes no reference. A heredoc fed to an interpreter stays a write,
since its script can write anywhere, but a script that names `refs/` only in
an `open(…)` with no write mode, or `Image.open`, is the hard case: leave it
gated unless it can be told apart without guessing. A gate that cannot tell
should still ask (rule 1); the fix is for the calls it can tell.

## Acceptance criteria

- [ ] `2>&1` and `>/dev/null` in a call that names a reference no longer make it a `ref-write`
- [ ] A call whose only output is a path outside `refs/` (`--out`, a redirect) is not a `ref-write`
- [ ] `cp x refs/…`, `> refs/…`, `sips -z refs/…` with no `--out`, and `sed -i` on a reference still are
- [ ] The guard (`tools/guards/spec.py`) and the console's gate agree on every case, as `refs_in` already makes them

## Blocked by

None - can start immediately
