# Contour

Code-authored Blender game assets. A model is a Python script, not a file you
sculpt — so it is diffable, reproducible, and mechanically checkable.

Every build starts from an empty scene and runs `build.py`. `verify.py` then
measures the result against a spec you wrote and reports pass or fail per
check. There is no hand-editing step to forget or repeat.

## Install

You need **Blender** and **Python 3** on `PATH`. Nothing else — no virtualenv,
no `pip install`, no dependencies — for everything `./contour` does, which is
the whole pipeline: it is a stdlib launcher that shells out to Blender and runs
everything inside Blender's own bundled Python. The one exception is
`contour-console`, the browser surface a run is driven from; it needs an
environment, which is why it is a second name rather than a subcommand.

```sh
git clone <this repo> Contour
cd Contour
./contour install-hooks              # required, see below
./contour selftest                   # proves the install works end to end
ln -s "$PWD/contour" ~/.local/bin/   # so you can run it from a model space
```

`selftest` builds a fixture, verifies it, renders it, exports a `.glb` and
re-imports it, and deliberately corrupts the build and the `.glb` in 37 ways
to prove the checks can actually fail. If it passes, you are installed.

**One suite run per machine at a time.** `selftest` and
`python3 -m unittest discover -s tests` both start real consoles, and the tests
that prove none outlives its test count every `console.server` on the machine —
on purpose, since an orphan has no parent to report it. A second run alongside,
from another terminal, worktree or agent session, looks to them like a leak
(issue 94). So the suite holds a lock for the length of a run (`tests/one_run.py`),
and a second run is refused at once, naming the pid of the one already going.

### The console needs an environment; `./contour` still does not

Everything above is the launcher, and the launcher keeps the promise: stdlib
only, nothing installed. `contour-console` — the browser surface a run is driven
from (ADR 0019) — is the exception, and it is the only one. It needs its own
interpreter, which is why it is a second name rather than a `contour`
subcommand:

```sh
python3 -m venv .venv && .venv/bin/pip install -r console/requirements.txt
```

Run it without one and it says *no console environment* and prints that command.
Nothing in the pipeline reads it: `contour selftest` proves a bare clone works,
and that is still what makes this repo shareable.

**`install-hooks` is not optional.** It copies `tools/hooks/pre-push` into
`.git/hooks/`, which is what stops model content ever reaching a remote
(ADR 0011). It is per clone, and nothing else enforces it — run it before you
add a remote, not after.

### Blender location

The launcher looks for Blender at
`/Applications/Blender.app/Contents/MacOS/Blender`. Anywhere else, point
`$BLENDER` at the binary:

```sh
export BLENDER=/path/to/blender
```

Developed against **Blender 5.2.1 LTS**. Other versions may work, but the
toolkit assumes API signatures it can check at runtime rather than recall —
see `./contour api` below. A build that takes longer than 300 s is killed.

### Why the symlink

Models do not live in this repository (ADR 0015). You work inside a *model
space* — its own directory, its own git repo — and run `contour` there, so the
launcher needs to be on `PATH`. It resolves its own location through the
symlink, so the toolkit can be moved later and only the link needs relinking.

## Make a model

A model is a directory of its own, anywhere you like, with its own git
history. It is never pushed. Spaces are found by their marker, not their
path, so the location is yours to choose — `project/` under the toolkit and a
sibling directory both work, and a space can be moved between them at any time
with `mv`.

If you keep them under the toolkit, note that `git clean -xdff` there deletes
them. Plain `git clean -xdf` does not — it skips nested repositories.

`contour init` makes the directory in the current one, runs `git init`, writes
the `.contour/project` marker and copies in the agent's rules: a `CLAUDE.md`,
the spec guard's settings, and the `build-model` and `release-model` skills. It
also installs a pre-push stub that refuses every push. It never overwrites a
file that already exists, so it can adopt a directory you have started.

