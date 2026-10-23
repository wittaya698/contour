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

- [x] `2>&1` and `>/dev/null` in a call that names a reference no longer make it a `ref-write`
- [x] A call whose only output is a path outside `refs/` (`--out`, a redirect) is not a `ref-write`
- [x] `cp x refs/…`, `> refs/…`, `sips -z refs/…` with no `--out`, and `sed -i` on a reference still are
- [x] The guard (`tools/guards/spec.py`) and the console's gate agree on every case, as `refs_in` already makes them

## Found (2026-10-23)

Three of the four warnings are gone. `writes` now takes out a redirect onto a
descriptor or into `/dev/null` before it looks for `>`, so `2>&1` writes no
file, for a spec as for a reference: `cat spec.yaml 2>&1` was a spec write
too. `mentioned` judges a reference write on the call without the writes
that plainly land elsewhere: a redirect into a file that is not a reference,
and a `sips` whose `--out` is not one.

The heredoc one stays. The script saved its copy to the scratchpad, but
telling `Image.open('refs/…')` from `.save('refs/…')` in a script is
guessing, and a gate that cannot tell still asks.

It turned up a hole the other way. `sips` was never a writer, and with no
`--out` it writes its change over the file it read: `sips -z 9 9
refs/front.png` resized a tracked reference with no gate and no guard. It
now writes whenever it is given a flag that is not one of its reading ones
(`-g`, `--oneLine`, `--help` and the like), in place unless `--out` says
elsewhere.

The guard and the gate still share `intent.classify`, and
`test_spec_guard` drives the hook through the same cases to keep them so.
`test_intent.ReadingAReferenceTest` holds the cases either way.

## Blocked by

None - can start immediately
