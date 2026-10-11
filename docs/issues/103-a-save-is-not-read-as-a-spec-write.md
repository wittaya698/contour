# 103 — A save is not read as a spec write

**Type:** HITL · **Source:** [issue 100](100-accept-adr-0028.md)'s tracer bullet, against ADR 0028, decisions 1 and 5 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

In `beaky-0028`, an unattended run asked to save this version made one call:

```sh
git add build.py spec.yaml sheet.png && git commit -q -F - <<'EOF'
beaky-0028: beak 10% longer (187 proud), spec revision 6
...
spec.yaml (revision 5 -> 6, user-approved): depth 615 -> 644 ...
EOF
```

It was set aside as a **spec write**, not a save. The classifier in `lib/intent.py`:

- counts any heredoc (`<<`) as a file write (`writes`), because a heredoc into an
  interpreter is how an agent edits a file;
- then reads the whole call's text for `spec.yaml` (`mentioned`), which here is
  in `git add`'s arguments and in the commit message;
- and keeps the strictest category, where a spec write outranks a commit.

So the approval's act, the run record, `status` and the chat all said *Claude
wants to change the spec*. The page did not show the files the save would take
in, which it builds only for a commit. A deny would have recorded a spec-write
veto for what was a save.

Nothing was let through that should have waited: a spec write is on the floor
as a save is. The fault is in the words, and in everything downstream that
trusts the category.

## Options (to decide)

The classifier is the guard on the gates that matter most, so loosening it is a
decision and not a fix:

- A heredoc that only feeds a program's input (`git commit -F -`, `cat | ...`
  with no redirect to a file) is not a write; one into an interpreter or a
  `> file` still is.
- Or: a call that carries a commit, and writes nothing beyond what `git add`
  stages, is read as a save, whatever its message mentions.
- Or: keep the strictest category for the gate, and have the approval name
  every category the call carries (*save this version, which includes a spec
  change*), so the words are never wrong even when the ranking is cautious.

## Acceptance criteria

- [ ] A save whose message or staged files mention `spec.yaml` is shown, recorded and vetoed as a save
- [ ] A shell call that does write `spec.yaml`, by heredoc or otherwise, is still a spec write
- [ ] Nothing the floor holds today is let through
