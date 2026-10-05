# 70 — A plain lobby and a plain gate, and ADR 0025 is accepted

**Type:** HITL · **Source:** ADR 0025, the tracer bullet — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

ADR 0025 used by hand and given its verdict. Open the lobby: `beaky` is a picture
with *matches the spec*, a never-built model shows a reference and *not built
yet*, and no row says toolkit or commits. Enter a throwaway model's console, start
a run, and meet the first build gate: it says what Claude wants in plain words.
Choose *Always for this model*, see the next build run without asking, see it
listed, undo it, and see the gate come back.

**Accept, amend or withdraw** ADR 0025 on what that shows.

## Acceptance criteria

- [ ] The lobby is read without a glossary word from the hidden tier
- [ ] The first build gate is plain, and Always stops the next one
- [ ] Undo brings the gate back
- [ ] ADR 0025's status says accepted, amended or withdrawn, with the evidence

## Blocked by

- [67](67-a-lobby-row-is-a-picture-and-a-verdict.md)
- [69](69-always-for-this-model.md)
