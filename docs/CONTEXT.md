# Contour — domain context

Shared vocabulary for this repo. When a word here appears in a spec, a commit
message, or a conversation, it means what this file says it means.

## Vocabulary

| Term | Means |
|---|---|
| **model space** | One model's own directory and its own git repository, found by walking up from the working directory for `.contour/project`. Never pushed (ADR 0011, ADR 0015). Spaces coexist; a variation of a model is a new space. |
| **variant** | The old word for a model space, from when each model lived on a long-lived branch of this repo (ADR 0003, retired by ADR 0015). It survives in older ADRs and in some code identifiers. |
| **spec** | `spec.yaml` at the root of a model space. The user's intent, expressed in numbers. Agent-read-only. The definition of correct. |
| **build** | Running the space's `build.py` under headless Blender to produce `out/<name>.blend` from an empty scene. |
| **verify** | Running `verify.py` against a build, judged by its spec. Produces a pass/fail line per check. |
| **checkpoint** | A moment the agent believes it is done or is stuck. Triggers a render sheet and a request for approval. |
| **sheet** | The 4-view orthographic Workbench render (front / right / top / persp) at 1024², with a 1 m grid and scale bar. The agent's only eyes. |
| **round-trip** | Re-importing an exported file into a clean Blender and re-measuring it there. The only proof an export is correct. |
| **toolkit** | This repository: `lib/`, `verify.py`, `schema/`, `templates/`, `.claude/`, `fixtures/`, `tools/`. Shared and pushable, and builds no model of its own. Every space uses it through the `contour` launcher. |
| **fixture** | `fixtures/smoke/` — a trivial shape existing only to exercise the pipeline. Never a deliverable. |
| **generated file** | `out/<name>.blend` in a model space. Read-only output. Regenerated from zero on every build. |
| **working file** | `work/scene.blend`. Yours. Links the generated collection. Git-ignored. Never read by the pipeline. |

## Pipeline stages

```
spec ──┐
       ├──> build ──> out/<name>.blend ──> verify ──> report (~10 lines)
       │                    │
       │                    ├──> render ──> sheet.png          (checkpoints only)
       │                    │
       └──────────────────> └──> export ──> exports/<name>.glb ──> round-trip ──> re-measure

                       every path is relative to the model space (ADR 0015)
```

Every stage is reachable through `contour` and nothing else. The wrapper
exists to keep Blender's stdout out of the conversation; the full log always
lands in `.contour/last-build.log` for when a stage fails.

## The three priorities, and what each one bought

Stated priorities, in order: **correctness**, **token usage**, **version control**.

- **Correctness** bought: the spec being agent-read-only (so the goalposts
  cannot move), `bmesh` over `bpy.ops` (so headless context cannot silently
  corrupt a build), orthographic multi-view renders with a scale reference (so
  misalignment and wrong scale are visible), and export round-tripping.
- **Token usage** bought: the `contour` wrapper's terse reports, renders
  rate-limited to checkpoints, three-layer docs so `CLAUDE.md` stays ~40 lines,
  and `contour api` so the agent looks up signatures instead of guess-failing.
- **Version control** bought: deterministic rebuilds (a commit fully describes a
  model), source-plus-thumbnail tracking, a repository per model that is never
  pushed, and a human approval gate so every commit is a state you chose.

## Known constraints

- Blender is **5.2.1 LTS, built 2026-08-25** — after the assistant's knowledge
  cutoff. Recalled `bpy` API details are unreliable; `contour api` is
  authoritative.
- Blender is Z-up, right-handed, 1 unit = 1 m. Every engine target differs; the
  export step converts and the round-trip proves it.
- The `.blend` format is opaque to git. It is treated as a build artifact, not
  as source.
