# 107 — A refusal says where the case goes, and a request sends nobody to a page

**Type:** AFK · **Source:** [issue 106](106-the-case-is-whatever-was-said-last.md)'s first real run, against rule 1 and ADR 0028, decisions 1 and 6 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

Run `d85a0bb6` in `beaky-0028`, requested from Desktop: *make the beak 10%
longer*. Its `Edit` of `spec.yaml` came with no text before it, and issue 106's
refusal named *644*. It retried the same `Edit`, again with no text before it,
and was refused again. A read-only script that read `spec.yaml` was then taken
for a spec write, and issue 101's refusal asked for the case *naming the span*.
There was no span: the user had asked for the change. The agent concluded one
was needed, and stopped. Only a build waited.

So the refusals said *in your text just before it*, and the agent did not take
that to mean words in its reply ahead of the call. And *naming the span* told it
a span is always needed, when rule 1 asks for one only where a number is read
off a reference.

And the chat called `open` two seconds after `request` again. The request tool
still said *where it stops for the user, its console has the page*, and its
reply said nothing about what to do next.

## Decided

- **Every spec-write refusal says where the case goes:** as text in the reply,
  before the tool call. Issues 101 and 104's name the span only *if you measured
  one*.
- **A started request says there is nothing to open:** what needs the user is
  set aside, and `status` says when something waits. The `request` tool no
  longer points at the page.

Noted, not changed: a script that only reads `spec.yaml` is classified as a spec
write, so 101's refusal meets it. Where that line falls is issue 103's narrow
decision, and the user's to reopen.

## Acceptance criteria

- [x] Each spec-write refusal says to put the case as text in the reply before the call, and none asks for a span unless one was measured
- [x] A started request says there is nothing to open, and the request tool does not point the chat at the console
