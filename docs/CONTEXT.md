# Contour — domain context

Shared vocabulary for this repo. When a word here appears in a spec, a commit
message, or a conversation, it means what this file says it means.

## Vocabulary

| Term | Means |
|---|---|
| **model space** | One model's own directory and its own git repository, found by walking up from the working directory for `.contour/project`. Never pushed (ADR 0011, ADR 0015). Spaces coexist; a variation of a model is a new space. |
| **variant** | The old word for a model space, from when each model lived on a long-lived branch of this repo (ADR 0003, retired by ADR 0015). It survives in older ADRs and in some code identifiers. |
| **spec** | `spec.yaml` at the root of a model space. The user's intent, expressed in numbers. Agent-read-only. The definition of correct. |
| **reference** | An image the user supplies, stored in `refs/` at original fidelity: their intent in pictures, in the spec's trust class (ADR 0012). Say *reference*, not "model picture" — and never *sheet*, which is Contour's own render. |
| **anchor** | The one real-world dimension the user states for a set of references, in millimetres. Every other size read off those images is a pixel ratio against it. Pictures carry proportion, never scale, so without an anchor the agent does not draft `dimensions` — it asks. |
| **mark** | A located comment: a position, one line of text, an author, and a status. The unit both sides use to point at a thing on the picture (ADR 0018). A **sheet mark** says *the build is wrong*; a **ref mark** says *here is what I meant*. |
| **pin** | Where a sheet mark actually is, once a ray has resolved it: a point in the hit part's own coordinates. Pixels lie the moment geometry moves; a pin moves with its part, and is *orphaned* — said so, in the file — if that part is deleted. |
| **badge** | A pin drawn on the sheet: the mark's id, painted over background pixels only and leashed to its pin, so the model is never covered by a remark about it. |
| **anchored** | Of a mark: resolved from a pixel to a pin (ADR 0018). Unrelated to **anchor** above, which is a millimetre figure about references. The sheet is anchored in parts, the references are anchored in millimetres, and nothing is both. |
| **span** | A ref mark with two ends instead of one: *this distance, right here*. It is what aims `contour measure` at a separation, which a scanline can only guess at because it finds runs and cannot know which two the question was about. The answer comes back as an agent mark pinned between the two pins, in millimetres against the space's stated height, and states its own error bar (ADR 0018). |
| **addressed** | What the agent may attach to a mark: *I believe this build deals with it*, stamped with that build's id. It dims the badge and is **not** a close — only the user closes a finding, because a finding is not disposed of by the party it is aimed at (ADR 0018). |
| **console** | The browser surface above the launcher, from which a run is driven and gated (ADR 0019). Long-lived, and still ends when the page says done. The one part of Contour that is not stdlib-only — `contour` itself stays a stdlib launcher, and that boundary is the decision, not an accident. |
| **run** | One agent session the console drives, from the first prompt to the agent stopping. Not a **build**, which is one execution of `build.py`; a run contains many. |
| **gate** | A point where a tool call stops and waits for the user (ADR 0019). Not a **checkpoint**: a checkpoint is the agent saying *I think I am done*, and a gate is the console saying *not until you say so*. One is the agent's judgement, the other is the user's authority. |
| **ask** | The third verdict beside allow and deny. What `tools/guards/spec.py` could not say, and the reason ADR 0016 traded prevention for detection *knowingly*. With it, a spec write pauses instead of being refused or merely noticed afterwards. |
| **ask-list** | The policy naming which tool calls are gated, per tool and per path. Lives in `~/.contour`, never in a space, and never written by the agent — which may propose a wider one and nothing more. An ask-list is a check, so rule 2 covers it. |
| **category** | What a call *means*, in Contour's vocabulary: a spec write, a ref write, a build, a commit, a push. The unit an **ask-list** is written in, and what the launcher answers when the console asks about a call rather than pattern-matching its text — one intent has several spellings, and a permission list needing one rule per spelling will still have a hole (ADR 0019). `contour intents` prints the set, because a list that cannot be printed cannot be audited. |
| **veto** | A denied call and the reason for it, authored by the user at a gate and tracked in the space (ADR 0019). Not a **mark**, which has a position and is *the build is wrong* or *here is what I meant*; a veto is *not this* — authority exercised against one call at one moment. Only the user can veto, as only the user closes. A veto about a part may be **promoted** to a sheet mark, which is what gives it a position. |
| **build** | Running the space's `build.py` under headless Blender to produce `out/<name>.blend` from an empty scene. |
| **verify** | Running `verify.py` against a build, judged by its spec. Produces a pass/fail line per check. |
| **green** | A verify report in which every check passed — `PASS`, and `contour` exits 0. The word the code itself uses (ADR 0005 budgets ~50 tokens on green). |
| **red** | A report in which any check failed — `FAIL n/total`, one line per failure, exit 1. A build that dies before verify runs is red too. Rule 2: red is a finding, never something to be made to go away by changing what was asked. |
| **checkpoint** | A moment the agent believes it is done or is stuck, and says so. In a terminal it triggers a render sheet and a request for approval; under a **console** the sheet is already current and a checkpoint is the agent's judgement alone (ADR 0019). Never the same as **green**: green is the spec satisfied, a checkpoint is the agent claiming to be finished — or admitting it is not getting there. |
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