```sh
cd ~/Workspace                     # or project/ under the toolkit, or anywhere
contour init chair && cd chair
cp ~/photos/*.jpg refs/            # whatever you are working from
cp /path/to/Contour/schema/spec.schema.yaml spec.yaml
$EDITOR spec.yaml                  # dimensions + tolerances, parts, budgets
$EDITOR build.py                   # bmesh + the data API, authored in mm
contour doctor                     # is the space in step with the toolkit
contour check                      # no model name: you are standing in it
```

`lib/kit.py` has the helpers a `build.py` uses — millimetre conversion,
materials from hex, boxes, spheres, cylinders, and `add()` to turn a bmesh
into a placed object. `fixtures/smoke/build.py` is a complete example in ten
lines.

`check` prints one line per failure and a two-line report when it passes:

```
chair PASS  verify 17/17 | tris 4,210 | height 900mm
  width 420.0 | depth 480.0 | quads 96% | parts 5/5 | mat_slots 2/2 | origin base_center
```

Then look at it, and ship it when it is right:

```sh
contour render                     # 4-view sheet -> sheet.png
contour export                     # .glb, re-imported and re-measured to prove it
git add -A && git commit
```

When an agent is doing the work, it stops before that last line. It shows you
the `check` report and the sheet the build was drawn from, and commits only
once you have seen both and said ship (rule 5 in `CLAUDE.md`).

## A rig, and clips that move it

A model that moves carries its rig and its animation in the same spec and the
same build (ADR 0023). Give parts a `parent:` and the spec has a tree; give it
`clips:` and the tree moves. Every number is yours, in the spec, and nothing is
posed by hand:

```yaml
parts:
  - { name: torso, count: 1 }
  - { name: leg_L, count: 1, parent: torso }
transform:
  pivot_tolerance_mm: 1        # how far a part's origin may sit from its seam
clips:
  walk:
    frames: 30
    fps: 30
    loop: true
    keys:                      # degrees about X, Y, Z, in the parent's frame
      0:  { leg_L: [25, 0, 0] }
      15: { leg_L: [-25, 0, 0] }
    tol_deg: 1
    seam_growth_mm: 3
    roundtrip_mm: 0.1
```

`build.py` ends with `kit.rig()`, which builds one bone per part from the tree,
binds each part rigidly to its bone and keys every clip from the spec. `check`
then holds the rig to it: every pivot on the centre of its seam, every key read
back within `tol_deg`, no seam growing past `seam_growth_mm` and no part entering
another at any frame. `export` carries bones and clips into the `.glb` and
re-imports them, every part within `roundtrip_mm` of the build at every frame.

What numbers cannot say — whether it reads as a walk — is a picture, drawn at a
checkpoint and never on a build:

```sh
contour filmstrip                  # six side and six front frames -> out/filmstrip.png
```

## Marking, and driving a run from the browser

Everything above is you and a terminal. There are two more surfaces, and both
exist because a number is not the only thing that goes wrong with a model.

**Marks are located comments** (ADR 0018). `contour canvas` puts the sheet and
your reference images in a browser; click a spot, type one line, and it is
tracked in `marks.json` beside the build. A mark on the sheet says *the build is
wrong here*; a mark on a reference says *here is what I meant*. The click becomes
a pin in the hit part's own coordinates, so it moves with the geometry instead of
pointing at a pixel that stopped meaning anything at the next build. The agent
marks too — `contour mark --part cap "..."` — and only you ever close one: the
agent can attach *addressed in this build*, which dims the badge and settles
nothing.

```sh
contour canvas                     # the sheet, to mark on; waits for you
```

**A number read off a reference is a span** (ADR 0022). Drag on a reference
instead of clicking, and the mark has two ends: *this distance, right here*.
`contour measure --span m9` reads it in millimetres, scaled from the
`dimensions.height` your spec states, and pins the answer beside it. A picture
carries proportion and never scale, so with no height in the spec it refuses
rather than guess.

