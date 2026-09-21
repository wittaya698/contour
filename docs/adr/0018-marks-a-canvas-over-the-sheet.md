# 0018 — Marks: a canvas over the sheet, and a shared way to point

**Status:** Proposed · 2026-09-21 · **extends [ADR 0005](0005-tiered-verification.md) (the sheet gains a second job) and [ADR 0017](0017-scaffold-measured-from-references.md) (a mark aims `contour measure`)**

## Context

Every other ADR here is about the agent reading the user's intent. This one is
about the return path, which has never been designed at all.

**There is no shared name for a thing on the picture.** `contour render` makes a
sheet; the user looks at it and answers in prose, and the agent answers in
prose. Both sides spend their words re-describing *which* thing before they can
say anything about it. The user's own statement of the problem: *"most users
prefer focussing on image and comment rather than reading full text."*

**`beaky-solo`, built this same day, is the worked example.** One perspective
reference, anchored at 1700 mm. Diameters came out right — torso 520 against
530, neck 269 against 280, leg 73 against 70. Leg spacing came out 126 against
168, 25% low, because a separation is a vector and projects by the cosine of the
yaw while a diameter does not. That error is **invisible inside the image**: the
reference's own inner gap sits in the same ratio to the same leg width, so
nothing in the picture contradicts it. Its `NOTES.md` open question 3 — *what
separates the legs* — is still open, and it is open for a mechanical reason.
**There was no way for the user to point at the reference and say: that
distance, right there.** Prose cannot carry a location.

**The agent's findings decay into text nobody reads.** `beaky-solo`'s
`NOTES.md` records that the beak's length is foreshortened and was never
measured. It is true, it matters, and it is a sentence in the middle of a file.
As a pin on the beak it would be unmissable and answerable in three words.

## Decision

**A *mark* is a located comment.** It carries a position, one short line of
text, an author, and a status. It is the unit both sides use to point.

**Marks are structured data, not a drawing.** A scribbled PNG would have to be
read back by vision, making the user's arrow the agent's *guess* at exactly the
moment precision matters, and leaving nothing checkable. The marked-up image is
a by-product of the records, never the record.

**`contour canvas` serves the page on localhost, and terminates.** Python's
stdlib `http.server`, the sheet and the references, one HTML page, marks POSTed
straight to disk. It is the first Contour command that waits rather than shoots,
so its lifetime is bounded: it serves until the page says done, then resolves,
prints a terse report, and exits. Model content stays on the machine by default;
publishing a canvas is a deliberate act like `contour export`, never a side
effect.

**The canvas lives in the toolkit. Marks live in the space.** The instrument is
shared and pushable; what it captures is model content that is never pushed.
This is the cut ADR 0015 already draws, applied unchanged.

**A click resolves to a part through an ID mask.** `contour render` emits, per
view, a second Workbench pass with `shading.color_type = 'OBJECT'` and each
object's `color` set to a unique index, so a pixel *is* a part number, occlusion
included. Nearest-centroid was rejected: it snaps a click on the beak to the
head whenever the head's centroid is nearer in screen space, and it silently
converts a click on empty background — *this gap is too wide* — into a comment
on an arbitrary neighbour. The mask also serves hover, which must be instant and
local and can never afford a Blender call.

**A sheet mark is anchored in the part's local space, not in pixels.** The sheet
is regenerated every build, so a pixel pin starts lying the moment geometry
moves, and looks authoritative while doing it. A mark is born unresolved, and
once per canvas session — not per click, not per build — one Blender run casts a
ray per unresolved mark from the sheet's camera through its pixel and writes
back the surface point in the hit part's own coordinates. `Scene.ray_cast`
returns location, normal, index and object, so no position buffer is rendered
and nothing is stored beyond ~200 bytes of camera parameters per sheet. Move a
part and its pins move with it; delete one and its pins are explicitly orphaned
rather than quietly misplaced.

**Two kinds of mark, and they mean different things.** A **sheet mark** carries
a part and says *the build is wrong*. A **ref mark** carries pixel coordinates
and the user's words alone — nothing in a photograph knows what a part is — and
says *here is what I meant*. A ref mark can never be closed by a build; it is
answered by a measurement or a spec revision. References themselves are never
touched: marks about them live in the space's notes, and rule 1 is unchanged.

