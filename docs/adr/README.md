# Architecture decision records

One file per structural decision, recording what was chosen, what was rejected,
and what it costs. Read these before proposing a change to how the pipeline
works — the alternative you are about to suggest is probably here with a reason.

| # | Decision |
|---|---|
| [0001](0001-headless-build-is-source-of-truth.md) | Headless build; `build.py` is the source of truth |
| [0002](0002-spec-is-agent-read-only-contract.md) | The spec is an agent-read-only contract |
| [0003](0003-toolkit-master-variant-branches.md) | `master` is a toolkit; variants are long-lived branches |
| [0004](0004-bmesh-over-bpy-ops.md) | `bmesh` and the data API over `bpy.ops` |
| [0005](0005-tiered-verification.md) | Tiered verification: asserts always, renders at checkpoints |
| [0006](0006-glb-only-with-round-trip.md) | `.glb` only for now, proven by round-trip |
| [0007](0007-tracked-artifacts-and-commit-gate.md) | What git tracks, and who commits |
| [0008](0008-contour-cli-and-doc-layers.md) | One CLI wrapper, three documentation layers |
| [0009](0009-verifier-proves-its-own-teeth.md) | The verifier proves it can fail, and refuses what it cannot check |
| [0010](0010-miniyaml-no-dependencies.md) | A small in-repo YAML reader instead of PyYAML |
| [0011](0011-model-content-stays-local.md) | Model content stays local; git carries the toolkit |
| [0012](0012-one-directory-per-model.md) | One directory per model |
| [0013](0013-releases-are-versioned-folders.md) | Releases are versioned folders, prepared by the tool |
| [0014](0014-toolkit-is-a-tool-a-model-is-a-project.md) | The toolkit is a tool; a model is a project |
| [0015](0015-model-spaces.md) | Model spaces: how the tool/project split actually works |
