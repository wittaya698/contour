# 160 — A script that reads a reference runs

**Type:** HITL · **Source:** the console run that checked issue 155, 2026-10-23

## What to build

A new-space run asked *Claude wants to change your reference pictures* twice
for scripts that only read the photo:

- `python3 -c "from PIL import Image; im=Image.open('refs/….png').convert('RGB'); for x,y in …: print(…getpixel((x,y)))"`
- `.venv/bin/python -c "import numpy as np; from PIL import Image; a=np.asarray(Image.open('refs/….png')…); …print(…)" 2>&1 | head -40`

Issue 152 left this case gated on purpose: an interpreter can write
anywhere, and telling `Image.open('refs/…')` from `.save('refs/…')` in a
script's text is guessing. But it is how the agent measures colour, so it is
the warning a run raises most, and every one is a click on a read. The one
that means it reads the same.

Proposed, for the user's verdict: stop guessing from the text. A script
that names a reference runs; afterwards git says whether `refs/` still
matches what it tracks. If a tracked reference changed, it is put back from
git at once and the agent is told the write was refused, as the guard tells
it now (rule 1, ADR 0012). A reference git does not track yet is how a space
starts, so it is left alone, as the guard leaves it.

Questions this needs answered before it is built:

- Is *put back after* as good as *stopped before* for rule 1? The picture is
  changed for the length of the call, and anything the script did with the
  changed picture in that time stands.
- Under a console only, or the guard too? The guard runs in a terminal
  session with no console to restore anything.
- Which calls: interpreters only, or every ref-write the text cannot rule
  out?

## Acceptance criteria

- [ ] The user has decided whether a script naming a reference runs and is checked after, and the answer is written into an ADR or this issue
- [ ] If yes: `python3 -c "…Image.open('refs/x.png')…"` raises no gate, and one that rewrites a tracked `refs/x.png` leaves it as git has it and tells the agent it was refused
- [ ] `cp x refs/…` and `> refs/…` on a tracked reference are still denied before they run

## Blocked by

None - can start immediately
