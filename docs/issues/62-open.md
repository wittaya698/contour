# 62 — `open`

**Type:** AFK · **Source:** ADR 0024, decision 5 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

A connector tool that opens the page where the user acts, and says only that it
did.

`open console` is the lobby's **enter**: the same function, the same refusals in
the same words — a space a console already serves, or no console environment. The
connector never sees the console's URL, so the secret behind every gate never
enters a conversation with an agent.

`open lobby` and `open canvas` start their commands detached and return at once;
Done is the user's, on the page. `open canvas` has one refusal of the connector's
own: a space a console serves gets no canvas — *already open in a console; its page
can mark* — because a second page would add a second writer to `marks.json` and
nothing else.

## Acceptance criteria

- [ ] `open console` starts a console through the lobby's own path, and refuses in the lobby's words
- [ ] `open lobby` and `open canvas` return before the page is done, and their processes outlive the connector
- [ ] `open canvas` on a space a console serves refuses, and says why
- [ ] No result of `open` contains a URL, a port or a token

## Blocked by

- [57](57-the-connector-answers-spaces.md)
