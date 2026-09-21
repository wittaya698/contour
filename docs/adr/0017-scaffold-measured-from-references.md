# 0017 — The scaffold: what the references measure, recorded separately

**Status:** Accepted · 2026-09-21 · **extends [ADR 0016](0016-specs-from-references-and-revision.md) and corrects its worked example, reorders `new-space` steps 5–6, clarifies rule 8 in [ADR 0011](0011-model-content-stays-local.md)**

> **Drafted Proposed, accepted the same day on the tracer bullet's result.** The
> untested claim was that pixel measurement can be made mechanical rather than
> perceptual. `contour measure` was built and run against the numbers `beaky`
> already held. It works — and it disagrees with them, which is the outcome that
> justifies the whole ADR rather than the one that withdraws it.

## Evidence: the tracer bullet, 2026-09-21

`contour measure` against `beaky`'s own references, anchored on 1700 mm:

| | `NOTES.md` / ADR 0016, by eye | `contour measure` | `build.py` | spec |
|---|---|---|---|---|
| width (front silhouette) | — | **888** | 886 | 880 ±20 |
| depth (side silhouette) | *"about 620"* | **597** | 612 | 600 ±20 |
| legs, centre to centre | *"191"* | **168** | 165 | — |
| head centre height | *"~1520"* | 1501 | 1505 | — |
| torso centre height | *"775"* | ~784 | 775 | — |

The leg figure is stable across five scanline heights (167–173, settling at 168)
and is confirmed independently by the navy profile's half-width minus the leg's
own width. Two query types, one answer.

**Two of `beaky`'s recorded findings do not survive it.**

*The legs.* `NOTES.md` calls them *"the one bullet from the original pass that
measuring confirmed"* — 191 measured against 165 built. Mechanically the
references give 168 against 165 built: a 3 mm difference, inside any tolerance
anyone would write. The defect is not there.

*The depth.* ADR 0016 states that `refs/side.jpg` *"gives about 620 mm"* and
concludes *"the contract is what is wrong"*. It gives 597. The contract's 600
matches the references within 3 mm; the build's 612 is what drifted. The
conclusion was inverted, and inverted in the direction that blamed the one
artifact the agent is not allowed to change.

**This is the justification for the whole ADR, stated better than the design
argument could state it.** Careful perception, done by an agent that knew it
must not recall, that wrote the discipline down three times, and that recorded
its results in a tracked file, was still wrong by 14% on the number it was most
confident about. `NOTES.md`'s lesson — *measure the image, do not recall it* —
turns out to name a distinction it could not itself act on, because looking
carefully and measuring are not the same operation.

## Context

ADR 0016 closed with a consequence it could not answer:

> *"**Nothing measures a reference image.** mm-per-pixel is the agent's own
> arithmetic on an image nothing else reads, and a wrong anchor reading is
> invisible to every check here."*

This ADR is about that sentence. The request that prompted it was broader —
turn a reference image into an editable, traceable, measured multi-view sheet —
and most of that request is this repository re-derived: a source of truth that
generates its views, an anchor because pictures carry proportion and not scale,
a mandatory confirm step, append-only history, a validator that blocks on hard
errors. What is genuinely absent is the thing ADR 0016 named.

**`refs/` is measured by nothing, and read by nothing.** `verify.py` measures
the build. `contour check` compares the spec against git. No command opens a
reference image. The one number that scales every other number — mm-per-pixel
from the anchor — is computed in the agent's head, used once, and discarded.

**The measurements exist, in prose, in the file nothing verifies.**
`beaky/NOTES.md` holds hand-typed three-way comparisons: legs 191 measured
against 165 built; beak 113 across and 163 proud against 100 and 155 specced;
torso centre 775 against 775; neck 1166 against 1170; head centre ~1520 against
1505. Each is a real finding. None is data. None is rechecked when `build.py`
moves.

**One of them is a deadlock waiting to be formalised.** `NOTES.md` records that
matching the reference's 163 mm beak would put depth on 620 mm, *"the exact
ceiling of 600 ± 20"*. The references and the contract disagree, irreconcilably,
and the contract wins. Any design that makes reference measurements binding
makes `beaky` unbuildable.

**Three spaces share one set of photographs.** `beaky`, `beaky-fable` and
`beaky-lite` each carry the same `front.jpg`, `back.jpg`, `side.jpg`,
`top.jpg`. Three specs, three builds, one body of evidence — and today it is
measured independently, by eye, in each.

