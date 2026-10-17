# 129 — The transcript reads in tiers

**Type:** AFK · **Source:** design session 2026-10-17; ADR 0025, decision 8

## What to build

Every transcript line is 12px, and only the prompt (bold) and a gate
(bordered) stand out. The agent's words, the thing a person reads, look like
the activity lines between them, which are there to skim. The transcript gets
five tiers, loudest first:

| Tier | Lines | Looks like |
|---|---|---|
| 1. Waiting for you | gate, question | unchanged: red border, red act. Nothing else outshouts it. |
| 2. The agent's words | `text` | body size (14px), full colour, a 2px rule in `--agent` on the left |
| 3. What you asked | `prompt`, `asked` | 13px, normal weight, a rule in `--line` on the left |
| 4. What it did | activity, `seeds`, `refused` | 12px, muted, as now |
| 5. Bookkeeping | `ended`, `limit`, `resolved`, `verdict`, spend | 11px, muted; `ended` has a hairline above it so a run visibly closes |

The two colours already mean something on this page, and this adds no other:
`--pin` is *stop and look*, and `--agent` is *Claude wrote this*, the colour
of the agent's marks. The prompt loses its bold, so that bold inside a line
only ever means the agent stressed it (issue 128). No backgrounds and no chat
bubbles: it is a log, half a page wide.

## Acceptance criteria

- [ ] The agent's words are set at body size with an `--agent` rule; the prompt has a `--line` rule and no bold
- [ ] Activity lines are unchanged; bookkeeping lines are smaller than activity
- [ ] A gate waiting is still the only red-bordered line in the transcript
- [ ] No colour is added to `lib/look.css` or `lib/canvas.html`

## Blocked by

None - can start immediately
