# Open questions

Decisions deliberately deferred. Each says what is blocked by it and what
happens by default if nobody decides.

## 1. What the first model is — RESOLVED 2026-09-20

`beaky`: a 1.7 m stylised character of 14 separate parts, target `web`, rigged later.
Its spec lives in its own model space, not here, because this repository is the
toolkit and builds no model (ADR 0015).

## 2. Target engine — deferred on purpose

`web` / glTF only is implemented (ADR 0006). Unity and Unreal are table entries
plus a transform when wanted.

**Blocks:** nothing today. Engine-specific spec fields — origin convention,
unit scale, material slot budget — stay at glTF defaults until a target lands.

## 3. Triangle budget and UV rules per model

`schema/spec.schema.yaml` carries the fields; the values are per-model and
come from the user or from a proposed-and-flagged assumption.

**Blocks:** meaningful `verify.py` output — a budget of 0 fails everything.

## 4. Headless UV unwrapping — the main technical risk

UV operations are likely `bpy.ops.uv.*` only, and operator context under
`--background` is exactly the failure class ADR 0004 avoids elsewhere. Not yet
attempted on this install.

**Blocks:** `uv.required: true` in any spec.
**If it proves unworkable headlessly:** either compute UVs directly in `bmesh`
(more work, fully deterministic), or declare UVs a manual step done in the
linked working file and drop the check. Decide only when a model needs UVs.

## 5. Whether `fixtures/smoke/` needs a golden-file hash

Rejected for now (ADR 0005) as brittle. Revisit if a Blender update ever
silently changes geometry output.

## 6. Remote and backup — PARTLY RESOLVED 2026-09-20

**Resolved: what a remote may ever receive.** Only `master`, the toolkit. Model
content never leaves via git: a model space is never pushed at all, and
`tools/hooks/pre-push` refuses any push that is not `master` or that carries
model paths (ADR 0011, ADR 0015). Sharing a model means `contour export`.

**Resolved: how work survives the disk.** File-level backup of the whole
working directory including `.git`, to external media. No `git push` involved,
so the rule above stays absolute. **Not yet set up — this is the live risk.**
`beaky`'s spec and `build.py` exist on one disk today.

**Resolved 2026-09-20: there is a remote.** A *private* repository at
`github.com/wittaya698/contour.git`, configured as `origin`, holding the
toolkit and nothing else. The intent behind it is to share the toolkit with
other people while no model — mine or theirs — ever appears in it. ADR 0014
decided the architecture that makes that structural instead of guarded, and ADR
0015 built it: a model space is a repository of its own and is never pushed. The
hook is now the backstop rather than the control; it was verified against this
remote the day it was added.

**Still open: the backup, and it is now the only live risk here.** Pushing
`master` protects the toolkit, which is replaceable. What is not — `beaky`'s
spec, its `build.py` and the four reference images that came from outside this
machine, all in its model space — can never be pushed, by design. It exists on
one disk.

**Blocks:** nothing. **Default if nobody decides:** the work survives exactly
as long as this working directory does.

## 7. Sheet size versus "512px thumbnail" — RESOLVED 2026-09-20

Kept the single 1024² sheet. Measured at 93 KB (fixture) and 169 KB (`beaky`), about
34 MB over 200 commits, so the size constraint that motivated 512px did not bind. ADR
0007 and the README now describe what `./contour render` writes.

**Revisit if:** a model's sheet passes ~400 KB. `lib/cmd_render.py` already holds the
pixels as an array, so writing a second, downscaled file to `renders/` is a few lines.

## 8. What `materials.max_slots` limits

Implemented as the number of distinct materials in use across the whole model. The
schema comment says "engine draw-call budget", which fits, but a per-object reading
is also plausible. Decide before a spec depends on the difference.

## 9. Spec fields `verify.py` rejects as unsupported

