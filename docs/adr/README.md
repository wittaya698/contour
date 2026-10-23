# Architecture decision records

One file per structural decision, recording what was chosen, what was rejected,
and what it costs. Read these before proposing a change to how the pipeline
works — the alternative you are about to suggest is probably here with a reason.

| # | Decision |
|---|---|
| [0001](0001-headless-build-is-source-of-truth.md) | Headless build; `build.py` is the source of truth |
| [0002](0002-spec-is-agent-read-only-contract.md) | The spec is an agent-read-only contract — amended by [0016](0016-specs-from-references-and-revision.md) |
| [0003](0003-toolkit-master-variant-branches.md) | `master` is a toolkit; variants are long-lived branches — superseded in part by [0014](0014-toolkit-is-a-tool-a-model-is-a-project.md), [0015](0015-model-spaces.md) |
| [0004](0004-bmesh-over-bpy-ops.md) | `bmesh` and the data API over `bpy.ops` |
| [0005](0005-tiered-verification.md) | Tiered verification: asserts always, renders at checkpoints |
| [0006](0006-glb-only-with-round-trip.md) | `.glb` only for now, proven by round-trip |
| [0007](0007-tracked-artifacts-and-commit-gate.md) | What git tracks, and who commits — superseded in part by [0012](0012-one-directory-per-model.md), [0013](0013-releases-are-versioned-folders.md), [0015](0015-model-spaces.md) |
| [0008](0008-contour-cli-and-doc-layers.md) | One CLI wrapper, three documentation layers |
| [0009](0009-verifier-proves-its-own-teeth.md) | The verifier proves it can fail, and refuses what it cannot check — extended by [0020](0020-checks-are-pure-over-a-measurement.md) |
| [0010](0010-miniyaml-no-dependencies.md) | A small in-repo YAML reader instead of PyYAML |
| [0011](0011-model-content-stays-local.md) | Model content stays local; git carries the toolkit — superseded in part by [0014](0014-toolkit-is-a-tool-a-model-is-a-project.md), [0015](0015-model-spaces.md) |
| [0012](0012-one-directory-per-model.md) | One directory per model — superseded in part by [0015](0015-model-spaces.md) |
| [0013](0013-releases-are-versioned-folders.md) | Releases are versioned folders, prepared by the tool — superseded in part by [0015](0015-model-spaces.md) |
| [0014](0014-toolkit-is-a-tool-a-model-is-a-project.md) | The toolkit is a tool; a model is a project — superseded in part by [0015](0015-model-spaces.md) |
| [0015](0015-model-spaces.md) | Model spaces: how the tool/project split actually works |
| [0016](0016-specs-from-references-and-revision.md) | Specs drawn from references, and revised under a counter — worked example corrected by [0017](0017-scaffold-measured-from-references.md) |
| [0017](0017-scaffold-measured-from-references.md) | The scaffold: what the references measure, recorded separately |
| [0018](0018-marks-a-canvas-over-the-sheet.md) | Marks: a canvas over the sheet, and a shared way to point |
| [0019](0019-console-a-driven-agent-behind-a-gate.md) | The console: a driven agent behind a gate — amends [0010](0010-miniyaml-no-dependencies.md), [0018](0018-marks-a-canvas-over-the-sheet.md) |
| [0020](0020-checks-are-pure-over-a-measurement.md) | Checks are pure over a measurement — extends [0009](0009-verifier-proves-its-own-teeth.md) |
| [0021](0021-the-lobby.md) | The lobby: a page above the spaces |
| [0022](0022-the-agent-reads-the-references-in-spans.md) | The agent reads the references in spans — *Accepted*; amends [0017](0017-scaffold-measured-from-references.md), [0018](0018-marks-a-canvas-over-the-sheet.md) |
| [0023](0023-a-rig-and-its-clips-are-part-of-the-build.md) | A rig and its clips are part of the build — *Accepted* |
| [0024](0024-the-connector-desktop-reads-and-opens.md) | The connector: Desktop reads and opens, never drives — *Accepted*; amends [0019](0019-console-a-driven-agent-behind-a-gate.md), [0021](0021-the-lobby.md) |
| [0025](0025-pages-for-someone-who-never-opened-a-terminal.md) | Pages for someone who has never opened a terminal — *Accepted, amended*; amends [0019](0019-console-a-driven-agent-behind-a-gate.md), [0021](0021-the-lobby.md), [0024](0024-the-connector-desktop-reads-and-opens.md) |
| [0026](0026-update-brings-a-space-in-step.md) | Update: a space's copies brought in step, where nobody edited them — *Accepted, amended*; extends [0015](0015-model-spaces.md), [0021](0021-the-lobby.md) |
| [0027](0027-the-unattended-run.md) | The unattended run: a request, a channel, and a gate nobody else can answer — *Accepted, amended*; amends [0019](0019-console-a-driven-agent-behind-a-gate.md), [0024](0024-the-connector-desktop-reads-and-opens.md) |
| [0028](0028-approvals-wait-and-the-run-goes-on.md) | Approvals wait, and the run goes on — *Proposed*; amends [0027](0027-the-unattended-run.md) |
| [0029](0029-a-spec-write-carries-its-case.md) | Under a console, a spec write carries its case — *Accepted*; amends [0028](0028-approvals-wait-and-the-run-goes-on.md) |
| [0030](0030-topics-label-a-model-for-finding.md) | Topics label a model for finding, and leave only in a release — *Proposed*; adds to [0028](0028-approvals-wait-and-the-run-goes-on.md), [0013](0013-releases-are-versioned-folders.md) |
| [0031](0031-a-console-nobody-can-reach-lets-go.md) | A console nobody can reach lets go — *Proposed*; amends [0027](0027-the-unattended-run.md), [0021](0021-the-lobby.md) |
| [0032](0032-a-span-is-measured-through-the-camera.md) | A span is measured through the camera — *Proposed*; amends [0017](0017-scaffold-measured-from-references.md), [0016](0016-specs-from-references-and-revision.md) |
| [0033](0033-create-carries-a-said-anchor.md) | `create` carries what the chat said the anchor is, and the console asks it — *Accepted*; amends [0024](0024-the-connector-desktop-reads-and-opens.md), [0021](0021-the-lobby.md) |
| [0034](0034-questions-are-a-form-the-chat-can-fill.md) | The agent's questions are a form, and a chat can fill it — *Accepted*; amends [0027](0027-the-unattended-run.md), [0028](0028-approvals-wait-and-the-run-goes-on.md), [0024](0024-the-connector-desktop-reads-and-opens.md), [0033](0033-create-carries-a-said-anchor.md) |
| [0035](0035-a-run-waits-on-its-by-eye-spans.md) | A run waits on its by-eye spans — *Proposed*; amends [0022](0022-the-agent-reads-the-references-in-spans.md), adds to [0034](0034-questions-are-a-form-the-chat-can-fill.md) |
