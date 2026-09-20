---
name: release-model
description: Export, verify and tag a finished Contour variant as a deliverable. Use when a model is done and needs to leave the repo for an engine, or when the user asks to release, tag or archive a model.
---

# Release a variant

## 1. Take the current toolkit

A variant that has not merged `master` recently is being judged by old checks.

```sh
git checkout <variant>
git merge master
./contour check <variant>
```

If the merge conflicts, the no-shared-files rule was broken somewhere — resolve
by moving the shared change to `master`, not by editing it here (ADR 0003).

## 2. Export and prove it

```sh
./contour export <variant>
```

This writes `models/<variant>/exports/<variant>.glb`, re-imports it into a clean headless
Blender, and re-measures dimensions, up axis, handedness and origin there. The
in-Blender scene passing verify proves nothing about the exported file — only
the round-trip does (ADR 0006).

A round-trip failure is an export bug, not a modeling bug. Do not "fix" the
model to compensate.

## 3. Final look

```sh
./contour render <variant>
```

Show the user the sheet and the full verify report. Releasing is their decision.

## 4. Assemble the release package

On approval only. A release is a folder, and it accumulates — v1 is never
overwritten by v2 (ADR 0013). N is one past the highest existing tag *and*
folder; if those two disagree, stop and say so rather than picking one.

```sh
mkdir -p models/<variant>/release/v<N>
cp models/<variant>/out/<variant>.blend      models/<variant>/release/v<N>/
cp models/<variant>/exports/<variant>.glb    models/<variant>/release/v<N>/
cp models/<variant>/sheet.png                models/<variant>/release/v<N>/
git add models/<variant>/release/v<N> models/<variant>/sheet.png
git commit -m "<variant>: release v<N>

verify 8/8 | tris 4,210 | glb round-trip ok"
git tag -a <variant>-v<N> -m "<variant> v<N>"
```

`release/` is tracked although `out/` and `exports/` beside it are not: the
package is the one deliberate copy of a derivable file (ADR 0013). Record the
toolkit commit the release was verified against — `git rev-parse --short
master` — in the commit message.

ADR 0013 specifies `./contour release <variant>` to do all of this and refuse
when tags and folders disagree. It is **not built yet**; until it is, the steps
above are manual and the disagreement check is yours to make.

## 5. Tell the user what to do with it

- `models/<variant>/release/v<N>/<variant>.glb` is the engine file.
- The `.blend` beside it is the archived source asset; their `work/scene.blend`
  links its collection and is unaffected.
- State the conventions the export used (Y-up, metres for `web`) so the import
  side can be set up correctly.
