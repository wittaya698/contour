# 125 — The labelling act says how it ended

**Type:** AFK · **Source:** found in flight, issue 120; issue [118](118-the-lobby-labels-the-unlabelled.md)

## What to build

Three defects in the lobby's labelling act, met on its first real use:

- An act that dies having set nothing aside leaves the page waiting with no word;
  the first click on the copies did, and looked frozen. The page says it ended
  and what it said on the way out.
- With every unlabelled space skipped, the act still starts the agent on an empty
  list, which then searches its empty directory for sheets. It proposes for
  nothing, says so, and starts no agent.
- Every act, test runs included, leaves its empty `contour-label-*` working
  directory behind; about 130 were found. It removes it.

## Acceptance criteria

- [ ] An act that exits with nothing set aside is shown on the page as ended, with its reason
- [ ] An act with no space to propose for starts no agent and says why
- [ ] No act leaves its working directory behind

## Blocked by

None - can start immediately