**Both parties write marks.** The agent pins what it already computes — check
deltas, `contour measure` readings, the parts it is unsure of — so a finding
arrives as a badge on the picture instead of a paragraph. The discipline that
makes this survivable: **a mark is a question or a measurement, never
narration.** An agent mark is still only a proposal; rule 1's propose → confirm
→ write, with `revision:` bumped, is untouched by it.

**Only the user closes a mark.** The agent may attach *addressed in build N*,
which dims the badge, but the finding stands until the user says otherwise. This
is rule 5's gate and rule 2's principle: a finding is not disposed of by the
party it is aimed at. Auto-closing on a green check was rejected outright — a
mark exists precisely because the spec did not catch the thing, so green would
erase the findings that matter most.

**`contour check` prints one line when marks are open, and nothing at zero.**
`3 marks open`. It is **not** a failure. Red means the build violates the spec;
blurring that would wreck the vocabulary `docs/CONTEXT.md` defines. Without the
line the file rots unseen, and a stale marks file is worse than none.

**`marks.json` is tracked.** ADR 0016's lesson was that `beaky`'s one known
defect lived permanently in `NOTES.md`, the one file nothing verifies. Ignored
marks inherit that weakness and add another: they vanish on a clean checkout,
taking the reasoning with them. Tracked, they are small text that diffs well,
and `git log` finally records *why* two builds differ. The spec guard does not
cover them — the agent must be able to write them, and they are a conversation,
not a contract.

## Consequences

- **The sheet gains a second job.** ADR 0005 made it the agent's only eyes. It
  is now also the shared surface both parties point at, which raises the value
  of a render and argues for the dimension layer already deferred.
- **A ref mark is the natural way to aim `contour measure`.** Two pins give a
  span the user chose, replacing a guessed scanline. `beaky-solo`'s open
  question 3 is answerable the day this lands.
- **First browser surface in a pure Python + Blender toolkit.** Accepted
  deliberately. The page is one file with no build step and no dependency; if it
  ever needs a bundler, that is the signal the scope went wrong.
- **Token cost is zero on the hot path.** Marks are a file, not output. The only
  conversation cost is one line on `check` when marks are open.
- **Render cost rises by four Workbench passes**, inside the existing process,
  with no lights and no materials. The mask lands in git-ignored `out/` and is
  regenerated every build.
- **Resolution has a window.** The ray must hit the geometry the sheet was
  rendered from. Resolving at session close keeps it shut; marking a sheet,
  rebuilding, then resolving would land rays in a changed scene, and the canvas
  must refuse rather than guess.
- **Closed marks need pruning, open ones do not.** The canvas drops resolved
  marks older than the last release tag; git holds the archive.
- **`beaky-solo` and `beaky` gain no marks retroactively.** Nothing migrates;
  the anchor for an old comment no longer exists.

## Rejected

- **Build nothing; keep answering in prose.** Free, and it is the status quo the
  user named as the problem — findings that are true, located, and unread.
- **A scribble canvas saving a marked-up PNG.** The cheapest thing to build. The
  mark's meaning becomes a vision guess, nothing can check that the agent acted
  on it, and the pin cannot survive a rebuild.
- **An existing annotation product through its API.** Avoids writing a page, and
  buys nothing that matters: no part identity, no local-space anchoring, no
  resolution against a build — every one of which would still have to be built
  on top. It adds an account, a network round-trip, and an upload of model
  content, which the default must not do.
- **A published Artifact instead of localhost.** Nicer page, no local process.
  Rejected as a *default* only: it ships every sheet off-machine as a side
  effect. Rule 8 is a git boundary, so this stays available later as an explicit
  flag when the user actually wants to show someone.
- **A static page over `file://`.** Zero server, and it cannot write to disk, so
  every round trip becomes download-then-move-it-yourself.
- **A long-lived canvas daemon.** Rejected against the shape of every other
  command: a shot that prints and exits. A daemon is a thing to remember to kill
  and a thing to serve a stale sheet.
- **Position buffers rendered per view.** The first design for anchoring: ~12 MB
  per sheet and new render work. Rejected once `contour api` showed
  `Scene.ray_cast` returns the object and location together, making lazy
  resolution strictly cheaper and exact.
- **Pixel-only pins now, anchoring later.** Rejected on migration: every mark
  made before the change is unanchorable, because the geometry it referred to is
  gone.
- **Part-level marks with no position.** Considered first and rejected once the
  user confirmed the need. It collapses *the left of the beak* back to *the
  beak*, which returns the conversation to prose.
- **Auto-closing marks on a green check**, and **the agent closing its own** —
  both rejected above, for rule 2's reason.
