# 03 — The lib/ split becomes a test

**Type:** AFK · **Source:** ADR 0019 decision 29

## What to build

`lib/` has two halves: modules that run outside Blender and modules that run
inside it. The split is currently legible only by reading imports, and two
properties now depend on it:

**The Blender-free half must stay stdlib-only.** One pip-installed import there
breaks `./contour` on a bare clone, which is the whole of the containment ADR
0019 rests on — the launcher needs nothing, the console needs an environment.

**The console must never import a `bpy`-bound module.** It reads state by
importing the Blender-free half; reaching into the other half would put Blender
in the process that is supposed to spawn it.

`contour selftest` gains the check, because that command is what proves a bare
clone works and is where a violation should surface. The test names the two
halves explicitly rather than inferring them, so adding a module is a decision
about which half it is in.

## Acceptance criteria

- [ ] `contour selftest` fails when a Blender-free module imports a third-party package
- [ ] `contour selftest` fails when a Blender-free module imports `bpy`
- [ ] The test names which module and which import
- [ ] A new module in `lib/` must be assigned to a half or the test says so
- [ ] The check costs no Blender run
- [ ] `contour selftest` stays green on the current tree

## Blocked by

None — can start immediately. The console half of the assertion can be added by
slice 06 once there is a console to assert about.
