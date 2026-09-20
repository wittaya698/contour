---
name: new-variant
description: Create a new model variant in Contour — its branch, spec and build script. Use when starting a new model, or when the user asks for a variation that should live alongside an existing one.
---

# Start a new variant

A variant is one model on its own long-lived branch. Variants coexist
permanently and never merge back (ADR 0003).

## 1. Get the intent first

Do not write anything until you have, from the user:

- **What the object is** — concrete, not a category.
- **Overall dimensions in millimetres**, with a tolerance each.
- **A triangle budget.** If the user has no number, propose one from the object
  class and the engine target, and say what you assumed.
- **Named parts** the model must contain.
- Anything prose-only that matters but cannot be measured.

If the user cannot answer a field, propose a value and mark it clearly as your
assumption. Do not invent silently — the spec is *their* intent (ADR 0002).

## 2. Branch

```sh
git checkout master
git pull            # if a remote exists
git checkout -b <variant>
```

The branch name, the `model:` field, and the directory under `models/` must all
be the same string.

## 3. Write one directory

```
models/<variant>/
    spec.yaml     from schema/spec.schema.yaml
    refs/         whatever images the user gave you, at original fidelity
    build.py
    NOTES.md      deferred refinements, and open questions in the
                  docs/OPEN-QUESTIONS.md format
```

**Nothing outside it.** A variant branch that touches `lib/`, `verify.py`,
`schema/`, `.claude/` or `docs/` breaks the conflict-free merge guarantee
(ADR 0012).

If the user supplied reference images, save them into `refs/` *before* writing
geometry. They usually arrive in a chat log, which is not storage, and they are
the one input nothing can regenerate.

Fill the spec from `schema/spec.schema.yaml`, deleting fields that genuinely do
not apply and leaving nothing at a placeholder value. Then hand the spec to the
user to confirm **before** writing geometry — it is the contract, and the agent
does not get to author it alone.

Writing a spec is the one time hard rule 1 permits creating one, and only at
the user's request. List back every number you chose rather than they did, and
**call out the tolerances first**: the user can check a dimension they gave you,
but a `tol` you invented is a goalpost they have no way to judge. From its first
commit the file is theirs, and rule 1 applies to it in full.

## 4. First build

Start with the crudest thing that satisfies the dimensions and the parts list —
boxes in the right places, correct names, correct origin. Get
`./contour check <variant>` green on structure before adding any detail. Then
render, show the user, and refine from there.

Hand off to the `build-model` skill for the iterate loop.
