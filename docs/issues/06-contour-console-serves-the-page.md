# 06 — `contour-console` exists and serves the page

**Type:** AFK · **Source:** ADR 0019 decisions 2, 34, 23

## What to build

The executable and its lifetime, with no agent in it. Demoable on its own: run it
in a model space, the sheet opens in a browser, close the tab, the process exits.

**Its own executable, beside `contour`.** A `contour console` subcommand is
structurally defensible and was rejected because it hides the install boundary at
the exact point someone meets it. Two names are self-documenting: `contour` needs
nothing, `contour-console` needs an environment. It also keeps the process tree
honest — `contour-console → contour → Blender`, each layer a subprocess of the one
above, and the dependency only at the top.

**A missing environment fails as *no console environment*,** with the command to
create one. Never a traceback about an import. The console needs an interpreter
the launcher does not, and that is the one error message a first-time reader is
guaranteed to hit.

**Not pip-installed.** It imports `lib/` and classifies the launcher's command
table, so it is bound to this checkout by design; shipping it separately invites a
version mismatch neither side can detect.

**It reads state by importing `lib/`'s Blender-free half and acts by spawning
`./contour`.** Parsing the files independently would put *what a mark is* in two
places that drift silently, both still parsing the old shape. Growing read
subcommands on the launcher would be new surface with one consumer and a process
spawn per read, for what an import already gives.

**It ends when the page says done** — last tab closes, process exits, which is how
`contour canvas` already works. An idle timeout catches the tab left open on
Friday.

## Acceptance criteria

- [x] `contour-console` run in a space opens a browser on the sheet
- [x] Run without the environment, it prints *no console environment* and the command to create one, and exits non-zero
- [x] Run outside a model space, it says so
- [x] Closing the last tab exits the process
- [x] An idle run exits on the timeout
- [x] It serves `lib/canvas.html`, not a copy
- [x] It inherits slice 01's authentication; an unauthenticated request is refused
- [x] `./contour` still runs on a bare clone with no environment, proven by `contour selftest`
- [x] Slice 03's test now also asserts the console imports no `bpy`-bound module
- [x] Ctrl-C leaves no orphan server and no held lock

## Blocked by

- [01 — The canvas server authenticates](01-canvas-server-authenticates.md)
