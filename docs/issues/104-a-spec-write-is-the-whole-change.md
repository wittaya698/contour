# 104 — A spec write is the whole change, and a request opens nothing

**Type:** AFK · **Source:** [issue 102](102-an-unattended-agent-tries-the-write.md)'s first real run, against ADR 0028, decisions 1 and 6 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

In `beaky-0028`, a run requested from a fresh Desktop chat to make the beak 10%
longer tried the spec write, as rule 1 now says. Its first `Edit` moved only
`revision: 5` → `revision: 6`, meaning to write depth and the beak note in later
`Edit`s. That one was set aside, the agent was told not to try it another way,
and it stopped. So the page showed *Claude wants to change the spec* with nothing
under it and *Claude gave no case for this*: allowing it would have bumped the
revision and changed nothing. Rule 1 already asks for the bump *in that same
write*.

And the console opened in the browser two seconds after the request. The
connector's instructions still said *To change a model, open its console*, a line
older than `request`, which tells the chat to open the console on every request
to change something, against ADR 0028, decision 6: the console is opened when
the person says *now*.

## Decided

- **A spec write that moves only `revision:`, or moves a field without moving
  `revision:`, is refused** in every console run, before the ask-list, as issue
  101 refuses one made by script. The agent is told to make the whole change,
  revision bump included, as one `Edit`, or a `Write` of the whole spec, with
  its case just before it. A write whose diff cannot be read (an `Edit` whose
  old text is not in the spec, a spec that does not parse) is left to the gate,
  as it is today.
- **The connector's third line** says to change a model by requesting a run in
  it, and to open its console only when the user asks to watch, or says *now*
  to approvals waiting.

## Acceptance criteria

- [x] A spec write of the revision alone is refused, and so is one that moves a field and not the revision, in a run watched or not
- [x] One `Edit` that moves a field and the revision is still set aside, with its diff
- [x] The connector no longer tells a chat to open the console to change a model
