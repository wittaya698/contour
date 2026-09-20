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

This writes `exports/<variant>.glb`, re-imports it into a clean headless
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

## 4. Tag and archive

On approval only. The tag is the one place a `.blend` enters git, as the
archived deliverable — insurance against a future Blender changing rebuild
behaviour (ADR 0007).

```sh
git add -f out/<variant>.blend
git add renders/<variant>.png
git commit -m "<variant>: release v<N>

verify 8/8 | tris 4,210 | glb round-trip ok"
git tag -a <variant>-v<N> -m "<variant> v<N>"
```

Note `-f`: `out/` is gitignored, and this deliberate exception is the only time
it is overridden.

## 5. Tell the user what to do with it

- `exports/<variant>.glb` is the engine file.
- `out/<variant>.blend` is the archived source asset; their `work/scene.blend`
  links its collection and is unaffected.
- State the conventions the export used (Y-up, metres for `web`) so the import
  side can be set up correctly.
