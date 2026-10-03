---
name: new-space
description: Start a new Contour model — create its model space, draft its spec and reach a first green build. Use when starting a new model, or when the user asks for a variation of an existing one, which is a new space of its own.
---

# Start a new model space

A model is its own directory and its own git repository — a *model space* — and
it is never pushed (ADR 0015). There are no variant branches: a variation of an
existing model is a new space, not a branch of that one.

## 1. Get the intent first

Do not write anything until you have, from the user:

- **What the object is** — concrete, not a category.
- **Overall dimensions in millimetres**, with a tolerance each. If they are
  working from reference images rather than numbers, what you need instead is
  **one anchor** — a single real-world dimension for that set of images. Ask
  for it; never guess it. Pictures carry proportion, never scale, and a guessed
  scale is wrong on every dimension at once, so verify goes green on a model
  that is uniformly the wrong size and only the user at the gate would see it
  (ADR 0016). With no anchor, do not draft `dimensions` at all.
- **A triangle budget.** If the user has no number, propose one from the object
  class and the engine target, and say what you assumed.
- **Named parts** the model must contain.
- Anything prose-only that matters but cannot be measured.

If the user cannot answer a field, propose a value and mark it clearly as your
assumption. Do not invent silently — the spec is *their* intent (ADR 0002).

## 2. Name it and place it

The name is the directory name, and the spec's `model:` field must equal it —
`verify.py` fails the build otherwise. Something like `oak-chair`.

Put it under `project/` unless the user names somewhere else. This repo ignores
`project/` and the push guard blocks it. A space is found by its marker, not its
path, so a sibling directory works equally well. Run `./contour spaces` first to
see whether the name is already taken.

**A variation of an existing model gets a fresh space.** Read the old space's
`spec.yaml` and `build.py` for reference, but do not `cp -a` the space: a copy
of a space is a space, and it would list twice in `contour spaces` (ADR 0015).

## 3. Create it

`init` makes the directory in the *current* directory, so stand in its parent:

```sh
cd project && ../contour init <name>
```

It creates `.contour/project` (the marker), `refs/`, `.gitignore`, the space's
own `CLAUDE.md` and spec-guard settings, and the `build-model` and
`release-model` skills. It runs `git init` and installs a pre-push stub that
refuses every push. It writes no `spec.yaml`, `build.py` or `NOTES.md`, and it
never overwrites a scaffold file that already exists.

Then check it from inside the space:

```sh
cd <name> && contour doctor
```

Every line should say `ok`. If it warns that `contour` is not on `PATH`, fix
that before going on (the warning prints the exact `ln -s`): the spec guard
runs through `PATH`, so without it rule 1 is unenforced.

A space's `CLAUDE.md`, guard and skills load from the directory a session starts
in (ADR 0015). Do the rest from inside the space, and tell the user that a
session opened there picks up its rules and one opened in the toolkit does not.
Run git from inside the space too, never from the toolkit root.

## 4. Save the references, then draft the spec

If the user supplied reference images, save them into `refs/` *before* writing
geometry, at original fidelity. They usually arrive in a chat log, which is not
storage, and they are the one input nothing can regenerate.

Draft `spec.yaml` from `schema/spec.schema.yaml` in the toolkit (`init` prints
its path). Delete fields that genuinely do not apply and leave nothing at a
placeholder.

Start `NOTES.md` for deferred refinements and open questions, in the format of
the toolkit's `docs/OPEN-QUESTIONS.md`.

**Measure the images with `contour measure`; never recall them.** It works
mm per pixel out from the anchor and reads every other dimension off the pixels.
`beaky`'s `NOTES.md` records three claims made by eye, all wrong, all caught only
by measuring: legs called bowed that are straight, a toon render pass read as
geometry, and a beak called too long that was merely thin.

**Every number you read off a reference is a span** (ADR 0022). Draw it with
`contour measure`, and let code place its ends wherever an edge can be found:

```sh
contour measure refs/side.jpg --silhouette --extent across "depth, front to back"
contour measure refs/front.jpg --scanline 250 --of '#3B3F72' --runs 1,2 \
    --between centres "the legs, centre to centre"
```

You say *which* edges; the command says *where*. Only where nothing snaps — a
photograph of a real object, a soft gradient — place the ends yourself, with
`--by-eye --from X,Y --to X,Y`, and the span is labelled by eye wherever it shows.

**Every number in the draft names its source**, and there are three:
- a span, by id: `depth 640 ±3 (span m4)`;
- the user, who gave it;
- *not measurable*, said plainly — a depth hidden behind the body, say.

A number from an unanswered **snapped** span is listed as the agent's own
reading, beside its id. A number from an unanswered **by-eye** span is not
proposed: ask the user to answer that span on the canvas first.
`contour measure --standing <id>` says which a span is.

**Look at the worksheet once, before you propose.** When you believe your
reading is finished, run `contour worksheet` and look at `worksheet.png`: every
span drawn on its reference, with its id and its number. Check each one measures
what its label says it does. Once, at that checkpoint — not after every span.

**Propose each measured number with its error bar.** `depth 640 ±3 (span m4),
proposing tol 15` is something the user can argue with; `tol: 20` alone is not.
A tolerance says how far the build may stray from intent — it is not a place to
hide how roughly you measured. State both; only the tolerance reaches the spec
(ADR 0016).

Drafting a spec is invited here, at the user's request. *Revising* one later is
a different act with its own gate — propose, wait for confirmation, then write
it with `revision:` bumped in the same edit. List back every number you chose
rather than they did, and
**call out the tolerances first**: the user can check a dimension they gave you,
but a `tol` you invented is a goalpost they have no way to judge. Numbers carried
over from an existing model's spec are theirs; every one you changed or added is
yours. Hand the spec over to confirm **before** writing geometry — it is the
contract, and the agent does not get to author it alone.

## 5. Commit the contract before any geometry

Once the user accepts the spec, offer a first commit of `spec.yaml`, `refs/` and
the marker alone, with no `build.py` yet. History then shows the contract was
accepted before a vertex existed, which is the discipline ADR 0002 is for.
Commit only on their explicit say-so (rule 5). From that commit the spec is
tracked, the guard refuses further writes to it, and rule 1 applies in full.

## 6. First build

Start with the crudest thing that satisfies the dimensions and the parts list —
boxes in the right places, correct names, correct origin. `lib/kit.py` in the
toolkit has the helpers, and `fixtures/smoke/build.py` is a complete example in
ten lines. Get `contour check` green on structure before adding any detail. Then
`contour render`, show the user, and refine from there.

Hand off to the `build-model` skill, which the space carries, for the iterate
loop.