**The references were read on 2026-09-21 to find out what a segmenter could
see.** They are flat-colour toon renders, and the outlines are *not* uniform.
Arms, hands, beak, eyes and shoes carry thin dark contours. Head, neck and
torso do not — they are smooth-shaded against a near-white ground. So colour
gives material regions, not parts: red is head **+** beak, ochre is neck **+**
arms **+** hands, navy is torso **+** legs **+** shoes. **The torso-to-leg
junction is navy-on-navy with no contour at all** — precisely where the one
confirmed open finding lives. An automatic part segmenter would be blindest
exactly where it is most needed.

**The references are perspective renders, not orthographic.** The tops of the
shoes are visible. An anchor corrects overall scale; it does not correct scale
that varies with depth.

**The mechanical position.** `lib/cmd_render.py` already projects world points
through the real camera and paints them onto finished pixels, only where the
render is still background, so the model occludes what is behind it — the exact
mechanism a dimension line needs. Its `FONT` carries glyphs for `front`,
`right`, `top`, `persp`, `grid 1 m`, and of the digits, only `1`. It imports
`numpy`, which exists in Blender's bundled Python and not in the system one.
`tools/guards/spec.py` covers `refs/**` alone; ADR 0016 moved spec enforcement
out of it into the launcher.

## Decision

**A new artifact, `scaffold.yaml`, records what the references measure.** It
sits at the root of a model space, tracked. It is the missing third term:
today the repository compares *spec ↔ build*; the scaffold adds *refs ↔ spec ↔
build*.

**It is a measurement record, never a geometry source.** It describes the
photographs, not the mesh. It never has to express `SHOE_PROFILE`, and
`build.py` is never generated from it after the first pass. This is the
decisive constraint: `beaky`'s two best improvements — the lathe beak and the
nine-row shoe profile — were both moves *away* from primitives, and a schema
that had to keep up with them would cap the model at its first draft. A photo
cannot tell you `round_k = 0.55` either.

**Every value carries provenance and a re-runnable basis.** Not `value: 163`
but the image, the pixel measurement, the anchor ratio, and one of
`user_set` / `estimated` / `assumed` / `derived`. Depth and anything occluded
is `assumed` by default, because photographs tell us least about it. A basis
that names the command and its output is something a second party can re-run;
a bare number is not.

**Divergence is reported, never red.** `contour check` stays green when the
scaffold and the build disagree; the difference surfaces in the report and on
the sheet. **The references are not the intent — the spec is.** The user is
entitled to stylise, simplify or correct a bad angle, and under a red rule that
deviation could only be resolved by editing the scaffold to match the build,
which is the agent moving goalposts one layer down. `beaky`'s beak proves the
stronger form: two contracts that cannot both be satisfied produce an
unsatisfiable red and an unbounded loop of Blender runs.

**A scaffold value becomes enforceable only by promotion into the spec**,
through ADR 0016's existing gate — propose, user confirms, write with
`revision:` bumped. There stays exactly one definition of correct.