The agent draws spans too, and never types a pixel for an end. It names what to
measure and code places the ends on what was found:

```sh
contour measure refs/side.jpg --silhouette --extent across "depth, front to back"
contour measure refs/front.jpg --scanline 250 --of '#3B3F72' --runs 1,2 \
    --between centres "the legs, centre to centre"
contour measure --again m4         # ask a snapped span's question again
```

Only where nothing snaps — a photograph of a real object, a soft gradient —
may it place the ends itself, with `--by-eye --from X,Y --to X,Y`. Such a span
is dashed on the canvas and says *by eye* wherever it shows, and its answer says
the error bar covers the arithmetic between the ends, not where they were put.

An agent span is a question, and you answer it on the canvas: **adopt** (it is
right, and yours from then on), **correct** (drag its ends where they belong; it
is re-measured), or **reject** (with one line of why; its number is not used).
When spans are waiting, the canvas says *Claude has 4 questions about your
pictures* and steps through them one at a time, each zoomed on its reference:
*Yes, that's it*, *Let me move it* and *Wrong thing…* are adopt, correct and
reject, and *skip for now* leaves one unanswered. Answering from the marks list
still works.
`contour measure --standing m4` says whether a span's number may go into a
proposal: yours, the agent's own reading for a snapped span you have not
answered yet, or not at all — a by-eye span waits for your answer, and a
rejected one never counts.

`contour worksheet` draws every span onto its reference as one image,
`worksheet.png`, with each span's id, number, owner, how it was placed and your
answer. It is how the agent sees its own spans, once, before it proposes a
number from them. No reference is ever written: an annotated photograph is not
the photograph.

**`contour-console` drives the agent behind a gate** (ADR 0019). Same page, one
more capability: a transcript on one side, the current sheet on the other, and
every call that means something — a build, a spec write, a commit, a push —
stopping to ask you first. A gate says the act in plain words, *Claude wants to
build the model to check its work* or *Claude wants to change the spec*, and
under it what would change: *seat depth 600 → 640 mm*, and the span the number
came from. The raw call is a click away. What you answer is a verdict and a
sentence, never an edited call: the agent writes the code, you say what you
think of it. A commit asks *Save this version?*. A denial is kept as a **veto**
in the space, because it is why two builds differ, and the page lists them under
*You said no to*.

```sh
cd /path/to/Contour               # once, in the toolkit checkout
python3 -m venv .venv && .venv/bin/pip install -r console/requirements.txt
ln -s "$PWD/contour-console" ~/.local/bin/

cd ~/Workspace/chair              # then from inside a model space
contour-console
```

What runs unwatched is yours to set, in `~/.contour/ask-list.yaml`. It has no
presets: a category it does not name is gated, so the first run asks about
everything and you tune it downward — `contour asks` prints what is in force and
`contour intents` prints the categories there are to name. A build gate also
offers *Always for this model*, which lets later builds in that space through
unasked; the page lists what runs unasked, each with Undo. Spec writes,
reference writes and saving never offer it, and neither does push. Select open marks
before starting and they compose into the prompt, and at the end the run says of
each one whether it was addressed, left alone, or orphaned by a part that went
away. What the run cost is one quiet line, *12 turns*, saying too how many
turns gates cost; the token breakdown is a click away, and `tools/tokens.py`
reads it afterwards in the same units it reports a terminal session in.

The page is written for someone who has never opened a terminal (ADR 0025).
Under the sheet it says whether the model is right: *matches the spec*, or one
plain sentence per check that fails, *Height is 1640 mm; the spec wants 1700,
give or take 5*. The transcript shows each call as one line of what was done,
*Built the model — 2 things don't match*, with the raw call a click away, and
the agent itself speaks in the same plain words. **Export** runs
`contour export` once the build is green, and a card shows the file with
Download and Show in Finder. Words worth learning, like *spec* and *span*,
explain themselves where they first appear. Every page carries the header
*Models › chair*, and *Models* goes back to the lobby.