Deliberately failing, not skipped (ADR 0009): named `dimensions` sub-measurements
(the schema's `seat_height`/`part:` example has no defined measurement), `origin:
world_origin` (no defined meaning for a whole model), UV overlap checking (question 4)
and `udim`. Each needs a definition before it can be enforced.

## 10. `base_center` is the bounding box footprint centre

`verify.py` reads `origin: base_center` as: bounding box minimum Z at 0, and the centre
of its X/Y extent at the origin. For an asymmetric model, such as one with a beak, that
centre is not the midpoint between the feet. Say so if a rig needs the feet centre.

## 11. Two agents, one space — RESOLVED 2026-09-25 by ADR 0019

ADR 0019 puts the console above the launcher, which makes it and a terminal agent
peers: both drive `./contour` over the same model space, and neither is
privileged. `marks.json` is append-mostly and survives concurrent writers by
luck. `build.py` does not — two agents editing it race, and the loser's work
disappears silently into a file the other one overwrote.

**Resolved, and built 2026-09-25.** A run-scoped hold at `.contour/run.lock`,
taken and enforced by the launcher, refusing a second caller with a message that
names the process holding it. The launcher holds it, not the console — so it also
covers terminal-versus-terminal, which raced before any of this existed. Scoped
to a run rather than a build, because the `build.py` edits between builds are
what actually race: `contour run <cmd>...` holds the space for a whole session,
and the builds inside that session are not refused by their own hold.

`check`, `render` and `export` are the commands a second run may not join in on.
`canvas` and `mark` deliberately take nothing: both only append to `marks.json`,
and a canvas session is a person at a page, which would be a hold nobody is
watching.
That decision is a column now — `holds` in `lib/commands.py`, applied in one
place by `lib/cli.py` and asserted per command in `tests/test_commands.py`
(issue 24). `resolve` holds for the reason a build does, and `run` because it
is the unit the hold is scoped to.

A hold whose process is gone is taken over, with a line saying whose it was, so
a killed run does not wedge the space behind a file the user has to know about.
A record written on another machine is never judged dead, because it cannot be.

**Blocks:** nothing.

## 12. A model space has no identity

`.contour/project` is the marker that finds a space (ADR 0015) and carries
`toolkit`, `toolkit_path` and `created`. Nothing in it is unique to the space, so
the only key available to anything outside is the filesystem path.

ADR 0019's per-space ask-list keys on that path and **fails closed** — an
unrecognised space gets the strictest list — so a moved or renamed space makes
the console ask about more than expected rather than less. The damage is
contained; the cause is not fixed.

**Blocks:** nothing. It bites when a space is renamed or moved, which has not
happened yet across `beaky`, `beaky-lite`, `beaky-fable` and `beaky-solo`.

**The path is a key in a second place, found 2026-09-29.** Claude Code files a
session's transcripts under `~/.claude/projects/<the path, slashed to dashes>/`,
and `tools/tokens.py` finds a space's transcripts by deriving that directory
from the space's path. A renamed space therefore starts its **spend** history
from nothing, and the old history sits under a path that no longer exists.

**The lobby makes it likelier.** Renaming a space from the **lobby** is a
decided feature: it shows everything a rename changes and everything it leaves
behind — the ask-list key and the transcripts — before the user confirms. That
makes the loss visible; it does not prevent it. An id in `~/.contour` would fix
both keys at once.

**If nobody decides:** paths stay the key and fail-closed stays the guard. The
durable fix is an id in `~/.contour` pointing *at* the path — not a field in
`.contour/project`, which is tracked, inside the space and agent-writable, and
would let the agent choose which permission set applies to it (ADR 0019 rejects
that explicitly).

## 13. The eight rules reach a space by where it happens to sit

`CLAUDE.md` lives in the toolkit. A space under `project/` inherits it because
Claude Code walks *up* from the working directory and the toolkit is a parent —
an accident of location, not a decision. ADR 0015 defines a space as its own
repository found by walking up for `.contour/project`, and says nothing about it
living under the toolkit.

So a space created elsewhere gets no `CLAUDE.md` and none of the eight hard rules.
`refs/` stays protected, because the guard is wired in the space's own
`.claude/settings.json` (ADR 0015) — but rules 2, 4, 6 and 7 quietly do not exist
for an agent working there.

**Blocks:** nothing today; every space on this machine is under `project/`.
ADR 0019 makes it sharper rather than causing it: a console is pointed at a path
rather than launched from a shell someone is standing in.

**If nobody decides:** it stays true and stays invisible until the first space
lives somewhere else. The candidate fixes are `contour init` writing a space-level
`CLAUDE.md` that points at the toolkit's, or `contour doctor` reporting when a
space cannot see the rules.

