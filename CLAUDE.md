# Contour — agent operating rules

Contour generates Blender game assets from code. `build.py` is the source of
truth; `.blend` files are disposable output, rebuilt from an empty scene.

## Commands — always these, never raw `blender`

| Command | Does | Cost |
|---|---|---|
| `./contour check <variant>` | build + verify, terse report | ~60 tok |
| `./contour api <symbol>` | real signature from the installed Blender | ~15 tok |
| `./contour render <variant>` | 4-view sheet → `renders/<variant>.png` | ~1400 tok |
| `./contour export <variant>` | `.glb` + round-trip re-measure | ~80 tok |
| `./contour selftest` | fixture pipeline test | ~60 tok |

Full Blender output goes to `out/last-build.log`. Read it **only on failure**.

## Hard rules

1. **Never edit `spec/*.yaml`.** It is the user's intent, not yours. Propose
   changes in chat; never write them.
2. **Never weaken a check to make it pass.** A red check is a finding. Report it.
3. **Never hand-edit `out/*.blend` or `work/*.blend`.** All change goes through
   `build.py`. `out/` is regenerated from zero every build.
4. **Never use `bpy.ops.*`** unless the call is in `lib/ops_whitelist.py`, and
   then only via `lib.ctx_override`. Build geometry with `bmesh` + the data API.
5. **Never commit without explicit approval.** Show the verify report and the
   render sheet, wait for the user to say ship, then commit.
6. **Never run raw `blender`** — its stdout costs 2–5k tokens per run.
7. **Verify unfamiliar API calls with `./contour api`** instead of recalling
   them. This Blender (5.2.1, built 2026-08-25) postdates the model cutoff, so
   recalled signatures are guesses.

## Repo shape

`master` is the toolkit and builds no model of its own. Each variant is a
long-lived branch adding **only** `spec/<v>.yaml` and `models/<v>/build.py`.
Never modify shared files from a variant branch — fix on `master`, then
`git merge master` into the variant.

## Where to look

- Workflow: `.claude/skills/` — `build-model`, `new-variant`, `release-model`
- bpy patterns: `.claude/skills/build-model/references/bpy-recipes.md`
- Decisions + rationale: `docs/adr/`
- Vocabulary and pipeline stages: `docs/CONTEXT.md`
- Undecided, and what it blocks: `docs/OPEN-QUESTIONS.md`