Nothing about the console is load-bearing for the pipeline: `contour selftest`
proves a clone with none of it installed still builds, verifies, renders and
exports.

## The lobby: every space on one page

```sh
contour lobby                      # from anywhere; no space needed
```

The lobby is a page above the spaces (ADR 0021). Each space is a row: the
model's last sheet, or a reference before its first build, its name, whether
it matches its spec, and when it was last worked on. Health shows only when
something is wrong: *needs an update*, or a remote, which a model must never
have. There is one lobby: running `contour lobby` again shows the one already
open, and `contour lobby --create [name]` opens it on the create form. It does
to the spaces what you would otherwise do in a terminal:

- **create** runs `contour init`, defaulting to `project/` under the toolkit,
  then opens the new space's console with the new-space flow as its first
  prompt. Reference pictures dropped onto its form, or chosen with its file
  picker, start the space in `refs/`, copied byte for byte; a picture that is
  not a PNG, JPEG or WebP, or is over 20 MB, is refused before anything is
  made. The lobby never drafts a spec itself: that happens in the console,
  behind its gates.
- **variation of this** is create, with a first prompt that points at the
  source's `spec.yaml` and `build.py` for reference. Nothing is copied, so the
  variation's spec is agreed as its own. It takes dropped references as create
  does; a space that already exists takes none, since adding a reference is a
  change its console gates.
- **enter** opens a space's console in a tab of its own. Closing the lobby
  ends none of them.
- **rename** shows everything it will change before it changes anything, and
  never commits; the space lists as renamed until you do.
- **update** sits beside a row's *needs an update*. It shows what
  `contour update` proposes, what it will replace and what it will leave
  alone and why, then does it on confirm. It never commits; the space lists as
  *updated, not saved yet* until you do.
- **delete** writes a `git bundle` of the space into `~/.contour/trash` first,
  and you confirm by typing its name. Deleted spaces are listed, and can be
  restored or purged from there.
- **open in Finder**, for anything else.

Every action is the command of the same name, run for you; the refusals are the
command's own. A space open in a canvas or a console says so in the list, and
cannot be renamed, updated or deleted from under it. Only enter and create's
handover need the console's environment; without one, the lobby shows the line
that makes it.

The lobby looks where `contour spaces` does: the directory holding the toolkit,
or the folders in `$CONTOUR_SPACES`, separated by `:`.

## Asking from Claude Desktop

```sh
contour mcp --config               # prints the block; writes nothing
```

The connector lets a Claude Desktop chat read your spaces (ADR 0024). Paste the
block it prints into `claude_desktop_config.json` under `mcpServers`, beside any
servers already there, and restart Desktop. The block names the `contour` link
from Install, not the checkout, so moving the toolkit is still only a relink. If
there is no link on `PATH`, the command says so and exits 1.

