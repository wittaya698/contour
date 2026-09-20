# Contour — agent operating rules

Contour generates Blender game assets from code. `build.py` is the source of
truth; `.blend` files are disposable output, rebuilt from an empty scene.

## Commands — always these, never raw `blender`

| Command | Does | Cost |
|---|---|---|
| `./contour check <variant>` | build + verify, terse report | ~60 tok |
| `./contour api <symbol>` | real signature from the installed Blender | ~15 tok |
| `./contour render <variant>` | 4-view sheet → `models/<variant>/sheet.png` | ~1400 tok |
| `./contour export <variant>` | `.glb` + round-trip re-measure | ~80 tok |
| `./contour selftest` | fixture pipeline test | ~60 tok |

Full Blender output goes to `.contour/last-build.log`. Read it **only on failure**.

## Hard rules

1. **Never change a `models/*/spec.yaml`, or anything under `models/*/refs/`,
   that exists.** It is the user's intent, not
   yours. Propose changes in chat; never write them. A *new* spec may be drafted
   when the user asks, with every number you chose flagged as yours — tolerances
   loudest, since a loose one at birth moves the goalposts just as surely.
   A `PreToolUse` hook enforces the tracked case; it is a backstop, not
   permission to try.
2. **Never weaken a check to make it pass.** A red check is a finding. Report it.
3. **Never hand-edit a generated `.blend`.** All change goes through
   `build.py`. `models/<v>/out/` is regenerated from zero every build.
4. **Never use `bpy.ops.*`** unless the call is in `lib/ops_whitelist.py`, and
   then only via `lib.ctx_override`. Build geometry with `bmesh` + the data API.
5. **Never commit or push without explicit approval.** Show the verify report
   and the render sheet, wait for the user to say ship, then commit — and push
   only in that same approved motion, never on your own initiative.
6. **Never run raw `blender`** — its stdout costs 2–5k tokens per run.
7. **Verify unfamiliar API calls with `./contour api`** instead of recalling
   them. This Blender (5.2.1, built 2026-08-25) postdates the model cutoff, so
   recalled signatures are guesses.
8. **Model content never leaves via git.** `models/` stays on this machine;
   only `master` — the toolkit — is ever pushed (ADR 0011). To share a model, `./contour export <variant>` and hand over the
   `.glb`. A `pre-push` hook enforces this; never bypass it with `--no-verify`,
   and never propose an exception to it.

## Repo shape

`master` is the toolkit and builds no model of its own. Each variant is a
long-lived branch adding **only** `models/<v>/` (ADR 0012).
Never modify shared files from a variant branch — fix on `master`, then
`git merge master` into the variant.

## Where to look

- Workflow: `.claude/skills/` — `build-model`, `new-variant`, `release-model`
- bpy patterns: `.claude/skills/build-model/references/bpy-recipes.md`
- Decisions + rationale: `docs/adr/`
- Vocabulary and pipeline stages: `docs/CONTEXT.md`
- Undecided, and what it blocks: `docs/OPEN-QUESTIONS.md`
- Push guard: `tools/hooks/pre-push`, installed by `./contour install-hooks`
- Spec guard: `tools/hooks/guard-spec.py`, wired by `.claude/settings.json`
