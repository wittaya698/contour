# 108 — Thinking is not said, and a request is not a spec

**Type:** AFK, and one HITL decision · **Source:** [issue 107](107-a-refusal-says-where-the-case-goes.md)'s first real run, against rule 1 and ADR 0028, decision 1 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

Run `889417cd` in a fresh `beaky-0028`, requested from Desktop: *make the beak
10% longer and save the model*. It lengthened the beak in `build.py`, and its
`contour check` was set aside as a build. It then tried the spec write as one
`Edit`, revision 5 → 6 and depth 615 → 632 ±20, and issue 106 refused it twice:
*your case names what it sets: 632; say why, with them, as text in your reply,
before the tool call*.

Neither time had it written any text, before the call or anywhere in the run.
Its reasoning for the change was all in its thinking, which the gate does not
see and the person is not shown. Its closing said it had given its reasoning in
the reply, and argued the change there, where the page does not put it.

So *as text in your reply* (issue 107) was not enough either: the agent took its
thinking for its reply.

The chat that requested the run also wrote the spec change into the request:
*update the spec's depth target to match (about 632±20) … so the model stays
green*. And for the first time it did not open the console after `request`, so
issue 107's change to the request tool held.

## Decided

- **A refusal for a spec write with no text before it says so:** the agent has
  written nothing the person can read, and its thinking is not shown to them, so
  the case goes in words in its reply. The gate can tell, since the run has no
  text at all. Whether the case is argued well remains the person's to judge.

## To decide (the user's)

- **A request that prescribes a spec's numbers.** The requesting chat named the
  new depth and tolerance so the check would stay green. Rule 1 calls that
  moving the goalposts, and it needs the user's confirmation, but here the
  number came from the chat, not from the user or a span. Options: leave it,
  since the spec write still waits for the person; or have the request tool say
  that a request asks for a change to the model, and a spec change is argued
  in the run and confirmed by the user.

## What the next runs did

- **Run `8af4cd7e`, requested as *make the beak 10% longer and save the model*,
  with no numbers:** the agent lengthened the beak, its build was set aside, and
  with nothing measured it asked in its closing rather than trying the write.
  The build, allowed on the page, read depth 648.5 against 615 ±20.
- **The chat then opened the canvas** when the user said yes: the connector told
  it every spec change is *argued from a span the user can see on the canvas*.
- **Run `2c982b0d`, requested with the chat's numbers** (648, and the beak note
  at ~187 proud, which the agent found wrong: 191.5): the agent tried the write
  as one `Write`, and this issue's refusal met it twice. Both times it retried
  with no text at all, its case, naming 648.5 and the user's request, in its
  thinking. It closed saying *my reason was written just before each attempt*.

So a refusal's wording does not reach it, three wordings in. Filed as
[issue 109](109-a-spec-write-carries-its-case.md) and
[ADR 0029](../adr/0029-a-spec-write-carries-its-case.md): the case becomes an
argument of the write, and this refusal goes with the text it pointed at.

## Decided (the user's)

**A request names no spec numbers.** The request tool says a request is what the
user wants of the model, in their words, and may change the spec, but never
names its new numbers: the run argues them, and the user confirms them on the
page. And the connector's line on spec changes says a span is needed for a
number read off a reference, and a change the user asked for needs none.

## Acceptance criteria

- [x] A spec write refused when no text was written in the run says the thinking is not shown, and to write the case as a reply
- [x] The user has decided whether a request may name a spec's new numbers
