---
name: release-model
description: Export, verify and tag a finished Contour model as a deliverable. Use when a model is done and needs to leave the repo for an engine, or when the user asks to release, tag or archive a model.
---

# Release a model

## 1. Check you are on the current toolkit

A space built against an old toolkit is being judged by old checks.

```sh
contour doctor      # toolkit commit, and whether the rules here have drifted
contour check
```

`doctor` reporting a newer toolkit is not itself a problem — record which
commit the release was verified against (step 4). Drift in `CLAUDE.md` or the
skills is a problem: those are copies, and a stale copy is a rule you are no
longer following (ADR 0015).

## 2. Export and prove it

```sh
contour export
```

This writes `exports/<NAME>.glb`, re-imports it into a clean headless
Blender, and re-measures dimensions, up axis, handedness and origin there. The
in-Blender scene passing verify proves nothing about the exported file — only
the round-trip does (ADR 0006).

A round-trip failure is an export bug, not a modeling bug. Do not "fix" the
model to compensate.

## 3. Final look

```sh
contour render
```

Show the user the sheet and the full verify report. Releasing is their decision:
ask *Release this as version <N>?*, in the words of *Speaking to the user* in
`CLAUDE.md`. The folder, the commit and the tag are how it is done, not what you
ask about. A release commits, so their yes is also the answer to *Save this
version?* — ask once, not twice.

## 4. Assemble the release package

On approval only. A release is a folder, and it accumulates — v1 is never
overwritten by v2 (ADR 0013). N is one past the highest `v<N>` tag *and*
folder; if those two disagree, stop and say so rather than picking one. Only a
tag named exactly `v<N>` is a release — any other tag in the space is the
user's own, and neither counts nor is touched.

```sh
contour release-glb v<N>     # the export, carrying this model's topics
cp out/<NAME>.blend      release/v<N>/
cp sheet.png             release/v<N>/
git add release/v<N> sheet.png
git commit -m "<NAME>: release v<N>

verify 8/8 | tris 4,210 | glb round-trip ok | toolkit <commit>"
git tag -a v<N> -m "<NAME> v<N>"
```

The release's `.glb` is not a plain copy of the export: `release-glb` writes
the model's topics into it, as they stand now, and a working export carries
none (ADR 0030, decision 9). It refuses a `v<N>` already released, so a topic
approved later never reaches a shipped file.

`release/` is tracked although `out/` and `exports/` beside it are not: the
package is the one deliberate copy of a derivable file (ADR 0013). Record the
toolkit commit the release was verified against in the commit message — the one
`doctor` printed in step 1, or the newer of the two if it printed both.

ADR 0013 specifies `contour release` to do all of this and refuse
when tags and folders disagree. It is **not built yet**; until it is, the steps
above are manual and the disagreement check is yours to make.

## 5. Tell the user what to do with it

In plain words: what each file is for, not how it was made.

- `release/v<N>/<NAME>.glb` is the engine file.
- The `.blend` beside it is the archived source asset; their `work/scene.blend`
  links its collection and is unaffected.
- State the conventions the export used (Y-up, metres for `web`) so the import
  side can be set up correctly.