Today the connector answers ten tools. `spaces` is the same reading as
`contour spaces --json`. `status` takes a space and gives its last check's
verdict, in the console's plain sentences beside the report lines, and its open
marks, uncommitted vetoes and toolkit drift. `log` gives the tail
of a space's last Blender log and says which stage wrote it. `picture` shows a
space's sheet, filmstrip or worksheet and says whether it is still current; it
never renders one. Desktop shows the picture inside the tool call's row, so
expand it to see it. `spec` gives a space's `spec.yaml` as text, and `spend` what
each console run there cost, in the units `tools/tokens.py` prints. `open`
starts a space's console or canvas, or the lobby, and says only whether it
did: never the page's address, which carries its secret. It refuses a second
console as the lobby does, and a canvas on a space a console already serves.
`create` is the lobby's create, plus reference pictures: give it a name and the
paths of images on disk, and it makes the space where the lobby would, copies
them into `refs/` byte for byte, and opens its console on the new-space flow.
It refuses any path that is not a `.png`, `.jpg` or `.webp` image before
anything is made, and drafts no spec. A picture pasted into the chat is not the
file, so it is not taken as a reference: `open` brings up the lobby on its
create form instead, the name filled in if you gave one, for the file to be
dropped there. `request` and `stop` are `contour request` and `contour stop`,
with the same arguments and the same refusals: a chat can ask for a run nobody
watches and end one, and that is all it can start in a space. It never answers
a gate or a question. A run it asked for does not stop at a gate: the act is
set aside for you, and the run carries on. Its console shows what waits, oldest
first, with the diff and Claude's case, whenever you open it: allow makes the
call then, and deny is a veto. A question is set aside the same way, in its
place in the order: your answer starts a new run in that console, with the
question and the answer as its first message. Until they are answered, the
lobby's row and `status` say how many wait and for what, never why, and a
request to that space is refused; the chat asks whether you want to answer
them now, which is `open`, or later. Its answers are meant to read as the pages do, in plain words. Otherwise
it never builds, writes, marks or holds anything in a space: to change a model
yourself, open its console. Every space it finds is visible to the chat,
so what you ask about goes to the model provider. Installing the connector is
the choice to allow that, and Desktop asks before each call.

## Commands

| Command | Does |
|---|---|
| `contour check` | build from an empty scene, verify against the spec |
| `contour render` | 4-view orthographic sheet with a 1 m grid and rulers |
| `contour export` | `.glb`, re-imported into a clean Blender and re-measured |
| `contour api <symbol>` | the real signature from the installed Blender |
| `contour selftest` | the fixture through every stage, plus 37 mutants |
| `contour init <name> [--to <dir>]` | create a model space here, or in `<dir>` |
| `contour doctor` | is this space still in step with the toolkit |
| `contour update` | propose bringing this space's rules in step, where nobody edited them; `--yes` does it |
| `contour spaces [name]` | list model spaces, or print one's path |
| `contour lobby [--create [name]]` | every space on this machine, on one page; or opened on its create form |
| `contour mcp` | the connector, for Claude Desktop; `--config` prints its block |
| `contour rename <name>` | propose renaming this space; `--yes` does it |
| `contour delete <name>` | propose deleting this space; `--yes` does it, leaving a bundle |
| `contour restore <id>` | clone a deleted space back from its bundle |
| `contour purge <id>` | propose removing a deleted space's bundle; `--yes` does it |
| `contour install-hooks` | install the push guard into this clone |
| `contour canvas` | the sheet and the references in a browser, to mark on |
| `contour mark --part <p>` | pin a finding on the sheet, for the user to see |
| `contour resolve` | anchor marks against this build, before it changes |
| `contour measure <ref>` | real pixel geometry from a reference image; draws and reads spans |
| `contour worksheet` | every span drawn onto its reference -> `worksheet.png` |
| `contour filmstrip [clip]` | a clip as six side and six front frames -> `out/filmstrip.png` |
| `contour run <cmd>...` | hold this space for one run, then release it |
| `contour asks` | what this space lets through, and what asks; `--always build` and `--undo <c>` are the page's |
| `contour intents` | the call categories a gate can ask about |
| `contour-console` | drive a run from the browser, behind a gate |
| `contour-console --begin <flow>` | the same, its run begun on `new-space` or `variation --of <space>` |

The commands a client reads — `init`, `spaces`, `rename`, `update`, `delete`,
`restore`, `purge`, `asks` — take `--json`, which is how the lobby runs them. The model commands
run inside a model space and take no model name. Outside one
they refuse and say so, rather than guessing. Every one of them is stdlib except
`contour-console`, which is a separate executable for exactly that reason.

Blender's stdout is 2–5k tokens of banner per run, so it goes to
`.contour/last-build.log` and only a terse report is printed. Read the log on
failure.

`api` exists because recalled signatures are guesses:

```sh
$ ./contour api bmesh.ops.create_cube
bmesh.ops.create_cube: BMeshOpFunc bmesh.ops.create_cube(bmesh, size=0.0,
    matrix=Matrix(), calc_uvs=False) -> dict(verts=[])
```

## Layout

A model space, anywhere on disk, its own git repository:

```
<space>/
    spec.yaml     your intent, in numbers    (the agent reads, never writes)
    refs/         your intent, in pictures   (the agent reads, never writes)
    build.py      the attempt                (rebuilt from an empty scene)
    sheet.png     the 4-view render you approved
    worksheet.png the spans drawn onto the references          (ADR 0022)
    marks.json    located comments and spans, from both sides   (ADR 0018)
    vetoes.json   calls you refused at a gate, and why            (ADR 0019)
    NOTES.md      what is deferred, and what is undecided
    CLAUDE.md     the agent's rules          (copied from the toolkit; `contour doctor` says which are behind or edited, `contour update` brings the behind ones in step)
    .claude/      the spec guard's settings, and the build and release skills
    .contour/     the marker, plus logs               (git-ignored)
    out/          generated .blend, filmstrip, scratch (git-ignored)
    exports/      generated .glb                      (git-ignored)
    release/v<N>/ archived .blend + .glb + sheet      (tracked, at a tag)
    work/scene.blend  YOUR file — materials, lights, camera (git-ignored)
```

Rebuild the asset and your scene file picks up the new geometry, because you
never worked inside the generated file.

## Branches

This repository is the toolkit — `lib/`, `verify.py`, `schema/`, `fixtures/`,
`tools/`. It builds no deliverable of its own and carries no model content on
any branch, which is what makes it shareable (ADR 0015).

Models are not branches here. Each one is its own repository — under
`project/`, which this repo ignores and the push guard blocks, or anywhere
else you like — with its own history, and it is never pushed. Earlier versions of Contour kept
models on long-lived branches; see
[docs/git-branch-strategy.md](docs/git-branch-strategy.md) for that history and
ADR 0015 for why it changed.

## What git tracks, and what never leaves

Source, specs, reference images, and the render sheet (1024², ~170 KB) per
accepted commit — so `git log` doubles as a visual timeline. The `.blend` is
derivable and stays ignored, except in a release package where it is committed
once alongside the `.glb` and the approved sheet (ADR 0013).

**Model content is never pushed.** Only `master`, the toolkit, reaches a
remote; the `pre-push` hook refuses everything else and refuses any push
carrying model paths, including onto `master` by mistake (ADR 0011). To share
a model, run `./contour export` and hand over the `.glb`.

Backup is therefore file-level: copy the working directory, including `.git`,
to external media. A push will never protect the part that matters.

## Working with an agent

`CLAUDE.md` holds the operating rules an agent must follow here — always the
`./contour` commands and never raw `blender`, never `bpy.ops` outside a
whitelist, never weaken a check to make it pass, and never commit or push
without being asked to. `.claude/skills/new-space` is the workflow for starting
a model. The iterate and release workflows are in `templates/space/.claude/skills/`,
and `contour init` copies them into each model space.

Two of those rules are enforced rather than trusted: `tools/hooks/pre-push`
blocks model content leaving via git, and `tools/guards/spec.py` — which a space
runs as `contour hook spec` — refuses writes to a spec or a reference image that
git already tracks. A spec is the definition of correct, so it is not the
agent's to adjust.

When the agent argues a spec is wrong, the argument has to be a measurement,
and a measurement off a reference has to be a span the proposal names (rule 1,
ADR 0022). A number with no span behind it is not an argument, and a by-eye
span argues nothing until you have answered it.

## Decisions

Every structural choice here has a short ADR in [docs/adr/](docs/adr/) with the
alternatives that were rejected and why. What has *not* been decided yet, and
what each gap blocks, is in [docs/OPEN-QUESTIONS.md](docs/OPEN-QUESTIONS.md).
