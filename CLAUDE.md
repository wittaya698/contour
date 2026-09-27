# Contour — agent operating rules

Contour generates Blender game assets from code. `build.py` is the source of
truth; `.blend` files are disposable output, rebuilt from an empty scene.

## Commands — always these, never raw `blender`

| Command | Does | Cost |
|---|---|---|
| `contour check` | build + verify, terse report; redraws the sheet for the page | ~60 tok |
| `contour api <symbol>` | real signature from the installed Blender | ~15 tok |
| `contour render` | 4-view sheet → `sheet.png` | ~1400 tok |
| `contour export` | `.glb` + round-trip re-measure | ~80 tok |
| `contour canvas` | the sheet in a browser, to mark on; waits for you | ~20 tok |
| `contour run <cmd>...` | hold this space for one run, then release it | ~0 tok |
| `contour selftest` | fixture pipeline test | ~60 tok |
| `contour spaces` | list model spaces; warns if one has a remote | ~20 tok |

Full Blender output goes to `.contour/last-build.log`. Read it **only on failure**.

## Hard rules

1. **Never change anything under `refs/`** — the user's intent in pictures.
   Measure them; never rewrite one. **A `spec.yaml` changes only as: propose →
   user confirms → write, bumping `revision:` in that same write.** The proposal
   is the argument — the measurement that shows the contract is wrong, *depth
   measures 620 against a tolerance of 600 ±20* — and it comes before the write
   wherever the confirm lands: prose in a terminal, a gate under a console. A
   gate is a confirm and never a proposal; it can stop a write, it cannot make
   the case for one. Never propose one while a check is red; fix `build.py` or
   report the failure.
   `contour check` fails if the spec moved and `revision:` did not (ADR 0016).
   A *new* spec may be drafted when the user asks — scale needs an anchor they
   give you, every number you chose flagged as yours, tolerances loudest, since
   a loose one at birth moves the goalposts just as surely.
2. **Never weaken a check to make it pass.** A red check is a finding. Report it.
3. **Never hand-edit a generated `.blend`.** All change goes through
   `build.py`. `out/` is regenerated from zero every build.
4. **Never use `bpy.ops.*`** unless the call is in `lib/ops_whitelist.py`, and
   then only via `lib.ctx_override`. Build geometry with `bmesh` + the data API.
5. **Never commit or push without explicit approval.** The user has to have
   seen what is being shipped — the verify report, and the sheet the build was
   drawn from — and said ship. Then commit, and push only in that same approved
   motion, never on your own initiative. Rendering to show them is the
   terminal's way of meeting that; under a console the panel is already current,
   so what is left is the saying, and an allowed gate on the commit is the user
   saying it.
6. **Never run raw `blender`** — its stdout costs 2–5k tokens per run.
7. **Verify unfamiliar API calls with `./contour api`** instead of recalling
   them. This Blender (5.2.1, built 2026-08-25) postdates the model cutoff, so
   recalled signatures are guesses.
8. **Model content never leaves via git.** A model space is never pushed at
   all, and the toolkit repo carries no model content to push (ADR 0011,
   ADR 0015). To share a model, run `contour export` inside its space and hand
   over the `.glb`. A `pre-push` hook enforces this; never bypass it with `--no-verify`,
   and never propose an exception to it.

## Repo shape

This repository is the **toolkit** and builds no model of its own. A model
lives in its own directory and its own git repository — a *model space* —
found by walking up from the working directory for `.contour/project`
(ADR 0015). Run the model commands from inside one; they take no model name.

The toolkit is shared and pushable. A model space is neither.

Spaces on this machine live under `project/` — a directory this repo ignores
and the push guard blocks, because each one is a separate git repository and
none of it may ever reach a remote. Treat `project/` as somebody else's repo:
never `git add` it, and never `git clean -xdff` in the toolkit, which deletes
it and the reference images with it.

## Where to look

- Workflow: `.claude/skills/new-space` here. `build-model` and `release-model`
  live in `templates/space/.claude/skills/`; `contour init` copies them into
  each model space (ADR 0015)
- bpy patterns: `templates/space/.claude/skills/build-model/references/bpy-recipes.md`
- Decisions + rationale: `docs/adr/`
- Vocabulary and pipeline stages: `docs/CONTEXT.md`
- Undecided, and what it blocks: `docs/OPEN-QUESTIONS.md`
- Planned work, sliced and grabbable: `docs/issues/`
- Push guard: `tools/hooks/pre-push`, installed by `contour install-hooks`
- Spec guard: `tools/guards/spec.py`, which a space runs as `contour hook spec`
  and never copies (ADR 0015)
