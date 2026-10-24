# 0036 — A script reads a locked reference

**Status:** Accepted · 2026-10-24 · **adds to ADR 0012 (references share the spec's trust class), and replaces what issue 152 left gated** ([0012](0012-one-directory-per-model.md))

## Context

The agent measures colour by sampling the photo with a short script:
`python3 -c "from PIL import Image; im=Image.open('refs/side.png'); print(im.getpixel((40, 80)))"`.
An interpreter can write anywhere, so `lib/intent.py` reads any interpreter
call that names `refs/` as a write. Issue 152 left it that way on purpose:
telling `Image.open('refs/…')` from `.save('refs/…')` in a script's text is
guessing.

The cost is on every colour reading. In a terminal the guard denies the call
outright when git tracks the picture. Under a console it is a gate, *Claude
wants to change your reference pictures*, and on 2026-10-23 a new-space run
raised it twice in one run, both times for a read (issue 160). It is the
warning a run raises most, and so far it has never once been a write. The one
that is a write reads the same.

Checking afterwards and putting the picture back (issue 160's first proposal)
lets the picture be changed while the script runs, which is short of rule 1's
*never change anything under `refs/`*.

## Decision

**1. A reference git tracks is read-only on disk.** Whenever a call names a
reference, the guard first takes the write permission off each one git tracks.
It does this before judging the call, and does it again each time, so a
picture tracked since the last call is covered. Git records only the
executable bit, so the space shows no change. A reference git does not track
yet is left writable, as the guard leaves it today (ADR 0012: saving a new one
is how a space starts).

**2. A script that names a locked reference runs, with no gate and no
denial.** This covers `python`, `python3`, `perl` and `ruby` by name wherever
they live (`.venv/bin/python` included), whether the script comes by `-c` or a
heredoc. A read works. A write such as `open(…, 'w')` or `.save('refs/…')`
fails with a permission error before anything changes, and the agent sees
that error.

**3. A script whose text names a way round the lock is still a ref-write.**
The lock stops writes to the file, but not to the folder: a script can delete
a locked picture and save a new one in its place, because `refs/` itself
stays writable (decision 1 leaves it so for new pictures). So a script that
names `chmod`, `remove`, `unlink`, `rename`, `replace`, `shutil`, `os.system`,
`subprocess` or `Popen` is judged as today: denied in a terminal, gated under
a console.

**4. Afterwards, git says whether the references still match.** After any
call that named a reference, a `PostToolUse` hook asks git whether a tracked
reference differs from what git holds. If one does, it is restored from git at
once, locked again, and the agent is told the write was refused, in the
guard's words (rule 1, ADR 0012). This is a backstop for what the lock and the
word list miss, and the same hook runs in a terminal and under a console.

**5. Every other write is unchanged.** `cp x refs/…`, `mv`, `> refs/…`,
`tee`, `dd`, `sips` without `--out`, and a `Write` or `Edit` of a reference
are still denied before they run, or gated, as they are today.

## What this does not cover

- **A script built to get round all of it**, for example one that assembles
  `chmod` or the path out of pieces. Decision 3 reads text, and text can hide
  things. Decision 4 still puts the picture back after, but only after. The
  gap is not new: a script that spells `refs` in pieces was never gated
  either. This decision stops mistakes, not an agent working against the
  rules.
- **Other programs that edit pictures.** Only the interpreters in decision 2
  are let through. `sips`, ImageMagick and the rest keep the rules they have.
- **Changing a reference on purpose.** Rule 1 has no confirmed path to
  rewriting one, and this adds none.

## Consequences

- Colour readings and pixel sampling run without a gate or a denial, in a
  terminal and under a console.
- A careless write to a tracked reference fails before it lands, instead of
  waiting on a click.
- The references in a space are read-only files. If you replace one yourself,
  your own tools may warn or ask before overwriting it. Adding a new picture
  is unaffected.
- The guard runs `chmod` and asks git on each call that names a reference: a
  few milliseconds per call.
- The rule moves out of `intent`'s word lists and into the filesystem, which
  enforces it whatever the script says. The word list in decision 3 is still
  text matching, and has to grow when a new way round turns up.

## Rejected

- **Run it and check after** (issue 160's first proposal). Simple, but the
  picture is really changed while the script runs, which rule 1 does not
  allow.
- **Keep it gated** (issue 152's answer). Safe, but every colour reading
  costs a click or a denial, and the warning loses its meaning when it is
  always a read.
- **Lock the `refs/` folder too.** It would close decision 3's gap, but adding
  a new reference, how every space starts, would need the folder unlocked
  first.
- **The macOS sandbox (`sandbox-exec`).** It stops a write to the folder as
  well as the file, but it is deprecated, works only on macOS, and means
  rewriting the agent's command before it runs.
- **Reading the script for `.save` and `open(…, 'w')`.** This is the guessing
  issue 152 refused.