**`spec.yaml` and its schema are untouched.** The spec has one trust class,
*confirmed*, and that is what makes it a contract; stamping `estimated` inside
it would either mean nothing or admit the gate did not happen. The complaint
that motivated per-value provenance — `beaky`'s *"tolerance the agent invented"*
— is answered by putting the error bar in the scaffold and the tolerance in the
spec, which is `new-space` step 4's own prescription (*"`depth 620 ±6 measured,
proposing tol 15`"*) with both halves finally given somewhere to live.

**The scaffold is agent-writable, and the commit gate is its control.** No new
guard. Re-measurement is the behaviour most worth encouraging, and *"I measured
it properly this time"* and *"I changed it so it would stop complaining"* are
the same diff — so the defence is the basis field, not a lock: the number cannot
move without the basis moving, and a basis is checkable against the photograph
in seconds. Rule 5 puts the user between disk and history regardless. The
heavier ADR 0016 counter is not applied, because the scaffold is by this ADR's
own decision *not* the definition of correct, and gating the advisory artifact
more tightly than the contract would be incoherent.

**Measurement is split by competence: the agent supplies semantics, code
supplies arithmetic.** Which blob is a hand, which way the face points, whether
the far arm is hidden — the agent. How many pixels across, where the centroid
sits, how far apart — `numpy`. This is rule 7's principle one domain over:
`contour api` exists because recalled signatures are guesses, and recalled pixel
counts are guesses for the same reason.

**`contour measure` is a query instrument the agent aims, not a segmenter.**
`--silhouette` (background difference), `--region <hex>` (a colour's bounding
box), `--scanline <y>` (runs of a colour at a height), `--profile <hex>`
(half-width per height). The references show a segmenter cannot find the
torso-to-leg boundary, but a scanline across the legs finds their two centres
without needing to know what a leg is. Composable, individually mutant-able
(ADR 0009), and honestly degrading: on a photograph of a real chair the
silhouette query still works, the colour queries do not, and `status` has to say
so.

**The scaffold is per-space, and duplication is safe because measurement is
deterministic.** Three spaces measuring the same image is one function evaluated
three times, not three opinions. Space isolation (ADR 0015) is untouched, and no
cross-space artifact is introduced. The semantic layer may and should differ
between spaces.

**The confirm step happens against a render, not a table.** The scaffold
generates a crude first `build.py`, which `contour check` and `contour render`
turn into a sheet the user actually looks at. A table of forty numbers cannot
catch *which way does the face point*; a picture can, and all three of `beaky`'s
wrong-by-eye claims would have been visible in one.

**`new-space` steps 5 and 6 therefore swap order, and the discipline is
preserved by what is tracked rather than by what exists.** The generated
`build.py` and everything in `out/` stay **untracked** until the spec is
confirmed, so the first commit is still `spec.yaml` + `refs/` + `scaffold.yaml`
with no geometry in it and `git log` still shows the contract accepted before a
vertex reached history. What ADR 0002 guards against is the agent fitting the
contract to what it managed to build; here there is no attempt to fit, only a
mechanical rendering of the user's own photographs.

**Two shareable artifacts, both generated, both tracked.** `sheet.png` gains a
dimension layer drawn from measured geometry. `worksheet.png` is new — the
scaffold's measurements replayed onto the references — written by `contour
worksheet`, kept separate from `contour render` because the two consume
different inputs at different stages. **It is a new file and never a write to
`refs/`**: an annotated photograph is not the photograph, and rule 1 holds.

**Rule 8 is a boundary on git and remotes, not on the machine.** No model space
is ever pushed; the hook stays; `project/` is never `git add`ed. Handing someone
a `.glb`, a `sheet.png` or a `worksheet.png` out of band was always sanctioned —
`contour export` is exactly that — and remains the owner's call.

**A presentation tool may only receive a finished render as a placed image.**
Never rebuilt panes, never a typed dimension. The drawing and the numbers must
come from one code path, or they drift the moment `build.py` moves.

**First milestone is a test, not a feature.** Build `contour measure` alone and
check it reproduces the six numbers in `beaky/NOTES.md`. If the scanline returns
191 for the legs, the mechanical half is validated and the rest is assembly. If
it returns 174, then perception and measurement disagree — the most important
thing this project could discover — learned for the price of one command. Only
then, `beaky-fable`, which has no commits yet and is the one space where a
scaffold can legitimately precede a spec. `beaky` itself is left alone
afterwards: its spec is committed, and divergences there want revisions, which
is ADR 0016's conversation and not this one.

## Consequences

- **`NOTES.md` prose becomes data.** Six hand-typed comparisons that rot today
  become values that are rechecked on every build.
- **A third comparison exists for the first time.** refs ↔ spec was previously
  unrepresentable; it was the gap ADR 0016 named and could not close.
- **The feature is purely additive.** One new file, two new commands, one new
  report line, nine new font glyphs. No existing file changes meaning. The
  spec schema, `verify.py`'s `TOP`, the guard and the mutant count are all
  untouched.
- **Cost is near zero on the hot path.** Divergence reporting follows the
  fail-only convention (ADR 0008), so `contour check` pays nothing when the
  scaffold agrees. `contour measure` is terse and called during extraction, not
  during iteration.
- **Extraction costs more turns than a one-shot extractor.** Ten to twenty
  `measure` calls to assemble a scaffold, against one call that guesses. That
  is the price of every number carrying a re-runnable basis, and the references
  show the one-shot version would guess wrong at the torso.
- **Colour queries only work on flat-colour references.** A photograph of a real
  object falls back to the silhouette query and to `estimated`, and the
  scaffold must say so. This is the same boundary as ADR 0004's and ADR 0006's:
  stated, not hidden.
- **Perspective error is disclosed, not corrected.** The references are not
  orthographic. The anchor fixes overall scale and nothing fixes depth-dependent
  scale, so per-part measurements carry a systematic bias this ADR records and
  does not remove.
- **Trust silhouettes and centres; discount extents.** A colour mask excludes
  the toon outline, so a region's *extent* under-reads by roughly the outline
  width per edge — the head measures 383 against 390 built, the red extent 520
  against 545. Centroids and centre-to-centre distances are unaffected, because
  the erosion is symmetric, and a silhouette has no bias at all because outlines
  are foreground. Measured on `beaky` 2026-09-21; the scaffold should carry the
  distinction, not the raw number alone.
- **A min/max bounding box is unusable on a JPEG.** On `refs/side.jpg`, 0.1% of
  the pixels — compression specks — moved the silhouette by 700 mm and made
  depth read 1300 instead of 597. `bbox` therefore ignores rows and columns
  holding fewer than three pixels, which costs at most a pixel of true extent.
  The first version of this command shipped the naive form and was wrong by a
  factor of two on the second image it saw.
- **Re-measuring can stale three scaffolds silently.** Improving the segmenter
  does not update spaces that already measured. Same class of staleness as
  `contour doctor` reporting a space behind the toolkit, and visible the same
  way.
- **Detection, not prevention, again.** A scaffold edited to silence a
  divergence is caught by the basis field and rule 5, not by a hook. That is a
  deliberate continuation of ADR 0016's trade, applied to a lighter artifact.
- **Both repositories change together.** `CLAUDE.md` is copied into every space
  and `contour doctor` compares them, so this puts every existing space into
  DRIFT until refreshed.
- **`beaky-fable`'s uncommitted work is exposed today.** It carries a
  `build.py`, a `NOTES.md` and a `sheet.png` with zero commits, in a repository
  that by design can never be pushed, on a machine where open question 6's
  backup is still not set up. Sequencing it second addresses the instance; it
  does not address the question.

## Rejected

- **A persistent structured sheet that is both intent and geometry**, patched by
  the agent each turn. The original request's shape. Rejected twice over: it
  leaves nothing for `verify.py` to be an independent judge of, since the
  measurements become true by construction; and its primitive vocabulary would
  have frozen `beaky`'s shoes as boxes. `NOTES.md`: *"The shoes were never the
  wrong size; they were the wrong shape."*
- **Scaffold divergence as a red check.** The rigorous option, and the one that
  would give the references real teeth. Rejected on `beaky`'s beak: 163 measured
  against a depth ceiling of 600 ± 20 is unsatisfiable, and rule 2 forbids
  weakening either side, so the agent loops at roughly 500–1500 tokens a cycle
  until a human breaks the tie. Two contracts is one too many.
- **Silence — the scaffold as a document nobody compares.** Free per run, and
  pays it back as rework: three wrong-by-eye claims in `beaky` each cost a
  discover-and-rebuild cycle after geometry existed, and the shoes were rebuilt
  entirely.
- **Per-value provenance inside `spec.yaml`.** Recommended early in the
  discussion that produced this ADR, then withdrawn. Rejected because the spec's
  single trust class is what makes it a contract, and because the scaffold
  answers the underlying complaint better and without touching a file sixteen
  ADRs are built around.
- **The full ADR 0016 gate on the scaffold** — propose, confirm, counter.
  Rejected as incoherent: the heavier gate on the artifact this ADR explicitly
  declares advisory, taxing the re-measurement it most wants to encourage.
- **Append-only scaffold history** with structured patch objects and a version
  graph. Rejected as `git log -p scaffold.yaml` rebuilt beside git, for an audit
  trail git already provides.
- **A shared scaffold across the three `beaky` spaces.** Correct-by-construction
  and measured once. Rejected as the first cross-space dependency in a design
  ADR 0015 spent its length avoiding; deterministic measurement makes the
  duplication harmless instead.
- **An automatic part segmenter.** The obvious reading of "measure the image".
  Rejected on the references themselves: no contour separates torso from leg, so
  it would fail at the one junction with a confirmed open finding.
- **A one-shot `contour scaffold refs/`.** Fewest round trips. Rejected for the
  same reason — it must be right about the part decomposition to be useful, and
  the images say it cannot be.
- **Annotated photographs as the confirm mechanism** (rather than as the
  shareable worksheet, which is accepted). Rejected because the ambiguities that
  matter are spatial — face direction, leg depth, mirrored arm — and a 2D
  annotation cannot show them.
- **A separate preview renderer for scaffold primitives.** Would preserve the
  commit ordering exactly. Rejected as a second geometry path beside
  `lib/kit.py`; two geometry paths drift.
- **Building the shareable sheet in a design tool.** Rejected on the rule the
  original request states and this would break: the drawing and the numbers must
  come from the same code path. A typed dimension is stale the moment `LEG_X`
  moves. Permitted only as a placed image, downstream of everything.
- **Publishing a sheet to a hosted page.** Not rejected on the merits; out of
  scope. It is a decision about where model content may go, and it belongs in
  its own ADR rather than arriving as a rendering convenience.
