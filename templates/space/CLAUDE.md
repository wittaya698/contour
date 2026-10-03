# <NAME> — agent operating rules

This is a **Contour model space** (ADR 0015): one model, its own git
repository, never pushed. `build.py` is the source of truth; `.blend` files
are disposable output, rebuilt from an empty scene.

The toolkit lives elsewhere and is invoked as `contour`. These rules are a
copy of the toolkit's, taken at the commit recorded in `.contour/project`.
Run `contour doctor` to find out whether that copy has gone stale.

## Commands — always these, never raw `blender`

| Command | Does | Cost |
|---|---|---|
| `contour check` | build + verify, terse report; redraws the sheet for the page | ~60 tok |
| `contour api <symbol>` | real signature from the installed Blender | ~15 tok |
| `contour render` | 4-view sheet → `sheet.png` | ~1400 tok |
| `contour export` | `.glb` + round-trip re-measure | ~80 tok |
| `contour canvas` | the sheet in a browser, to mark on; waits for you | ~20 tok |
| `contour measure` | pixel geometry off a reference; draws and reads spans | ~60 tok |
| `contour worksheet` | every span drawn onto its reference → `worksheet.png` | ~1400 tok |
| `contour doctor` | is this space still in step with the toolkit | ~20 tok |

Run them from inside this directory; they take no model name. Full Blender
output goes to `.contour/last-build.log`. Read it **only on failure**.

## Hard rules

1. **Never change anything under `refs/`** — the user's intent in pictures.
   Measure them; never rewrite one. **`spec.yaml` changes only as: propose →
   user confirms → write, bumping `revision:` in that same write.** The proposal
   is the argument — the measurement that shows the contract is wrong — and it
   comes before the write wherever the confirm lands: prose in a terminal, a
   gate under a console. A gate is a confirm and never a proposal; it can stop a
   write, it cannot make the case for one. A measurement read off a reference
   is a **span** — the user's, or an agent span — and the proposal names it. A
   number from a reference with no span behind it is not an argument, and a
   by-eye agent span argues nothing until the user has answered it. Never
   propose one while a check is red; fix `build.py` or report the failure.
   `contour check` fails if the spec moved and `revision:` did not (ADR 0016).
   A *new* spec may be drafted when the user asks — scale needs an anchor they
   give you, every number you chose flagged as yours, tolerances loudest, since
   a loose one at birth moves the goalposts just as surely.
2. **Never weaken a check to make it pass.** A red check is a finding. Report it.
3. **Never hand-edit a generated `.blend`.** All change goes through
   `build.py`. `out/` is regenerated from zero every build.
4. **Never use `bpy.ops.*`** unless the call is in the toolkit's
   `lib/ops_whitelist.py`, and then only via `lib.ctx_override`. Build geometry
   with `bmesh` + the data API.
5. **Never commit without explicit approval.** The user has to have seen what
   is being committed — the verify report, and the sheet the build was drawn
   from — and said ship. Rendering to show them is the terminal's way of meeting
   that; under a console the panel is already current, so what is left is the
   saying, and an allowed gate on the commit is the user saying it.
6. **Never run raw `blender`** — its stdout costs 2–5k tokens per run.
7. **Verify unfamiliar API calls with `contour api`** instead of recalling
   them. This Blender postdates the model cutoff, so recalled signatures are
   guesses.
8. **This repository is never pushed.** Not to any remote, ever (ADR 0011,
   ADR 0015). A `pre-push` hook refuses; never bypass it with `--no-verify`.
   To share the model, `contour export` and hand over the `.glb`.

## What is here

```
spec.yaml       the user's intent, in numbers     (read, never write)
refs/           the user's intent, in pictures    (read, never write)
build.py        yours
sheet.png       the 4-view render the user approved
marks.json      located comments on that sheet, from both sides (ADR 0018)
NOTES.md        deferred refinements, and open questions
release/v<N>/   archived .blend + .glb + sheet, at a tag
.contour/       the marker, provenance, and logs
out/ exports/   generated, git-ignored
```

## Where to look

- Workflow: `.claude/skills/` — `build-model`, `release-model`
- Everything about the toolkit — ADRs, the spec schema, `lib/kit.py` helpers —
  lives in the toolkit checkout. `contour doctor` prints its path.
